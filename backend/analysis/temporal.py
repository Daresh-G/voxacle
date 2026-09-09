"""Temporal / chunk-level analysis (spec §23-§25).

INPUT:   full standardized waveform + per-chunk evidence callbacks
MATH:    fixed-duration chunks (default 4 s) aligned to AASIST's documented
         64,600-sample window (~4.04 s at 16 kHz); per-chunk evidence values
         are REAL inference outputs only.
OUTPUT:  chunk timeline [{t0,t1,synthetic,quality,confidence,warnings}...] plus
         aggregate temporal statistics used by fusion/risk.

Mixed human+AI audio is supported: chunks can disagree, and the final
classification reflects the actual distribution rather than a forced binary.
"""
from __future__ import annotations

import logging
import time

import numpy as np

from backend.models.aasist import wrapper as aasist
from backend.audio import quality as quality_mod

logger = logging.getLogger("voxacle.temporal")


def chunk_bounds(n_samples: int, sr: int, chunk_seconds: float) -> list[tuple[int, int, float, float]]:
    step = int(chunk_seconds * sr)
    if step <= 0:
        step = sr * 4
    out = []
    t0 = 0
    idx = 0
    while t0 < n_samples:
        t1 = min(t0 + step, n_samples)
        out.append((t0, t1, idx * chunk_seconds, t0 / sr + (t1 - t0) / sr))
        idx += 1
        t0 = t1
        if idx > 64:  # safety cap
            break
    return out


def analyze_temporal(
    waveform: np.ndarray,
    sr: int,
    chunk_seconds: float = 4.0,
    include_details: bool = True,
) -> dict:
    """Run per-chunk AASIST evidence + quality. All values are real outputs."""
    total_t0 = time.perf_counter()
    bounds = chunk_bounds(waveform.size, sr, chunk_seconds)
    chunks: list[dict] = []
    unavailable = 0

    for (i0, i1, ts, te) in bounds:
        seg = waveform[i0:i1]
        q = quality_mod.analyze_quality(seg, sr)
        res = aasist.infer(seg, sr)
        if res["status"] != "success":
            unavailable += 1
        entry = {
            "t0": round(ts, 2),
            "t1": round(te, 2),
            "synthetic": res["value"]["synthetic_evidence"] if res["status"] == "success" else None,
            "bonafide_logit": res["value"]["bonafide_logit"] if res["status"] == "success" else None,
            "quality": q["state"],
            "confidence": res.get("confidence", 0),
            "warnings": res.get("warnings", []) + q.get("issues", []),
            "latency_ms": res.get("latency_ms"),
        }
        chunks.append(entry)

    valid = [c["synthetic"] for c in chunks if c["synthetic"] is not None]
    stats = {
        "n_chunks": len(chunks),
        "n_unavailable": unavailable,
        "mean_synthetic": round(float(np.mean(valid)), 4) if valid else None,
        "std_synthetic": round(float(np.std(valid)), 4) if valid else None,
        "max_synthetic": round(float(np.max(valid)), 4) if valid else None,
        "min_synthetic": round(float(np.min(valid)), 4) if valid else None,
    }
    # Temporal instability: how much chunk evidence varies over time
    if len(valid) >= 3:
        stats["temporal_instability"] = round(float(np.std(valid)), 4)
        stats["suspicious_chunk_ratio"] = round(float(np.mean(np.array(valid) > 0.5)), 3)
        stats["variable_evidence"] = bool(np.std(valid) > 0.2)
    else:
        stats["temporal_instability"] = None
        stats["suspicious_chunk_ratio"] = round(float(np.mean(np.array(valid) > 0.5)), 3) if valid else None
        stats["variable_evidence"] = False

    out = {
        "status": "success" if valid else "unavailable",
        "value": {"stats": stats, "chunks": chunks if include_details else []},
        "confidence": 1.0 if valid else 0.0,
        "warnings": (["All temporal chunks unavailable"] if not valid else []),
        "error": "MODEL_UNAVAILABLE" if not valid else None,
        "latency_ms": round((time.perf_counter() - total_t0) * 1000.0, 1),
    }
    return out
