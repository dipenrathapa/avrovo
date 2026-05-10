"""Auth service — JWT + RBAC + audit log. Argon2id password hashing."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum

import structlog
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from jose import jwt
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, DateTime, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

log = structlog.get_logger()
DB_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./auth.db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
ACCESS_TTL = int(os.getenv("JWT_ACCESS_TTL_MIN", "15"))

ph = PasswordHasher()
engine = create_async_engine(DB_URL, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Role(str, Enum):
    patient = "patient"
    family = "family"
    admin = "admin"


class UserRow(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default=Role.family.value)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditRow(Base):
    __tablename__ = "audit_log"
    id = Column(String, primary_key=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    target = Column(String, nullable=True)
    ip = Column(String, nullable=True)
    at = Column(DateTime, default=datetime.utcnow)


class SignupBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Role = Role.family


class LoginBody(BaseModel):
    email: EmailStr
    password: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Avrovo Auth Service", lifespan=lifespan)


async def db():
    async with SessionLocal() as s:
        yield s


async def audit(
    s: AsyncSession, actor: str, action: str, target: str | None, ip: str | None
):
    import uuid

    s.add(
        AuditRow(id=str(uuid.uuid4()), actor=actor, action=action, target=target, ip=ip)
    )
    await s.commit()


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/auth/signup", status_code=201)
async def signup(body: SignupBody, request: Request, s: AsyncSession = Depends(db)):
    import uuid

    existing = (
        await s.execute(select(UserRow).where(UserRow.email == body.email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "email taken")
    uid = str(uuid.uuid4())
    s.add(
        UserRow(
            id=uid,
            email=body.email,
            password_hash=ph.hash(body.password),
            role=body.role.value,
        )
    )
    await s.commit()
    await audit(
        s,
        actor=uid,
        action="signup",
        target=body.email,
        ip=request.client.host if request.client else None,
    )
    return {"id": uid, "email": body.email, "role": body.role.value}


@app.post("/auth/login")
async def login(body: LoginBody, request: Request, s: AsyncSession = Depends(db)):
    user = (
        await s.execute(select(UserRow).where(UserRow.email == body.email))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(401, "invalid credentials")
    try:
        ph.verify(user.password_hash, body.password)
    except VerifyMismatchError:
        await audit(
            s,
            actor=user.id,
            action="login_fail",
            target=body.email,
            ip=request.client.host if request.client else None,
        )
        raise HTTPException(401, "invalid credentials")
    token = jwt.encode(
        {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TTL),
        },
        JWT_SECRET,
        algorithm=JWT_ALG,
    )
    await audit(
        s,
        actor=user.id,
        action="login_success",
        target=body.email,
        ip=request.client.host if request.client else None,
    )
    return {"access_token": token, "token_type": "bearer", "role": user.role}


@app.get("/auth/me")
async def me(request: Request):
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "missing token")
    try:
        claims = jwt.decode(auth.split(" ", 1)[1], JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(401, "invalid token")
    return claims
