"use client";

/** Reports — analysis history table + detail dialog (spec §3092s). */
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/voxacle/api";
import type { AnalysisRow } from "@/lib/voxacle/types";
import { ClassBadge } from "./primitives";
import { Download, Eye } from "lucide-react";

export function ReportsView({ focusId }: { focusId: string | null }) {
  const [rows, setRows] = useState<AnalysisRow[]>([]);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    api.analyses().then((r) => setRows(r.analyses)).catch(() => setRows([])).finally(() => setLoading(false));
  }, []);
  useEffect(load, [load]);

  useEffect(() => {
    if (!focusId) return;
    let cancelled = false;
    api
      .analysis(focusId)
      .then((d) => {
        if (!cancelled) setDetail(d);
      })
      .catch(() => {
        if (!cancelled) setDetail(null);
      });
    return () => {
      cancelled = true;
    };
  }, [focusId]);

  const exportReport = (id: string) => window.open(api.reportTextUrl(id), "_blank");

  const openDetail = useCallback(async (id: string) => {
    try {
      setDetail(await api.analysis(id));
    } catch {
      setDetail(null);
    }
  }, []);

  return (
    <div className="rounded-xl border bg-white">
      <div className="border-b px-5 py-4">
        <h3 className="text-sm font-semibold text-gray-900">Reports</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Every analysis is recorded with its classification, risk, confidence and evidence hash. Records are removed after the configured retention period.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50/60 text-xs text-gray-500">
              <th className="px-5 py-2.5 text-left font-medium">Session ID</th>
              <th className="px-5 py-2.5 text-left font-medium">Date</th>
              <th className="px-5 py-2.5 text-left font-medium">Classification</th>
              <th className="px-5 py-2.5 text-right font-medium">Risk</th>
              <th className="px-5 py-2.5 text-right font-medium">Confidence</th>
              <th className="px-5 py-2.5 text-left font-medium">Action</th>
              <th className="px-5 py-2.5 text-right font-medium">View</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="px-5 py-10 text-center text-sm text-gray-400">Loading…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={7} className="px-5 py-10 text-center text-sm text-gray-400">No reports yet.</td></tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-5 py-3 font-mono text-xs text-gray-500">{r.id.slice(0, 8)}…</td>
                  <td className="px-5 py-3 text-xs text-gray-600">{new Date(r.created_at).toLocaleString()}</td>
                  <td className="px-5 py-3"><ClassBadge classification={r.classification} /></td>
                  <td className="px-5 py-3 text-right tabular-nums">{r.risk_score != null ? Math.round(r.risk_score) : "—"}</td>
                  <td className="px-5 py-3 text-right tabular-nums text-gray-600">{r.confidence != null ? `${Math.round(r.confidence)}%` : "—"}</td>
                  <td className="px-5 py-3 text-xs font-medium text-gray-700">{r.action ?? "—"}</td>
                  <td className="px-5 py-3">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => openDetail(r.id)} aria-label="View report">
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => exportReport(r.id)} aria-label="Export report">
                        <Download className="h-4 w-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Dialog open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Voice Integrity Report</DialogTitle>
            <DialogDescription>Generated from the stored analysis record.</DialogDescription>
          </DialogHeader>
          {detail && (
            <pre className="max-h-[60vh] overflow-auto rounded-lg bg-gray-50 p-4 text-[11px] leading-relaxed text-gray-700">
              {JSON.stringify(detail, null, 2)}
            </pre>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
