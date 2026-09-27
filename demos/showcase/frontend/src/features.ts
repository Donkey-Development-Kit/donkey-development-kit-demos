// Types shared across the UI. The catalog data itself comes from GET /api/features
// (backend app/features.py is the single source of truth); these just describe
// its shape and the shapes of the SSE events the backend streams.

export type FeatureAction =
  | "chat"
  | "pace"
  | "conformance"
  | "doctor"
  | "info";

export interface Feature {
  id: string;
  group: string;
  icon: string;
  title: string;
  badge: "live" | "roadmap";
  blurb: string;
  action: FeatureAction;
  prompt: string;
  model: string;
  watch: string;
  without: string;
  with: string;
}

export interface Budget {
  limit: number | null;
  remaining: number | null;
  fraction_used: number | null;
  reset_at: string | null;
  observed_at: string | null;
}

export interface LastCall {
  state: string;
  served_model: string | null;
  served_provider: string | null;
  routing_type: string | null;
  fallback: boolean | null;
  substituted: boolean | null;
  request_id: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
}

export interface Span {
  name: string;
  trace_id: string;
  span_id: string;
  status: string;
  attributes: Record<string, unknown>;
}

export interface Governance {
  type: string;
  message: string;
  remediation: string | null;
  retryable: boolean;
  correlation_id: string | null;
  call_id: string | null;
  request_id: string | null;
  entities?: unknown;
  retry_after?: number | null;
  categories?: unknown;
  code?: string | null;
  error_type?: string | null;
  base_url?: string | null;
}

export interface SimulatorInfo {
  base_url: string;
  scenarios: string[];
  healthy: boolean;
  managed: boolean;
}

// ---- compare (/api/compare) ----

export interface CompareWithout {
  ok: boolean;
  text?: string;
  status_code?: number | null;
  body?: string;
  note?: string;
}

export interface CompareWith {
  ok: boolean;
  text?: string;
  governance?: Governance;
  budget?: Budget;
  note?: string;
}

export interface CompareResult {
  prompt: string;
  model: string;
  without: CompareWithout;
  with: CompareWith;
}

// ---- conformance (/api/conformance) ----

export interface ConformanceRow {
  name: string;
  title: string;
  status: "pass" | "fail" | "exempt";
  detail: string | null;
}

export interface ConformanceResult {
  rows: ConformanceRow[];
  summary: { pass: number; fail: number; exempt: number; total: number };
}
