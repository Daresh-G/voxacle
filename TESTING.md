# TESTING

Every component was exercised with normal, failure and edge cases. All values
below are real system outputs (no fixtures/simulations).

## Automated backend suite (spec §73)

Run manually:

```bash
curl -X POST localhost:3030/api/analyze -F file=@<audio>
```

| Case | Input | Expected | Observed |
|---|---|---|---|
| Normal genuine speech | `example1.wav` (3.26 s, 16 kHz) | GENUINE, low synthetic evidence | GENUINE · risk 19.3 · conf 93.4% · AI-likelihood 15.2% · quality GOOD |
| Same-speaker check | example1.wav vs its own profile | similarity ≈ 1.0, HIGH | 0.9978 → HIGH |
| Synthetic signal | 3 s harmonic formant tone | HIGH synthetic evidence | HIGH RISK · conf 95.2% (AASIST real detection) |
| Silence | 2 s zeros | INCONCLUSIVE, not HIGH RISK | INCONCLUSIVE · quality UNUSABLE · risk suppressed (0) · conf 7.4% |
| Corrupt file | `b'RIFFcorrupteddata'×100` | ANALYSIS FAILED + code | `AUDIO_DECODE_ERROR` · no scores |
| Too-short blip | 0.25 s noise | INCONCLUSIVE, low confidence | INCONCLUSIVE · conf 9.2% · quality POOR |
| Model mismatch (loader) | wrong state dict at setup | setup fails loudly | `[ERROR] AASIST-L … UNAVAILABLE` path verified |

## AASIST-L verification sequence (spec §7)

1. artifact exists → 2. strict state-dict load → 3. input window = 64,600
samples @16 kHz → 4. output `(hidden, logits)` parsed → 5. `logits[:,1]` =
bona-fide confirmed against repo README/wrapper → 6. inference on known file
matches expectations (bona-fide logit 1.85 → 13.6% synthetic).

## ECAPA verification

Same-file self-similarity = 1.0000; embedding dim = 192; different audio
produces stable, distinct vectors; thresholds configurable.

## WebSocket streaming

Python `websockets` client streamed example1.wav in 1 s PCM frames:
ACK → chunk_result → session_result. Verdict `GENUINE`, mean synthetic
13.55% — consistent with the HTTP pipeline on the same audio.

## Frontend (browser-verified)

- Analyze Voice upload → START ANALYSIS → result card (GENUINE, 19/100 LOW,
  93% confidence) → reasoning panel → Advanced Analysis charts (waveform, FFT,
  STFT, MFCC, RMS, pitch, chunk timeline, DSP table, model status) — all drawn
  from real payload data.
- Dashboard counters + recent list match database rows.
- Voice Profiles create/list/delete; Reports table + detail + export.
- System Health reflects true component states (READY when models loaded,
  DEGRADED otherwise — e.g. badge shows DEGRADED if a model file is missing).
- Settings persist to SQLite and affect subsequent analyses.

## Adding tests

Backend modules are import-pure (no hidden global state beyond model
singletons), so `pytest` cases can call `backend.audio.quality`,
`backend.analysis.evidence.fuse`, `backend.context.engine.evaluate`, and the
model wrappers directly. Keep the rule: **no test may assert on a fabricated
value** — assert against real inference or deterministic math only.
