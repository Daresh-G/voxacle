# PRIVACY & COMPLIANCE

Privacy wraps the entire pipeline (it is a system layer, not a feature).

## Data minimization

- **Voice profiles** store only the 192-d ECAPA embedding + label/metadata.
  Raw enrollment audio is **not** persisted.
- **Analyses** store decision fields (classification, scores, warnings, model
  versions, evidence hash) and a slim result JSON. Large DSP matrices
  (spectrogram/MFCC) are response-only, not stored.
- Original audio is written to `backend/data/evidence/<session>/original_*.bin`
  **only** when the `store_original_audio` policy is enabled; temporary
  analysis copies are deleted after processing.

## Anonymization

Caller IDs are masked before storage: `+91 98765 43210 → *******43210`
(`privacy.anonymize_caller_id`). Context reasoning in the UI uses masked forms.

## Retention

- `retention_hours` (default 24) governs analysis records.
- `POST /api/privacy/cleanup` (also runnable from Settings) deletes expired
  rows and prunes empty evidence directories.

## Processing disclosure

The UI shows one simple statement during analysis:
"Audio is processed for verification and retained only according to the
configured evidence policy." No legal wall during the workflow.

## Deployment honesty

- The current prototype runs **server-side** inference; edge/on-device
  deployment is an architectural option, not a claim.
- Multilingual/Indian-accent robustness is a design goal; **target-language
  validation is required** before any deployment claim.
- No accuracy/performance numbers are claimed beyond labeled third-party
  benchmark results.
