"""Chunk processor for near-real-time streaming sessions (spec §23).

Accumulates PCM chunks; when a full analysis window is buffered it runs the
REAL per-chunk pipeline (quality + AASIST + DSP summary) and emits a chunk
result. `verdict()` aggregates chunk evidence truthfully — unavailable chunks
reduce confidence and never fabricate values.
"""
from __future__ import annotations

import time

import numpy as np

from backend.audio import quality as quality_mod
from backend.models import aasist as aasist_mod
from backend.signal import time_domain


class ChunkSession:
    def __init__(self, sample_rate: int = 16000, chunk_seconds: float = 4.0):
        self.sr = sample_rate
        self.chunk_samples = int(sample_rate * chunk_seconds)
        self.buffer = np.zeros(0, dtype=np.float32)
        self.results: list[dict] = []
        self.index = 0
        self.t0 = time.time()

    def push(self, samples: np.ndarray) -> list[dict]:
        self.buffer = np.concatenate([self.buffer, samples.astype(np.float32)])
        out = []
        while self.buffer.size >= self.chunk_samples:
            seg = self.buffer[: self.chunk_samples]
            self.buffer = self.buffer[self.chunk_samples:]
            out.append(self._process(seg))
        return out

    def flush(self) -> list[dict]:
        out = []
        if self.buffer.size > self.sr // 2:  # >0.5 s residual is analyzable
            seg = self.buffer
            self.buffer = np.zeros(0, dtype=np.float32)
            out.append(self._process(seg))
        return out

    def _process(self, seg: np.ndarray) -> dict:
        ts = round(self.index * self.chunk_samples / self.sr, 2)
        te = round(ts + seg.size / self.sr, 2)
        self.index += 1
        q = quality_mod.analyze_quality(seg, self.sr)
        ares = aasist_mod.wrapper.infer(seg, self.sr)
        t = time_domain.analyze(seg, self.sr)
        cr = {
            "index": self.index - 1,
            "t0": ts,
            "t1": te,
            "quality": q["state"],
            "synthetic": ares["value"]["synthetic_evidence"] if ares["status"] == "success" else None,
            "bonafide_logit": ares["value"].get("bonafide_logit") if ares["status"] == "success" else None,
            "rms": t["rms"],
            "zcr": t["zcr"],
            "confidence": ares.get("confidence", 0),
            "warnings": ares.get("warnings", []) + q["issues"],
            "latency_ms": ares.get("latency_ms"),
        }
        self.results.append(cr)
        return cr

    def verdict(self) -> dict:
        vals = [r["synthetic"] for r in self.results if r["synthetic"] is not None]
        if not vals:
            return {
                "classification": "INCONCLUSIVE",
                "synthetic_evidence": None,
                "confidence": 0,
                "warnings": ["No chunk produced synthetic evidence (model unavailable or no audio)."],
                "n_chunks": len(self.results),
            }
        mean = float(np.mean(vals))
        std = float(np.std(vals))
        suspicious_ratio = float(np.mean(np.array(vals) > 0.5))
        confidence = round(min(95.0, 55.0 + 10.0 * len(vals)) * (0.6 + 0.4 * (1.0 - min(1.0, std))), 1)
        if mean >= 0.6 and suspicious_ratio >= 0.5:
            classification = "HIGH RISK"
        elif mean >= 0.35 or std > 0.2:
            classification = "SUSPICIOUS"
        elif mean < 0.15 and confidence >= 45:
            classification = "GENUINE"
        else:
            classification = "INCONCLUSIVE"
        return {
            "classification": classification,
            "synthetic_evidence": round(mean, 4),
            "std_synthetic": round(std, 4),
            "suspicious_chunk_ratio": round(suspicious_ratio, 3),
            "confidence": confidence,
            "n_chunks": len(self.results),
            "elapsed_sec": round(time.time() - self.t0, 1),
            "warnings": [],
        }
