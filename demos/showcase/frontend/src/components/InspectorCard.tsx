// The "what DDK just gave you for free" panel appended after a governed run:
// the live Budget bar, the gateway identity from donkey.last_call, and the raw
// donkey.llm.chat OTel span JSON — the same span that flows to Grafana/Tempo.
import type { Budget, LastCall, Span } from "../features";
import { BudgetBar } from "./bits";

function SpanAttrs({ span }: { span: Span }) {
  // Surface the governance-relevant attributes first, then the rest.
  const attrs = span.attributes ?? {};
  const keys = Object.keys(attrs).sort((a, b) => {
    const rank = (k: string) =>
      k.startsWith("donkey.") ? 0 : k.startsWith("gen_ai.") ? 1 : 2;
    return rank(a) - rank(b) || a.localeCompare(b);
  });
  return (
    <div className="kv">
      <div className="k">name</div>
      <div className="v accent">{span.name}</div>
      <div className="k">status</div>
      <div className={`v ${span.status === "ERROR" ? "" : "accent"}`}>
        {span.status}
      </div>
      {keys.map((k) => (
        <div key={k} style={{ display: "contents" }}>
          <div className="k">{k}</div>
          <div className={`v${k.startsWith("donkey.") ? " accent" : ""}`}>
            {String(attrs[k])}
          </div>
        </div>
      ))}
    </div>
  );
}

export function InspectorCard({
  budget,
  lastCall,
  span,
}: {
  budget: Budget | null;
  lastCall: LastCall | null;
  span: Span | null;
}) {
  return (
    <details className="inspect" open>
      <summary>DDK gave you this — for free</summary>
      <div className="inspect-body">
        {budget && <BudgetBar budget={budget} />}

        {lastCall && (
          <div>
            <div className="budget-meta" style={{ marginBottom: 4 }}>
              <span>donkey.last_call — gateway identity</span>
            </div>
            <div className="kv">
              <div className="k">served_model</div>
              <div className="v accent">{lastCall.served_model ?? "—"}</div>
              <div className="k">routing_type</div>
              <div className="v">{lastCall.routing_type ?? "—"}</div>
              <div className="k">fallback</div>
              <div className="v">{String(lastCall.fallback)}</div>
              {lastCall.total_tokens != null && (
                <>
                  <div className="k">tokens (in/out/total)</div>
                  <div className="v">
                    {lastCall.input_tokens}/{lastCall.output_tokens}/
                    {lastCall.total_tokens}
                  </div>
                </>
              )}
              {lastCall.request_id && (
                <>
                  <div className="k">request_id</div>
                  <div className="v">{lastCall.request_id}</div>
                </>
              )}
            </div>
          </div>
        )}

        {span && (
          <div>
            <div className="budget-meta" style={{ marginBottom: 4 }}>
              <span>OTel GenAI span</span>
            </div>
            <SpanAttrs span={span} />
          </div>
        )}
      </div>
    </details>
  );
}
