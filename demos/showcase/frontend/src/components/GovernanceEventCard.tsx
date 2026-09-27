// Renders a typed refusal as a first-class chat event: the exception type, the
// human message, its remediation, any shape-specific fields (PII entities,
// content-safety categories, retry_after) and the correlation/call/request ids
// that join the log line, the span and the gateway record.
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

export function GovernanceEventCard({ gov }: { gov: Governance }) {
  const entities = entityList(gov.entities);
  const categories = entityList(gov.categories);
  return (
    <div className={`gov-card${gov.retryable ? " retryable" : ""}`}>
      <div className="gov-head">
        <span className="gov-type">{gov.type}</span>
        <span className={`badge ${gov.retryable ? "badge-roadmap" : "badge-neutral"}`}>
          {gov.retryable ? "retryable" : "terminal"}
        </span>
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
          <b>retry_after:</b> {gov.retry_after}s — wait for the window, don't
          retry immediately.
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
