# VOXACLE — Architecture

## Pipeline (as implemented)

```
INPUT AUDIO
  │
  ▼
INPUT VALIDATION            size ≤ 50 MB, extension allow-list, non-empty
  ▼
AUDIO DECODING              SoundFile fast-path (WAV/FLAC/OGG) → FFmpeg fallback
  ▼                         (mp3/m4a/webm/amr/3gp → PCM f32)
STANDARDIZATION             resample → 16 kHz mono, peak-safe scaling
  ▼
QUALITY GATE                duration · RMS · SNR estimate · clipping · silence
  │                         states: GOOD / FAIR / POOR / UNUSABLE
  ├─ ORIGINAL AUDIO ──► evidence store (SHA-256 hashed, policy-gated)
  └─ ANALYSIS COPY ──► gentle DC/rumble removal ONLY (aggressive filtering
       │                is forbidden: artifacts may be the evidence)
       ▼
CORE ANALYSIS ENGINE
  ├─ DSP (deterministic)   RMS, Energy, ZCR, FFT, STFT, centroid/bandwidth/
  │                        rolloff/flatness, MFCC(13), SNR
  ├─ AASIST-L              raw-waveform synthetic-speech detector
  │                        (first 64,600 samples @16 kHz, tile-padded;
  │                         logits[:,1]=bona-fide → synthetic = 1−σ(logit))
  ├─ ECAPA-TDNN            192-d speaker embedding; cosine(ref, suspect);
  │                        HIGH ≥ 0.75 · MEDIUM ≥ 0.55 (configurable)
  └─ PROSODY               pyin pitch stats, energy CV, pause structure,
                           temporal regularity (autocorr of energy envelope)
       ▼
CHUNK / TEMPORAL ANALYSIS   ~4 s windows aligned to AASIST input;
                            per-chunk REAL inference; mixed-audio support
       ▼
EVIDENCE FUSION             reliability-weighted (not naive average);
                            every source carries status/value/confidence/warnings
       ▼
DISAGREEMENT CHECK          temporal variability · prosody-vs-AASIST conflict ·
                            quality-vs-evidence conflict → warnings, not cover-ups
       ▼
CONFIDENCE ENGINE           f(quality, duration, coverage, availability, agreement)
       ▼                     ≠ AI likelihood ≠ risk score (never conflated)
CONTEXT MODULE              caller origin/ID, known contact, channel, claimed
(separate until risk)       identity, txn type/amount, fraud indicator
       ▼
RISK ENGINE                 0-100 product scale, configurable weights,
                            impersonation-pattern boost (high sim + high synthetic)
       ▼
POLICY / ACTION ENGINE      LOW→ALLOW · MEDIUM→WARN · HIGH→VERIFY · CRITICAL→BLOCK
       ▼
ALERT + REPORT              SQLite record + text report + evidence hash
       ▼
FRONTEND (Next.js)          decision-first UI; technical detail behind
                            "Advanced Analysis"
```

## Separation of concerns

- **AI/ML models** (trained NN inference): AASIST-L, ECAPA-TDNN.
- **Not AI** (deterministic computation): the entire DSP engine, quality gate,
  fusion, confidence, risk, context, policy, privacy layers. These are rules
  and mathematics — described accurately as such in the UI.

## Failure handling

| Failure | Behavior |
|---|---|
| Corrupt/unsupported audio | `ANALYSIS FAILED` + `AUDIO_DECODE_ERROR` / `UNSUPPORTED_FORMAT` |
| Silent / <0.2 s audio | quality `UNUSABLE` → `INCONCLUSIVE`, risk display suppressed |
| AASIST-L load/inference error | evidence contract `MODEL_UNAVAILABLE`; fusion proceeds with remaining sources; confidence capped down |
| ECAPA error | speaker similarity `N/A`; similarity weight removed from risk |
| Evidence disagreement | `SUSPICIOUS`/`INCONCLUSIVE` + explicit warning text |

No code path fabricates a score. Grep for `random`, `_simulated`, or hardcoded
confidence values in `backend/` — detection outputs come only from loaded models.

## Storage

- SQLite (`backend/data/voxacle.db`): analyses (slim payload; advanced DSP
  matrices stay in the response only), profiles (ECAPA embeddings only — no
  audio), settings.
- Evidence dir (`backend/data/evidence/<session>/`): original bytes, SHA-256
  hashed, kept only when `store_original_audio` policy is enabled.
- Retention: `privacy.session_cleanup()` deletes analyses older than
  `retention_hours` (default 24 h) — callable from Settings.
