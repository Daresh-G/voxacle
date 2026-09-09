"""ECAPA-TDNN speaker-embedding wrapper — REAL inference (spec §9).

Source (verified): SpeechBrain speechbrain/spkrec-ecapa-voxceleb, loaded from
the local model store (downloaded by scripts/setup_models.py with checksums).

PURPOSE: "Does this incoming voice resemble the enrolled/reference speaker?"
It does NOT determine whether speech is AI-generated. Output is cosine
similarity between 192-d embeddings:
    similarity = (a · b) / (||a|| · ||b||)
Labels: Speaker similarity % and Speaker consistency LOW/MEDIUM/HIGH.
Thresholds are configurable (settings: speaker_high/medium) and must be
validated for the target environment (spec §9).
"""
from __future__ import annotations

import logging
import threading
import time

import numpy as np

from backend import config

logger = logging.getLogger("voxacle.ecapa")

MODEL_VERSION = {
    "model": "ECAPA-TDNN",
    "checkpoint": "speechbrain/spkrec-ecapa-voxceleb (embedding_model.ckpt)",
    "source": "https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb",
    "embedding_dim": 192,
}

_state_lock = threading.Lock()
_encoder = None
_load_error: str | None = None


def _load():
    global _encoder, _load_error
    with _state_lock:
        if _encoder is not None or _load_error is not None:
            return
        try:
            import torch  # noqa: F401
            from speechbrain.inference.speaker import EncoderClassifier
            _encoder = EncoderClassifier.from_hparams(
                source=config.ECAPA_DIR,
                savedir=config.ECAPA_DIR,
                run_opts={"device": "cpu"},
            )
            logger.info("[ECAPA] loaded from %s", config.ECAPA_DIR)
        except Exception as e:  # noqa: BLE001
            _load_error = f"ECAPA failed to load: {e}"
            logger.exception("[ECAPA] load failure")


def is_available() -> bool:
    _load()
    return _encoder is not None


def availability() -> dict:
    _load()
    return {"available": _encoder is not None, "error": _load_error, "version": MODEL_VERSION}


def embed(waveform: np.ndarray, sr: int) -> dict:
    """Compute a 192-d ECAPA embedding (normalized by SpeechBrain pipeline)."""
    _load()
    if _encoder is None:
        return {
            "status": "unavailable",
            "value": None,
            "confidence": 0,
            "warnings": ["ECAPA-TDNN is unavailable on this system"],
            "error": "MODEL_UNAVAILABLE",
        }
    import torch

    t0 = time.perf_counter()
    try:
        if sr != 16000:
            return {"status": "unavailable", "value": None, "confidence": 0,
                    "warnings": ["ECAPA requires 16 kHz input"], "error": "MODEL_INPUT_ERROR"}
        wav_t = torch.from_numpy(np.asarray(waveform, dtype=np.float32))
        with torch.no_grad():
            emb = _encoder.encode_batch(wav_t)  # [1, 1, 192]
        vec = emb.squeeze().cpu().numpy().astype(np.float32)
        lat = round((time.perf_counter() - t0) * 1000.0, 1)
        logger.info("[ECAPA] embed shape=%s latency=%.1fms", tuple(vec.shape), lat)
        return {
            "status": "success",
            "value": vec,
            "confidence": 1.0,
            "warnings": [],
            "error": None,
            "latency_ms": lat,
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("[ECAPA] inference failure")
        return {"status": "unavailable", "value": None, "confidence": 0,
                "warnings": [f"ECAPA inference failed: {e}"], "error": "MODEL_INFERENCE_ERROR"}


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    b = np.asarray(b, dtype=np.float64).reshape(-1)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def consistency_label(sim: float, settings: dict) -> str:
    if sim >= settings.get("speaker_high", 0.75):
        return "HIGH"
    if sim >= settings.get("speaker_medium", 0.55):
        return "MEDIUM"
    return "LOW"


def compare(reference_vec: np.ndarray, suspect_vec: np.ndarray, settings: dict) -> dict:
    sim = cosine_similarity(reference_vec, suspect_vec)
    # Transparent display: raw cosine mapped to 0-100 (no inflation).
    return {
        "status": "success",
        "value": {
            "similarity": round(sim, 4),
            "similarity_percent": round(max(0.0, min(1.0, sim)) * 100.0, 1),
            "consistency": consistency_label(sim, settings),
        },
        "confidence": 1.0,
        "warnings": [],
        "error": None,
        "model_version": MODEL_VERSION,
    }
