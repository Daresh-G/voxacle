"""MFCC feature extraction (spec §18).

Pipeline: WAVEFORM → FFT → POWER SPECTRUM → MEL FILTER BANK → LOG → DCT → MFCC
Frontend framing: "MFCC features contribute supporting acoustic evidence."
(never "MFCC detects AI").
"""
from __future__ import annotations

import numpy as np
import librosa

MAX_MFCC_TIME = 120


def mfcc_data(x: np.ndarray, sr: int, n_mfcc: int = 13) -> dict:
    y = x.astype(np.float32)
    if y.size < 1024:
        y = np.pad(y, (0, 1024 - y.size))
    M = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    t_frac = min(1.0, MAX_MFCC_TIME / M.shape[1])
    if t_frac < 1.0:
        idx = np.round(np.linspace(0, M.shape[1] - 1, max(2, int(M.shape[1] * t_frac)))).astype(int)
        M = M[:, idx]
    return {
        "coefficients": [[round(float(v), 3) for v in row] for row in M],
        "n_mfcc": n_mfcc,
        "frames": int(M.shape[1]),
    }


def summarize(x: np.ndarray, sr: int) -> dict:
    """Scalar MFCC statistics used as supporting evidence inputs."""
    y = x.astype(np.float32)
    if y.size < 1024:
        y = np.pad(y, (0, 1024 - y.size))
    M = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    c1 = M[1]
    # temporal variability of low-order coefficients (supporting evidence)
    return {
        "mfcc_c1_mean": round(float(np.mean(c1)), 4),
        "mfcc_c1_std": round(float(np.std(c1)), 4),
        "mfcc_delta_mean": round(float(np.mean(np.abs(np.diff(M, axis=1)))) if M.shape[1] > 1 else 0.0, 5),
    }


def analyze(x: np.ndarray, sr: int) -> dict:
    out = summarize(x, sr)
    out["matrix"] = mfcc_data(x, sr)
    return out
