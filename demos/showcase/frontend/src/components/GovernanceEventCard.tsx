// Renders a typed refusal as a first-class chat event: the exception type, the
// human message, its remediation, any shape-specific fields (PII entities,
// content-safety categories, retry_after, the policy that fired, the kill latch,
// the request window) and the correlation/call/request ids that join the log
// line, the span and the gateway record.
import type { Governance } from "../features";

function entityList(entities: unknown): string[] {
  if (!entities) return [];
  if (Array.isArray(entities)) {
    return entities.map((e) =>
      typeof e === "string" ? e : JSON.stringify(e),
    );
  }
  return [String(entities)];
}

function retryAfterNote(gov: Governance): string {
  if (gov.disposition === "pending") {
    return "the gateway's Retry-After. Re-send the same request then; it goes through once the user approves.";
  }
  if (gov.type === "RequestRateLimitExceeded") {
    return "from x-ratelimit-reset. Wait for the request window, don't retry immediately.";
  }
  return "wait for the window, don't retry immediately.";
}

export function GovernanceEventCard({ gov }: { gov: Governance }) {
  const entities = entityList(gov.entities);
  const categories = entityList(gov.categories);
  const disposition = gov.disposition ?? (gov.retryable ? "retryable" : "terminal");
  const soft = disposition !== "terminal";
  const rw = gov.requests_window;
  return (
    <div className={`gov-card${soft ? " retryable" : ""}`}>
      <div className="gov-head">
        <span className="gov-type">{gov.type}</span>
        <span className={`badge ${soft ? "badge-roadmap" : "badge-neutral"}`}>
          {disposition === "pending" ? "pending: not a refusal" : disposition}
        </span>
        {gov.policy && (
          <span className="pill" title="e.policy">
            policy={gov.policy}
          </span>
        )}
      </div>

      <div className="gov-msg">{gov.message}</div>

      {gov.remediation && (
        <div className="gov-remediation">
          <span className="label">Remediation</span>
          {gov.remediation}
        </div>
      )}

      {entities.length > 0 && (
        <div>
          <div className="gov-msg" style={{ marginBottom: 4 }}>
            Flagged entities:
          </div>
          <div className="gov-entities">
            {entities.map((e, i) => (
              <span className="pill" key={i}>
                {e}
              </span>
            ))}
          </div>
        </div>
      )}

      {categories.length > 0 && (
        <div>
          <div className="gov-msg" style={{ marginBottom: 4 }}>
            Blocked categories:
          </div>
          <div className="gov-entities">
            {categories.map((c, i) => (
              <span className="pill" key={i}>
                {c}
              </span>
            ))}
          </div>
        </div>
      )}

      {gov.retry_after != null && (
        <div className="gov-msg">
          <b>retry_after:</b> {gov.retry_after}s, {retryAfterNote(gov)}
        </div>
      )}

      {rw && rw.limit != null && (
        <div className="gov-msg">
          <b>donkey.budget.requests:</b> {rw.remaining ?? "?"} of {rw.limit}{" "}
          requests left ({((rw.fraction_used ?? 0) * 100).toFixed(0)}% used). A
          request-count window, separate from the token budget.
        </div>
      )}

      {gov.latched && (
        <div className="gov-msg">
          <b>Budget latched:</b> <code>pace()</code> and{" "}
          <code>wait_for_reset()</code> on this Donkey now raise AgentKilled
          too, so paced work stops. No <code>donkey.on(...)</code> reaction
          can be registered for it.
        </div>
      )}

      <div className="gov-ids">
        {gov.correlation_id && (
          <span>
            <b>correlation_id</b> {gov.correlation_id}
          </span>
        )}
        {gov.call_id && (
          <span>
            <b>call_id</b> {gov.call_id}
          </span>
        )}
        {gov.request_id && (
          <span>
            <b>request_id</b> {gov.request_id}
          </span>
        )}
        {gov.code && (
          <span>
            <b>code</b> {gov.code}
          </span>
        )}
        {gov.base_url && (
          <span>
            <b>base_url</b> {gov.base_url}
          </span>
        )}
      </div>
    </div>
  );
}
