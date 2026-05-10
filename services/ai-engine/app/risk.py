"""Risk scoring — deterministic, unit-testable.

Inputs: latest observations (code -> value), active conditions, active meds.
Output: score 0..100, severity bucket, contributing factors.
"""
from __future__ import annotations

from shared.fhir_models import RiskScore, Severity

# Reference adult ranges (simplified). Out-of-range values increment risk.
RANGES: dict[str, tuple[float, float, float]] = {
    # code: (low, high, weight)
    "heart_rate": (60, 100, 8),
    "spo2":       (95, 100, 12),
    "systolic":   (90, 130, 8),
    "diastolic":  (60, 85, 6),
    "glucose":    (70, 140, 10),
    "temp_c":     (36.1, 37.5, 6),
    "respiratory_rate": (12, 20, 6),
}

HIGH_RISK_CONDITIONS = {"heart_failure", "copd", "ckd", "diabetes", "stroke"}


def compute_risk(latest: dict[str, float], conditions: list[str], meds: list[str]) -> RiskScore:
    score = 0.0
    factors: list[str] = []

    for code, value in latest.items():
        rng = RANGES.get(code)
        if not rng:
            continue
        low, high, weight = rng
        if value < low:
            delta = (low - value) / max(low, 1)
            score += weight * min(delta * 4, 1.5)
            factors.append(f"{code} low ({value})")
        elif value > high:
            delta = (value - high) / max(high, 1)
            score += weight * min(delta * 4, 1.5)
            factors.append(f"{code} high ({value})")

    for c in conditions:
        if c.lower() in HIGH_RISK_CONDITIONS:
            score += 8
            factors.append(f"condition:{c}")

    if len(meds) >= 5:
        score += 5
        factors.append("polypharmacy")

    score = max(0.0, min(100.0, score))
    if score >= 60:
        sev = Severity.high
    elif score >= 30:
        sev = Severity.medium
    else:
        sev = Severity.low

    # patient_id filled by caller
    return RiskScore(patient_id="00000000-0000-0000-0000-000000000000", score=round(score, 1), severity=sev, contributing_factors=factors)
