"""FHIR-inspired Pydantic v2 models shared across services."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"
    unknown = "unknown"


class Severity(str, Enum):
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"


class Patient(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=200)
    age: int = Field(ge=0, le=130)
    gender: Gender = Gender.unknown
    conditions: list[str] = Field(default_factory=list)
    family_id: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MedicationRequest(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID
    drug: str = Field(min_length=1, max_length=200)
    dosage: str = Field(min_length=1, max_length=100)
    frequency: str = Field(min_length=1, max_length=100)
    start: datetime
    end: Optional[datetime] = None
    status: str = "active"

    @field_validator("end")
    @classmethod
    def end_after_start(cls, v, info):
        if v and v < info.data.get("start"):
            raise ValueError("end must be after start")
        return v


class Observation(BaseModel):
    """LOINC-like coded measurement."""

    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID
    code: str = Field(min_length=1, max_length=50)  # e.g. heart_rate, glucose, spo2
    value: float
    unit: str = Field(min_length=1, max_length=20)
    effective_at: datetime = Field(default_factory=datetime.utcnow)


class Encounter(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID
    type: str = Field(pattern="^(admission|discharge|visit|emergency)$")
    start: datetime
    end: Optional[datetime] = None
    location: str = ""


class RiskScore(BaseModel):
    patient_id: UUID
    score: float = Field(ge=0, le=100)
    severity: Severity
    contributing_factors: list[str] = Field(default_factory=list)
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class AlertEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID
    severity: Severity
    title: str
    body: str
    raised_at: datetime = Field(default_factory=datetime.utcnow)


# --- Event envelope used on Kafka ---------------------------------------------


class EventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    payload: dict
