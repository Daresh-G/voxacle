"use client";

/**
 * Live Monitor — near-real-time chunk streaming over WebSocket /ws/analysis.
 * Records microphone audio, streams PCM to the backend, and renders REAL
 * per-chunk AASIST results as they arrive. Uses graceful, truthful states
 * when WebSocket or microphone is unavailable.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { drawChunkTimeline } from "./charts";
import { ClassBadge, MetricTile, QualityBadge } from "./primitives";
import { Mic, Square, Wifi, WifiOff } from "lucide-react";
import { wsAnalysisUrl } from "@/lib/voxacle/api";

interface LiveChunk {
  index: number;
  t0: number;
  t1: number;
  synthetic: number | null;
  quality: string;
  latency_ms?: number;
}

interface SessionVerdict {
  classification: string;
  synthetic_evidence: number | null;
  confidence: number;
  n_chunks: number;
  warnings?: string[];
}

export function LiveMonitorView() {
  const [wsState, setWsState] = useState<"idle" | "connecting" | "open" | "error">("idle");
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [chunks, setChunks] = useState<LiveChunk[]>([]);
  const [verdict, setVerdict] = useState<SessionVerdict | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [micError, setMicError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (canvasRef.current) {
      drawChunkTimeline(canvasRef.current, chunks.map((c) => ({ t0: c.t0, t1: c.t1, synthetic: c.synthetic })));
    }
  }, [chunks]);

  const stopEverything = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (processorRef.current) { processorRef.current.disconnect(); processorRef.current = null; }
    if (sourceRef.current) { sourceRef.current.disconnect(); sourceRef.current = null; }
    if (streamRef.current) { streamRef.current.getTracks().forEach((t) => t.stop()); streamRef.current = null; }
    if (audioCtxRef.current) { audioCtxRef.current.close().catch(() => {}); audioCtxRef.current = null; }
    if (recRef.current) { recRef.current = null; }
    setRecording(false);
  }, []);

  useEffect(() => () => { stopEverything(); wsRef.current?.close(); }, [stopEverything]);

  const start = async () => {
    setError(null);
    setMicError(null);
    setChunks([]);
    setVerdict(null);
    setElapsed(0);
    setWsState("connecting");

    let ws: WebSocket;
    try {
      ws = new WebSocket(wsAnalysisUrl());
    } catch {
      setWsState("error");
      setError("WebSocket could not be created in this environment.");
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      setWsState("open");
      ws.send(JSON.stringify({ type: "start", sample_rate: 16000, chunk_seconds: 4.0 }));
    };
    ws.onerror = () => {
      setWsState("error");
      setError("WebSocket connection failed. Live streaming requires the analysis service to be reachable.");
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "chunk_result") {
          setChunks((c) => [...c, msg as LiveChunk]);
        } else if (msg.type === "session_result") {
          setVerdict(msg as SessionVerdict);
        } else if (msg.type === "error") {
          setError(msg.message || "Streaming error.");
        }
      } catch { /* ignore malformed frame */ }
    };
    ws.onclose = () => setWsState((s) => (s === "error" ? s : "idle"));

    // microphone capture -> 16k mono float32 PCM frames
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const ctx = new AudioContext({ sampleRate: 16000 });
      audioCtxRef.current = ctx;
      const src = ctx.createMediaStreamSource(stream);
      sourceRef.current = src;
      const proc = ctx.createScriptProcessor(4096, 1, 1);
      processorRef.current = proc;
      proc.onaudioprocess = (e) => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) return;
        const f32 = e.inputBuffer.getChannelData(0);
        // base64 encode float32
        const bytes = new Uint8Array(f32.buffer, f32.byteOffset, f32.byteLength);
        let bin = "";
        const CH = 8192;
        for (let i = 0; i < bytes.length; i += CH) {
          bin += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + CH)));
        }
        wsRef.current.send(JSON.stringify({ type: "audio", pcm_base64: btoa(bin), samples: f32.length }));
      };
      src.connect(proc);
      proc.connect(ctx.destination);
      setRecording(true);
      timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);
    } catch {
      setMicError("Microphone unavailable. Grant permission or use the Analyze Voice page for file-based analysis.");
      ws.close();
      setWsState("idle");
      return;
    }
  };

  const stop = () => {
    stopEverything();
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "flush" }));
      setTimeout(() => wsRef.current?.close(), 1500);
    }
  };

  const fmtElapsed = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  const last = chunks.length ? chunks[chunks.length - 1] : null;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-white px-5 py-4">
        <div className="flex items-center gap-3">
          <span className={`flex h-10 w-10 items-center justify-center rounded-full ${recording ? "bg-red-50" : "bg-gray-100"}`}>
            <Mic className={`h-5 w-5 ${recording ? "text-red-600" : "text-gray-400"}`} />
          </span>
          <div>
            <div className="text-sm font-semibold text-gray-900">
              {recording ? "Live session monitoring" : "Live Monitor"}
            </div>
            <div className="text-xs text-gray-500">
              {recording ? `Elapsed ${fmtElapsed(elapsed)} · ${chunks.length} chunk${chunks.length === 1 ? "" : "s"} analyzed` : "Stream microphone audio for continuous chunk analysis"}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-xs font-medium text-gray-500">
            {wsState === "open" ? <Wifi className="h-4 w-4 text-green-600" /> : <WifiOff className="h-4 w-4 text-gray-400" />}
            WS {wsState.toUpperCase()}
          </span>
          {recording ? (
            <Button variant="destructive" size="sm" className="gap-2" onClick={stop}>
              <Square className="h-3.5 w-3.5" /> Stop session
            </Button>
          ) : (
            <Button size="sm" className="gap-2 bg-blue-600 text-white hover:bg-blue-700" onClick={start} disabled={wsState === "connecting"}>
              <Mic className="h-4 w-4" /> Start live session
            </Button>
          )}
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Live streaming unavailable</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {micError && (
        <Alert className="border-amber-200 bg-amber-50 text-amber-800">
          <AlertTitle>Microphone unavailable</AlertTitle>
          <AlertDescription>{micError}</AlertDescription>
        </Alert>
      )}

      {last && (
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          <MetricTile label="Current Chunk" value={`${last.t0}s–${last.t1}s`} sub={`${chunks.length} analyzed`} />
          <MetricTile
            label="AI Likelihood"
            value={last.synthetic != null ? `${Math.round(last.synthetic * 100)}%` : "N/A"}
            tone={last.synthetic != null ? (last.synthetic >= 0.6 ? "danger" : last.synthetic >= 0.35 ? "warn" : "good") : "default"}
          />
          <MetricTile label="Audio Quality" value={<span className="text-xl">{last.quality}</span>} />
          <MetricTile label="Processing Latency" value={last.latency_ms != null ? `${Math.round(last.latency_ms)} ms` : "—"} sub="per-chunk AASIST inference" />
        </div>
      )}

      <div className="rounded-xl border bg-white p-5">
        <h3 className="text-sm font-semibold text-gray-900">Chunk timeline (AI evidence over time)</h3>
        <canvas ref={canvasRef} data-h={130} className="mt-3 w-full" />
        <p className="mt-2 text-[11px] text-gray-400">
          Each bar is one ~4-s window scored by real AASIST-L inference. Red dashed line = 50% synthetic-evidence level.
        </p>
      </div>

      {verdict && (
        <div className="rounded-xl border bg-white p-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">Session verdict</h3>
            <ClassBadge classification={verdict.classification} />
          </div>
          <div className="mt-3 flex flex-wrap gap-x-8 gap-y-2 text-sm text-gray-600">
            <span>Mean synthetic evidence: <b className="tabular-nums">{verdict.synthetic_evidence != null ? `${Math.round(verdict.synthetic_evidence * 100)}%` : "N/A"}</b></span>
            <span>Confidence: <b className="tabular-nums">{Math.round(verdict.confidence)}%</b></span>
            <span>Chunks: <b className="tabular-nums">{verdict.n_chunks}</b></span>
          </div>
        </div>
      )}

      {chunks.length > 0 && (
        <div className="rounded-xl border bg-white">
          <div className="border-b px-5 py-3 text-sm font-semibold text-gray-900">Chunk log</div>
          <div className="max-h-64 overflow-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-gray-50 text-gray-500">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">Window</th>
                  <th className="px-4 py-2 text-left font-medium">AI Likelihood</th>
                  <th className="px-4 py-2 text-left font-medium">Quality</th>
                  <th className="px-4 py-2 text-left font-medium">Latency</th>
                </tr>
              </thead>
              <tbody>
                {[...chunks].reverse().map((c) => (
                  <tr key={c.index} className="border-t">
                    <td className="px-4 py-2 tabular-nums text-gray-700">{c.t0}s – {c.t1}s</td>
                    <td className="px-4 py-2 tabular-nums">{c.synthetic != null ? `${Math.round(c.synthetic * 100)}%` : "unavailable"}</td>
                    <td className="px-4 py-2"><QualityBadge state={c.quality} /></td>
                    <td className="px-4 py-2 tabular-nums text-gray-500">{c.latency_ms != null ? `${Math.round(c.latency_ms)} ms` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
