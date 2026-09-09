"use client";

import { Badge } from "@/components/ui/badge";

/** Classification -> visual language (spec: GREEN genuine / YELLOW suspicious /
 * RED high risk / GRAY inconclusive / DARK GRAY failed; no glow). */
export const CLASS_STYLE: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  "GENUINE": { bg: "bg-green-50", text: "text-green-700", border: "border-green-200", dot: "bg-green-500" },
  "SUSPICIOUS": { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200", dot: "bg-amber-500" },
  "HIGH RISK": { bg: "bg-red-50", text: "text-red-700", border: "border-red-200", dot: "bg-red-500" },
  "INCONCLUSIVE": { bg: "bg-gray-50", text: "text-gray-600", border: "border-gray-200", dot: "bg-gray-400" },
  "ANALYSIS FAILED": { bg: "bg-zinc-100", text: "text-zinc-700", border: "border-zinc-300", dot: "bg-zinc-600" },
};

export function ClassBadge({ classification, className = "" }: { classification: string; className?: string }) {
  const s = CLASS_STYLE[classification] ?? CLASS_STYLE["INCONCLUSIVE"];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${s.bg} ${s.text} ${s.border} ${className}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {classification}
    </span>
  );
}

export function QualityBadge({ state }: { state: string | null | undefined }) {
  if (!state) return <Badge variant="outline" className="text-gray-400">N/A</Badge>;
  const map: Record<string, string> = {
    GOOD: "bg-green-50 text-green-700 border-green-200",
    FAIR: "bg-amber-50 text-amber-700 border-amber-200",
    POOR: "bg-orange-50 text-orange-700 border-orange-200",
    UNUSABLE: "bg-red-50 text-red-700 border-red-200",
  };
  return (
    <Badge variant="outline" className={map[state] ?? "bg-gray-50 text-gray-600 border-gray-200"}>
      {state}
    </Badge>
  );
}

export function MetricTile({
  label,
  value,
  sub,
  tone = "default",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "default" | "good" | "warn" | "danger";
}) {
  const toneCls =
    tone === "good" ? "text-green-700" : tone === "warn" ? "text-amber-700" : tone === "danger" ? "text-red-700" : "text-gray-900";
  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="text-[11px] font-medium uppercase tracking-wide text-gray-500">{label}</div>
      <div className={`mt-1 text-2xl font-bold tabular-nums ${toneCls}`}>{value}</div>
      {sub && <div className="mt-0.5 text-xs text-gray-500">{sub}</div>}
    </div>
  );
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">{children}</div>;
}

export function StatusDot({ status }: { status: string }) {
  const cls =
    status === "READY" || status === "ok"
      ? "bg-green-500"
      : status === "DEGRADED"
        ? "bg-amber-500"
        : status === "LOADING"
          ? "bg-blue-500 animate-pulse"
          : "bg-red-500";
  return <span className={`inline-block h-2 w-2 rounded-full ${cls}`} />;
}
