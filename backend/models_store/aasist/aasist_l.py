# aasist_l.py
from __future__ import annotations
import os
import numpy as np
import torch
from speech_spoof_bench.model import AntiSpoofingModel
from _net import Model as AASISTNet

_CKPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AASIST-L.pth")
_CUT = 64600
# from config/AASIST-L.conf -> model_config (clovaai/aasist). Lightweight variant:
# narrower residual stack (…[32,24],[24,24]) and gat_dims [24,32] vs AASIST's
# [32,64],[64,64] / [64,32]; pool_ratios [0.4,0.5,0.7,0.5].
_D_ARGS = {
    "architecture": "AASIST",
    "nb_samp": 64600,
    "first_conv": 128,
    "filts": [70, [1, 32], [32, 32], [32, 24], [24, 24]],
    "gat_dims": [24, 32],
    "pool_ratios": [0.4, 0.5, 0.7, 0.5],
    "temperatures": [2.0, 2.0, 100.0, 100.0],
}


def pad_fixed(x: np.ndarray, max_len: int = _CUT) -> np.ndarray:
    """Deterministic eval window: first max_len samples; tile-repeat if shorter.

    Matches clovaai/aasist data_utils.pad() used for dev/eval (no random crop).
    """
    x = np.asarray(x, dtype=np.float32).reshape(-1)
    n = x.shape[0]
    if n >= max_len:
        return x[:max_len]
    reps = max_len // n + 1
    return np.tile(x, reps)[:max_len].astype(np.float32)


class AASIST_L(AntiSpoofingModel):
    name = "AASIST-L"
    expected_sample_rate = 16000
    batch_size = 16  # tuned by sweep 2026-06-03 (peak 256.5 utt/s on 4070 Ti SUPER; bs=64 OOM)

    def load(self) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        net = AASISTNet(_D_ARGS)
        sd = torch.load(_CKPT, map_location="cpu")
        sd = sd.get("state_dict", sd) if isinstance(sd, dict) else sd
        net.load_state_dict(sd, strict=True)
        self.net = net.eval().to(self.device)

    @torch.no_grad()
    def score_batch(self, audios, srs):
        x = np.stack([pad_fixed(a) for a in audios])
        xt = torch.from_numpy(x).to(self.device)
        _hidden, logits = self.net(xt)          # logits[:, 1] = bona fide
        return logits[:, 1].detach().cpu().float().tolist()

    def unload(self) -> None:
        self.net = None
