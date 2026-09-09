"use client";

/**
 * Canvas chart renderers for REAL backend data (spec: never fake charts).
 * All inputs come from the analysis payload produced by actual DSP/model runs.
 */

const AXIS_COLOR = "#e2e8f0";
const TEXT_COLOR = "#64748b";

function prepCanvas(canvas: HTMLCanvasElement): CanvasRenderingContext2D | null {
  const parent = canvas.parentElement;
  if (!parent) return null;
  const w = parent.clientWidth || 320;
  const h = canvas.dataset.h ? parseInt(canvas.dataset.h) : 140;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = `${w}px`;
  canvas.style.height = `${h}px`;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return ctx;
}

/** Waveform: symmetric min/max envelope from amplitude values. */
export function drawWaveform(canvas: HTMLCanvasElement, values: number[], color = "#2563eb") {
  const ctx = prepCanvas(canvas);
  if (!ctx) return;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  ctx.strokeStyle = AXIS_COLOR;
  ctx.beginPath(); ctx.moveTo(0, h / 2); ctx.lineTo(w, h / 2); ctx.stroke();
  if (!values.length) return;
  const n = values.length;
  const mid = h / 2;
  const scale = (h / 2 - 4) / Math.max(0.05, Math.max(...values.map(Math.abs)));
  const colW = w / n;
  ctx.fillStyle = color;
  for (let x = 0; x < n; x++) {
    const a = Math.abs(values[x]) * scale;
    ctx.fillRect(x * colW, mid - a, Math.max(1, colW * 0.9), a * 2 || 1);
  }
}

/** RMS energy curve over time. */
export function drawCurve(
  canvas: HTMLCanvasElement,
  times: number[],
  values: number[],
  color = "#0d9488",
  fill = true,
) {
  const ctx = prepCanvas(canvas);
  if (!ctx) return;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (times.length < 2) return;
  const max = Math.max(...values, 1e-9);
  const t0 = times[0], t1 = times[times.length - 1];
  const px = (t: number) => ((t - t0) / Math.max(1e-9, t1 - t0)) * w;
  const py = (v: number) => h - 6 - (v / max) * (h - 14);
  if (fill) {
    ctx.beginPath();
    ctx.moveTo(px(times[0]), h);
    times.forEach((t, i) => ctx.lineTo(px(t), py(values[i])));
    ctx.lineTo(px(times[times.length - 1]), h);
    ctx.closePath();
    ctx.fillStyle = color + "22";
    ctx.fill();
  }
  ctx.beginPath();
  times.forEach((t, i) => (i ? ctx.lineTo(px(t), py(values[i])) : ctx.moveTo(px(t), py(values[i]))));
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.6;
  ctx.stroke();
  ctx.fillStyle = TEXT_COLOR;
  ctx.font = "10px sans-serif";
  ctx.fillText(`max ${max.toFixed(3)}`, 6, 12);
}

/** Frequency spectrum (dB). */
export function drawSpectrum(canvas: HTMLCanvasElement, freqs: number[], mags: number[]) {
  const ctx = prepCanvas(canvas);
  if (!ctx) return;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (!mags.length) return;
  const min = Math.min(...mags), max = Math.max(...mags);
  const bw = w / mags.length;
  mags.forEach((m, i) => {
    const v = (m - min) / Math.max(1e-9, max - min);
    const bh = v * (h - 16);
    const heat = 200 + Math.round(v * 55);
    ctx.fillStyle = `rgb(${40 + v * 40}, ${90 + v * 60}, ${heat})`;
    ctx.fillRect(i * bw, h - 14 - bh, Math.max(1, bw - 0.5), bh);
  });
  ctx.fillStyle = TEXT_COLOR;
  ctx.font = "10px sans-serif";
  ctx.fillText(`${Math.round(freqs[0])} Hz`, 4, h - 2);
  const fmax = freqs[freqs.length - 1];
  ctx.fillText(`${Math.round(fmax) >= 1000 ? (fmax / 1000).toFixed(1) + " kHz" : Math.round(fmax) + " Hz"}`, w - 52, h - 2);
}

/** Viridis-like color for heatmap cells. */
function heatColor(v: number): [number, number, number] {
  // v in [0,1]; simple perceptual ramp: dark blue -> teal -> yellow
  const r = Math.round(255 * Math.min(1, Math.max(0, 1.6 * v - 0.6)));
  const g = Math.round(255 * Math.min(1, Math.max(0, 1.5 * v - 0.1)));
  const b = Math.round(255 * Math.min(1, Math.max(0, 0.4 + 1.2 * (v < 0.45 ? v : 1 - v * 0.8))));
  return [r, g, b];
}

