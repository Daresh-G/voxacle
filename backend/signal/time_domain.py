"""Time-domain DSP analysis (spec §11-§14).

INPUT:   mono waveform x[n]
MATH:    RMS = sqrt((1/N) Σ x[n]²) · E = Σ x[n]² · ZCR = (1/(N-1)) Σ I(x[n]x[n-1]<0)
OUTPUT:  per-metric values + curves for frontend visualization
ROLE:    supporting signal evidence ONLY — never standalone proof of cloning.
"""
from __future__ import annotations

import numpy as np


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) if x.size else 0.0


def signal_energy(x: np.ndarray) -> float:
    return float(np.sum(x.astype(np.float64) ** 2)) if x.size else 0.0


def zero_crossing_rate(x: np.ndarray) -> float:
    if x.size < 2:
        return 0.0
    return float(np.mean(x[1:] * x[:-1] < 0))


def rms_curve(x: np.ndarray, sr: int, frame_ms: float = 25.0, hop_ms: float = 10.0) -> dict:
    fl = max(1, int(sr * frame_ms / 1000))
    hp = max(1, int(sr * hop_ms / 1000))
    n = 1 + max(0, (x.size - fl)) // hp
    if n <= 0:
        return {"times": [], "values": []}
    idx = np.arange(n)[:, None] * hp + np.arange(fl)[None, :]
    fr = x[np.clip(idx, 0, x.size - 1)].astype(np.float64)
    vals = np.sqrt(np.mean(fr ** 2, axis=1))
    times = (np.arange(n) * hp / sr).tolist()
    return {"times": [round(t, 3) for t in times], "values": [round(float(v), 6) for v in vals]}


def analyze(x: np.ndarray, sr: int) -> dict:
    """Full time-domain metric set for one analysis segment."""
    x64 = x.astype(np.float64)
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    return {
        "rms": round(rms(x), 6),
        "energy": round(signal_energy(x), 4),
        "zcr": round(zero_crossing_rate(x), 5),
        "peak_amplitude": round(peak, 5),
        "dc_offset": round(float(np.mean(x64)), 7),
        "duration_sec": round(x.size / sr, 3),
    }
