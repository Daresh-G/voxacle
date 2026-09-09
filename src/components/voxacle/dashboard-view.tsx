"use client";

/** Dashboard view — simple status + counters + recent analyses (spec §2900s). */
import { useEffect, useState } from "react";
import { api } from "@/lib/voxacle/api";
import type { DashboardData, HealthResponse } from "@/lib/voxacle/types";
import { ClassBadge, MetricTile, StatusDot } from "./primitives";
import { Skeleton } from "@/components/ui/skeleton";

export function DashboardView({ onOpenAnalysis }: { onOpenAnalysis: (id: string) => void }) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    api.dashboard().then(setData).catch(() => setData(null));
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  if (!data) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
        </div>
        <Skeleton className="h-72 rounded-xl" />
      </div>
    );
  }

  const comps = health?.components ?? {};

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <MetricTile label="Total Analyses" value={String(data.stats.total)} sub="all sessions" />
        <MetricTile label="Genuine" value={String(data.stats.genuine)} tone="good" sub="classified genuine" />
        <MetricTile label="Suspicious" value={String(data.stats.suspicious)} tone="warn" sub="need attention" />
        <MetricTile label="High Risk" value={String(data.stats.high_risk)} tone="danger" sub="verification required" />
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="rounded-xl border bg-white p-5 lg:col-span-2">
          <h3 className="text-sm font-semibold text-gray-900">Recent analyses</h3>
          {data.recent.length === 0 ? (
            <p className="mt-6 mb-2 text-center text-sm text-gray-400">
              No analyses yet — run one from the Analyze Voice page.
            </p>
          ) : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-xs text-gray-500">
                    <th className="py-2 text-left font-medium">Date</th>
                    <th className="py-2 text-left font-medium">File</th>
                    <th className="py-2 text-left font-medium">Result</th>
                    <th className="py-2 text-right font-medium">Risk</th>
                    <th className="py-2 text-right font-medium">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent.map((r) => (
                    <tr
                      key={r.id}
                      className="cursor-pointer border-b last:border-0 hover:bg-gray-50"
                      onClick={() => onOpenAnalysis(r.id)}
                    >
                      <td className="py-2.5 text-xs text-gray-500">{new Date(r.created_at).toLocaleString()}</td>
                      <td className="max-w-40 truncate py-2.5 text-xs">{r.file_name || "—"}</td>
                      <td className="py-2.5"><ClassBadge classification={r.classification} /></td>
                      <td className="py-2.5 text-right tabular-nums">{Math.round(r.risk_score)}</td>
                      <td className="py-2.5 text-right tabular-nums text-gray-500">{Math.round(r.confidence)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="rounded-xl border bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900">Component health</h3>
          <ul className="mt-3 space-y-2.5">
            {["audio_decoder", "dsp_engine", "aasist_l", "ecapa", "database", "streaming"].map((k) => (
              <li key={k} className="flex items-center justify-between text-sm">
                <span className="text-gray-600">{k.replace("_", " ")}</span>
                <span className="flex items-center gap-1.5 text-xs font-medium text-gray-500">
                  <StatusDot status={comps[k] ?? "LOADING"} />
                  {(comps[k] ?? "…").toUpperCase()}
                </span>
              </li>
            ))}
          </ul>
          {data.stats.avg_risk != null && (
            <div className="mt-4 rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
              Average risk across analyses: <span className="font-semibold text-gray-900">{data.stats.avg_risk}</span>/100
            </div>
          )}
          {health?.notes?.[0] && (
            <p className="mt-3 text-[11px] leading-relaxed text-gray-400">{health.notes[0]}</p>
          )}
        </div>
      </div>
    </div>
  );
}
