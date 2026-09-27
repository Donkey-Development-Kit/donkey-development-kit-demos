// Renderers for the non-chat action results that still land in the timeline:
// the pacing batch, the conformance table, and the `donkey doctor` report.
import type { Budget, ConformanceResult } from "../features";
import { BudgetBar } from "./bits";

export interface PaceCallRow {
  n: number;
  status: "ok";
}

export interface ReserveReached {
  n: number;
  fraction_used: number | null;
  reserve: number;
  reset_at: string | null;
  remediation: string | null;
}

export function PaceResult({
  reserve,
  calls,
  reserveReached,
  budget,
}: {
  reserve: number;
  calls: PaceCallRow[];
  reserveReached: ReserveReached | null;
  budget: Budget | null;
}) {
  return (
    <div className="inspect" style={{ padding: "0.7rem 0.8rem" }}>
      <div className="budget-meta" style={{ marginBottom: 6 }}>
        <span>
          budget.pace(reserve={reserve}) — {calls.length} call
          {calls.length === 1 ? "" : "s"} completed
        </span>
      </div>
      {budget && <BudgetBar budget={budget} />}
      <div className="gov-entities" style={{ marginTop: 8 }}>
        {calls.map((c) => (
          <span className="pill" key={c.n}>
            #{c.n} ✓
          </span>
        ))}
      </div>
      {reserveReached && (
        <div className="gov-card retryable" style={{ marginTop: 10 }}>
          <div className="gov-head">
            <span className="gov-type">BudgetReserveReached</span>
            <span className="badge badge-roadmap">before call #{reserveReached.n}</span>
          </div>
          <div className="gov-msg">
            Stopped at {((reserveReached.fraction_used ?? 0) * 100).toFixed(1)}%
            used — before crossing the {(reserveReached.reserve * 100).toFixed(0)}%
            reserve. In production you'd{" "}
            <code>await donkey.budget.wait_for_reset()</code> and continue.
          </div>
          {reserveReached.remediation && (
            <div className="gov-remediation">
              <span className="label">Remediation</span>
              {reserveReached.remediation}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ConformanceTable({ result }: { result: ConformanceResult }) {
  const s = result.summary;
  return (
    <div>
      <div className="conf-summary">
        <span className="status-chip pass">{s.pass} pass</span>
        {s.fail > 0 && <span className="status-chip fail">{s.fail} fail</span>}
        {s.exempt > 0 && (
          <span className="status-chip exempt">{s.exempt} exempt</span>
        )}
        <span style={{ color: "var(--af-fg-subtle)" }}>of {s.total}</span>
      </div>
      <table className="conf-table">
        <thead>
          <tr>
            <th>Scenario</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {result.rows.map((r) => (
            <tr key={r.name}>
              <td>
                {r.title}
                {r.detail && (
                  <div style={{ color: "var(--af-fg-subtle)", marginTop: 2 }}>
                    {r.detail}
                  </div>
                )}
              </td>
              <td>
                <span className={`status-chip ${r.status}`}>{r.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DoctorReport({ output }: { output: string }) {
  return <pre className="code scroll-fade">{output.trim()}</pre>;
}
