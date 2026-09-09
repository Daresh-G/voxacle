"""Risk engine (spec §29).

Risk = f(synthetic evidence, speaker consistency, signal evidence, prosody,
temporal consistency, audio quality, contextual factors). Score is 0-100 for
product UX. Weightings are configurable and thresholds are product defaults —
NOT universal scientific truth (spec §81).
"""
from __future__ import annotations

WEIGHTS = {
    "synthetic": 0.42,
    "speaker": 0.16,
    "dsp": 0.10,
    "prosody": 0.07,
    "temporal": 0.10,
    "context": 0.15,
}


def _band(risk: float, settings: dict) -> str:
    if risk <= settings.get("risk_low_max", 30):
        return "LOW"
    if risk <= settings.get("risk_medium_max", 55):
        return "MEDIUM"
    if risk <= settings.get("risk_high_max", 75):
        return "HIGH"
    return "CRITICAL"


def compute_risk(
    synthetic_evidence: float | None,   # 0..1
    speaker: dict | None,               # {"similarity":0..1,"consistency":...} or None
    dsp_anomaly: float | None,          # 0..1
    prosody_regularities: float | None, # 0..1
    temporal_stats: dict | None,
    context_result: dict,
    settings: dict,
) -> dict:
    components: dict[str, float] = {}
    notes: list[str] = []

    # synthetic evidence — primary driver
    components["synthetic"] = (synthetic_evidence or 0.0) * 100 if synthetic_evidence is not None else 0.0
    if synthetic_evidence is None:
        notes.append("Synthetic evidence unavailable; risk relies more heavily on context and quality.")

    # speaker consistency: only meaningful when a reference exists.
    # HIGH similarity is only a RISK DRIVER when combined with synthetic
    # evidence (cloned-impersonation pattern, spec §56). A genuine caller
    # should also match their reference — similarity alone is NOT risk.
    if speaker and speaker.get("similarity") is not None and synthetic_evidence is not None:
        sim = float(speaker["similarity"])
        if synthetic_evidence >= 0.6:
            speaker_w = 1.0            # strong impersonation pattern
        elif synthetic_evidence >= 0.35:
            speaker_w = 0.6            # partial corroboration
        elif synthetic_evidence >= 0.15:
            speaker_w = 0.15           # weak; mostly neutral
        else:
            speaker_w = 0.0            # genuine-sounding voice matching reference = legitimate
        components["speaker"] = sim * 100.0 * speaker_w
        if speaker_w == 0.0:
            notes.append("Speaker similarity is high but synthetic evidence is low — consistent with a legitimate caller.")
    else:
        components["speaker"] = 0.0

    components["dsp"] = (dsp_anomaly or 0.0) * 100
    components["prosody"] = (prosody_regularities or 0.0) * 100

    # temporal: mean chunk synthetic + instability
    tmean = (temporal_stats or {}).get("mean_synthetic")
    inst = (temporal_stats or {}).get("temporal_instability")
    tv = (tmean or 0.0) * 100
    if inst:
        tv += min(20.0, inst * 100.0)
    components["temporal"] = min(100.0, tv)

    ctx = context_result.get("score", 0.0)
    components["context"] = float(ctx)

    risk = sum(WEIGHTS[k] * components.get(k, 0.0) for k in WEIGHTS)

    # boost: very high similarity AND very high synthetic evidence -> impersonation pattern
    if speaker and synthetic_evidence is not None:
        if speaker.get("similarity", 0) >= 0.75 and synthetic_evidence >= 0.6:
            risk = min(100.0, risk + 8.0)
            notes.append("High speaker similarity combined with strong synthetic evidence matches a cloned-voice impersonation pattern.")

    risk = round(float(max(0.0, min(100.0, risk))), 1)
    band = _band(risk, settings)

    drivers = sorted(
        ({"component": k, "contribution": round(WEIGHTS[k] * components.get(k, 0.0), 1)} for k in WEIGHTS),
        key=lambda d: d["contribution"], reverse=True,
    )
    return {
        "risk_score": risk,
        "risk_level": band,
        "components": {k: round(v, 1) for k, v in components.items()},
        "weights": WEIGHTS,
        "drivers": drivers,
        "notes": notes,
    }
