"""VOXACLE full analysis pipeline (spec §3/§80).

INPUT AUDIO → validation → decoding → standardization → quality gate
  → original preserved separately / analysis copy
  → preprocessing → CORE ANALYSIS (DSP + AASIST-L + ECAPA + prosody)
  → chunk/temporal analysis → evidence fusion → disagreement check
  → confidence engine → (+ context module) → risk engine
  → policy/action engine → alert + report

FAILURE PHILOSOPHY (spec §1/§33/§52/§81):
- never convert a technical failure into a fake confidence value
- unavailable components yield MODEL_UNAVAILABLE and reduce confidence
- UNUSABLE audio yields INCONCLUSIVE, not HIGH RISK
"""
from __future__ import annotations

import logging
import time
import uuid

import numpy as np

from backend import config, database
from backend.audio import decoder, quality as quality_mod, filters
from backend.audio.standardizer import standardize
from backend.signal import time_domain, frequency, spectral, mfcc, prosody
from backend.models import aasist as aasist_mod, ecapa as ecapa_mod
from backend.analysis import temporal as temporal_mod, evidence, confidence as conf_mod, risk as risk_mod
from backend.context import engine as context_engine
from backend.policy import action_engine
from backend.privacy import retention
from backend.reports import report_generator

logger = logging.getLogger("voxacle.pipeline")

FINAL_STATES = {
    "GENUINE": "GENUINE",
    "SUSPICIOUS": "SUSPICIOUS",
    "HIGH RISK": "HIGH RISK",
    "INCONCLUSIVE": "INCONCLUSIVE",
    "ANALYSIS FAILED": "ANALYSIS FAILED",
}


def _classify(risk_level: str, synthetic: float | None, fusion: dict, conf: dict, qstate: str) -> str:
    """Map evidence to the five truthful user states (spec §34)."""
    if qstate == "UNUSABLE":
        return "INCONCLUSIVE"
    if conf["label"] == "LOW" and (synthetic is None or fusion.get("disagreement")):
        return "INCONCLUSIVE"
    if synthetic is None:
        return "INCONCLUSIVE"
    if risk_level == "CRITICAL":
        return "HIGH RISK"
    if risk_level == "HIGH":
        return "HIGH RISK"
    if synthetic >= 0.6:
        return "HIGH RISK"
    if synthetic >= 0.35 or fusion.get("disagreement"):
        return "SUSPICIOUS"
    if risk_level == "MEDIUM" and conf["confidence"] >= 45:
        return "SUSPICIOUS"
    return "GENUINE"


