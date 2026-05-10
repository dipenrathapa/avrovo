import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from datetime import datetime, timedelta

import pytest
from hypothesis import given, strategies as st

from app.risk import compute_risk
from app.trend import detect_trend


def test_normal_vitals_low_risk():
    r = compute_risk({"heart_rate": 75, "spo2": 98, "systolic": 120, "glucose": 100}, [], [])
    assert r.severity.value == "LOW"
    assert r.score < 30


def test_critical_spo2_drives_high_risk():
    r = compute_risk({"spo2": 80, "heart_rate": 130, "systolic": 180}, ["heart_failure"], ["a", "b", "c", "d", "e"])
    assert r.severity.value == "HIGH"
    assert r.score >= 60
    assert any("spo2" in f for f in r.contributing_factors)


def test_unknown_codes_ignored():
    r = compute_risk({"unknown_code": 9999}, [], [])
    assert r.score == 0


def test_trend_insufficient_data():
    assert detect_trend([])["trend"] == "insufficient_data"


def test_trend_worsening_up():
    now = datetime.utcnow()
    pts = [(now + timedelta(minutes=i), 100 + i * 5) for i in range(6)]
    out = detect_trend(pts)
    assert out["trend"] == "worsening_up"


def test_trend_stable():
    now = datetime.utcnow()
    pts = [(now + timedelta(minutes=i), 100) for i in range(6)]
    assert detect_trend(pts)["trend"] in {"stable", "flat"}


@given(hr=st.floats(min_value=20, max_value=220, allow_nan=False))
def test_risk_score_bounds(hr):
    r = compute_risk({"heart_rate": hr}, [], [])
    assert 0 <= r.score <= 100
