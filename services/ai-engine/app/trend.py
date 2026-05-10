"""Trend detection — sliding window slope on a series of observations."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

import numpy as np


def detect_trend(points: Iterable[tuple[datetime, float]], window: int = 6) -> dict:
    pts = sorted(points, key=lambda p: p[0])[-window:]
    if len(pts) < 3:
        return {"trend": "insufficient_data", "slope": 0.0, "samples": len(pts)}
    xs = np.array([p[0].timestamp() for p in pts], dtype=float)
    ys = np.array([p[1] for p in pts], dtype=float)
    xs -= xs[0]
    if xs[-1] == 0:
        return {"trend": "flat", "slope": 0.0, "samples": len(pts)}
    slope, _ = np.polyfit(xs, ys, 1)
    rel = float(slope) * (xs[-1] - xs[0]) / (np.mean(ys) or 1)
    if rel > 0.1:
        label = "worsening_up"
    elif rel < -0.1:
        label = "worsening_down"
    else:
        label = "stable"
    return {"trend": label, "slope": float(slope), "samples": len(pts)}
