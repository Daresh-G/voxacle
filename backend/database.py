"""SQLite helpers for analyses, profiles and sessions (spec §46)."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from backend import config


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(config.DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_analysis(record: dict[str, Any]) -> str:
    rid = record.get("id") or new_id()
    with _conn() as c:
        c.execute(
            """INSERT INTO analyses
               (id, session_id, created_at, classification, risk_score, risk_level,
                confidence, ai_likelihood, speaker_similarity, audio_quality,
                context_risk, context_risk_score, warnings, model_versions,
                evidence_hash, latency_ms, has_reference, result_json, file_name, action)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rid,
                record["session_id"],
                record.get("created_at") or utcnow_iso(),
                record["classification"],
                record["risk_score"],
                record["risk_level"],
                record["confidence"],
                record.get("ai_likelihood"),
                record.get("speaker_similarity"),
                record.get("audio_quality"),
                record.get("context_risk"),
                record.get("context_risk_score"),
                json.dumps(record.get("warnings", [])),
                json.dumps(record.get("model_versions", {})),
                record.get("evidence_hash"),
                record.get("latency_ms"),
                1 if record.get("has_reference") else 0,
                json.dumps(record.get("result", record)),
                record.get("file_name"),
                record.get("action"),
            ),
        )
    return rid


def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM analyses WHERE id=?", (analysis_id,)).fetchone()
    return _row_to_dict(r) if r else None


def list_analyses(limit: int = 100) -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM analyses ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    d["warnings"] = json.loads(d.get("warnings") or "[]")
    d["model_versions"] = json.loads(d.get("model_versions") or "{}")
    try:
        d["result"] = json.loads(d.get("result_json") or "{}")
    except Exception:  # noqa: BLE001
        d["result"] = {}
    d.pop("result_json", None)
    d["has_reference"] = bool(d.get("has_reference"))
    return d


def analysis_stats() -> dict[str, Any]:
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) n FROM analyses").fetchone()["n"]
        susp = c.execute(
            "SELECT COUNT(*) n FROM analyses WHERE classification IN ('SUSPICIOUS')"
        ).fetchone()["n"]
        high = c.execute(
            "SELECT COUNT(*) n FROM analyses WHERE classification IN ('HIGH RISK')"
        ).fetchone()["n"]
        genuine = c.execute(
            "SELECT COUNT(*) n FROM analyses WHERE classification = 'GENUINE'"
        ).fetchone()["n"]
        inconclusive = c.execute(
            "SELECT COUNT(*) n FROM analyses WHERE classification IN ('INCONCLUSIVE','ANALYSIS FAILED')"
        ).fetchone()["n"]
        avg_risk = c.execute("SELECT AVG(risk_score) a FROM analyses").fetchone()["a"]
    return {
        "total": total,
        "suspicious": susp,
        "high_risk": high,
        "genuine": genuine,
        "inconclusive_or_failed": inconclusive,
        "avg_risk": round(avg_risk, 1) if avg_risk is not None else None,
    }


def save_profile(record: dict[str, Any]) -> str:
    pid = record.get("id") or new_id()
    with _conn() as c:
        c.execute(
            """INSERT INTO profiles (id, name, speaker_label, status, quality,
               duration_sec, created_at, embedding, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                pid,
                record["name"],
                record["speaker_label"],
                record["status"],
                record.get("quality"),
                record.get("duration_sec"),
                record.get("created_at") or utcnow_iso(),
                json.dumps(record["embedding"]),
                record.get("notes"),
            ),
        )
    return pid


def list_profiles() -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM profiles ORDER BY created_at DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        emb = json.loads(d["embedding"])
        d["embedding"] = emb
        d["embedding_dim"] = len(emb)
        d.pop("embedding", None)  # do not ship raw vectors to list views
        out.append(d)
    return out


def get_profile(profile_id: str) -> dict[str, Any] | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM profiles WHERE id=?", (profile_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["embedding"] = json.loads(d["embedding"])
    return d


def delete_profile(profile_id: str) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM profiles WHERE id=?", (profile_id,))
    return cur.rowcount > 0


def cleanup_expired(retention_hours: int) -> int:
    """Privacy: remove analysis rows older than retention window (spec §32)."""
    cutoff = (
        (datetime.now(timezone.utc) - timedelta(hours=retention_hours)).isoformat()
    )
    with _conn() as c:
        cur = c.execute("DELETE FROM analyses WHERE created_at < ?", (cutoff,))
    return cur.rowcount
