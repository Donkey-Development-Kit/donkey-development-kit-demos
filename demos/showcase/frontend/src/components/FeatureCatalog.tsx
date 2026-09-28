// The left pane: features grouped exactly as the docs' feature overview
// (Model access, Governance, Observability, Developer tooling, Roadmap), each a
// clickable card carrying a prepared prompt and a with/without comparison.
import type { Feature } from "../features";
import { FeatureCard } from "./FeatureCard";

const GROUP_ORDER = [
  "Model access",
  "Governance",
  "Observability",
  "Developer tooling",
  "Roadmap",
];

export function FeatureCatalog({
  features,
  selectedId,
  busy,
  onSelect,
  onRun,
  onCollapse,
}: {
  features: Feature[];
  selectedId: string | null;
  busy: boolean;
  onSelect: (id: string) => void;
  onRun: (feature: Feature) => void;
  onCollapse: () => void;
}) {
  const groups = new Map<string, Feature[]>();
  for (const f of features) {
    if (!groups.has(f.group)) groups.set(f.group, []);
    groups.get(f.group)!.push(f);
  }
  const orderedGroups = [...groups.keys()].sort(
    (a, b) => GROUP_ORDER.indexOf(a) - GROUP_ORDER.indexOf(b),
  );

  return (
    <div className="pane left">
      <div className="pane-head">
        <span className="eyebrow">Features · milestone 11</span>
        <span className="spacer" />
        <span className="hint">Click a card, then run it in the chat →</span>
        <button
          className="icon-btn collapse-btn"
          title="Collapse features"
          onClick={onCollapse}
        >
          «
        </button>
      </div>
      <div className="catalog-scroll scroll-fade">
        {orderedGroups.map((group) => (
          <div className="catalog-group" key={group}>
            <div className="catalog-group-label">
              {group === "Roadmap" ? "Roadmap · documented, not wired" : group}
            </div>
            {groups.get(group)!.map((f) => (
              <FeatureCard
                key={f.id}
                feature={f}
                selected={selectedId === f.id}
                busy={busy}
                onSelect={() => onSelect(f.id)}
                onRun={onRun}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
