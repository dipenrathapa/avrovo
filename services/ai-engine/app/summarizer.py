"""LLM summarizer with deterministic fallback (graceful degradation)."""
from __future__ import annotations

import os

import httpx
import pybreaker
from tenacity import retry, stop_after_attempt, wait_exponential

PROVIDER = os.getenv("LLM_PROVIDER", "mock")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

llm_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=60)


def _fallback(patient: dict, risk: dict, trend: dict) -> str:
    name = patient.get("name", "the patient")
    sev = risk.get("severity", "LOW")
    factors = ", ".join(risk.get("contributing_factors", [])[:4]) or "no notable factors"
    direction = trend.get("trend", "stable").replace("_", " ")
    return (
        f"{name} is currently at {sev} risk (score {risk.get('score', 0)}/100). "
        f"Vitals trend: {direction}. Notable: {factors}."
    )


@llm_breaker
@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=0.5, max=3))
async def _call_openai(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a clinical summary assistant for family caregivers. Be brief, plain-language, non-diagnostic."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def summarize(patient: dict, risk: dict, trend: dict) -> str:
    prompt = (
        f"Patient: {patient}\nRisk: {risk}\nTrend: {trend}\n"
        "Write 2-3 sentences for a family member."
    )
    if PROVIDER == "openai" and OPENAI_KEY:
        try:
            return await _call_openai(prompt)
        except Exception:
            return _fallback(patient, risk, trend)
    return _fallback(patient, risk, trend)
