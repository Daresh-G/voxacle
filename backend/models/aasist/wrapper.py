"""AASIST-L synthetic-speech detector — REAL inference wrapper (spec §7-§8).

Source (verified): HuggingFace SpeechAntiSpoofingBenchmarks/AASIST-L
- Architecture: _net.py `Model` (clovaai/aasist AASIST architecture)
- Checkpoint:   AASIST-L.pth (ASVspoof2019 LA pretrained, strict load verified)
- Input:        raw waveform, mono 16 kHz float32, deterministic first
                64,600-sample window (tile-padded if shorter) — per the
                repository's documented evaluation wrapper (aasist_l.py).
- Output:       forward() -> (hidden, logits); logits[:, 1] = BONA FIDE logit
                ("higher = more bona fide" per repo README + Arena wrapper).

SEMANTIC RULE (spec §8):
AASIST-L is ONE synthetic-voice evidence source — never the final truth.
Synthetic evidence in [0,1] = 1 - sigmoid(bona_fide_logit).
If the model cannot load or inference fails, this wrapper returns an explicit
MODEL_UNAVAILABLE contract — it NEVER substitutes a random/simulated score.
"""
from __future__ import annotations

import importlib.util
import logging
import os
import sys
import threading
import time

import numpy as np

from backend import config

logger = logging.getLogger("voxacle.aasist")

MODEL_VERSION = {
    "model": "AASIST-L",
    "checkpoint": "AASIST-L.pth (SpeechAntiSpoofingBenchmarks/AASIST-L)",
    "source": "https://huggingface.co/SpeechAntiSpoofingBenchmarks/AASIST-L",
    "paper": "Jung et al., AASIST, ICASSP 2022 (arXiv:2110.01200)",
    "benchmark_eer": "0.99% ASVspoof2019 LA (in-domain benchmark, NOT VOXACLE accuracy)",
}

_state_lock = threading.Lock()
_model = None
_load_error: str | None = None


def _import_net():
    """Import _net.Model directly from the model store (bypasses the
    benchmark repo's speech_spoof_bench dependency, which we do not need)."""
    d = config.AASIST_DIR
    spec = importlib.util.spec_from_file_location(
        "voxacle_aasist_net", os.path.join(d, "_net.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("voxacle_aasist_net", mod)
    spec.loader.exec_module(mod)
    return mod.Model


# exact upstream config from the repo's aasist_l.py (lightweight variant)
_D_ARGS = {
    "architecture": "AASIST",
    "nb_samp": 64600,
    "first_conv": 128,
    "filts": [70, [1, 32], [32, 32], [32, 24], [24, 24]],
    "gat_dims": [24, 32],
    "pool_ratios": [0.4, 0.5, 0.7, 0.5],
    "temperatures": [2.0, 2.0, 100.0, 100.0],
}
_CUT = 64600


def pad_fixed(x: np.ndarray, max_len: int = _CUT) -> np.ndarray:
    """Deterministic eval window: first max_len samples; tile-repeat if shorter.
    Matches clovaai/aasist data_utils.pad() used for dev/eval (no random crop)."""
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    n = x.shape[0]
    if n >= max_len:
        return x[:max_len]
    reps = max_len // n + 1
    return np.tile(x, reps)[:max_len].astype(np.float32)


def _load():
    """Load the model once. Sets _model or _load_error truthfully."""
    global _model, _load_error
    with _state_lock:
        if _model is not None or _load_error is not None:
            return
        ckpt = os.path.join(config.AASIST_DIR, "AASIST-L.pth")
        netfile = os.path.join(config.AASIST_DIR, "_net.py")
        if not os.path.exists(ckpt):
            _load_error = "AASIST-L checkpoint file missing"
            logger.error("[AASIST] %s", _load_error)
            return
        if not os.path.exists(netfile):
            _load_error = "AASIST-L network definition (_net.py) missing"
            logger.error("[AASIST] %s", _load_error)
            return
        try:
            import torch
            Model = _import_net()
            net = Model(_D_ARGS)
            sd = torch.load(ckpt, map_location="cpu", weights_only=True)
            sd = sd.get("state_dict", sd) if isinstance(sd, dict) else sd
            net.load_state_dict(sd, strict=True)
            net.eval()
            _model = net
            n_params = sum(p.numel() for p in net.parameters())
            logger.info("[AASIST] loaded strictly, params=%d, device=cpu", n_params)
        except Exception as e:  # noqa: BLE001
            _load_error = f"AASIST-L failed to load: {e}"
            logger.exception("[AASIST] load failure")


def is_available() -> bool:
    _load()
    return _model is not None


def availability() -> dict:
    _load()
    return {
        "available": _model is not None,
        "error": _load_error,
        "version": MODEL_VERSION,
    }


def _synthetic_evidence_from_logit(logit: float) -> float:
    """ bona_fide prob = sigmoid(logit); synthetic evidence = 1 - p. """
    s = 1.0 / (1.0 + float(np.exp(-float(logit))))
    return float(max(0.0, min(1.0, 1.0 - s)))


def infer(waveform: np.ndarray, sr: int) -> dict:
    """Run REAL AASIST-L inference on one standardized waveform.

    Contract (spec §26):
      success    -> {"status":"success","value":{...},"confidence":...,...}
      unavailable-> {"status":"unavailable","value":None,...,"error":"MODEL_UNAVAILABLE"}
    """
    _load()
    if _model is None:
        return {
            "status": "unavailable",
            "value": None,
            "confidence": 0,
            "warnings": ["AASIST-L is unavailable on this system"],
            "error": "MODEL_UNAVAILABLE",
        }
    import torch

    t0 = time.perf_counter()
    try:
        if sr != 16000:
            return {
                "status": "unavailable",
                "value": None,
                "confidence": 0,
                "warnings": ["AASIST-L requires 16 kHz input; standardization failed"],
                "error": "MODEL_INPUT_ERROR",
            }
        x = pad_fixed(waveform)
        xt = torch.from_numpy(x).unsqueeze(0)  # shape [1, 64600]
        with torch.no_grad():
            _hidden, logits = _model(xt)
        bona_logit = float(logits[:, 1].detach().cpu().float().item())
        syn = _synthetic_evidence_from_logit(bona_logit)
        lat = round((time.perf_counter() - t0) * 1000.0, 1)
        logger.info("[AASIST] input shape=%s bona_logit=%.4f synthetic=%.4f latency=%.1fms",
                    tuple(xt.shape), bona_logit, syn, lat)
        return {
            "status": "success",
            "value": {
                "synthetic_evidence": round(syn, 4),        # 0..1, higher = more synthetic
                "bonafide_logit": round(bona_logit, 4),
                "window_samples": _CUT,
            },
            "confidence": 0.9,  # in-domain model on clean 16k input; capped, not a probability claim
            "warnings": [],
            "error": None,
            "latency_ms": lat,
            "model_version": MODEL_VERSION,
        }
    except Exception as e:  # noqa: BLE001
        logger.exception("[AASIST] inference failure")
        return {
            "status": "unavailable",
            "value": None,
            "confidence": 0,
            "warnings": [f"AASIST inference failed: {e}"],
            "error": "MODEL_INFERENCE_ERROR",
        }
