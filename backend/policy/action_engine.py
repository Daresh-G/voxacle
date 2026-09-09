"""Policy / action engine (spec §31).

Configurable mapping from risk band to recommended action. The prototype
produces a RECOMMENDATION — it cannot actually block a bank transfer without a
real banking integration (this is stated honestly in the UI copy).
"""
from __future__ import annotations

from backend import config

ACTIONS = {
    "LOW": {
        "action": "ALLOW",
        "title": "Continue normally",
        "detail": "No synthetic-voice indicators elevated. Standard logging applies.",
    },
    "MEDIUM": {
        "action": "WARN",
        "title": "Stay alert",
        "detail": "Some indicators are elevated. Continue with increased attention; avoid sharing sensitive data.",
    },
    "HIGH": {
        "action": "VERIFY",
        "title": "Verify caller using another trusted channel",
        "detail": "Elevated impersonation pattern. Call the person back on a known/official number before acting on any request.",
    },
    "CRITICAL": {
        "action": "BLOCK",
        "title": "Block sensitive action and escalate",
        "detail": "Strong cloned-impersonation indicators. Do not proceed with transactions; escalate to security/fraud team.",
    },
}


def decide(risk_level: str, classification: str, settings: dict | None = None) -> dict:
    s = settings or config.get_settings()
    if classification == "INCONCLUSIVE":
        return {
            "action": "VERIFY",
            "title": "Capture a clearer recording",
            "detail": "Evidence was insufficient or unreliable. Re-capture audio with better quality before deciding.",
        }
    if classification == "ANALYSIS FAILED":
        return {
            "action": "RETRY_LATER",
            "title": "Analysis could not complete",
            "detail": "A required component failed. Check System Health and retry — no result is shown because none could be computed.",
        }
    key = {"LOW": "policy_low", "MEDIUM": "policy_medium", "HIGH": "policy_high", "CRITICAL": "policy_critical"}.get(
        risk_level, "policy_medium"
    )
    act = s.get(key, ACTIONS[risk_level]["action"])
    payload = dict(ACTIONS[risk_level])
    payload["action"] = act
    return payload
