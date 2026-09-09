"use client";

/**
 * AnalyzeVoiceView — reference template layout (screenshot-matched):
 * Section 1 Reference Voice | Section 2 Incoming Voice
 * Section 3 Call Context (3-col form)
 * Sticky footer: privacy statement + START ANALYSIS
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { api } from "@/lib/voxacle/api";
import { EMPTY_CONTEXT, type AnalyzeResult, type CallContext, type Profile } from "@/lib/voxacle/types";
import { VoiceCard, type AttachedAudio } from "./voice-card";
import { AnalyzeResultView } from "./result-view";
import { PIPELINE_STAGES, PipelineProgress } from "./progress";
import { ShieldCheck } from "lucide-react";

const ORIGINS = ["UNKNOWN", "VERIFIED", "INTERNATIONAL", "BLOCKED", "INTERNAL"];
const CHANNELS = ["MOBILE", "LANDLINE", "VOIP", "UNKNOWN"];
const IDENTITIES = ["NONE", "CEO", "CFO", "MANAGER", "BANK_OFFICER", "GOVERNMENT", "RELATIVE", "OTHER"];
const TXN_TYPES = ["NONE", "TRANSFER", "PAYMENT", "OTP_SHARING", "ACCOUNT_CHANGE"];
const FRAUD = ["NONE", "SUSPICIOUS", "CONFIRMED"];

export function AnalyzeVoiceView() {
  const [reference, setReference] = useState<AttachedAudio | null>(null);
  const [suspect, setSuspect] = useState<AttachedAudio | null>(null);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [profileChoice, setProfileChoice] = useState<string>("__none__"); // __none__ | __file__ | profileId
  const [context, setContext] = useState<CallContext>(EMPTY_CONTEXT);
  const [running, setRunning] = useState(false);
  const [stageIdx, setStageIdx] = useState(-1);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadProfiles = useCallback(() => {
    api.profiles().then((r) => setProfiles(r.profiles)).catch(() => setProfiles([]));
  }, []);
  useEffect(loadProfiles, [loadProfiles]);

  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  const set = (k: keyof CallContext) => (v: string) => setContext((c) => ({ ...c, [k]: v }));

  const start = async () => {
    if (!suspect) {
      setError("Please provide the incoming (suspect) voice to analyze.");
      return;
    }
    setError(null);
    setResult(null);
    setRunning(true);
    setStageIdx(0);
    // Progress display reflects the real backend pipeline stages; the request
    // resolves when the actual analysis completes (real values only).
    timerRef.current = setInterval(() => {
      setStageIdx((i) => Math.min(i + 1, PIPELINE_STAGES.length - 2));
    }, 450);
    try {
      const refFile =
        profileChoice === "__file__" ? reference?.file : undefined;
      const refProfile =
        profileChoice !== "__none__" && profileChoice !== "__file__"
          ? profileChoice
          : undefined;
      const res = await api.analyze(suspect.file, context, refProfile, refFile);
      setResult(res);
      setStageIdx(PIPELINE_STAGES.length - 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis request failed.");
      setStageIdx(-1);
    } finally {
      setRunning(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  };

  return (
    <div className="flex min-h-full flex-col">
      <div className="grid gap-5 lg:grid-cols-2">
        <section>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
            Section 1 · Reference Voice
          </div>
          {/* profile selector (optional): reuse enrolled profile OR one-off file */}
          <div className="mb-3 rounded-xl border bg-white p-4">
            <Label className="text-xs font-medium text-gray-600">Speaker profile source</Label>
            <Select value={profileChoice} onValueChange={setProfileChoice}>
              <SelectTrigger className="mt-1.5 h-9 w-full text-sm">
                <SelectValue placeholder="No reference" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">No reference — synthetic detection only</SelectItem>
                <SelectItem value="__file__">Upload / record reference audio below</SelectItem>
                {profiles.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    Profile: {p.name} ({p.speaker_label})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <VoiceCard
            title="Reference Voice"
            optionalBadge
            description="Genuine voice of the claimed speaker — used for speaker-consistency comparison."
            value={reference}
            onChange={setReference}
          />
        </section>

        <section>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
            Section 2 · Incoming Voice
          </div>
          <VoiceCard
            title="Incoming Voice"
            description="The suspect voice that VOXACLE will analyze for synthetic evidence."
            value={suspect}
            onChange={setSuspect}
          />
        </section>
      </div>

      <section className="mt-6">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
          Section 3 · Call Context
        </div>
        <div className="rounded-xl border bg-white p-5">
          <h3 className="text-sm font-semibold text-gray-900">Call Context</h3>
          <p className="mt-0.5 text-xs text-gray-500">
            Context is evaluated separately from audio evidence and combined only at the risk stage.
          </p>
          <div className="mt-4 grid gap-x-6 gap-y-4 md:grid-cols-2 xl:grid-cols-3">
            <Field label="Caller origin">
              <Select value={context.caller_origin} onValueChange={set("caller_origin")}>
                <SelectTrigger className="h-10 w-full text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>{ORIGINS.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
              </Select>
            </Field>
            <Field label="Caller ID">
              <Input
                placeholder="e.g. +91 98xxxxxx01"
                value={context.caller_id}
                onChange={(e) => setContext((c) => ({ ...c, caller_id: e.target.value }))}
                className="h-10 text-sm"
              />
            </Field>
            <Field label="Known contact">
              <Select value={context.known_contact} onValueChange={set("known_contact")}>
                <SelectTrigger className="h-10 w-full text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>{["NO", "YES"].map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
              </Select>
            </Field>
            <Field label="Communication channel">
              <Select value={context.channel} onValueChange={set("channel")}>
                <SelectTrigger className="h-10 w-full text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>{CHANNELS.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
              </Select>
            </Field>
            <Field label="Claimed identity">
              <Select value={context.claimed_identity} onValueChange={set("claimed_identity")}>
                <SelectTrigger className="h-10 w-full text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>{IDENTITIES.map((o) => <SelectItem key={o} value={o}>{o.replace("_", " ")}</SelectItem>)}</SelectContent>
              </Select>
            </Field>
            <Field label="Transaction type">
              <Select value={context.transaction_type} onValueChange={set("transaction_type")}>
                <SelectTrigger className="h-10 w-full text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>{TXN_TYPES.map((o) => <SelectItem key={o} value={o}>{o.replace("_", " ")}</SelectItem>)}</SelectContent>
              </Select>
            </Field>
            <Field label="Transaction amount">
              <Input
                type="number" min={0} placeholder="e.g. 800000"
                value={context.transaction_amount}
                onChange={(e) => setContext((c) => ({ ...c, transaction_amount: e.target.value }))}
                className="h-10 text-sm"
              />
            </Field>
            <Field label="Fraud indicator">
              <Select value={context.fraud_indicator} onValueChange={set("fraud_indicator")}>
                <SelectTrigger className="h-10 w-full text-sm"><SelectValue /></SelectTrigger>
                <SelectContent>{FRAUD.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
              </Select>
            </Field>
          </div>
        </div>
      </section>

      {error && (
        <Alert variant="destructive" className="mt-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {running && (
        <div className="mt-6">
          <PipelineProgress current={stageIdx} />
        </div>
      )}

      {result && (
        <div className="mt-6">
          <AnalyzeResultView result={result} />
        </div>
      )}

      {/* Sticky action footer (matches reference template) */}
      <div className="sticky bottom-0 -mx-6 mt-6 border-t bg-white/95 px-6 py-3.5 backdrop-blur supports-[backdrop-filter]:bg-white/80">
        <div className="flex flex-col items-center justify-between gap-3 sm:flex-row">
          <p className="flex items-center gap-2 text-xs text-gray-500">
            <ShieldCheck className="h-4 w-4 text-gray-400" />
            Audio is processed for verification and retained only according to the configured evidence policy.
          </p>
          <Button
            onClick={start}
            disabled={running || !suspect}
            className="h-10 min-w-44 gap-2 bg-blue-600 px-6 text-sm font-semibold text-white hover:bg-blue-700"
          >
            {running ? "ANALYZING…" : "START ANALYSIS"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <Label className="text-xs font-medium text-gray-600">{label}</Label>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}
