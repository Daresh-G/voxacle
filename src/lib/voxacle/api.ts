/** VOXACLE API client — all requests go through the Caddy gateway using the
 * XTransformPort query parameter (port 3030 = Python FastAPI backend). */
import type {
  AnalyzeResult,
  AnalysisRow,
  CallContext,
  DashboardData,
  HealthResponse,
  Profile,
} from "./types";

const PORT = 3030;

function u(path: string): string {
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}XTransformPort=${PORT}`;
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON error body */
  }
  if (!res.ok) {
    const detail =
      (body as { detail?: { message?: string } | string })?.detail ?? null;
    const msg =
      typeof detail === "string"
        ? detail
        : detail?.message || `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return body as T;
}

export const api = {
  health: () =>
    fetch(u("/api/health"), { cache: "no-store" }).then((r) =>
      jsonOrThrow<HealthResponse>(r),
    ),

  profiles: () =>
    fetch(u("/api/profiles"), { cache: "no-store" }).then((r) =>
      jsonOrThrow<{ profiles: Profile[] }>(r),
    ),

  createProfile: (file: File, name: string, speakerLabel: string, notes = "") => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", name);
    fd.append("speaker_label", speakerLabel);
    fd.append("notes", notes);
    return fetch(u("/api/enrollment"), { method: "POST", body: fd }).then((r) =>
      jsonOrThrow<{
        status: string;
        profile_id: string;
        quality: string;
        duration_sec: number;
        embedding_dim: number;
      }>(r),
    );
  },

  deleteProfile: (id: string) =>
    fetch(u(`/api/profiles/${id}`), { method: "DELETE" }).then((r) =>
      jsonOrThrow<{ status: string }>(r),
    ),

  analyze: (
    file: File,
    context: Partial<CallContext>,
    referenceProfileId?: string,
    referenceFile?: File | null,
  ) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append(
      "context",
      JSON.stringify({
        caller_origin: context.caller_origin || "UNKNOWN",
        caller_id: context.caller_id || "",
        known_contact: context.known_contact || "NO",
        channel: context.channel || "MOBILE",
        claimed_identity: context.claimed_identity || "NONE",
        transaction_type: context.transaction_type || "NONE",
        transaction_amount: Number(context.transaction_amount) || 0,
        fraud_indicator: context.fraud_indicator || "NONE",
      }),
    );
    if (referenceProfileId) fd.append("reference_profile_id", referenceProfileId);
    if (referenceFile) fd.append("reference_file", referenceFile);
    return fetch(u("/api/analyze"), { method: "POST", body: fd }).then((r) =>
      jsonOrThrow<AnalyzeResult>(r),
    );
  },

  analyses: (limit = 100) =>
    fetch(u(`/api/analyses?limit=${limit}`), { cache: "no-store" }).then((r) =>
      jsonOrThrow<{ analyses: AnalysisRow[] }>(r),
    ),

  analysis: (id: string) =>
    fetch(u(`/api/analysis/${id}`), { cache: "no-store" }).then((r) =>
      jsonOrThrow<{ result: AnalyzeResult } & Record<string, unknown>>(r),
    ),

  reportTextUrl: (id: string) => u(`/api/analysis/${id}/report.txt`),

  dashboard: () =>
    fetch(u("/api/dashboard"), { cache: "no-store" }).then((r) =>
      jsonOrThrow<DashboardData>(r),
    ),

  settings: () =>
    fetch(u("/api/settings"), { cache: "no-store" }).then((r) =>
      jsonOrThrow<{ settings: Record<string, unknown> }>(r),
    ),

  saveSettings: (values: Record<string, unknown>) =>
    fetch(u("/api/settings"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    }).then((r) => jsonOrThrow<{ settings: Record<string, unknown> }>(r)),
};

/** WebSocket URL for live monitor streaming. */
export function wsAnalysisUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/analysis?XTransformPort=${PORT}`;
}
