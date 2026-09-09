"""Prosody / temporal-behavior analysis (spec §19).

INPUT:   waveform segment
MATH:    pitch via librosa pyin (median, variation), pause structure from
         energy VAD, speaking-rate proxy from voiced-segment statistics,
         energy dynamics (CV of frame RMS), temporal regularity score
OUTPUT:  human-readable prosody evidence with value + reliability contract
ROLE:    "Human speech contains natural temporal and prosodic variation.
         Synthetic speech can sometimes show measurable regularities or
         unnatural transitions. These are supporting signals, not proof."
"""
from __future__ import annotations

import numpy as np
import librosa

from backend.signal.time_domain import rms_curve


def analyze(x: np.ndarray, sr: int) -> dict:
    y = x.astype(np.float32)
    warnings: list[str] = []
    out: dict = {"status": "success", "value": None, "confidence": 0.0, "warnings": warnings, "error": None}

    if y.size < sr // 2:  # <0.5 s: prosody unreliable
        return {"status": "unavailable", "value": None, "confidence": 0.0,
                "warnings": ["Segment too short for prosody analysis"], "error": None}

    # --- Pitch (pyin; may return all-NaN on unvoiced/noise) ---
    f0, voiced_flag, _ = librosa.pyin(
        y, fmin=65, fmax=400, sr=sr, frame_length=min(2048, 1 << int(np.log2(max(y.size, 512))))
    )
    voiced = f0[voiced_flag.astype(bool)] if f0 is not None else np.array([])
    pitch_mean = float(np.nanmean(voiced)) if voiced.size else None
    pitch_std = float(np.nanstd(voiced)) if voiced.size else None
    # pitch variation as semitone spread
    if voiced.size > 4:
        midi = librosa.hz_to_midi(voiced)
        midi = midi[np.isfinite(midi)]
        pitch_var_st = float(np.std(midi)) if midi.size else 0.0
        voiced_ratio = float(np.mean(voiced_flag))
    else:
        pitch_var_st = 0.0
        voiced_ratio = 0.0
        if voiced.size == 0:
            warnings.append("Pitch could not be estimated reliably (possible noise or unvoiced audio).")

    # --- Energy dynamics ---
    curve = rms_curve(y, sr)
    vals = np.array(curve["values"], dtype=np.float64)
    energy_cv = float(np.std(vals) / (np.mean(vals) + 1e-9)) if vals.size > 2 else 0.0

    # --- Pauses / speaking-rate proxy via energy VAD ---
    fl = max(1, int(sr * 0.03))
    n = (y.size // fl) * fl
    fr = y[:n].reshape(-1, fl).astype(np.float64)
    fe = np.sqrt(np.mean(fr ** 2, axis=1))
    if fe.size >= 4:
        thr = max(np.percentile(fe, 35) * 0.4, 1e-5)
        speech = fe > thr
        # pause runs between voiced regions
        runs = []
        cur = 0
        for s in speech:
            if not s:
                cur += 1
            elif cur:
                runs.append(cur)
                cur = 0
        if cur:
            runs.append(cur)
        pause_dur_ms = [round(r * 30.0, 1) for r in runs if r >= 2]
        n_pauses = len(pause_dur_ms)
        speech_rate_proxy = float(np.mean(fe[speech]) / (np.mean(fe) + 1e-9))
        pause_regularity = float(np.std(pause_dur_ms) / (np.mean(pause_dur_ms) + 1e-6)) if n_pauses > 1 else 0.0
    else:
        n_pauses, speech_rate_proxy, pause_regularity = 0, 0.0, 0.0

    # --- Temporal regularity: autocorrelation flatness of energy envelope ---
    if vals.size > 8:
        v = vals - np.mean(vals)
        ac = np.correlate(v, v, mode="full")[v.size - 1:]
        ac = ac / (ac[0] + 1e-12)
        lag_peak = float(np.max(ac[2: min(len(ac), 25)])) if ac.size > 4 else 0.0
    else:
        lag_peak = 0.0

    out["value"] = {
        "pitch_mean_hz": round(pitch_mean, 1) if pitch_mean is not None else None,
        "pitch_std_hz": round(pitch_std, 2) if pitch_std is not None else None,
        "pitch_variation_semitones": round(pitch_var_st, 3),
        "voiced_ratio": round(voiced_ratio, 3),
        "energy_cv": round(energy_cv, 4),
        "pause_count": n_pauses,
        "pause_regularity": round(pause_regularity, 4),
        "speech_rate_proxy": round(speech_rate_proxy, 4),
        "temporal_regularity": round(lag_peak, 4),
    }
    # Reliability: proportional to voiced content and length (NOT a synthetic score)
    out["confidence"] = round(min(1.0, max(0.2, voiced_ratio * 1.2) * min(1.0, y.size / (sr * 3.0))), 3)
    # Pitch curve for visualization
    if f0 is not None:
        tt = librosa.times_like(f0, sr=sr)
        keep = slice(0, len(f0), max(1, len(f0) // 240))
        out["pitch_curve"] = {
            "times": [round(float(t), 3) for t in tt[keep]],
            "hz": [round(float(v), 1) if np.isfinite(v) else None for v in f0[keep]],
        }
    return out