def analyze(
    audio_bytes: bytes,
    original_name: str | None,
    context: dict | None,
    reference_profile_id: str | None = None,
    reference_audio_bytes: bytes | None = None,
    session_id: str | None = None,
) -> dict:
    """Run the complete pipeline. Returns the full result payload."""
    wall_t0 = time.perf_counter()
    session_id = session_id or uuid.uuid4().hex
    analysis_id = database.new_id()
    settings = config.get_settings()
    context = context or {}
    warnings: list[str] = []

    # ---------------- 1. VALIDATION + DECODING ----------------
    try:
        if len(audio_bytes) > config.MAX_UPLOAD_BYTES:
            return _fail(analysis_id, session_id, "FILE_TOO_LARGE", "Upload exceeds the 50 MB limit.", wall_t0)
        std = decoder.decode_to_16k_mono(audio_bytes, original_name)
    except decoder.UnsupportedFormatError as e:
        return _fail(analysis_id, session_id, e.code, str(e), wall_t0)
    except decoder.AudioDecodeError as e:
        return _fail(analysis_id, session_id, e.code, str(e), wall_t0)
    except Exception as e:  # noqa: BLE001
        logger.exception("decode failure")
        return _fail(analysis_id, session_id, "AUDIO_DECODE_ERROR", f"Unexpected decode failure: {e}", wall_t0)

    x = std["waveform"]
    sr = std["sample_rate"]

    # ---------------- 2. QUALITY GATE ----------------
    quality = quality_mod.analyze_quality(x, sr)
    qstate = quality["state"]
    warnings.extend(quality["issues"])

    # ---------------- 3. EVIDENCE PRESERVATION ----------------
    ev_hash = retention.evidence_hash(audio_bytes)
    orig_path = retention.store_original(
        session_id, analysis_id, audio_bytes,
        policy_allows=bool(settings.get("store_original_audio", True)),
    )
    analysis_copy_path = retention.store_analysis_copy(session_id, analysis_id, x, sr)

    # ---------------- 4. PREPROCESSING (analysis copy only) ----------------
    xa, pre_ops = filters.default_preprocess(x, sr)

    # ---------------- 5. CORE ANALYSIS ----------------
    # 5a. time domain
    t_feats = time_domain.analyze(xa, sr)
    rms_c = time_domain.rms_curve(xa, sr)

    # 5b. frequency + spectral + mfcc
    freq = frequency.analyze(xa, sr)
    spec = spectral.analyze(xa, sr)
    mf = mfcc.analyze(xa, sr)

    # 5c. prosody
    pros = prosody.analyze(xa, sr)

    # 5d. AASIST-L on FULL (first-window) audio — primary synthetic evidence
    aasist_ev = aasist_mod.wrapper.infer(xa, sr)

    # 5e. temporal chunk analysis (per-chunk real inference)
    temporal_ev = temporal_mod.analyze_temporal(
        xa, sr, chunk_seconds=float(settings.get("chunk_seconds", 4.0)),
        include_details=True,
    )

    # 5f. ECAPA speaker consistency (reference required)
    ecapa_ev: dict | None = None
    speaker_summary: dict | None = None
    ref_vec = None
    if reference_profile_id:
        prof = database.get_profile(reference_profile_id)
        if prof and prof.get("embedding"):
            ref_vec = np.array(prof["embedding"], dtype=np.float32)
        else:
            ecapa_ev = {"status": "unavailable", "value": None, "confidence": 0,
                        "warnings": ["Reference profile not found"], "error": "PROFILE_NOT_FOUND"}
    elif reference_audio_bytes:
        try:
            rstd = decoder.decode_to_16k_mono(reference_audio_bytes, None)
            r_emb = ecapa_mod.wrapper.embed(rstd["waveform"], rstd["sample_rate"])
            if r_emb["status"] == "success":
                ref_vec = r_emb["value"]
        except Exception as e:  # noqa: BLE001
            ecapa_ev = {"status": "unavailable", "value": None, "confidence": 0,
                        "warnings": [f"Reference audio failed: {e}"], "error": "REFERENCE_DECODE_ERROR"}

    if ref_vec is not None:
        s_emb = ecapa_mod.wrapper.embed(xa, sr)
        if s_emb["status"] == "success":
            ecapa_ev = ecapa_mod.wrapper.compare(ref_vec, s_emb["value"], settings)
            speaker_summary = ecapa_ev["value"]
            ecapa_ev["latency_ms"] = s_emb.get("latency_ms")
        else:
            ecapa_ev = s_emb

    # ---------------- 6. DSP EVIDENCE ----------------
    dsp_features = {
        "spectral_flatness": spec.get("spectral_flatness"),
        "spectral_centroid_hz": spec.get("spectral_centroid_hz"),
        "spectral_bandwidth_hz": spec.get("spectral_bandwidth_hz"),
        "spectral_rolloff_hz": spec.get("spectral_rolloff_hz"),
        "zcr": t_feats.get("zcr"),
        "rms": t_feats.get("rms"),
        "snr_db": quality["metrics"]["estimated_snr_db"],
    }
    dsp_anomaly = evidence.dsp_anomaly(
        {"features": dsp_features, "prosody": pros}, qstate
    )
    dsp_ev = {
        "status": "success",
        "value": {"anomaly_score": dsp_anomaly, "features": dsp_features},
        "confidence": 0.7 if qstate == "GOOD" else 0.5,
        "warnings": [], "error": None,
    }

    # prosody synthetic-regularities supporting signal (0..1) — from real features
    pval = pros.get("value") or {}
    prosody_reg = None
    if pros["status"] == "success" and pval:
        pv = pval.get("pitch_variation_semitones")
        tr = pval.get("temporal_regularity")
        ecv = pval.get("energy_cv")
        if pv is not None and tr is not None:
            reg = 0.0
            if pv < 0.8:
                reg += 0.5
            elif pv < 1.2:
                reg += 0.25
            if tr > 0.5:
                reg += 0.3
            if ecv is not None and ecv < 0.25:
                reg += 0.2
            prosody_reg = round(min(1.0, reg), 3)
    prosody_ev = {
        "status": pros["status"],
        "value": ({"synthetic_regularities": prosody_reg, **pval} if pros["status"] == "success" else None),
        "confidence": pros.get("confidence", 0),
        "warnings": pros.get("warnings", []),
        "error": pros.get("error"),
    }

    # ---------------- 7. FUSION + CONFIDENCE ----------------
    fusion = evidence.fuse(aasist_ev, temporal_ev, dsp_ev, prosody_ev, quality)
    synthetic = fusion.get("synthetic_evidence")

    # ---------------- 8. CONTEXT (separate until risk stage) ----------------
    context_result = context_engine.evaluate(context)

    # ---------------- 9. RISK ENGINE ----------------
    temporal_stats = (temporal_ev.get("value") or {}).get("stats") if temporal_ev.get("value") else None
    speaker_for_risk = speaker_summary
    risk = risk_mod.compute_risk(
        synthetic, speaker_for_risk, dsp_anomaly, prosody_reg, temporal_stats,
        context_result, settings,
    )

    conf = conf_mod.analyze_confidence(quality, fusion, aasist_ev, ecapa_ev, x.size / sr, settings)

    # ---------------- 10. FINAL CLASSIFICATION + POLICY ----------------
    classification = _classify(risk["risk_level"], synthetic, fusion, conf, qstate)
    if qstate == "UNUSABLE":
        risk["risk_score"] = 0.0
        risk["risk_level"] = "LOW"  # risk display suppressed for unusable audio; state is INCONCLUSIVE
    policy = action_engine.decide(risk["risk_level"], classification, settings)

    latency_ms = round((time.perf_counter() - wall_t0) * 1000.0, 1)

    # ---------------- 11. REASONING (UI-facing, spec §40) ----------------
    reasoning = {
        "synthetic_evidence": _band_label(synthetic),
        "speaker_consistency": (speaker_summary or {}).get("consistency") if speaker_summary else ("NOT EVALUATED" if not reference_profile_id and not reference_audio_bytes else "UNAVAILABLE"),
        "temporal": _temporal_label(temporal_stats),
        "audio_quality": qstate,
        "context": context_result["band"],
        "confidence": conf["label"],
        "lines": (fusion.get("reasoning", []) + risk["notes"] + context_result["reasoning"][:4] + conf["warnings"]),
    }

    # ---------------- 12. BUILD RESULT PAYLOAD ----------------
    model_versions = {
        "AASIST-L": (aasist_ev.get("model_version") or aasist_mod.wrapper.MODEL_VERSION)
        if aasist_ev.get("status") == "success" else {"status": "unavailable", "error": aasist_ev.get("error")},
        "ECAPA-TDNN": ecapa_mod.wrapper.MODEL_VERSION | {"status": (ecapa_ev or {}).get("status", "not_evaluated")}
        if ecapa_ev else {**ecapa_mod.wrapper.MODEL_VERSION, "status": "not_evaluated"},
        "DSP": {"engine": "NumPy/SciPy/Librosa deterministic DSP", "version": "1.0"},
    }

    result = {
        "analysis_id": analysis_id,
        "session_id": session_id,
        "created_at": database.utcnow_iso(),
        "classification": classification,
        "risk_score": risk["risk_score"],
        "risk_level": risk["risk_level"],
        "confidence": conf["confidence"],
        "confidence_label": conf["label"],
        "ai_likelihood_percent": round(synthetic * 100, 1) if synthetic is not None else None,
        "ai_likelihood_label": conf_mod.ai_likelihood_label(synthetic),
        "speaker_similarity": speaker_summary,
        "audio_quality": qstate,
        "quality_metrics": quality["metrics"],
        "context_risk": context_result["band"],
        "context_risk_score": context_result["score"],
        "context_reasoning": context_result["reasoning"],
        "fusion": {
            "availability": fusion.get("availability"),
            "disagreement": fusion.get("disagreement"),
            "coverage": fusion.get("coverage"),
        },
        "risk_components": risk["components"],
        "risk_drivers": risk["drivers"],
        "warnings": warnings + fusion.get("warnings", []) + conf["warnings"],
        "recommended_action": policy["action"],
        "action_title": policy["title"],
        "action_detail": policy["detail"],
        "reasoning": reasoning,
        "evidence_hash": ev_hash,
        "latency_ms": latency_ms,
        "processing": {
            "preprocessing_ops": pre_ops,
            "chunk_seconds": settings.get("chunk_seconds", 4.0),
            "aasist_latency_ms": aasist_ev.get("latency_ms"),
            "ecapa_latency_ms": (ecapa_ev or {}).get("latency_ms"),
        },
        "model_versions": model_versions,
        "advanced": {
            "waveform": _waveform_points(xa, sr),
            "rms_curve": rms_c,
            "spectrum": freq["spectrum"],
            "spectrogram": spec.get("spectrogram"),
            "mfcc": mf.get("matrix"),
            "pitch_curve": pros.get("pitch_curve"),
            "chunks": (temporal_ev.get("value") or {}).get("chunks", []),
            "temporal_stats": temporal_stats,
            "dsp_metrics": dsp_features,
            "mfcc_summary": {k: v for k, v in mf.items() if k != "matrix"},
            "aasist": {k: aasist_ev.get(k) for k in ("status", "value", "error", "warnings")},
            "ecapa_status": {"status": (ecapa_ev or {}).get("status", "not_evaluated"),
                             "error": (ecapa_ev or {}).get("error")},
            "quality_issues": quality["issues"],
        },
        "file_name": original_name,
        "has_reference": bool(ref_vec is not None),
    }

    # ---------------- 13. PERSIST + CLEANUP ----------------
    record = {
        "id": analysis_id,
        "session_id": session_id,
        "created_at": result["created_at"],
        "classification": classification,
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
        "confidence": result["confidence"],
        "ai_likelihood": result["ai_likelihood_percent"],
        "speaker_similarity": (speaker_summary or {}).get("similarity") if speaker_summary else None,
        "audio_quality": qstate,
        "context_risk": context_result["band"],
        "context_risk_score": context_result["score"],
        "warnings": result["warnings"],
        "model_versions": model_versions,
        "evidence_hash": ev_hash,
        "latency_ms": latency_ms,
        "has_reference": result["has_reference"],
        "result": {k: v for k, v in result.items() if k != "advanced"},  # slim DB copy
        "file_name": original_name,
        "action": policy["action"],
    }
    database.save_analysis(record)
    if not settings.get("store_original_audio", True):
        retention.delete_analysis_copy(analysis_copy_path)
    else:
        # analysis copies are temporary by policy; originals kept under evidence dir
        retention.delete_analysis_copy(analysis_copy_path)

    result["report"] = report_generator.build_report(record, result)
    return result


