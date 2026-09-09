"use client";

/** Pipeline progress — simple honest stage indicators (no cinematic effects).
 * Stages mirror the REAL backend pipeline order (spec §72/§2960). */
import { CheckCircle2, Loader2, Circle } from "lucide-react";

export const PIPELINE_STAGES = [
  "Validation",
  "Decoding",
  "Standardization",
  "Quality Check",
  "DSP Analysis",
  "AASIST-L",
  "ECAPA-TDNN",
  "Prosody",
  "Evidence Fusion",
  "Risk Analysis",
];

export function PipelineProgress({ current }: { current: number }) {
  return (
    <div className="rounded-xl border bg-white p-5">
      <div className="mb-3 text-sm font-semibold text-gray-900">Analyzing voice…</div>
      <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3 lg:grid-cols-5">
        {PIPELINE_STAGES.map((s, i) => {
          const done = i < current;
          const active = i === current;
          return (
            <div key={s} className="flex items-center gap-2 text-sm">
              {done ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />
              ) : active ? (
                <Loader2 className="h-4 w-4 shrink-0 animate-spin text-blue-600" />
              ) : (
                <Circle className="h-4 w-4 shrink-0 text-gray-300" />
              )}
              <span className={done ? "text-gray-600" : active ? "font-medium text-gray-900" : "text-gray-400"}>
                {s}
              </span>
            </div>
          );
        })}
      </div>
      <p className="mt-3 text-xs text-gray-400">
        Progress is indicative; final values appear only after the backend completes the real analysis.
      </p>
    </div>
  );
}
