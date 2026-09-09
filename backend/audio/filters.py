"""Conservative optional filtering (spec §21).

Filtering is OPTIONAL and conservative: aggressive filtering may destroy the
very artifacts that constitute synthetic-speech evidence. Only gentle DC/rumble
removal is applied by default; everything else is opt-in.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt


def highpass(x: np.ndarray, sr: int, cutoff_hz: float = 60.0, order: int = 4) -> np.ndarray:
    sos = butter(order, cutoff_hz, btype="highpass", fs=sr, output="sos")
    return sosfilt(sos, x).astype(np.float32)


def lowpass(x: np.ndarray, sr: int, cutoff_hz: float = 7600.0, order: int = 4) -> np.ndarray:
    sos = butter(order, cutoff_hz, btype="lowpass", fs=sr, output="sos")
    return sosfilt(sos, x).astype(np.float32)


def bandpass(x: np.ndarray, sr: int, lo: float = 60.0, hi: float = 7600.0) -> np.ndarray:
    sos = butter(4, [lo, hi], btype="bandpass", fs=sr, output="sos")
    return sosfilt(sos, x).astype(np.float32)


def default_preprocess(x: np.ndarray, sr: int) -> tuple[np.ndarray, list[str]]:
    """Minimal, evidence-preserving preprocessing: DC offset / infrasonic rumble."""
    ops: list[str] = []
    dc = float(np.mean(x))
    if abs(dc) > 1e-4:
        x = x - dc
        ops.append("DC offset removed")
    if sr >= 16000:
        x = highpass(x, sr, 50.0)
        ops.append("Gentle 50 Hz high-pass (rumble removal)")
    return x.astype(np.float32), ops