def _band_label(v: float | None) -> str:
    """Unified with confidence.ai_likelihood_label thresholds so UI never
    shows two different labels for the same underlying value."""
    if v is None:
        return "UNAVAILABLE"
    if v >= 0.6:
        return "HIGH"
    if v >= 0.35:
        return "ELEVATED"
    if v >= 0.15:
        return "MODERATE"
    return "LOW"


def _temporal_label(stats: dict | None) -> str:
    if not stats or stats.get("mean_synthetic") is None:
        return "UNAVAILABLE"
    if stats.get("variable_evidence"):
        return "VARIABLE"
    m = stats["mean_synthetic"]
    if m >= 0.6:
        return "CONSISTENTLY SUSPICIOUS"
    if m >= 0.35:
        return "SUSPICIOUS"
    return "NORMAL"


def _waveform_points(x: np.ndarray, sr: int, target: int = 600) -> dict:
    n = x.size
    if n == 0:
        return {"times": [], "values": []}
    if n <= target:
        idx = np.arange(n)
    else:
        idx = np.round(np.linspace(0, n - 1, target)).astype(int)
    vals = x[idx]
    times = idx / sr
    return {
        "times": [round(float(t), 3) for t in times],
        "values": [round(float(v), 5) for v in vals],
    }


def _fail(analysis_id: str, session_id: str, code: str, message: str, wall_t0: float) -> dict:
    """Truthful failure payload (spec §33/§34/§68) — no fabricated values."""
    latency = round((time.perf_counter() - wall_t0) * 1000.0, 1)
    result = {
        "analysis_id": analysis_id,
        "session_id": session_id,
        "created_at": database.utcnow_iso(),
        "classification": "ANALYSIS FAILED",
        "error": {"code": code, "message": message, "retryable": code in ("MODEL_UNAVAILABLE",)},
        "risk_score": None,
        "risk_level": None,
        "confidence": None,
        "ai_likelihood_percent": None,
        "speaker_similarity": None,
        "audio_quality": None,
        "warnings": [f"{code}: {message}"],
        "recommended_action": "RETRY_LATER",
        "action_title": "Analysis could not complete",
        "action_detail": message + " No result is shown because none could be computed.",
        "latency_ms": latency,
        "evidence_hash": None,
        "model_versions": {},
        "file_name": None,
        "has_reference": False,
    }
    return result
