"""Spectral feature analysis (spec §16-§17) + spectrogram transport (STFT).

INPUT:   waveform segment
MATH:    STFT X(m,k) = Σ x[n]·w[n-mH]·e^(-j2πkn/N);
         centroid C = Σ f[k]·M[k] / Σ M[k]; bandwidth; rolloff; flatness
OUTPUT:  scalar features + spectrogram matrix (downsampled) for the frontend
ROLE:    supporting signal evidence; not an AI model.
"""
from __future__ import annotations

import numpy as np
import librosa

MAX_SPEC_TIME = 160
MAX_SPEC_FREQ = 96


def spectrogram_data(x: np.ndarray, sr: int) -> dict:
    n_fft = min(1024, max(256, 1 << int(np.log2(max(x.size, 256)))))
    S = np.abs(librosa.stft(x.astype(np.float32), n_fft=n_fft, hop_length=n_fft // 4)) ** 2
    S_db = librosa.power_to_db(S + 1e-12, ref=np.max)
    # downsample for transport
    f_frac = min(1.0, MAX_SPEC_FREQ / S_db.shape[0])
    t_frac = min(1.0, MAX_SPEC_TIME / S_db.shape[1])
    import scipy.ndimage as ndi
    S_small = ndi.zoom(S_db, (f_frac, t_frac), order=1)
    times = np.linspace(0, x.size / sr, S_small.shape[1])
    freqs = np.linspace(0, sr / 2, S_small.shape[0])
    return {
        "db": [[round(float(v), 1) for v in row] for row in S_small],
        "times": [round(float(t), 3) for t in times],
        "freqs": [round(float(f), 1) for f in freqs],
        "shape": list(S_small.shape),
    }


def features(x: np.ndarray, sr: int) -> dict:
    if x.size < 512:
        x = np.pad(x, (0, 512 - x.size))
    y = x.astype(np.float32)
    cent = librosa.feature.spectral_centroid(y=y, sr=sr)
    bw = librosa.feature.spectral_bandwidth(y=y, sr=sr)
    roll = librosa.feature.spectral_rolloff(y=y, sr=sr)
    flat = librosa.feature.spectral_flatness(y=y)
    return {
        "spectral_centroid_hz": round(float(np.mean(cent)), 1),
        "spectral_bandwidth_hz": round(float(np.mean(bw)), 1),
        "spectral_rolloff_hz": round(float(np.mean(roll)), 1),
        "spectral_flatness": round(float(np.mean(flat)), 5),
    }


def analyze(x: np.ndarray, sr: int) -> dict:
    out = features(x, sr)
    if x.size >= 2048:
        out["spectrogram"] = spectrogram_data(x, sr)
    return out
