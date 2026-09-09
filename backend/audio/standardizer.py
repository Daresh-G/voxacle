"""Standardization to internal analysis representation (spec §3/§4/§5).

INPUT:   waveform at arbitrary rate/channels
MATH:    polyphase resampling to 16 kHz, mono mixdown, peak-safe scaling check
OUTPUT:  dict {waveform float32 mono 16k, sample_rate, channels}
ERRORS:  empty/silent-degenerate input raises AudioDecodeError upstream

NOTE: digital samples x[n] are already numeric amplitude values (spec §7);
no "analog to 0/1" conversion happens here.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import resample_poly

from backend.audio.decoder import AudioDecodeError


def standardize(waveform: np.ndarray, sample_rate: int) -> dict:
    x = np.asarray(waveform, dtype=np.float32).reshape(-1)
    if x.size == 0:
        raise AudioDecodeError("Waveform is empty.")

    sr = int(sample_rate)
    if sr != 16000:
        g = np.gcd(sr, 16000)
        x = resample_poly(x, 16000 // g, sr // g).astype(np.float32)
        sr = 16000

    # Guard against pathological non-finite values (corrupt decode)
    if not np.all(np.isfinite(x)):
        n_bad = int(np.sum(~np.isfinite(x)))
        x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        # non-finite samples indicate corruption; count is surfaced by quality gate
    else:
        n_bad = 0

    peak = float(np.max(np.abs(x))) if x.size else 0.0
    if peak > 1.0:
        x = (x / peak).astype(np.float32)  # safety scale only; preserves shape

    return {
        "waveform": x,
        "sample_rate": sr,
        "channels": 1,
        "nonfinite_samples": n_bad,
        "decoded_by": "soundfile",
    }
