// Small presentational helpers shared across the UI.
import { Highlight, themes } from "prism-react-renderer";
import type { Budget } from "../features";

export function Badge({ kind }: { kind: "live" | "roadmap" }) {
  return (
    <span className={`badge badge-${kind}`}>
      {kind === "live" ? "● Live" : "Roadmap"}
    </span>
  );
}

// Guess the language so the shell-flavoured cards (donkey mock / curl / pytest)
// highlight as bash and the rest as python. First non-comment line decides.
function guessLang(code: string): string {
  const first = code
    .split("\n")
    .map((l) => l.trim())
    .find((l) => l && !l.startsWith("#"));
  if (first && (first.startsWith("$") || /^(pytest|curl|donkey|export)\b/.test(first))) {
    return "bash";
  }
  return "python";
}

export function CodeBlock({
  children,
  lang,
}: {
  children: string;
  lang?: string;
}) {
  const code = children.replace(/\n+$/, "");
  const language = lang ?? guessLang(code);
  // Code stays on the dark VS-Code palette in both light and dark app themes,
  // matching the docs site's Shiki blocks.
  return (
    <Highlight code={code} language={language} theme={themes.vsDark}>
      {({ tokens, getLineProps, getTokenProps }) => (
        <pre className="code scroll-fade">
          {tokens.map((line, i) => (
            <span {...getLineProps({ line })} key={i} className="code-line">
              {line.map((token, key) => (
                <span {...getTokenProps({ token })} key={key} />
              ))}
            </span>
          ))}
        </pre>
      )}
    </Highlight>
  );
}

export function BudgetBar({ budget }: { budget: Budget | null }) {
  const frac = budget?.fraction_used ?? 0;
  const pct = Math.min(100, Math.max(0, frac * 100));
  const cls = pct >= 90 ? "crit" : pct >= 70 ? "warn" : "";
  return (
    <div className="budget">
      <div className="budget-meta">
        <span>token budget</span>
        <span>
          {budget?.remaining ?? "—"}
          {budget?.limit != null ? ` / ${budget.limit}` : ""} left ·{" "}
          {(pct).toFixed(1)}% used
        </span>
      </div>
      <div className="budget-track">
        <span className={cls} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function Spinner() {
  return <span className="spinner" aria-label="loading" />;
}

// The thin strip shown in place of a collapsed pane; click to expand it back.
export function CollapsedRail({
  side,
  label,
  onExpand,
}: {
  side: "left" | "right";
  label: string;
  onExpand: () => void;
}) {
  return (
    <div className={`pane ${side}`}>
      <div className="rail">
        <button
          className="icon-btn collapse-btn"
          title={`Expand ${label}`}
          onClick={onExpand}
        >
          {side === "left" ? "»" : "«"}
        </button>
        <span className="rail-label">{label}</span>
      </div>
    </div>
  );
}
