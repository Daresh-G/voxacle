"""Frequency-domain analysis via FFT (spec §15).

INPUT:   waveform segment x[n]
MATH:    X[k] = Σ x[n]·e^(-j2πkn/N)  (numpy FFT)
OUTPUT:  magnitude spectrum (downsampled for transport), peak frequency
ROLE:    shows how energy is distributed across frequencies; supporting
         evidence only.
"""
from __future__ import annotations

import numpy as np

MAX_BINS = 256  # transport-friendly spectrum resolution


def magnitude_spectrum(x: np.ndarray, sr: int) -> dict:
    if x.size < 16:
        return {"freqs": [], "mags": [], "peak_freq_hz": None}
    win = np.hanning(x.size)
    spec = np.fft.rfft(x * win)
    mags = np.abs(spec) / max(1, x.size // 2)
    freqs = np.fft.rfftfreq(x.size, d=1.0 / sr)

    # log-ish compression for stable visualization
    mags_db = 20.0 * np.log10(mags + 1e-12)

    # downsample to MAX_BINS by max-pooling
    if mags_db.size > MAX_BINS:
        pad = (-mags_db.size) % MAX_BINS
        padded = np.pad(mags_db, (0, pad), constant_values=mags_db.min())
        pooled = padded.reshape(MAX_BINS, -1).max(axis=1)
        fpad = np.pad(freqs, (0, pad), constant_values=freqs[-1])
        pfreqs = fpad.reshape(MAX_BINS, -1).max(axis=1)
    else:
        pooled, pfreqs = mags_db, freqs

    k = int(np.argmax(mags))
    return {
        "freqs": [round(float(f), 1) for f in pfreqs],
        "mags": [round(float(m), 2) for m in pooled],
        "peak_freq_hz": round(float(freqs[k]), 1),
    }


def analyze(x: np.ndarray, sr: int) -> dict:
    ms = magnitude_spectrum(x, sr)
    return {
        "spectrum": ms,
        "nyquist_hz": sr // 2,
    }
