// Side-by-side "Without DDK" vs "With DDK" for a feature: the code contrast
// always shows; once the user runs the live comparison (/api/compare) the real
// outcome of each path is rendered beneath its column.
import type { CompareResult, Feature } from "../features";
import { CodeBlock } from "./bits";

function WithoutOutcome({ result }: { result: CompareResult }) {
  const w = result.without;
  if (w.ok) {
    return (
      <div className="compare-outcome ok">
        <span className="tag">200 OK</span> — {(w.text || "").slice(0, 160)}
      </div>
    );
  }
  return (
    <div className="compare-outcome err">
      <div>
        <span className="tag">HTTP {w.status_code ?? "?"}</span> opaque response
      </div>
      {w.note && <div style={{ marginTop: 4 }}>{w.note}</div>}
    </div>
  );
}

function WithOutcome({ result }: { result: CompareResult }) {
  const w = result.with;
  if (w.ok) {
    return (
      <div className="compare-outcome ok">
        <span className="tag">answer</span> — {(w.text || "").slice(0, 160)}
      </div>
    );
  }
  const g = w.governance;
  return (
    <div className="compare-outcome err">
      <div>
        <span className="tag">{g?.type ?? "DonkeyError"}</span> — typed &
        catchable
      </div>
      {g?.remediation && <div style={{ marginTop: 4 }}>↳ {g.remediation}</div>}
      {w.note && (
        <div style={{ marginTop: 4, color: "var(--af-fg-subtle)" }}>{w.note}</div>
      )}
    </div>
  );
}

export function ComparePanel({
  feature,
  result,
}: {
  feature: Feature;
  result: CompareResult | null;
}) {
  return (
    <div className="compare">
      <div className="compare-col without">
        <div className="head">✕ Without DDK</div>
        <CodeBlock>{feature.without || "// (nothing — you're on your own)"}</CodeBlock>
        {result && <WithoutOutcome result={result} />}
      </div>
      <div className="compare-col with">
        <div className="head">✓ With DDK</div>
        <CodeBlock>{feature.with}</CodeBlock>
        {result && <WithOutcome result={result} />}
      </div>
    </div>
  );
}
