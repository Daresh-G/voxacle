"use client";

/**
 * VoiceCard — upload / record / drag-drop input card (reference screenshot).
 * Recording uses the browser microphone; playback preview included.
 * All metadata shown (duration/size) comes from the REAL selected file.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Mic, Pause, Play, Square, Upload, X } from "lucide-react";

export interface AttachedAudio {
  file: File;
  durationSec: number | null;
  previewUrl: string;
  isRecording: boolean;
}

export function VoiceCard({
  title,
  optionalBadge = false,
  description,
  value,
  onChange,
}: {
  title: string;
  optionalBadge?: boolean;
  description: string;
  value: AttachedAudio | null;
  onChange: (v: AttachedAudio | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [recording, setRecording] = useState(false);
  const [recError, setRecError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [playing, setPlaying] = useState(false);

  const attach = useCallback(
    (file: File, durationSec: number | null) => {
      onChange({
        file,
        durationSec,
        previewUrl: URL.createObjectURL(file),
        isRecording: false,
      });
    },
    [onChange],
  );

  const probeDuration = useCallback(
    (file: File, cb: (d: number | null) => void) => {
      const url = URL.createObjectURL(file);
      const a = new Audio();
      a.preload = "metadata";
      a.onloadedmetadata = () => {
        cb(isFinite(a.duration) ? a.duration : null);
        URL.revokeObjectURL(url);
      };
      a.onerror = () => {
        cb(null);
        URL.revokeObjectURL(url);
      };
      a.src = url;
    },
    [],
  );

  const onPick = (f: File | undefined) => {
    if (!f) return;
    setRecError(null);
    probeDuration(f, (d) => attach(f, d));
  };

  const startRecording = async () => {
    setRecError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: rec.mimeType || "audio/webm" });
        const ext = (rec.mimeType || "audio/webm").includes("mp4") ? "m4a" : "webm";
        const file = new File([blob], `recording_${Date.now()}.${ext}`, { type: blob.type });
        probeDuration(file, (d) => attach(file, d));
      };
      rec.start();
      mediaRecorderRef.current = rec;
      setRecording(true);
    } catch (e) {
      setRecError(
        "Microphone unavailable in this environment. Use Upload instead — recording requires browser mic permission.",
      );
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
    setRecording(false);
  };

  useEffect(() => () => { if (value) URL.revokeObjectURL(value.previewUrl); }, [value]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (playing) { audioRef.current.pause(); setPlaying(false); }
    else { audioRef.current.play(); setPlaying(true); }
  };

  const fmtSize = (b: number) => (b > 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(1)} MB` : `${Math.round(b / 1024)} KB`);

  return (
    <div className="rounded-xl border bg-white">
      <div className="flex items-start justify-between border-b px-5 py-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
            {optionalBadge && (
              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-gray-500">
                OPTIONAL
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-gray-500">{description}</p>
        </div>
      </div>

      <div className="p-5">
        {!value ? (
          <div
            data-dropzone
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              onPick(e.dataTransfer.files?.[0]);
            }}
            className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-10 transition-colors ${
              dragOver ? "border-blue-400 bg-blue-50/40" : "border-gray-200 bg-gray-50/50"
            }`}
          >
            <div className="flex items-center gap-3">
              <Button type="button" variant="outline" size="sm" className="gap-2" onClick={() => inputRef.current?.click()}>
                <Upload className="h-4 w-4" /> Upload
              </Button>
              {recording ? (
                <Button type="button" variant="destructive" size="sm" className="gap-2" onClick={stopRecording}>
                  <Square className="h-3.5 w-3.5" /> Stop
                </Button>
              ) : (
                <Button type="button" variant="outline" size="sm" className="gap-2" onClick={startRecording}>
                  <Mic className="h-4 w-4" /> Record
                </Button>
              )}
            </div>
            <p className="mt-3 text-xs text-gray-400">Drag &amp; drop or choose a file · WAV, MP3, M4A, FLAC, OGG, WEBM</p>
            {recording && (
              <p className="mt-2 flex items-center gap-1.5 text-xs font-medium text-red-600">
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-red-500" /> Recording…
              </p>
            )}
            {recError && <p className="mt-2 max-w-sm text-center text-xs text-red-600">{recError}</p>}
            <input
              ref={inputRef}
              type="file"
              accept=".wav,.mp3,.m4a,.flac,.ogg,.webm,audio/*"
              className="hidden"
              onChange={(e) => onPick(e.target.files?.[0])}
            />
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3 rounded-lg border bg-gray-50/60 px-3 py-2.5">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-gray-800">{value.file.name}</div>
                <div className="mt-0.5 text-xs text-gray-500">
                  {fmtSize(value.file.size)}
                  {value.durationSec != null && ` · ${value.durationSec.toFixed(1)} s`}
                  {value.isRecording && " · microphone recording"}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <Button type="button" variant="ghost" size="icon" className="h-8 w-8" onClick={togglePlay} aria-label={playing ? "Pause preview" : "Play preview"}>
                  {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-gray-400 hover:text-red-600"
                  onClick={() => { setPlaying(false); onChange(null); }}
                  aria-label="Remove file"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <audio ref={audioRef} src={value.previewUrl} onEnded={() => setPlaying(false)} className="hidden" />
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="text-xs font-medium text-blue-600 hover:underline"
            >
              Replace file…
            </button>
            <input
              ref={inputRef}
              type="file"
              accept=".wav,.mp3,.m4a,.flac,.ogg,.webm,audio/*"
              className="hidden"
              onChange={(e) => onPick(e.target.files?.[0])}
            />
          </div>
        )}
      </div>
    </div>
  );
}
