"use client";

/** System Health — real component statuses from /api/health (spec §51/§62). */
import { useEffect, useState } from "react";
import { api } from "@/lib/voxacle/api";
import type { HealthResponse } from "@/lib/voxacle/types";
import { StatusDot } from "./primitives";
import { Skeleton } from "@/components/ui/skeleton";

const LABELS: Record<string, string> = {
  api: "API",
  audio_decoder: "Audio Decoder",
  dsp_engine: "DSP Engine",
  aasist_l: "AASIST-L",
  ecapa: "ECAPA-TDNN",
  database: "Database",
  streaming: "WebSocket Streaming",
};

export function HealthView() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    const load = () => api.health().then(setHealth).catch(() => setHealth(null));
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  if (!health) {
    return <div className="space-y-3"><Skeleton className="h-16 rounded-xl" /><Skeleton className="h-96 rounded-xl" /></div>;
  }

  const det = health.details;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between rounded-xl border bg-white px-5 py-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">System status</h3>
          <p className="mt-0.5 text-xs text-gray-500">Component-level truthfulness: degraded components are reported, never hidden.</p>
        </div>
        <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-semibold ${
          health.status === "READY" ? "border-green-200 bg-green-50 text-green-700"
          : health.status === "DEGRADED" ? "border-amber-200 bg-amber-50 text-amber-700"
          : "border-red-200 bg-red-50 text-red-700"}`}>
          <StatusDot status={health.status} /> {health.status}
        </span>
      </div>

      <div className="rounded-xl border bg-white">
        <table className="w-full text-sm">
          <tbody>
            {Object.entries(health.components).map(([k, v]) => (
              <tr key={k} className="border-b last:border-0">
                <td className="px-5 py-3 font-medium text-gray-700">{LABELS[k] ?? k}</td>
                <td className="px-5 py-3">
                  <span className="flex items-center gap-2 text-xs font-semibold">
                    <StatusDot status={v} />
                    <span className={v === "ok" ? "text-green-700" : "text-red-600"}>{v === "ok" ? "READY" : "UNAVAILABLE"}</span>
                  </span>
                </td>
                <td className="px-5 py-3 text-right text-xs text-gray-400">
                  {k === "aasist_l" && det?.aasist_l?.error ? det.aasist_l.error : ""}
                  {k === "ecapa" && det?.ecapa?.error ? det.ecapa.error : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-xl border bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900">Model versions & traceability</h3>
          <div className="mt-3 space-y-3 text-xs leading-relaxed text-gray-600">
            <div className="rounded-lg bg-gray-50 p-3">
              <div className="font-semibold text-gray-800">AASIST-L</div>
              <div>Checkpoint: AASIST-L.pth · SpeechAntiSpoofingBenchmarks/AASIST-L</div>
              <div>Paper: Jung et al., AASIST, ICASSP 2022 (arXiv:2110.01200)</div>
              <div className="text-gray-400">Benchmark EER 0.99% (ASVspoof2019 LA) is a dataset benchmark — not VOXACLE accuracy.</div>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <div className="font-semibold text-gray-800">ECAPA-TDNN</div>
              <div>Checkpoint: speechbrain/spkrec-ecapa-voxceleb · 192-d embeddings</div>
              <div>Similarity: cosine (a·b)/(‖a‖‖b‖), thresholds configurable in Settings.</div>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <div className="font-semibold text-gray-800">DSP Engine</div>
              <div>NumPy / SciPy / Librosa deterministic computations (FFT, STFT, MFCC, ZCR, RMS, SNR).</div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900">Scope notes</h3>
          <ul className="mt-3 space-y-2 text-xs leading-relaxed text-gray-600">
            {(health.notes ?? []).map((n, i) => (
              <li key={i} className="rounded-lg bg-gray-50 p-3">• {n}</li>
            ))}
            <li className="rounded-lg bg-gray-50 p-3">
              • VOXACLE does not depend on a single AI detector. It combines signal-level mathematical evidence,
              synthetic-speech detection, speaker consistency, temporal behavior, audio quality, contextual risk and
              policy rules to produce an explainable voice-integrity decision.
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
