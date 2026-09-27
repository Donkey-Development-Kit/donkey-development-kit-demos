// One catalog entry. Collapsed: icon, title, badge, blurb. Expanded (when
// selected): what-to-watch, the primary action button that drives the chat
// pane, an on-demand live "Without vs With DDK" comparison, and the code
// contrast that makes the value concrete.
import { useState } from "react";
import type { CompareResult, Feature } from "../features";
import { track } from "../analytics";
import { api } from "../api";
import { Badge, Spinner } from "./bits";
import { ComparePanel } from "./ComparePanel";

const ACTION_LABEL: Record<Feature["action"], string | null> = {
  chat: "▶ Run in chat",
  pace: "▶ Run the batch",
  conformance: "▶ Run conformance",
  doctor: "▶ Run donkey doctor",
  info: null,
};

export function FeatureCard({
  feature,
  selected,
  busy,
  onSelect,
  onRun,
}: {
  feature: Feature;
  selected: boolean;
  busy: boolean;
  onSelect: () => void;
  onRun: (feature: Feature) => void;
}) {
  const [compare, setCompare] = useState<CompareResult | null>(null);
  const [comparing, setComparing] = useState(false);

  const isRoadmap = feature.badge === "roadmap";
  const runLabel = ACTION_LABEL[feature.action];

  async function runCompare() {
    track(`compare-${feature.id}`, feature.title);
    setComparing(true);
    try {
      setCompare(await api.compare({ prompt: feature.prompt, model: feature.model }));
    } finally {
      setComparing(false);
    }
  }

  return (
    <div
      className={`feature-card${selected ? " selected" : ""}${
        isRoadmap ? " roadmap" : ""
      }`}
    >
      <button className="feature-card-head" onClick={onSelect}>
        <span className="feature-icon">{feature.icon}</span>
        <span className="feature-text">
          <span className="feature-title-row">
            <span className="feature-title">{feature.title}</span>
            <Badge kind={feature.badge} />
          </span>
          <span className="feature-blurb">{feature.blurb}</span>
        </span>
      </button>

      {selected && (
        <div className="feature-detail">
          <div className="watch-note">
            <span className="label">Watch</span>
            {feature.watch}
          </div>

          {!isRoadmap && (
            <div className="feature-actions">
              {runLabel && (
                <button
                  className="btn btn-primary"
                  disabled={busy}
                  onClick={() => onRun(feature)}
                >
                  {runLabel}
                </button>
              )}
              {feature.action === "chat" && (
                <button
                  className="btn btn-secondary"
                  disabled={comparing}
                  onClick={runCompare}
                >
                  {comparing ? <Spinner /> : "⇄"} Compare live
                </button>
              )}
            </div>
          )}

          <ComparePanel feature={feature} result={compare} />
        </div>
      )}
    </div>
  );
}
