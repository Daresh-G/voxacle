# API

Base URL: FastAPI on port **3030** (`/api/docs` for OpenAPI UI). Behind the
Caddy gateway the browser uses `?XTransformPort=3030`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | per-component health (`api`, `audio_decoder`, `dsp_engine`, `aasist_l`, `ecapa`, `database`, `streaming`) + overall READY/DEGRADED/OFFLINE + model versions + scope notes |
| POST | `/api/enrollment` | multipart `file` + `name` + `speaker_label` → ECAPA 192-d profile |
| GET | `/api/profiles` | list profiles (no raw embeddings in list view) |
| DELETE | `/api/profiles/{id}` | delete profile |
| POST | `/api/analyze` | multipart: `file` (suspect), `context` (JSON string), optional `reference_profile_id` or `reference_file` → full result payload |
| POST | `/api/analyze/context` | evaluate context JSON only (preview) |
| GET | `/api/analyses?limit=` | report rows |
| GET | `/api/analysis/{id}` | stored analysis record |
| GET | `/api/analysis/{id}/report.txt` | plain-text Voice Integrity Report |
| GET | `/api/dashboard` | stats + recent analyses |
| GET/POST | `/api/settings` | read / update configurable thresholds & policy |
| POST | `/api/privacy/cleanup` | run retention cleanup now |
| WS | `/ws/analysis` | near-real-time chunk streaming |

## Analyze result (abridged)

```json
{
  "classification": "GENUINE | SUSPICIOUS | HIGH RISK | INCONCLUSIVE | ANALYSIS FAILED",
  "risk_score": 19.3, "risk_level": "LOW",
  "confidence": 93.4, "confidence_label": "HIGH",
  "ai_likelihood_percent": 15.2, "ai_likelihood_label": "MODERATE",
  "speaker_similarity": {"similarity": 0.9978, "similarity_percent": 99.8, "consistency": "HIGH"},
  "audio_quality": "GOOD", "context_risk": "HIGH",
  "fusion": {"availability": {...}, "disagreement": false, "coverage": 0.8},
  "reasoning": {"synthetic_evidence": "MODERATE", "speaker_consistency": "...",
                "temporal": "NORMAL", "audio_quality": "GOOD",
                "context": "HIGH", "confidence": "HIGH", "lines": ["..."]},
  "warnings": ["..."], "evidence_hash": "sha256…", "latency_ms": 1734.7,
  "model_versions": {...},
  "advanced": {"waveform": …, "rms_curve": …, "spectrum": …, "spectrogram": …,
               "mfcc": …, "pitch_curve": …, "chunks": […], "temporal_stats": …,
               "dsp_metrics": …, "aasist": …, "ecapa_status": …}
}
```

## Error contract

```json
{"status":"error","code":"AUDIO_TOO_SHORT","message":"…","retryable":false}
{"status":"unavailable","code":"AASIST_MODEL_UNAVAILABLE","message":"…","retryable":true}
```

## WebSocket `/ws/analysis`

```text
client: {"type":"start","sample_rate":16000,"chunk_seconds":4.0}
server: {"type":"started","chunk_samples":64000,"aasist_available":true,…}
client: {"type":"audio","pcm_base64":"<f32le mono 16k>","samples":16000}   (repeat)
server: {"type":"chunk_result","t0":0,"t1":4,"synthetic":0.42,"quality":"GOOD",…}
client: {"type":"flush"}
server: {"type":"session_result","classification":"SUSPICIOUS",
         "synthetic_evidence":0.44,"confidence":71.4,"n_chunks":3}
```

Errors are sent as `{"type":"error","code":…,"message":…}` — never as fake scores.
