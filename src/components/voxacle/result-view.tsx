"use client";

/** Result display (spec §39-§42, §64): clear verdict + WHY + action.
 * Technical details live ONLY inside the Advanced Analysis disclosure. */
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { CLASS_STYLE, ClassBadge, MetricTile, QualityBadge } from "./primitives";
import { drawChunkTimeline, drawCurve, drawHeatmap, drawPitch, drawSpectrum, drawWaveform } from "./charts";
import { api } from "@/lib/voxacle/api";
import type { AnalyzeResult } from "@/lib/voxacle/types";
import { AlertTriangle, Download, FileText, Info } from "lucide-react";

export function AnalyzeResultView({ result }: { result: AnalyzeResult }) {
  const [reportOpen, setReportOpen] = useState(false);

  const downloadReport = async () => {
    try {
      const res = await fetch(api.reportTextUrl(result.analysis_id));
      const text = await res.text();
      const blob = new Blob([text], { type: "text/plain" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `voxacle_report_${result.analysis_id.slice(0, 8)}.txt`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      window.open(api.reportTextUrl(result.analysis_id), "_blank");
    }
  };

  if (result.classification === "ANALYSIS FAILED") {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Analysis could not complete</AlertTitle>
        <AlertDescription>
          <p className="font-mono text-xs">{result.error?.code}</p>
          <p className="mt-1">{result.error?.message}</p>
          <p className="mt-2 text-xs">
            VOXACLE does not display scores when a required component fails — showing a number here would be dishonest.
          </p>
        </AlertDescription>
      </Alert>
    );
  }

  const cls = result.classification;
  const s = CLASS_STYLE[cls] ?? CLASS_STYLE["INCONCLUSIVE"];
  const sp = result.speaker_similarity;

  return (
    <div className="space-y-5">
      {result.warnings.length > 0 && (
        <Alert className="border-amber-200 bg-amber-50 text-amber-800">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription className="text-xs leading-relaxed">
            {result.warnings.slice(0, 4).map((w, i) => <div key={i}>• {w}</div>)}
          </AlertDescription>
        </Alert>
      )}

      {/* ------- verdict card ------- */}
      <div className={`rounded-xl border-2 ${s.border} ${s.bg} p-6`}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">VOXACLE Result</div>
            <div className={`mt-1 text-3xl font-bold tracking-tight ${s.text}`}>{cls}</div>
          </div>
          <div className="text-right">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">Risk Score</div>
            <div className={`text-3xl font-bold tabular-nums ${s.text}`}>
              {result.risk_score != null ? Math.round(result.risk_score) : "—"}
              <span className="ml-1 text-sm font-medium text-gray-400">/100 · {result.risk_level}</span>
            </div>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
          <MetricTile
            label="AI Likelihood"
            value={result.ai_likelihood_percent != null ? `${Math.round(result.ai_likelihood_percent)}%` : "N/A"}
            sub={result.ai_likelihood_label ? `${result.ai_likelihood_label} synthetic evidence` : undefined}
            tone={result.ai_likelihood_percent != null ? (result.ai_likelihood_percent >= 60 ? "danger" : result.ai_likelihood_percent >= 35 ? "warn" : "good") : "default"}
          />
          <MetricTile
            label="Speaker Similarity"
            value={sp ? `${sp.similarity_percent}%` : "N/A"}
            sub={sp ? `Consistency ${sp.consistency}` : result.has_reference ? "unavailable" : "no reference provided"}
          />
          <MetricTile label="Audio Quality" value={<span className="text-xl">{result.audio_quality ?? "N/A"}</span>} sub={undefined} tone={result.audio_quality === "GOOD" ? "good" : result.audio_quality === "UNUSABLE" ? "danger" : "warn"} />
          <MetricTile
            label="Analysis Confidence"
            value={result.confidence != null ? `${Math.round(result.confidence)}%` : "N/A"}
            sub={result.confidence_label ? `${result.confidence_label} confidence` : undefined}
          />
        </div>
      </div>

      {/* ------- why + action ------- */}
      <div className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-xl border bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900">Why this result?</h3>
          <dl className="mt-3 space-y-2 text-sm">
            <ReasonRow k="Synthetic evidence" v={result.reasoning.synthetic_evidence} />
            <ReasonRow k="Speaker consistency" v={result.reasoning.speaker_consistency} />
            <ReasonRow k="Temporal evidence" v={result.reasoning.temporal} />
            <ReasonRow k="Audio quality" v={result.reasoning.audio_quality} />
            <ReasonRow k="Contextual risk" v={result.reasoning.context} />
            <ReasonRow k="Confidence" v={result.reasoning.confidence} />
          </dl>
          {result.reasoning.lines.length > 0 && (
            <ul className="mt-4 space-y-1.5 border-t pt-3 text-xs leading-relaxed text-gray-600">
              {result.reasoning.lines.slice(0, 6).map((l, i) => (
                <li key={i} className="flex gap-2"><span className="text-gray-300">•</span>{l}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-xl border bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900">Recommended action</h3>
          <div className={`mt-3 rounded-lg border px-4 py-3 ${s.border} ${s.bg}`}>
            <div className={`text-base font-bold ${s.text}`}>{result.action_title}</div>
            <p className="mt-1 text-xs leading-relaxed text-gray-600">{result.action_detail}</p>
          </div>
          {result.context_reasoning && result.context_reasoning.length > 0 && (
            <div className="mt-4">
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">Context contributions</div>
              <ul className="mt-2 space-y-1 text-xs text-gray-600">
                {result.context_reasoning.slice(0, 5).map((c, i) => <li key={i}>• {c}</li>)}
              </ul>
            </div>
          )}
          <div className="mt-4 flex flex-wrap gap-2 border-t pt-4">
            <Button variant="outline" size="sm" className="gap-2" onClick={() => setReportOpen((v) => !v)}>
              <FileText className="h-4 w-4" /> {reportOpen ? "Hide" : "View"} Report Summary
            </Button>
            <Button variant="outline" size="sm" className="gap-2" onClick={downloadReport}>
              <Download className="h-4 w-4" /> Export Report
            </Button>
          </div>
          {reportOpen && result.report && (
            <pre className="mt-3 max-h-64 overflow-auto rounded-lg bg-gray-50 p-3 text-[11px] leading-relaxed text-gray-700">
              {JSON.stringify(result.report, null, 2)}
            </pre>
          )}
        </div>
      </div>

      {/* ------- advanced analysis (technical details live here) ------- */}
      <AdvancedAnalysis result={result} />
    </div>
  );
}

function ReasonRow({ k, v }: { k: string; v: string }) {
  const tone =
    ["HIGH", "CRITICAL", "CONSISTENTLY SUSPICIOUS", "VARIABLE", "UNUSABLE", "LOW"].includes(v)
      ? v === "LOW" && (k === "Synthetic evidence" || k === "Contextual risk")
        ? "text-green-700"
        : ["HIGH", "CRITICAL"].includes(v) && k === "Confidence"
          ? "text-green-700"
          : ["HIGH", "CRITICAL", "CONSISTENTLY SUSPICIOUS", "VARIABLE"].includes(v)
            ? "text-red-700"
            : "text-red-700"
      : "text-gray-800";
  return (
    <div className="flex items-center justify-between gap-3 border-b border-gray-100 pb-1.5 last:border-0">
      <dt className="text-gray-500">{k}</dt>
      <dd className={`font-semibold ${tone}`}>{v}</dd>
    </div>
  );
}

function AdvancedAnalysis({ result }: { result: AnalyzeResult }) {
  const adv = result.advanced;
  const [open, setOpen] = useState("");
  const waveRef = useRef<HTMLCanvasElement>(null);
  const rmsRef = useRef<HTMLCanvasElement>(null);
  const specRef = useRef<HTMLCanvasElement>(null);
  const heatRef = useRef<HTMLCanvasElement>(null);
  const mfccRef = useRef<HTMLCanvasElement>(null);
  const pitchRef = useRef<HTMLCanvasElement>(null);
  const chunkRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!adv || open !== "adv") return;
    // wait one frame so canvases have layout after the accordion mounts them
    const raf = requestAnimationFrame(() => {
      if (waveRef.current) drawWaveform(waveRef.current, adv.waveform.values);
      if (rmsRef.current) drawCurve(rmsRef.current, adv.rms_curve.times, adv.rms_curve.values);
      if (specRef.current) drawSpectrum(specRef.current, adv.spectrum.freqs, adv.spectrum.mags);
      if (heatRef.current && adv.spectrogram) drawHeatmap(heatRef.current, adv.spectrogram.db);
      if (mfccRef.current && adv.mfcc) drawHeatmap(mfccRef.current, adv.mfcc.coefficients, { lowHigh: true });
      if (pitchRef.current && adv.pitch_curve) drawPitch(pitchRef.current, adv.pitch_curve.times, adv.pitch_curve.hz);
      if (chunkRef.current) drawChunkTimeline(chunkRef.current, adv.chunks);
    });
    return () => cancelAnimationFrame(raf);
  }, [adv, open]);

  if (!adv) return null;
  const dm = adv.dsp_metrics;

  return (
    <Accordion type="single" collapsible value={open} onValueChange={setOpen} className="rounded-xl border bg-white">
      <AccordionItem value="adv" className="border-0">
        <AccordionTrigger className="px-5 py-4 text-sm font-semibold text-gray-900 hover:no-underline">
          <span className="flex items-center gap-2">
            <Info className="h-4 w-4 text-gray-400" />
            Advanced Analysis — technical evidence
          </span>
        </AccordionTrigger>
        <AccordionContent className="space-y-6 px-5 pb-6">
          <p className="text-xs text-gray-500">
            All values below are actual backend computations (NumPy/SciPy/Librosa DSP + AASIST-L/ECAPA-TDNN inference).
            Formulas and internals are for technical review only.
          </p>

          <div className="grid gap-5 lg:grid-cols-2">
            <Panel title="Waveform · x[n]">
              <canvas ref={waveRef} data-h={110} className="w-full" />
              <Note>RMS = √((1/N) Σ x[n]²) — measures signal magnitude; not a deepfake detector.</Note>
            </Panel>
            <Panel title="Frequency Spectrum (FFT)">
              <canvas ref={specRef} data-h={110} className="w-full" />
              <Note>X[k] = Σ x[n]·e^(−j2πkn/N) — shows how energy is distributed across frequencies.</Note>
            </Panel>
            <Panel title="Spectrogram (STFT)">
              {adv.spectrogram ? (
                <canvas ref={heatRef} data-h={140} className="w-full rounded" />
              ) : (
                <Note>Audio too short for a spectrogram.</Note>
              )}
              <Note>STFT shows how frequency content changes over time.</Note>
            </Panel>
            <Panel title={`MFCC (${adv.mfcc?.n_mfcc ?? 13} coefficients)`}>
              {adv.mfcc ? (
                <canvas ref={mfccRef} data-h={140} className="w-full rounded" />
              ) : (
                <Note>Audio too short for MFCC extraction.</Note>
              )}
              <Note>MFCC features contribute supporting acoustic evidence.</Note>
            </Panel>
            <Panel title="RMS Energy Curve">
              <canvas ref={rmsRef} data-h={110} className="w-full" />
              <Note>Frame-level energy over time (25 ms frames, 10 ms hop).</Note>
            </Panel>
            <Panel title="Pitch Curve (prosody)">
              {adv.pitch_curve ? (
                <canvas ref={pitchRef} data-h={110} className="w-full" />
              ) : (
                <Note>Pitch could not be estimated for this audio.</Note>
              )}
              <Note>Human speech shows natural pitch variation; synthetic speech can show regularities.</Note>
            </Panel>
          </div>

          <Panel title="AI Evidence Timeline (chunk-level, real inference)">
            <canvas ref={chunkRef} data-h={120} className="w-full" />
            <Note>
              Each bar = one ~{result.processing?.chunk_seconds ?? 4}-s chunk scored by AASIST-L.
              {adv.temporal_stats && adv.temporal_stats.mean_synthetic != null &&
                ` Mean ${(adv.temporal_stats.mean_synthetic * 100).toFixed(0)}%, max ${((adv.temporal_stats.max_synthetic ?? 0) * 100).toFixed(0)}%, across ${adv.temporal_stats.n_chunks} chunks.`}
            </Note>
            {adv.chunks.length > 0 && (
              <div className="mt-3 max-h-52 overflow-auto rounded-lg border">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-gray-50 text-gray-500">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">Window</th>
                      <th className="px-3 py-2 text-left font-medium">Synthetic</th>
                      <th className="px-3 py-2 text-left font-medium">Quality</th>
                      <th className="px-3 py-2 text-left font-medium">Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {adv.chunks.map((c, i) => (
                      <tr key={i} className="border-t">
                        <td className="px-3 py-1.5 tabular-nums text-gray-700">{c.t0}s – {c.t1}s</td>
                        <td className="px-3 py-1.5 tabular-nums">
                          {c.synthetic != null ? `${(c.synthetic * 100).toFixed(0)}%` : <span className="text-gray-400">unavailable</span>}
                        </td>
                        <td className="px-3 py-1.5"><QualityBadge state={c.quality} /></td>
                        <td className="px-3 py-1.5 tabular-nums text-gray-500">{c.latency_ms != null ? `${c.latency_ms} ms` : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          <div className="grid gap-5 lg:grid-cols-2">
            <Panel title="DSP Metrics (compact table)">
              <table className="w-full text-xs">
                <tbody>
                  {[
                    ["RMS", dm.rms],
                    ["Signal Energy", dm.energy ?? undefined],
                    ["Zero-Crossing Rate", dm.zcr],
                    ["Estimated SNR", dm.snr_db != null ? `${dm.snr_db} dB` : undefined],
                    ["Spectral Centroid", dm.spectral_centroid_hz != null ? `${dm.spectral_centroid_hz} Hz` : undefined],
                    ["Spectral Bandwidth", dm.spectral_bandwidth_hz != null ? `${dm.spectral_bandwidth_hz} Hz` : undefined],
                    ["Spectral Rolloff", dm.spectral_rolloff_hz != null ? `${dm.spectral_rolloff_hz} Hz` : undefined],
                    ["Spectral Flatness", dm.spectral_flatness],
                  ].map(([k, v]) =>
                    v != null ? (
                      <tr key={k as string} className="border-b border-gray-100">
                        <td className="py-1.5 text-gray-500">{k}</td>
                        <td className="py-1.5 text-right font-medium tabular-nums text-gray-800">{String(v)}</td>
                      </tr>
                    ) : null,
                  )}
                </tbody>
              </table>
            </Panel>

            <Panel title="Model Status & Traceability">
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between rounded border px-3 py-2">
                  <span className="font-medium text-gray-700">AASIST-L</span>
                  <span className={adv.aasist?.status === "success" ? "text-green-700" : "text-red-600"}>
                    {adv.aasist?.status ?? "unknown"}
                    {adv.aasist?.error ? ` · ${adv.aasist.error}` : ""}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded border px-3 py-2">
                  <span className="font-medium text-gray-700">ECAPA-TDNN</span>
                  <span className={adv.ecapa_status?.status === "success" ? "text-green-700" : "text-amber-700"}>
                    {adv.ecapa_status?.status ?? "not evaluated"}
                    {adv.ecapa_status?.error ? ` · ${adv.ecapa_status.error}` : ""}
                  </span>
                </div>
                <div className="rounded bg-gray-50 p-3 leading-relaxed text-gray-600">
                  <div>AASIST latency: {result.processing?.aasist_latency_ms ?? "—"} ms</div>
                  <div>ECAPA latency: {result.processing?.ecapa_latency_ms ?? "—"} ms</div>
                  <div>Total pipeline: {result.latency_ms} ms</div>
                  <div className="mt-1 font-mono text-[10px] text-gray-400">
                    evidence: {result.evidence_hash?.slice(0, 24) ?? "—"}…
                  </div>
                </div>
              </div>
            </Panel>
          </div>

          {adv.quality_issues.length > 0 && (
            <Panel title="Quality Warnings">
              <ul className="space-y-1 text-xs text-amber-700">
                {adv.quality_issues.map((w, i) => <li key={i}>• {w}</li>)}
              </ul>
            </Panel>
          )}
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border">
      <div className="border-b px-4 py-2.5 text-xs font-semibold text-gray-700">{title}</div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function Note({ children }: { children: React.ReactNode }) {
  return <p className="mt-2 text-[11px] leading-relaxed text-gray-400">{children}</p>;
}
