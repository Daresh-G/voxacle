# MODEL SETUP

All artifacts are downloaded from **official sources only** and verified before
use. The app never invents checkpoints and never silently swaps model versions.

## Sources (verified)

| Model | Source | Files |
|---|---|---|
| AASIST-L | https://huggingface.co/SpeechAntiSpoofingBenchmarks/AASIST-L | `AASIST-L.pth` · `aasist_l.py` · `_net.py` · `README.md` · `meta.yaml` |
| ECAPA-TDNN | https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb | `embedding_model.ckpt` · `hyperparams.yaml` · `config.json` · `classifier.ckpt` · `label_encoder.txt` · `mean_var_norm_emb.ckpt` |

## Bootstrap

```bash
python3 scripts/setup_models.py
```

Steps performed: create dirs → download missing files → SHA-256 manifest
(`backend/models_store/checksums.txt`) → strict state-dict load of AASIST-L →
ECAPA load + 1 s inference smoke test → print truthful status. Exit code 2 if
any model fails (the backend still starts and reports `MODEL_UNAVAILABLE`
rather than pretending).

## Verified semantics

**AASIST-L** (read from the repo's own wrapper `aasist_l.py` + README):
- input: mono 16 kHz float32, deterministic **first 64,600-sample** window,
  tile-padded if shorter (matches clovaai/aasist `data_utils.pad()` at eval)
- forward returns `(hidden, logits)`; **`logits[:,1]` = bona-fide logit**
- synthetic evidence = `1 − sigmoid(bonafide_logit)` ∈ [0,1]
- architecture config (lightweight variant): `filts [70,[1,32],[32,32],[32,24],[24,24]]`,
  `gat_dims [24,32]`, `pool_ratios [0.4,0.5,0.7,0.5]`, `temperatures [2,2,100,100]`
- 85,306 parameters; strict `load_state_dict` verified at setup

**ECAPA-TDNN** (SpeechBrain `EncoderClassifier`):
- input: mono 16 kHz float32 tensor
- output: 192-d embedding (`encode_batch`), L2-normalizable
- similarity: cosine `(a·b)/(‖a‖‖b‖)`; consistency labels via configurable
  thresholds (Settings: `speaker_high` 0.75 / `speaker_medium` 0.55)

## Runtime load behavior

`backend/models/*/wrapper.py` lazily loads each model once (thread-safe). If
loading fails, availability() reports the error string and every inference
request returns the contract:

```json
{"status":"unavailable","value":null,"confidence":0,
 "warnings":["AASIST-L is unavailable on this system"],
 "error":"MODEL_UNAVAILABLE"}
```

`GET /api/health` exposes per-component availability + version/checkpoint IDs
for traceability (spec §48/§51). Checkpoint files live under
`backend/models_store/{aasist,ecapa}/`.
