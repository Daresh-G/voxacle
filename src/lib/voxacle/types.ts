/** VOXACLE frontend type definitions — mirrors backend payloads exactly. */

export type QualityState = "GOOD" | "FAIR" | "POOR" | "UNUSABLE";
export type Classification =
  | "GENUINE"
  | "SUSPICIOUS"
  | "HIGH RISK"
  | "INCONCLUSIVE"
  | "ANALYSIS FAILED";

export interface ComponentHealth {
  available: boolean;
  error: string | null;
  version: Record<string, unknown> | null;
}

export interface HealthResponse {
  status: "READY" | "DEGRADED" | "OFFLINE";
  components: Record<string, "ok" | "unavailable">;
  details: { aasist_l: ComponentHealth; ecapa: ComponentHealth };
  notes: string[];
}

export interface SpeakerSimilarity {
  similarity: number;
  similarity_percent: number;
  consistency: "HIGH" | "MEDIUM" | "LOW";
}

export interface ChunkResult {
  t0: number;
  t1: number;
  synthetic: number | null;
  bonafide_logit: number | null;
  quality: QualityState;
  confidence: number;
  warnings: string[];
  latency_ms?: number;
  index?: number;
}

export interface TemporalStats {
  n_chunks: number;
  n_unavailable: number;
  mean_synthetic: number | null;
  std_synthetic: number | null;
  max_synthetic: number | null;
  min_synthetic: number | null;
  temporal_instability: number | null;
  suspicious_chunk_ratio: number | null;
  variable_evidence: boolean;
}

export interface AnalyzeResult {
  analysis_id: string;
  session_id: string;
  created_at: string;
  classification: Classification;
  error?: { code: string; message: string; retryable: boolean } | null;
  risk_score: number | null;
  risk_level: string | null;
  confidence: number | null;
  confidence_label?: string;
  ai_likelihood_percent: number | null;
  ai_likelihood_label?: string;
  speaker_similarity: SpeakerSimilarity | null;
  audio_quality: QualityState | null;
  quality_metrics?: Record<string, number>;
  context_risk: string | null;
  context_risk_score?: number;
  context_reasoning?: string[];
  fusion?: { availability: Record<string, string>; disagreement: boolean | null; coverage: number | null };
  risk_components?: Record<string, number>;
  risk_drivers?: { component: string; contribution: number }[];
  warnings: string[];
  recommended_action?: string;
  action_title?: string;
  action_detail?: string;
  reasoning: {
    synthetic_evidence: string;
    speaker_consistency: string;
    temporal: string;
    audio_quality: string;
    context: string;
    confidence: string;
    lines: string[];
  };
  evidence_hash: string | null;
  latency_ms: number;
  processing?: {
    preprocessing_ops: string[];
    chunk_seconds: number;
    aasist_latency_ms?: number;
    ecapa_latency_ms?: number;
  };
  model_versions: Record<string, unknown>;
  advanced?: {
    waveform: { times: number[]; values: number[] };
    rms_curve: { times: number[]; values: number[] };
    spectrum: { freqs: number[]; mags: number[]; peak_freq_hz: number | null };
    spectrogram?: { db: number[][]; times: number[]; freqs: number[]; shape: number[] };
    mfcc?: { coefficients: number[][]; n_mfcc: number; frames: number };
    pitch_curve?: { times: number[]; hz: (number | null)[] };
    chunks: ChunkResult[];
    temporal_stats?: TemporalStats;
    dsp_metrics: Record<string, number>;
    mfcc_summary?: Record<string, number>;
    aasist?: { status: string; value: { synthetic_evidence: number; bonafide_logit: number } | null; error: string | null; warnings: string[] };
    ecapa_status?: { status: string; error: string | null };
    quality_issues: string[];
  };
  report?: Record<string, unknown>;
  file_name?: string | null;
  has_reference: boolean;
}

export interface Profile {
  id: string;
  name: string;
  speaker_label: string;
  status: string;
  quality: string | null;
  duration_sec: number | null;
  created_at: string;
  embedding_dim: number;
  notes?: string | null;
}

export interface AnalysisRow {
  id: string;
  session_id: string;
  created_at: string;
  classification: Classification;
  risk_score: number;
  risk_level: string;
  confidence: number;
  ai_likelihood: number | null;
  speaker_similarity: number | null;
  audio_quality: string | null;
  context_risk: string | null;
  action: string | null;
  file_name: string | null;
  evidence_hash: string | null;
  latency_ms: number | null;
}

export interface DashboardData {
  stats: {
    total: number;
    suspicious: number;
    high_risk: number;
    genuine: number;
    inconclusive_or_failed: number;
    avg_risk: number | null;
  };
  recent: {
    id: string;
    created_at: string;
    classification: Classification;
    risk_level: string;
    risk_score: number;
    confidence: number;
    file_name: string | null;
    action: string | null;
  }[];
}

export interface CallContext {
  caller_origin: string;
  caller_id: string;
  known_contact: string;
  channel: string;
  claimed_identity: string;
  transaction_type: string;
  transaction_amount: string | number;
  fraud_indicator: string;
}

export const EMPTY_CONTEXT: CallContext = {
  caller_origin: "UNKNOWN",
  caller_id: "",
  known_contact: "NO",
  channel: "MOBILE",
  claimed_identity: "NONE",
  transaction_type: "NONE",
  transaction_amount: "",
  fraud_indicator: "NONE",
};