/** Spectrogram heatmap from dB matrix (rows = freq, cols = time). */
export function drawHeatmap(
  canvas: HTMLCanvasElement,
  matrix: number[][],
  opts: { lowHigh?: boolean } = {},
) {
  const ctx = prepCanvas(canvas);
  if (!ctx) return;
  if (!matrix.length || !matrix[0].length) return;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  const rows = matrix.length, cols = matrix[0].length;
  let min = Infinity, max = -Infinity;
  for (const row of matrix) for (const v of row) { if (v < min) min = v; if (v > max) max = v; }
  const range = Math.max(1e-9, max - min);
  const cw = w / cols, ch = h / rows;
  for (let r = 0; r < rows; r++) {
    const yTop = opts.lowHigh ? r * ch : h - (r + 1) * ch;
    for (let c = 0; c < cols; c++) {
      const v = (matrix[r][c] - min) / range;
      const [R, G, B] = heatColor(v);
      ctx.fillStyle = `rgb(${R},${G},${B})`;
      ctx.fillRect(c * cw, yTop, cw + 0.6, ch + 0.6);
    }
  }
}

/** AI-likelihood timeline over chunks (bar per chunk). */
export function drawChunkTimeline(
  canvas: HTMLCanvasElement,
  chunks: { t0: number; t1: number; synthetic: number | null }[],
) {
  const ctx = prepCanvas(canvas);
  if (!ctx) return;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  ctx.strokeStyle = AXIS_COLOR;
  [0.25, 0.5, 0.75].forEach((g) => {
    ctx.beginPath(); ctx.moveTo(0, h * g); ctx.lineTo(w, h * g); ctx.stroke();
  });
  if (!chunks.length) return;
  const bw = w / chunks.length;
  chunks.forEach((c, i) => {
    const bh = c.synthetic == null ? 0 : c.synthetic * (h - 12);
    const v = c.synthetic ?? 0;
    ctx.fillStyle =
      c.synthetic == null ? "#cbd5e1" : v > 0.6 ? "#dc2626" : v > 0.35 ? "#f59e0b" : "#16a34a";
    ctx.fillRect(i * bw + 1, h - 10 - bh, Math.max(2, bw - 3), bh);
    ctx.fillStyle = TEXT_COLOR;
    ctx.font = "9px sans-serif";
    if (chunks.length <= 24 || i % Math.ceil(chunks.length / 24) === 0) {
      ctx.fillText(`${Math.round(c.t0)}s`, i * bw + 2, h - 1);
    }
  });
  ctx.strokeStyle = "#dc2626";
  ctx.setLineDash([4, 3]);
  ctx.beginPath();
  ctx.moveTo(0, h - 10 - 0.5 * (h - 12));
  ctx.lineTo(w, h - 10 - 0.5 * (h - 12));
  ctx.stroke();
  ctx.setLineDash([]);
}

/** Pitch curve (nulls for unvoiced frames). */
export function drawPitch(canvas: HTMLCanvasElement, times: number[], hz: (number | null)[]) {
  const ctx = prepCanvas(canvas);
  if (!ctx) return;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  const valid = hz.filter((v): v is number => v != null && isFinite(v));
  if (valid.length < 2 || times.length < 2) return;
  const min = Math.min(...valid), max = Math.max(...valid);
  const t0 = times[0], t1 = times[times.length - 1];
  const px = (t: number) => ((t - t0) / Math.max(1e-9, t1 - t0)) * w;
  const py = (v: number) => h - 6 - ((v - min) / Math.max(1e-9, max - min)) * (h - 14);
  ctx.strokeStyle = "#7c3aed";
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  let started = false;
  for (let i = 0; i < times.length; i++) {
    const v = hz[i];
    if (v == null || !isFinite(v)) { started = false; continue; }
    if (!started) { ctx.moveTo(px(times[i]), py(v)); started = true; }
    else ctx.lineTo(px(times[i]), py(v));
  }
  ctx.stroke();
  ctx.fillStyle = TEXT_COLOR;
  ctx.font = "10px sans-serif";
  ctx.fillText(`${Math.round(min)} Hz`, 6, 12);
  ctx.fillText(`${Math.round(max)} Hz`, 6, h - 4);
}
