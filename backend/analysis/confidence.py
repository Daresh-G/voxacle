"""Confidence engine (spec §28).

Separates three distinct quantities that must NEVER be conflated:
  - AI likelihood      (synthetic evidence level)
  - ANALYSIS CONFIDENCE (how much the system trusts its own analysis)
  - RISK SCORE         (decision-support combination with context)

Analysis confidence derives from: audio quality, evidence coverage, model
availability, evidence agreement, and duration. It is NOT a probability of
"AI" — it is reliability of the analysis itself.
"""
from __future__ import annotations


def analyze_confidence(
    quality: dict,
    fusion: dict,
    aasist_ev: dict,
    ecapa_ev: dict | None,
    duration_sec: float,
    settings: dict,
) -> dict:
    warnings: list[str] = []
    conf = 100.0
    qstate = quality.get("state", "UNUSABLE")

    # --- audio quality factor ---
    q_factor = {"GOOD": 1.0, "FAIR": 0.75, "POOR": 0.4, "UNUSABLE": 0.1}.get(qstate, 0.3)
    conf *= q_factor
    if qstate in ("FAIR",):
        warnings.append("Audio quality is fair; confidence reduced.")
    if qstate in ("POOR", "UNUSABLE"):
        warnings.append(f"Audio quality is {qstate.lower()}; analysis confidence is substantially reduced.")

    # --- duration factor ---
    if duration_sec < 2.0:
        conf *= 0.7
        warnings.append("Audio shorter than 2 s limits reliability.")
    elif duration_sec < 3.0:
        conf *= 0.85

    # --- evidence coverage ---
    coverage = float(fusion.get("coverage", 1.0))
    conf *= (0.5 + 0.5 * coverage)
    if coverage < 0.9:
        warnings.append("Some evidence sources were unavailable.")

    # --- model availability ---
    if aasist_ev.get("status") != "success":
        conf *= 0.45
        warnings.append("AASIST-L unavailable — synthetic evidence lacks its primary source.")
    if ecapa_ev is not None and ecapa_ev.get("status") != "success":
        conf *= 0.85
        warnings.append("ECAPA unavailable — speaker similarity not evaluated.")

    # --- disagreement penalty ---
    if fusion.get("disagreement"):
        conf -= float(settings.get("confidence_disagreement_penalty", 15))

    conf = float(max(2.0, min(100.0, conf)))
    if qstate == "POOR":
        conf = min(conf, float(settings.get("confidence_poor_quality_cap", 55)))

    label = "HIGH" if conf >= 70 else ("MEDIUM" if conf >= 45 else "LOW")
    return {
        "confidence": round(conf, 1),
        "label": label,
        "warnings": warnings,
    }


def ai_likelihood_label(synthetic_evidence: float | None) -> str:
    if synthetic_evidence is None:
        return "UNAVAILABLE"
    if synthetic_evidence >= 0.6:
        return "HIGH"
    if synthetic_evidence >= 0.35:
        return "ELEVATED"
    if synthetic_evidence >= 0.15:
        return "MODERATE"
    return "LOW"
