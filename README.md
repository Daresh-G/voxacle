# VOXACLE — AI-Based Voice Cloning Impersonation Detection

VOXACLE analyzes an incoming voice and determines whether the audio contains
evidence consistent with **genuine human speech**, **synthetic / AI-generated
speech**, **cloned-voice impersonation**, or is **uncertain / insufficient
quality**. It never collapses a technical failure into a fake score.

> VOXACLE does not depend on a single AI detector. It combines signal-level
> mathematical evidence, synthetic-speech detection (AASIST-L), speaker
> consistency (ECAPA-TDNN), temporal behavior, audio quality, contextual risk
> and policy rules to produce an explainable voice-integrity decision.

## What VOXACLE answers

| Question | Component |
|---|---|
| WHO is speaking? | ECAPA-TDNN speaker embedding + cosine similarity |
| Is the voice SYNTHETIC / spoofed? | AASIST-L anti-spoofing inference |
| What does the SIGNAL look like? | Deterministic DSP (RMS, ZCR, FFT, STFT, MFCC, SNR, prosody) |
| What SHOULD the user do? | Context + risk engine + policy/action engine |

## Result states (truthful by design)

🟢 GENUINE · 🟡 SUSPICIOUS · 🔴 HIGH RISK · ⚪ INCONCLUSIVE · ⚫ ANALYSIS FAILED

- Unavailable model → `MODEL_UNAVAILABLE` (confidence reduced, no substitute value)
- Unusable audio → `INCONCLUSIVE` (never forced to HIGH RISK)
- Corrupt input → `ANALYSIS FAILED` with a structured error code

## Architecture (implemented)

```
INPUT AUDIO → validation → decoding (FFmpeg/SoundFile) → standardization (16 kHz mono)
  → quality gate (GOOD/FAIR/POOR/UNUSABLE) → original preserved / analysis copy
  → CORE ANALYSIS: DSP + AASIST-L + ECAPA-TDNN + prosody
  → chunk/temporal analysis (~4 s windows, real per-chunk inference)
  → evidence fusion (reliability-weighted) → disagreement check
  → confidence engine → risk engine (+ context module) → policy engine
  → ALLOW / WARN / VERIFY / BLOCK → alert + report → frontend
```

## Models (real, verified artifacts)

- **AASIST-L** — `SpeechAntiSpoofingBenchmarks/AASIST-L` (Hugging Face).
  Raw-waveform input, deterministic first 64,600-sample window @ 16 kHz.
  `logits[:,1]` = bona-fide logit → synthetic evidence = `1 − σ(logit)`.
  Benchmark EER 0.99% (ASVspoof2019 LA) is a **dataset benchmark**, not VOXACLE accuracy.
- **ECAPA-TDNN** — `speechbrain/spkrec-ecapa-voxceleb`. 192-d embeddings,
  cosine similarity, configurable consistency thresholds.

See `MODEL_SETUP.md`, `ARCHITECTURE.md`, `API.md`, `TESTING.md`, `PRIVACY.md`.

## Layout

```
backend/                  Python FastAPI analysis service (port 3030)
  audio/                  decoder · standardizer · quality gate · filters
  signal/                 time-domain · frequency · spectral · MFCC · prosody
  models/aasist|ecapa/    verified real-inference wrappers
  analysis/               temporal · evidence fusion · confidence · risk
  context/ · policy/ · privacy/ · streaming/ · reports/
  main.py                 FastAPI app (REST + WebSocket)
src/                      Next.js 16 frontend (7-view dashboard, port 3000)
scripts/setup_models.py   model bootstrap with checksums + load tests
scripts/start_backend.sh  detached backend launcher
```

## Running

```bash
# 1. backend dependencies (CPU torch recommended)
pip install -r backend/requirements.txt

# 2. download + verify models (~85 MB)
python3 scripts/setup_models.py

# 3. start analysis backend
bash scripts/start_backend.sh          # or: uvicorn backend.main:app --port 3030

# 4. frontend
bun install && bun run dev             # Next.js on :3000
```

The Next.js server also auto-spawns the backend on boot (`src/instrumentation.ts`).
When a gateway (Caddy) fronts both services, the browser reaches the Python API
via `?XTransformPort=3030`.

## Scope & limitations (honest)

- Designed for multilingual / Indian-accent robustness; **target-language
  validation is required** before deployment claims.
- Benchmark numbers belong to their datasets; VOXACLE's own accuracy is
  unvalidated until tested on the target environment.
- Policy actions are recommendations; blocking real bank transfers requires a
  banking integration.
- Near-real-time = chunked processing (4 s windows), not zero-latency.
