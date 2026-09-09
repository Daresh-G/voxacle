"use client";

/** Settings — configurable thresholds/policy persisted to backend (spec §63). */
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/voxacle/api";
import { useToast } from "@/hooks/use-toast";

interface SettingsShape {
  [key: string]: string | number | boolean;
}

const NUMBER_FIELDS: { key: string; label: string; hint: string; min?: number; max?: number }[] = [
  { key: "risk_low_max", label: "Low risk threshold (≤)", hint: "Risk scores at or below this are LOW (0-100 scale).", min: 0, max: 100 },
  { key: "risk_medium_max", label: "Medium risk threshold (≤)", hint: "Above low and up to this value is MEDIUM.", min: 0, max: 100 },
  { key: "risk_high_max", label: "High risk threshold (≤)", hint: "Above this value risk is CRITICAL.", min: 0, max: 100 },
  { key: "speaker_high", label: "Speaker similarity — HIGH (cosine)", hint: "ECAPA cosine similarity at/above this = HIGH consistency.", min: 0, max: 1 },
  { key: "speaker_medium", label: "Speaker similarity — MEDIUM (cosine)", hint: "At/above this but below HIGH = MEDIUM consistency.", min: 0, max: 1 },
  { key: "confidence_poor_quality_cap", label: "Confidence cap for POOR audio (%)", hint: "Analysis confidence cannot exceed this when quality is POOR.", min: 0, max: 100 },
  { key: "confidence_disagreement_penalty", label: "Disagreement penalty (points)", hint: "Confidence deducted when evidence sources disagree.", min: 0, max: 50 },
  { key: "chunk_seconds", label: "Chunk duration (seconds)", hint: "Temporal analysis window; ~4 s matches AASIST input.", min: 1, max: 15 },
  { key: "retention_hours", label: "Evidence retention (hours)", hint: "Analysis records older than this are deleted by privacy cleanup.", min: 1, max: 720 },
];

const SELECT_FIELDS: { key: string; label: string; options: string[] }[] = [
  { key: "policy_low", label: "LOW risk action", options: ["ALLOW", "WARN", "VERIFY", "BLOCK"] },
  { key: "policy_medium", label: "MEDIUM risk action", options: ["ALLOW", "WARN", "VERIFY", "BLOCK"] },
  { key: "policy_high", label: "HIGH risk action", options: ["ALLOW", "WARN", "VERIFY", "BLOCK"] },
  { key: "policy_critical", label: "CRITICAL risk action", options: ["ALLOW", "WARN", "VERIFY", "BLOCK"] },
  { key: "log_level", label: "Logging level (backend logs only)", options: ["DEBUG", "INFO", "WARNING", "ERROR"] },
];

const BOOL_FIELDS: { key: string; label: string; hint: string }[] = [
  { key: "store_original_audio", label: "Preserve original audio evidence", hint: "Keep original uploads for evidence integrity. Disable to store feature-only records." },
];

export function SettingsView() {
  const [values, setValues] = useState<SettingsShape | null>(null);
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    api.settings().then((r) => setValues(r.settings as SettingsShape)).catch(() => setValues(null));
  }, []);

  const save = async () => {
    if (!values) return;
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {};
      Object.keys(values).forEach((k) => {
        if (NUMBER_FIELDS.some((f) => f.key === k) || SELECT_FIELDS.some((f) => f.key === k) || BOOL_FIELDS.some((f) => f.key === k)) {
          payload[k] = values[k];
        }
      });
      const r = await api.saveSettings(payload);
      setValues(r.settings as SettingsShape);
      toast({ title: "Settings saved", description: "Thresholds apply to new analyses immediately." });
    } catch (e) {
      toast({ title: "Save failed", description: e instanceof Error ? e.message : "Unknown error", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  if (!values) {
    return <div className="h-96 animate-pulse rounded-xl bg-gray-100" />;
  }

  const set = (k: string, v: string | number | boolean) => setValues((s) => ({ ...(s ?? {}), [k]: v }));

  return (
    <div className="space-y-5">
      <div className="rounded-xl border bg-white p-5">
        <h3 className="text-sm font-semibold text-gray-900">Risk & confidence thresholds</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Product defaults — not universal scientific truth. Validate these for your deployment environment.
        </p>
        <div className="mt-4 grid gap-x-8 gap-y-4 md:grid-cols-2">
          {NUMBER_FIELDS.map((f) => (
            <div key={f.key}>
              <Label className="text-xs font-medium text-gray-600">{f.label}</Label>
              <Input
                type="number"
                min={f.min}
                max={f.max}
                step="any"
                value={String(values[f.key] ?? "")}
                onChange={(e) => set(f.key, e.target.value === "" ? "" : Number(e.target.value))}
                className="mt-1.5 h-9 text-sm"
              />
              <p className="mt-1 text-[11px] text-gray-400">{f.hint}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h3 className="text-sm font-semibold text-gray-900">Policy actions</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Recommended actions per risk band. The prototype produces recommendations; blocking real bank transfers requires a banking integration.
        </p>
        <div className="mt-4 grid gap-x-8 gap-y-4 md:grid-cols-2">
          {SELECT_FIELDS.map((f) => (
            <div key={f.key}>
              <Label className="text-xs font-medium text-gray-600">{f.label}</Label>
              <Select value={String(values[f.key] ?? "")} onValueChange={(v) => set(f.key, v)}>
                <SelectTrigger className="mt-1.5 h-9 text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {f.options.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h3 className="text-sm font-semibold text-gray-900">Privacy</h3>
        <div className="mt-4 space-y-3">
          {BOOL_FIELDS.map((f) => (
            <label key={f.key} className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={Boolean(values[f.key])}
                onChange={(e) => set(f.key, e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-gray-300"
              />
              <span>
                <span className="block text-sm font-medium text-gray-800">{f.label}</span>
                <span className="block text-xs text-gray-500">{f.hint}</span>
              </span>
            </label>
          ))}
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              try {
                await fetch(`/api/privacy/cleanup?XTransformPort=3030`, { method: "POST" });
                toast({ title: "Retention cleanup executed" });
              } catch {
                toast({ title: "Cleanup failed", variant: "destructive" });
              }
            }}
          >
            Run retention cleanup now
          </Button>
        </div>
      </div>

      <div className="sticky bottom-0 flex justify-end border-t bg-white/95 px-1 py-3 backdrop-blur">
        <Button onClick={save} disabled={saving} className="bg-blue-600 text-white hover:bg-blue-700">
          {saving ? "Saving…" : "Save settings"}
        </Button>
      </div>
    </div>
  );
}
