"""VOXACLE FastAPI application (spec §44).

Endpoints:
  GET  /api/health              component-level health (spec §51)
  POST /api/enrollment          create reference voice profile
  GET  /api/profiles            list profiles
  DELETE /api/profiles/{id}     delete profile
  POST /api/analyze             full analysis (suspect + optional ref + context)
  POST /api/analyze/context     context-only evaluation preview
  GET  /api/analyses            list analyses (reports page)
  GET  /api/analysis/{id}       single analysis detail
  GET  /api/analysis/{id}/report.txt   text report export
  GET  /api/dashboard           aggregate stats for dashboard
  GET/POST /api/settings        configuration
  WS   /ws/analysis             near-real-time chunk streaming (spec §23)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from backend import config, database
from backend.audio import decoder, quality as quality_mod
from backend.models import aasist as aasist_mod, ecapa as ecapa_mod
from backend.analysis import temporal as temporal_mod
from backend.context import engine as context_engine
from backend.privacy import retention
from backend.pipeline import analyze
from backend.reports import report_generator
from backend.streaming.chunk_processor import ChunkSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("voxacle.api")

config.init_db()

app = FastAPI(title="VOXACLE API", version="1.0.0", docs_url="/api/docs")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.get("/api/health")
def health():
    aas = aasist_mod.wrapper.availability()
    eca = ecapa_mod.wrapper.availability()
    audio_ok = decoder.ffmpeg_available()
    components = {
        "api": "ok",
        "audio_decoder": "ok" if audio_ok else "unavailable",
        "dsp_engine": "ok",
        "aasist_l": "ok" if aas["available"] else "unavailable",
        "ecapa": "ok" if eca["available"] else "unavailable",
        "database": "ok",
        "streaming": "ok",
    }
    overall = "READY" if all(v == "ok" for v in components.values()) else (
        "DEGRADED" if any(v == "ok" for v in components.values()) else "OFFLINE"
    )
    return {
        "status": overall,
        "components": components,
        "details": {"aasist_l": aas, "ecapa": eca},
        "versions": {
            "aasist_l": aas["version"] if aas["available"] else None,
            "ecapa": eca["version"] if eca["available"] else None,
        },
        "notes": [
            "Benchmark EER figures belong to their referenced datasets and are not VOXACLE accuracy.",
            config.get_settings()["language_scope_note"],
        ],
    }


@app.post("/api/enrollment")
async def enrollment(
    file: UploadFile = File(...),
    name: str = Form(...),
    speaker_label: str = Form(""),
    notes: str = Form(""),
):
    data = await file.read()
    try:
        std = decoder.decode_to_16k_mono(data, file.filename)
    except decoder.AudioDecodeError as e:
        raise HTTPException(status_code=400, detail={"status": "error", "code": e.code, "message": str(e)}) from e
    except decoder.UnsupportedFormatError as e:
        raise HTTPException(status_code=400, detail={"status": "error", "code": e.code, "message": str(e)}) from e

    x, sr = std["waveform"], std["sample_rate"]
    q = quality_mod.analyze_quality(x, sr)
    if q["state"] == "UNUSABLE":
        raise HTTPException(status_code=400, detail={
            "status": "error", "code": "AUDIO_UNUSABLE",
            "message": "Audio quality is unusable for enrollment. Please provide a clearer recording."})

    emb = ecapa_mod.wrapper.embed(x, sr)
    if emb["status"] != "success":
        raise HTTPException(status_code=503, detail={
            "status": "unavailable", "code": "ECAPA_MODEL_UNAVAILABLE",
            "message": "Speaker enrollment requires the ECAPA-TDNN model, which is currently unavailable.",
            "detail": emb.get("error")})

    pid = database.save_profile({
        "name": name,
        "speaker_label": speaker_label or name,
        "status": "ACTIVE" if q["state"] in ("GOOD", "FAIR") else "LOW_QUALITY",
        "quality": q["state"],
        "duration_sec": q["metrics"]["duration_sec"],
        "created_at": database.utcnow_iso(),
        "embedding": emb["value"].tolist(),
        "notes": notes,
    })
    return {
        "status": "success",
        "profile_id": pid,
        "quality": q["state"],
        "duration_sec": q["metrics"]["duration_sec"],
        "embedding_dim": int(emb["value"].shape[0]),
        "model": ecapa_mod.wrapper.MODEL_VERSION,
    }


@app.get("/api/profiles")
def profiles():
    return {"status": "success", "profiles": database.list_profiles()}


@app.delete("/api/profiles/{profile_id}")
def profile_delete(profile_id: str):
    ok = database.delete_profile(profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail={"status": "error", "code": "NOT_FOUND", "message": "Profile not found."})
    return {"status": "success"}


@app.post("/api/analyze")
async def analyze_endpoint(
    file: UploadFile = File(...),
    context: str = Form("{}"),
    reference_profile_id: str = Form(""),
    reference_file: UploadFile | None = File(None),
):
    data = await file.read()
    ref_bytes = await reference_file.read() if reference_file else None
    try:
        ctx = json.loads(context or "{}")
    except json.JSONDecodeError:
        ctx = {}
    # anonymize caller id for storage (privacy layer)
    ctx_store = dict(ctx)
    if ctx_store.get("caller_id"):
        ctx_store["caller_id_masked"] = retention.anonymize_caller_id(ctx_store["caller_id"])
    result = analyze(
        data, file.filename, ctx_store,
        reference_profile_id=reference_profile_id or None,
        reference_audio_bytes=ref_bytes,
    )
    code = 200
    if result.get("classification") == "ANALYSIS FAILED":
        code = 422
    return result


@app.post("/api/analyze/context")
def analyze_context(context: dict):
    return context_engine.evaluate(context or {})


@app.get("/api/analyses")
def analyses(limit: int = 100):
    rows = database.list_analyses(limit)
    slim = []
    for r in rows:
        slim.append({
            "id": r["id"], "session_id": r["session_id"], "created_at": r["created_at"],
            "classification": r["classification"], "risk_score": r["risk_score"],
            "risk_level": r["risk_level"], "confidence": r["confidence"],
            "ai_likelihood": r["ai_likelihood"], "speaker_similarity": r["speaker_similarity"],
            "audio_quality": r["audio_quality"], "context_risk": r["context_risk"],
            "action": r["action"], "file_name": r["file_name"],
            "evidence_hash": r["evidence_hash"], "latency_ms": r["latency_ms"],
        })
    return {"status": "success", "analyses": slim}


@app.get("/api/analysis/{analysis_id}")
def analysis_detail(analysis_id: str):
    r = database.get_analysis(analysis_id)
    if not r:
        raise HTTPException(status_code=404, detail={"status": "error", "code": "NOT_FOUND", "message": "Analysis not found."})
    return r


@app.get("/api/analysis/{analysis_id}/report.txt", response_class=PlainTextResponse)
def analysis_report(analysis_id: str):
    r = database.get_analysis(analysis_id)
    if not r:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
    rep = report_generator.build_report(r, r.get("result", {}))
    return report_generator.report_text(rep)


@app.get("/api/dashboard")
def dashboard():
    stats = database.analysis_stats()
    rows = database.list_analyses(8)
    recent = [{
        "id": r["id"], "created_at": r["created_at"], "classification": r["classification"],
        "risk_level": r["risk_level"], "risk_score": r["risk_score"], "confidence": r["confidence"],
        "file_name": r["file_name"], "action": r["action"],
    } for r in rows]
    return {"status": "success", "stats": stats, "recent": recent}


@app.get("/api/settings")
def get_settings():
    return {"status": "success", "settings": config.get_settings()}


@app.post("/api/settings")
def post_settings(values: dict):
    allowed = {k: v for k, v in (values or {}).items() if k in config.DEFAULT_SETTINGS}
    updated = config.update_settings(allowed)
    return {"status": "success", "settings": updated}


@app.post("/api/privacy/cleanup")
def privacy_cleanup():
    return retention.session_cleanup()


@app.websocket("/ws/analysis")
async def ws_analysis(ws: WebSocket):
    """Near-real-time chunk streaming (spec §23).

    Protocol (JSON text frames):
      client -> {"type":"start","chunk_seconds":4.0,"sample_rate":16000}
      client -> {"type":"audio","pcm_base64": "...", "samples": N}   (f32le mono 16k)
      client -> {"type":"flush"}                                      finalize session
      server -> {"type":"chunk_result", ...} per chunk (real inference)
      server -> {"type":"session_result", ...} fused verdict
      server -> {"type":"error", ...} truthful failures only
    """
    await ws.accept()
    session: ChunkSession | None = None
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_text(json.dumps({"type": "error", "code": "BAD_JSON", "message": "Invalid JSON frame."}))
                continue
            mtype = msg.get("type")
            if mtype == "start":
                session = ChunkSession(
                    sample_rate=int(msg.get("sample_rate", 16000)),
                    chunk_seconds=float(msg.get("chunk_seconds", config.get_settings().get("chunk_seconds", 4.0))),
                )
                await ws.send_text(json.dumps({
                    "type": "started",
                    "chunk_samples": session.chunk_samples,
                    "aasist_available": aasist_mod.wrapper.is_available(),
                    "note": "Chunk results are real AASIST-L + DSP outputs.",
                }))
            elif mtype == "audio" and session is not None:
                import base64
                pcm = base64.b64decode(msg.get("pcm_base64", ""))
                arr = np.frombuffer(pcm, dtype=np.float32)
                for cr in session.push(arr):
                    await ws.send_text(json.dumps({"type": "chunk_result", **cr}))
            elif mtype == "flush" and session is not None:
                for cr in session.flush():
                    await ws.send_text(json.dumps({"type": "chunk_result", **cr}))
                verdict = session.verdict()
                await ws.send_text(json.dumps({"type": "session_result", **verdict}))
                session = None
            elif mtype == "ping":
                await ws.send_text(json.dumps({"type": "pong", "time": time.time()}))
            else:
                await ws.send_text(json.dumps({"type": "error", "code": "BAD_STATE", "message": "Unknown type or session not started."}))
    except WebSocketDisconnect:
        return
    except Exception as e:  # noqa: BLE001
        try:
            await ws.send_text(json.dumps({"type": "error", "code": "WS_INTERNAL_ERROR", "message": str(e)}))
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3030, log_level="info")
