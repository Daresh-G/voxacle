"""Evidence fusion (spec §26-§27).

INPUT:   evidence contracts from every module, each shaped:
           {"status":"success"|"unavailable", "value":..., "confidence":0..1,
            "warnings":[...], "error":...}
MATH:    reliability-weighted combination — NOT a naive average. Each source is
         weighted by its own confidence and availability; unavailable sources
         reduce total confidence and generate warnings instead of fake values.
OUTPUT:  fused synthetic evidence [0,1], availability map, disagreement flag,
         human-readable reasoning list.
"""
from __future__ import annotations

import numpy as np

# Base weights express the intended evidential priority (configurable later):
# AASIST is the dedicated synthetic detector; DSP/prosody/temporal corroborate.
BASE_WEIGHTS = {
    "aasist": 0.50,
    "temporal": 0.20,
    "dsp": 0.15,
    "prosody": 0.15,
}


def _sig(v: float) -> bool:
    return v is not None and np.isfinite(v)


def fuse(
    aasist_ev: dict,
    temporal_ev: dict,
    dsp_ev: dict,
    prosody_ev: dict,
    quality: dict,
) -> dict:
    warnings: list[str] = []
    availability: dict[str, str] = {}
    weighted_sum = 0.0
    weight_total = 0.0

    def consume(name: str, ev: dict, value_getter):
        nonlocal weighted_sum, weight_total
        st = ev.get("status")
        availability[name] = st or "unavailable"
        if st != "success":
            if ev.get("error"):
                warnings.append(f"{name}: {ev['error']}")
            for w in ev.get("warnings", []):
                warnings.append(f"{name}: {w}")
            return
        v = value_getter(ev)
        if not _sig(v):
            warnings.append(f"{name}: value missing")
            return
        conf = float(ev.get("confidence", 0) or 0)
        w = BASE_WEIGHTS.get(name, 0.1) * max(0.05, conf)
        weighted_sum += w * float(v)
        weight_total += w

    consume("aasist", aasist_ev, lambda ev: ev["value"]["synthetic_evidence"])
    consume("temporal", temporal_ev, lambda ev: (ev["value"]["stats"] or {}).get("mean_synthetic"))
    consume("dsp", dsp_ev, lambda ev: ev["value"].get("anomaly_score"))
    consume("prosody", prosody_ev, lambda ev: ev["value"].get("synthetic_regularities"))

    if weight_total <= 0:
        return {
            "status": "unavailable",
            "synthetic_evidence": None,
            "availability": availability,
            "warnings": warnings + ["No synthetic-evidence sources were available"],
            "disagreement": None,
            "reasoning": ["No synthetic-evidence source could run; analysis cannot be graded."],
            "error": "NO_EVIDENCE_SOURCES",
        }

    fused = weighted_sum / weight_total

    # coverage penalty: missing sources reduce evidential completeness
    available_frac = weight_total / sum(BASE_WEIGHTS.values())
    fused_eff = fused * (0.65 + 0.35 * available_frac)

    # --- Disagreement check (mandatory, spec §27) ---
    disagreement = False
    reasoning: list[str] = []
    a_ok = aasist_ev.get("status") == "success"
    t_stats = (temporal_ev.get("value") or {}).get("stats") if temporal_ev.get("value") else None

    if a_ok and t_stats and t_stats.get("variable_evidence"):
        disagreement = True
        reasoning.append("Temporal chunk evidence varies over time — audio may contain mixed genuine and synthetic sections.")
    prosody_val = (prosody_ev.get("value") or {}) if prosody_ev.get("value") else {}
    if a_ok and prosody_val.get("synthetic_regularities") is False and fused_eff > 0.6:
        disagreement = True
        reasoning.append("Synthetic detector output is elevated while prosody looks natural; evidence sources disagree.")
    if quality.get("state") in ("POOR", "UNUSABLE") and fused_eff > 0.5:
        disagreement = True
        reasoning.append("Detectors report synthetic evidence but audio reliability is limited; treat with caution.")

    if a_ok:
        se = aasist_ev["value"]["synthetic_evidence"]
        if se >= 0.6:
            reasoning.append(f"AASIST-L reports strong synthetic-speech evidence ({se*100:.0f}%).")
        elif se >= 0.35:
            reasoning.append(f"AASIST-L reports moderate synthetic-speech evidence ({se*100:.0f}%).")
        else:
            reasoning.append(f"AASIST-L reports low synthetic-speech evidence ({se*100:.0f}%).")
    if t_stats and t_stats.get("mean_synthetic") is not None:
        reasoning.append(
            f"Chunk-level synthetic evidence averaged {t_stats['mean_synthetic']*100:.0f}% "
            f"across {t_stats['n_chunks']} chunks (max {round((t_stats.get('max_synthetic') or 0)*100):0.0f}%)."
        )
    if available_frac < 0.999:
        reasoning.append("Some evidence sources were unavailable; overall confidence reduced accordingly.")

    return {
        "status": "success",
        "synthetic_evidence": round(float(fused_eff), 4),
        "raw_fused": round(float(fused), 4),
        "availability": availability,
        "warnings": warnings,
        "disagreement": disagreement,
        "coverage": round(available_frac, 3),
        "reasoning": reasoning,
        "error": None,
    }


def dsp_anomaly(dsp: dict, quality_state: str) -> float:
    """Derive a normalized DSP supporting-anomaly score from real features.

    Basis (supporting evidence only, spec §12-§18):
    - spectral flatness unusually high for speech (noise-like)
    - extremely low pitch variation combined with high temporal regularity
    Values are computed from actual features; never random.
    """
    score = 0.0
    feats = dsp.get("features", {})
    pros = dsp.get("prosody", {})
    flat = feats.get("spectral_flatness")
    if _sig(flat) and flat > 0.35:
        score += min(0.4, (flat - 0.35) * 1.2)
    tr = (pros.get("value") or {}).get("temporal_regularity") if pros.get("value") else None
    pv = (pros.get("value") or {}).get("pitch_variation_semitones") if pros.get("value") else None
    if _sig(tr) and _sig(pv):
        if pv < 0.8 and tr > 0.5:
            score += 0.35
        elif pv < 1.2 and tr > 0.65:
            score += 0.2
    if quality_state == "FAIR":
        score *= 0.85
    elif quality_state in ("POOR", "UNUSABLE"):
        score *= 0.5
    return round(float(min(1.0, score)), 4)
