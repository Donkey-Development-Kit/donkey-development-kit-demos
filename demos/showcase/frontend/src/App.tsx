// Two-pane shell: clickable feature catalog on the left, governed-agent chat on
// the right. App owns the message timeline, the live budget, and the run
// orchestration; the panes are presentational.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { track } from "./analytics";
import { api, STATIC, type SSEEvent } from "./api";
import type {
  Budget,
  ConformanceResult,
  Feature,
  Governance,
  LastCall,
  SimulatorInfo,
  Span,
} from "./features";
import { newId, type Inspector, type Message } from "./messages";
import type { PaceCallRow, ReserveReached } from "./components/results";
import { Chat } from "./components/Chat";
import { FeatureCatalog } from "./components/FeatureCatalog";
import { CollapsedRail } from "./components/bits";
import { StatsPanel } from "./components/StatsPanel";

type Theme = "light" | "dark";
type Collapsed = "left" | "right" | null;

const EMPTY_INSPECTOR: Inspector = { budget: null, lastCall: null, span: null };

export default function App() {
  const [features, setFeatures] = useState<Feature[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [sim, setSim] = useState<SimulatorInfo | null>(null);
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem("ddk-theme") as Theme) || "light",
  );
  const [collapsed, setCollapsed] = useState<Collapsed>(null);
  const [statsOpen, setStatsOpen] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("ddk-theme", theme);
  }, [theme]);

  const activeFeature = useMemo(
    () => features.find((f) => f.id === selectedId) ?? null,
    [features, selectedId],
  );

  useEffect(() => {
    api.features().then(setFeatures).catch(() => setFeatures([]));
    api.simulator().then(setSim).catch(() => setSim(null));
    api.budget().then(setBudget).catch(() => {});
  }, []);

  // ---- message helpers -------------------------------------------------

  const patch = useCallback(
    (id: string, fn: (m: Message) => Message) => {
      setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)));
    },
    [],
  );

  const patchInspector = useCallback(
    (id: string, delta: Partial<Inspector>) => {
      patch(id, (m) => {
        if (m.kind !== "assistant" && m.kind !== "governance") return m;
        return { ...m, inspector: { ...(m.inspector ?? EMPTY_INSPECTOR), ...delta } };
      });
    },
    [patch],
  );

  // ---- chat ------------------------------------------------------------

  const runChat = useCallback(
    async (prompt: string, model: string) => {
      const userId = newId();
      const asstId = newId();
      setMessages((prev) => [
        ...prev,
        { kind: "user", id: userId, text: prompt },
        { kind: "assistant", id: asstId, text: "", streaming: true, inspector: null },
      ]);
      setBusy(true);
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      const onEvent = (ev: SSEEvent) => {
        const d = ev.data as Record<string, unknown>;
        switch (ev.event) {
          case "token":
            patch(asstId, (m) =>
              m.kind === "assistant"
                ? { ...m, text: m.text + String(d.text ?? "") }
                : m,
            );
            break;
          case "governance":
            patch(asstId, (m) => ({
              kind: "governance",
              id: asstId,
              gov: ev.data as Governance,
              inspector:
                m.kind === "assistant" || m.kind === "governance"
                  ? m.inspector
                  : null,
            }));
            break;
          case "budget":
            setBudget(ev.data as Budget);
            patchInspector(asstId, { budget: ev.data as Budget });
            break;
          case "last_call":
            patchInspector(asstId, { lastCall: ev.data as LastCall });
            break;
          case "span":
            patchInspector(asstId, { span: ev.data as Span });
            break;
        }
      };

      try {
        await api.chat({ prompt, model }, onEvent, ctrl.signal);
      } catch (err) {
        if (!ctrl.signal.aborted) {
          patch(asstId, (m) =>
            m.kind === "assistant"
              ? { ...m, text: m.text || `⚠️ ${String(err)}` }
              : m,
          );
        }
      } finally {
        patch(asstId, (m) =>
          m.kind === "assistant" ? { ...m, streaming: false } : m,
        );
        setBusy(false);
        abortRef.current = null;
      }
    },
    [patch, patchInspector],
  );

  // ---- pacing batch ----------------------------------------------------

  const runPace = useCallback(async () => {
    const id = newId();
    setMessages((prev) => [
      ...prev,
      {
        kind: "pace",
        id,
        reserve: 0.05,
        calls: [],
        reserveReached: null,
        budget: null,
        running: true,
      },
    ]);
    setBusy(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    const onEvent = (ev: SSEEvent) => {
      const d = ev.data as Record<string, unknown>;
      switch (ev.event) {
        case "budget":
          setBudget(ev.data as Budget);
          patch(id, (m) =>
            m.kind === "pace" ? { ...m, budget: ev.data as Budget } : m,
          );
          break;
        case "call":
          patch(id, (m) =>
            m.kind === "pace"
              ? { ...m, calls: [...m.calls, ev.data as PaceCallRow] }
              : m,
          );
          break;
        case "reserve_reached":
          patch(id, (m) =>
            m.kind === "pace"
              ? { ...m, reserveReached: ev.data as ReserveReached }
              : m,
          );
          break;
      }
      void d;
    };

    try {
      await api.pace({ calls: 6, reserve: 0.05 }, onEvent, ctrl.signal);
    } finally {
      patch(id, (m) => (m.kind === "pace" ? { ...m, running: false } : m));
      setBusy(false);
      abortRef.current = null;
    }
  }, [patch]);

  // ---- conformance / doctor -------------------------------------------

  const runConformance = useCallback(async () => {
    const id = newId();
    setMessages((prev) => [
      ...prev,
      { kind: "conformance", id, result: null, running: true },
    ]);
    setBusy(true);
    try {
      const result: ConformanceResult = await api.conformance();
      patch(id, (m) =>
        m.kind === "conformance" ? { ...m, result, running: false } : m,
      );
    } finally {
      patch(id, (m) => (m.kind === "conformance" ? { ...m, running: false } : m));
      setBusy(false);
    }
  }, [patch]);

  const runDoctor = useCallback(async () => {
    const id = newId();
    setMessages((prev) => [
      ...prev,
      { kind: "doctor", id, output: "", running: true },
    ]);
    setBusy(true);
    try {
      const res = await api.doctor();
      patch(id, (m) =>
        m.kind === "doctor" ? { ...m, output: res.output, running: false } : m,
      );
    } finally {
      patch(id, (m) => (m.kind === "doctor" ? { ...m, running: false } : m));
      setBusy(false);
    }
  }, [patch]);

  // ---- dispatch --------------------------------------------------------

  const onRun = useCallback(
    (f: Feature) => {
      setSelectedId(f.id);
      if (busy) return;
      track(`run-${f.id}`, f.title);
      switch (f.action) {
        case "chat":
          runChat(f.prompt, f.model);
          break;
        case "pace":
          runPace();
          break;
        case "conformance":
          runConformance();
          break;
        case "doctor":
          runDoctor();
          break;
        case "info":
          setMessages((prev) => [
            ...prev,
            {
              kind: "note",
              id: newId(),
              icon: f.icon,
              title: f.title,
              body: f.watch,
            },
          ]);
          break;
      }
    },
    [busy, runChat, runPace, runConformance, runDoctor],
  );

  const onSend = useCallback(
    (text: string) => {
      const model =
        activeFeature && activeFeature.action === "chat"
          ? activeFeature.model
          : "gpt-5.1";
      track("chat-freeform");
      runChat(text, model);
    },
    [activeFeature, runChat],
  );

  const onCancel = useCallback(() => {
    abortRef.current?.abort();
    setBusy(false);
  }, []);

  const logoSrc = `${import.meta.env.BASE_URL}img/ddk-logo-stacked-${
    theme === "dark" ? "white" : "black"
  }.png`;

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <button
            className="logo-btn"
            aria-label="Show showcase stats"
            title="Showcase stats"
            onClick={() => setStatsOpen(true)}
          >
            <img src={logoSrc} alt="" />
          </button>
          <div className="titles">
            <span className="title">Donkey Development Kit</span>
            <span className="subtitle">
              Agent Fabric governance, made legible — feature showcase
            </span>
          </div>
        </div>
        <div className="header-spacer" />
        {STATIC && (
          <span
            className="sim-pill"
            title="Recorded from the real backend against donkey mock. Run demos/showcase/run.sh for the live version."
          >
            static replay
          </span>
        )}
        {budget?.limit != null && (
          <span className="sim-pill">
            budget {budget.remaining}/{budget.limit}
          </span>
        )}
        <span className={`sim-pill${sim?.healthy ? " up" : ""}`}>
          <span className="dot" />
          {sim?.healthy ? "simulator up" : "simulator…"} · {sim?.base_url ?? "127.0.0.1:8080"}
        </span>
        <button
          className="icon-btn"
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
        >
          {theme === "dark" ? "☀" : "☾"}
        </button>
        <a
          className="header-link"
          href="https://donkey-development-kit.github.io/donkey-development-kit"
          target="_blank"
          rel="noreferrer"
        >
          Docs ↗
        </a>
        <a
          className="header-link"
          href="https://github.com/Donkey-Development-Kit/donkey-development-kit"
          target="_blank"
          rel="noreferrer"
        >
          GitHub ↗
        </a>
      </header>

      <div
        className="panes"
        style={{
          gridTemplateColumns:
            collapsed === "left"
              ? "48px 1fr"
              : collapsed === "right"
                ? "1fr 48px"
                : "1fr 1.15fr",
        }}
      >
        {collapsed === "left" ? (
          <CollapsedRail
            side="left"
            label="Features"
            onExpand={() => setCollapsed(null)}
          />
        ) : (
          <FeatureCatalog
            features={features}
            selectedId={selectedId}
            busy={busy}
            onSelect={(id) => {
              if (selectedId !== id) track(`open-${id}`);
              setSelectedId((cur) => (cur === id ? null : id));
            }}
            onRun={onRun}
            onCollapse={() => setCollapsed("left")}
          />
        )}
        {collapsed === "right" ? (
          <CollapsedRail
            side="right"
            label="Governed agent"
            onExpand={() => setCollapsed(null)}
          />
        ) : (
          <Chat
            messages={messages}
            activeFeature={activeFeature}
            onClearFeature={() => setSelectedId(null)}
            busy={busy}
            onSend={onSend}
            onCancel={onCancel}
            onCollapse={() => setCollapsed("right")}
            logoSrc={logoSrc}
          />
        )}
      </div>
      {statsOpen && (
        <StatsPanel features={features} onClose={() => setStatsOpen(false)} />
      )}
    </div>
  );
}
