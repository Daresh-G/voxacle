"""Report generator (spec §47).

Produces the VOICE INTEGRITY REPORT payload + printable text format containing
session info, quality, evidence, risk, confidence, warnings, recommended
action, model versions, latency and evidence hash.
"""
from __future__ import annotations

from typing import Any


def build_report(record: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": "VOICE INTEGRITY REPORT",
        "analysis_id": record.get("id"),
        "session_id": record.get("session_id"),
        "timestamp": record.get("created_at"),
        "input_information": {
            "file_name": record.get("file_name"),
            "has_reference": record.get("has_reference"),
        },
        "audio_quality": result.get("quality", {}).get("state"),
        "ai_likelihood": result.get("ai_likelihood_percent"),
        "speaker_similarity": result.get("speaker_similarity"),
        "prosody_evidence": result.get("reasoning", {}).get("prosody"),
        "signal_evidence": result.get("reasoning", {}).get("dsp"),
        "temporal_evidence": result.get("reasoning", {}).get("temporal"),
        "contextual_risk": record.get("context_risk"),
        "final_risk_level": record.get("risk_level"),
        "classification": record.get("classification"),
        "analysis_confidence": record.get("confidence"),
        "warnings": record.get("warnings", []),
        "recommended_action": record.get("action"),
        "model_versions": record.get("model_versions", {}),
        "processing_latency_ms": record.get("latency_ms"),
        "evidence_hash": record.get("evidence_hash"),
        "privacy_note": "Audio is processed for verification and retained only according to configured evidence policy.",
    }


def report_text(r: dict[str, Any]) -> str:
    lines = [r["title"], "=" * len(r["title"]), ""]
    for k, v in r.items():
        if k in ("title",):
            continue
        if isinstance(v, dict):
            lines.append(f"{k.replace('_', ' ').upper()}:")
            for k2, v2 in v.items():
                lines.append(f"  {k2}: {v2}")
        elif isinstance(v, list):
            lines.append(f"{k.replace('_', ' ').upper()}:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{k.replace('_', ' ').upper()}: {v}")
    lines.append("")
    return "\n".join(lines)
