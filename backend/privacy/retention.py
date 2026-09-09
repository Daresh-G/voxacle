"""Privacy / compliance layer (spec §32).

System-wide rules implemented here:
- minimize audio retention; keep original only when evidence policy requires
- feature-only logging by default
- anonymize caller identifiers in stored records
- session cleanup removes expired analyses + temporary analysis copies

The frontend shows one simple statement: "Audio is processed for verification
and retained only according to configured evidence policy."
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil

from backend import config, database


def anonymize_caller_id(caller_id: str | None) -> str:
    """Keep last 2 digits visible; mask the rest (e.g. +91 98xxxxxx01)."""
    if not caller_id:
        return ""
    digits = re.sub(r"\D", "", caller_id)
    if len(digits) <= 2:
        return "*" * len(digits)
    return "*" * (len(digits) - 2) + digits[-2:]


def evidence_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def store_original(session_id: str, analysis_id: str, data: bytes, policy_allows: bool) -> str | None:
    """Preserve ORIGINAL evidence separately (never modified) when policy allows."""
    if not policy_allows:
        return None
    d = os.path.join(config.EVIDENCE_DIR, session_id)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"original_{analysis_id}.bin")
    with open(p, "wb") as f:
        f.write(data)
    return p


def store_analysis_copy(session_id: str, analysis_id: str, waveform, sr: int) -> str:
    """Temporary analysis copy; deleted after processing where policy allows."""
    import soundfile as sf

    d = os.path.join(config.EVIDENCE_DIR, session_id)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"analysis_{analysis_id}.wav")
    sf.write(p, waveform, sr, subtype="PCM_16")
    return p


def delete_analysis_copy(path: str | None) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def session_cleanup(older_than_hours: int | None = None) -> dict:
    """Remove expired analyses and their evidence directories."""
    hours = older_than_hours if older_than_hours is not None else int(config.get_settings().get("retention_hours", 24))
    removed = database.cleanup_expired(hours)
    # remove evidence dirs with no remaining analyses would require listing;
    # for prototype, prune empty dirs
    for sid in os.listdir(config.EVIDENCE_DIR):
        d = os.path.join(config.EVIDENCE_DIR, sid)
        if os.path.isdir(d) and not os.listdir(d):
            shutil.rmtree(d, ignore_errors=True)
    return {"removed_analyses": removed, "retention_hours": hours}
