---
license: mit
tags:
  - audio
  - anti-spoofing
  - audio-deepfake-detection
  - speech
  - asvspoof
---

# AASIST-L

[![EER% 0.99 on ASVspoof2019_LA](https://img.shields.io/badge/EER%25%20on%20ASVspoof2019__LA-0.99%25-brightgreen)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 13.15 on ASVspoof2021_LA](https://img.shields.io/badge/EER%25%20on%20ASVspoof2021__LA-13.15%25-yellow)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 15.96 on ASVspoof2021_DF](https://img.shields.io/badge/EER%25%20on%20ASVspoof2021__DF-15.96%25-yellow)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 44.45 on InTheWild](https://img.shields.io/badge/EER%25%20on%20InTheWild-44.45%25-red)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 50.72 on CD-ADD](https://img.shields.io/badge/EER%25%20on%20CD--ADD-50.72%25-red)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 51.55 on SONAR](https://img.shields.io/badge/EER%25%20on%20SONAR-51.55%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 37.07 on LibriSeVoc](https://img.shields.io/badge/EER%25%20on%20LibriSeVoc-37.07%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 47.40 on CFAD](https://img.shields.io/badge/EER%25%20on%20CFAD-47.40%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 57.45 on CVoiceFake_small](https://img.shields.io/badge/EER%25%20on%20CVoiceFake__small-57.45%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 37.53 on ASVspoof5](https://img.shields.io/badge/EER%25%20on%20ASVspoof5-37.53%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 49.68 on DeepVoice](https://img.shields.io/badge/EER%25%20on%20DeepVoice-49.68%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 47.52 on ArAD](https://img.shields.io/badge/EER%25%20on%20ArAD-47.52%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 28.99 on DECRO](https://img.shields.io/badge/EER%25%20on%20DECRO-28.99%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 40.26 on J-SPAW_LA](https://img.shields.io/badge/EER%25%20on%20J--SPAW__LA-40.26%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 47.14 on ODSS](https://img.shields.io/badge/EER%25%20on%20ODSS-47.14%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 34.84 on HABLA](https://img.shields.io/badge/EER%25%20on%20HABLA-34.84%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 32.72 on DFADD](https://img.shields.io/badge/EER%25%20on%20DFADD-32.72%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 30.78 on PyAra](https://img.shields.io/badge/EER%25%20on%20PyAra-30.78%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 50.38 on XMAD](https://img.shields.io/badge/EER%25%20on%20XMAD-50.38%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![1-SRR% 31.86 on LRLspoof](https://img.shields.io/badge/1--SRR%25%20on%20LRLspoof-31.86%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 28.26 on ADD22_eval_31](https://img.shields.io/badge/EER%25%20on%20ADD22__eval__31-28.26%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 45.43 on ADD2023_track12_test_r1](https://img.shields.io/badge/EER%25%20on%20ADD2023__track12__test__r1-45.43%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![EER% 12.63 on EmoFake_test](https://img.shields.io/badge/EER%25%20on%20EmoFake__test-12.63%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![1-SRR% 69.08 on EmoSpoofTTS](https://img.shields.io/badge/1--SRR%25%20on%20EmoSpoofTTS-69.08%25-lightgrey)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![arena tier](https://img.shields.io/endpoint?url=https://speechantispoofingbenchmarks-speechantispoofingarena.hf.space/badge/aasist-l/tier.json)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)
[![arena rank](https://img.shields.io/endpoint?url=https://speechantispoofingbenchmarks-speechantispoofingarena.hf.space/badge/aasist-l/rank.json)](https://huggingface.co/spaces/SpeechAntiSpoofingBenchmarks/SpeechAntiSpoofingArena?system=aasist-l)

AASIST-L is the **lightweight variant** of AASIST audio anti-spoofing
(voice-deepfake detection) from *"AASIST: Audio Anti-Spoofing using Integrated
Spectro-Temporal Graph Attention Networks"* (Jung et al., ICASSP 2022). It uses
the upstream [clovaai/aasist](https://github.com/clovaai/aasist) ASVspoof2019 LA
pretrained `AASIST-L` checkpoint. The model takes a raw speech waveform and
returns a score where **higher = more bona fide**.

- **Code:** https://github.com/clovaai/aasist
- **Paper:** https://arxiv.org/abs/2110.01200
- **Parameters:** 85,306 (0.085 M)
- **Checkpoint:** [`AASIST-L.pth`](./AASIST-L.pth)

This repo is self-contained for inference: the network definition is in
[`_net.py`](./_net.py) (identical to the full AASIST) and the exact wrapper used
to produce the Arena scores in [`aasist_l.py`](./aasist_l.py). AASIST-L shares
the AASIST architecture but with a narrower residual stack and graph dimensions
(~85k params vs ~298k).

## Architecture

AASIST operates directly on the raw waveform: a sinc-convolution front-end and a
RawNet2-style residual encoder produce a spectro-temporal feature map, which is
modelled by heterogeneous stacking graph attention layers over spectral and
temporal sub-graphs with a learnable max/average readout, followed by a 2-class
output (bona fide vs. spoof). The Arena score is the bona-fide logit. The "-L"
variant narrows the residual channels (`…[32,24],[24,24]`) and graph dims
(`[24,32]`).

## Reproducing the Arena scores

Inference uses a deterministic first-64600-sample window (no random crop),
matching the upstream `data_utils.pad()` used at eval. Audio is provided as
float32 mono at 16 kHz (no resampling in the wrapper).

```python
from aasist_l import AASIST_L
m = AASIST_L(); m.load()
scores = m.score_batch([wav], [16000])   # higher = more bona fide
```

| Dataset | EER % | n_trials |
|---------|------:|---------:|
| ASVspoof2019_LA (in-domain) | 0.99 | 71,237 |
| ASVspoof2021_LA | 13.15 | 181,566 |
| ASVspoof2021_DF | 15.96 | 611,829 |
| InTheWild | 44.45 | 31,779 |
| CD-ADD | 50.72 | 20,786 |

The in-domain ASVspoof2019 LA result (~0.99%) reproduces the paper's reported
AASIST-L EER. AASIST-L matches the full AASIST closely at ~3.5× fewer parameters.

## License

MIT (inherited from clovaai/aasist; see [`LICENSE`](./LICENSE)).

## Maintainer

Maintained by Kirill Borodin (SpeechAntiSpoofingBenchmarks).
- Email: kborodin.research@gmail.com
- Telegram: [@korallll_ai](https://t.me/korallll_ai)
