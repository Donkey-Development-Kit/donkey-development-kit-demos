// Site stats behind the header logo: visits to the page and, per feature card,
// how often it was opened, run, and compared — read from GoatCounter's public
// counter. GoatCounter counts once per visitor session, so these are visits,
// not raw hits.
import { useEffect, useRef, useState } from "react";
import { ANALYTICS, CounterError, DASHBOARD, counter } from "../analytics";
import type { Feature } from "../features";
import { Spinner } from "./bits";

interface Row {
  feature: Feature;
  opens: number;
  runs: number;
  compares: number;
}

interface Stats {
  visits: { all: number; month: number; week: number };
  freeform: number;
  rows: Row[];
}

export function StatsPanel({
  features,
  onClose,
}: {
  features: Feature[];
  onClose: () => void;
}) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    if (!ANALYTICS) return;
    const page = window.location.pathname;
    Promise.all([
      counter(page),
      counter(page, "month"),
      counter(page, "week"),
      counter("chat-freeform"),
      ...features.flatMap((f) => [
        counter(`open-${f.id}`),
        counter(`run-${f.id}`),
        f.action === "chat" ? counter(`compare-${f.id}`) : Promise.resolve(0),
      ]),
    ])
      .then(([all, month, week, freeform, ...perFeature]) => {
        const rows = features
          .map((feature, i) => ({
            feature,
            opens: perFeature[i * 3],
            runs: perFeature[i * 3 + 1],
            compares: perFeature[i * 3 + 2],
          }))
          .sort((a, b) => b.runs + b.opens - (a.runs + a.opens));
        setStats({ visits: { all, month, week }, freeform, rows });
      })
      .catch((err) => {
        setError(
          err instanceof CounterError
            ? `GoatCounter's public counter answered ${err.status}; it may not be enabled for this site yet.`
            : "Could not read the counts: the public counter may not be enabled yet, or an ad blocker is blocking GoatCounter.",
        );
      });
  }, [features]);

  const top = Math.max(1, ...(stats?.rows.map((r) => r.runs + r.opens) ?? [1]));

  return (
    <div className="stats-backdrop" onClick={onClose}>
      <div
        className="stats-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="stats-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="stats-head">
          <h2 id="stats-title">Showcase stats</h2>
          <button ref={closeRef} className="icon-btn" aria-label="Close stats" onClick={onClose}>
            ✕
          </button>
        </div>

        {!ANALYTICS && (
          <p className="stats-note">
            Stats are collected on the GitHub Pages build only; this build sends nothing.
          </p>
        )}
        {ANALYTICS && error && <p className="stats-note">{error}</p>}
        {ANALYTICS && !stats && !error && (
          <p className="stats-note">
            <Spinner /> Loading…
          </p>
        )}

        {stats && (
          <>
            <div className="stats-tiles">
              <Tile label="Visits · all time" value={stats.visits.all} />
              <Tile label="Last 30 days" value={stats.visits.month} />
              <Tile label="Last 7 days" value={stats.visits.week} />
              <Tile label="Free-form prompts" value={stats.freeform} />
            </div>

            <h3>Favourite demos</h3>
            <table className="stats-table">
              <thead>
                <tr>
                  <th scope="col">Feature</th>
                  <th scope="col">Opened</th>
                  <th scope="col">Run</th>
                  <th scope="col">Compared</th>
                </tr>
              </thead>
              <tbody>
                {stats.rows.map((r) => (
                  <tr key={r.feature.id}>
                    <th scope="row">
                      <span aria-hidden="true">{r.feature.icon}</span> {r.feature.title}
                      <span
                        className="stats-bar"
                        style={{ width: `${((r.runs + r.opens) / top) * 100}%` }}
                      />
                    </th>
                    <td>{r.opens}</td>
                    <td>{r.feature.action === "info" ? "—" : r.runs}</td>
                    <td>{r.feature.action === "chat" ? r.compares : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        <p className="stats-foot">
          Anonymous, cookie-less counts via{" "}
          <a href="https://www.goatcounter.com" target="_blank" rel="noreferrer">
            GoatCounter
          </a>
          : page visits and which cards are opened, run and compared. No cookies and no
          personal data. Counts are per visitor session and refresh every few hours.
          {ANALYTICS && (
            <>
              {" "}Maintainers:{" "}
              <a href={DASHBOARD} target="_blank" rel="noreferrer">
                full dashboard ↗
              </a>
            </>
          )}
        </p>
      </div>
    </div>
  );
}

function Tile({ label, value }: { label: string; value: number }) {
  return (
    <div className="stats-tile">
      <span className="stats-value">{value.toLocaleString()}</span>
      <span className="stats-label">{label}</span>
    </div>
  );
}
