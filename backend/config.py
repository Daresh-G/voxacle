"""VOXACLE configuration.

All thresholds are configurable (spec §63) and must NOT be presented as
universal scientific truths (spec §29). Settings persist to SQLite and can be
changed at runtime from the Settings page.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "voxacle.db")
EVIDENCE_DIR = os.path.join(BASE_DIR, "data", "evidence")
MODELS_STORE = os.path.join(BASE_DIR, "models_store")
AASIST_DIR = os.path.join(MODELS_STORE, "aasist")
ECAPA_DIR = os.path.join(MODELS_STORE, "ecapa")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EVIDENCE_DIR, exist_ok=True)

# Internal standard representation (spec §4/§5)
TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1
AASIST_WINDOW_SAMPLES = 64600          # documented AASIST-L evaluation window
MAX_UPLOAD_BYTES = 50 * 1024 * 1024    # 50 MB (spec §67 security)
MIN_SPEECH_SECONDS = 0.6               # below this -> AUDIO_TOO_SHORT

DEFAULT_SETTINGS: dict[str, Any] = {
    # Risk engine thresholds (0-100 UX scale)
    "risk_low_max": 30,
    "risk_medium_max": 55,
    "risk_high_max": 75,          # above -> CRITICAL
    # ECAPA speaker similarity cosine thresholds (configurable, spec §9)
    "speaker_high": 0.75,
    "speaker_medium": 0.55,
    # Confidence engine
    "confidence_poor_quality_cap": 55,   # cap analysis confidence when quality POOR
    "confidence_disagreement_penalty": 15,
    # Chunking (spec §23) — chunk seconds for temporal analysis
    "chunk_seconds": 4.0,
    # Policy mapping (spec §31)
    "policy_low": "ALLOW",
    "policy_medium": "WARN",
    "policy_high": "VERIFY",
    "policy_critical": "BLOCK",
    # Privacy (spec §32)
    "retention_hours": 24,
    "store_original_audio": True,
    "feature_only_logging": True,
    # General
    "log_level": "INFO",
    "language_scope_note": "VOXACLE is designed for multilingual and Indian-accent robustness and requires target-language validation.",
}

_lock = threading.Lock()
_cache: dict[str, Any] | None = None


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                classification TEXT NOT NULL,
                risk_score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                confidence REAL NOT NULL,
                ai_likelihood REAL,
                speaker_similarity REAL,
                audio_quality TEXT,
                context_risk TEXT,
                context_risk_score REAL,
                warnings TEXT NOT NULL DEFAULT '[]',
                model_versions TEXT NOT NULL DEFAULT '{}',
                evidence_hash TEXT,
                latency_ms REAL,
                has_reference INTEGER NOT NULL DEFAULT 0,
                result_json TEXT NOT NULL,
                file_name TEXT,
                action TEXT
            );
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                speaker_label TEXT NOT NULL,
                status TEXT NOT NULL,
                quality TEXT,
                duration_sec REAL,
                created_at TEXT NOT NULL,
                embedding TEXT NOT NULL,
                notes TEXT
            );
            """
        )


def get_settings() -> dict[str, Any]:
    global _cache
    with _lock:
        if _cache is not None:
            return dict(_cache)
        out = dict(DEFAULT_SETTINGS)
        with _conn() as c:
            rows = c.execute("SELECT key, value FROM settings").fetchall()
        for r in rows:
            try:
                out[r["key"]] = json.loads(r["value"])
            except Exception:  # noqa: BLE001
                out[r["key"]] = r["value"]
        _cache = out
        return dict(out)


def set_setting(key: str, value: Any) -> None:
    global _cache
    with _lock:
        with _conn() as c:
            c.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value)),
            )
        _cache = None


def update_settings(values: dict[str, Any]) -> dict[str, Any]:
    for k, v in values.items():
        if k in DEFAULT_SETTINGS:
            set_setting(k, v)
    return get_settings()
