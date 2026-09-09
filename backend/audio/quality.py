"""Audio quality gate (spec §20).

INPUT:   standardized mono 16 kHz waveform
MATH:    duration, speech presence (energy VAD-like), estimated SNR (ITU-style
         active/noise floor split), clipping ratio, silence ratio, DC offset
OUTPUT:  {state: GOOD|FAIR|POOR|UNUSABLE, metrics{...}, issues[]}
ERRORS:  UNUSABLE is a truthful state, not an error — pipeline must stop and
         report INCONCLUSIVE when quality is UNUSABLE (spec §20/§34).

Quality affects ANALYSIS CONFIDENCE, never fabricates detector values.
"""
from __future__ import annotations

import numpy as np


def frame_energy(x: np.ndarray, sr: int, frame_ms: float = 20.0) -> np.ndarray:
    fl = max(1, int(sr * frame_ms / 1000))
    n = (x.size // fl) * fl
    if n == 0:
        return np.array([float(np.mean(x ** 2))])
    fr = x[:n].reshape(-1, fl)
    return np.mean(fr.astype(np.float64) ** 2, axis=1)


def estimate_snr(x: np.ndarray, sr: int) -> float:
    """Estimate SNR (dB) via energy-percentile split. Supporting metric only."""
    e = frame_energy(x, sr)
    if e.size < 4:
        return 0.0
    p95 = np.percentile(e, 95)
    p10 = np.percentile(e, 10)
    noise = max(p10, 1e-10)
    active = max(p95, 1e-10)
    return float(round(10.0 * np.log10(active / noise), 2))


def analyze_quality(x: np.ndarray, sr: int) -> dict:
    issues: list[str] = []
    dur = x.size / sr
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) if x.size else 0.0

    # Clipping: samples at/near full scale
    clip_ratio = float(np.mean(np.abs(x) >= 0.985)) if x.size else 0.0
    if clip_ratio > 0.03:
        issues.append("Severe clipping detected (waveform hits full scale frequently).")
    elif clip_ratio > 0.005:
        issues.append("Some clipping present.")

    # Silence ratio via energy threshold relative to frame energies
    e = frame_energy(x, sr)
    thresh = (np.percentile(e, 20) * 0.1) if e.size else 0.0
    silence_ratio = float(np.mean(e <= max(thresh, 1e-9))) if e.size else 1.0

    snr = estimate_snr(x, sr)

    # Speech presence: share of frames with meaningful energy
    active_ratio = float(np.mean(e > max(np.percentile(e, 50) * 0.25, 1e-8))) if e.size else 0.0

    if rms < 1e-4 and peak < 1e-3:
        issues.append("Audio is effectively silent.")
    if dur < 1.0:
        issues.append("Audio is extremely short (<1 s).")

    # --- State decision (deterministic, configurable later if needed) ---
    if dur < 0.2 or (rms < 1e-4 and peak < 1e-3):
        state = "UNUSABLE"
    elif dur < 1.0 or clip_ratio > 0.10 or active_ratio < 0.05:
        state = "POOR"
    elif clip_ratio > 0.03 or snr < 8 or active_ratio < 0.12 or silence_ratio > 0.7:
        state = "FAIR"
    else:
        state = "GOOD"

    if snr < 12 and state == "GOOD":
        state = "FAIR"
        issues.append("Moderate background noise (low estimated SNR).")

    return {
        "state": state,
        "metrics": {
            "duration_sec": round(dur, 3),
            "peak_amplitude": round(peak, 4),
            "rms": round(rms, 6),
            "clipping_ratio": round(clip_ratio, 5),
            "silence_ratio": round(silence_ratio, 3),
            "active_ratio": round(active_ratio, 3),
            "estimated_snr_db": snr,
            "sample_rate": sr,
            "channels": 1,
        },
        "issues": issues,
    }
