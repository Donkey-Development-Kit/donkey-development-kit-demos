// Types shared across the UI. The catalog data itself comes from GET /api/features
// (backend app/features.py), or matching public/replay/features.json metadata in
// static mode. These describe its shape and the backend's SSE event shapes.

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
  // "live": wired into this showcase. "shipped": on SDK develop but
  // descriptive-only here. "roadmap": not on SDK develop. None of them means
  // live gateway verification; that is stated in each card's `watch` text.
  // Descriptive-only cards use action "info" and never invent replay outputs.
  badge: "live" | "shipped" | "roadmap";
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
  // "terminal" (never retried), "retryable" (5xx) or "pending" (CIBA: the
  // gateway is waiting on the user; re-send after retry_after).
  disposition?: "terminal" | "retryable" | "pending";
  policy?: string | null;
  correlation_id: string | null;
  call_id: string | null;
  request_id: string | null;
  entities?: unknown;
  retry_after?: number | null;
  categories?: unknown;
  code?: string | null;
  error_type?: string | null;
  base_url?: string | null;
  // AgentKilled: whether the Budget latched (pace()/wait_for_reset() now raise it).
  latched?: boolean;
  // RequestRateLimitExceeded: donkey.budget.requests after the 429.
  requests_window?: {
    limit: number | null;
    remaining: number | null;
    fraction_used: number | null;
  };
}

// What a donkey.on(...) refusal reaction did (refusal-reactions card).
export interface ReactionTrail {
  on: string;
  reaction: string;
  refusal: string;
  policy: string | null;
  removed: string[];
  resent_prompt: string | null;
  resends: number;
  max_times: number;
  outcome: "answered" | "refused again";
  // donkey.policy.decision of each governed request's span, oldest first.
  decisions?: (string | null)[];
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
  reaction?: ReactionTrail;
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
