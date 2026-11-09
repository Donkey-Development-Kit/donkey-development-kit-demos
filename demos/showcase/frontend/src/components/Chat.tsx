// The right pane: the governed-agent chat timeline + the composer. Purely
// presentational — App owns the message list and the run orchestration and
// passes send/cancel handlers down.
import { useEffect, useRef, useState } from "react";
import type { Feature } from "../features";
import type { Message } from "../messages";
import { GovernanceEventCard } from "./GovernanceEventCard";
import { InspectorCard } from "./InspectorCard";
import { ConformanceTable, DoctorReport, PaceResult, StoryReport } from "./results";
import { Spinner } from "./bits";

function MessageView({ msg }: { msg: Message }) {
  switch (msg.kind) {
    case "user":
      return (
        <div className="msg user">
          <span className="role">You</span>
          <div className="bubble">{msg.text}</div>
        </div>
      );
    case "assistant":
      return (
        <div className="msg assistant">
          <span className="role">Agent</span>
          <div className={`bubble${msg.streaming ? " cursor-blink" : ""}`}>
            {msg.text}
          </div>
          {msg.inspector && (
            <div style={{ width: "100%", marginTop: 4 }}>
              <InspectorCard {...msg.inspector} />
            </div>
          )}
        </div>
      );
    case "governance":
      return (
        <div className="msg assistant" style={{ maxWidth: "100%" }}>
          <span className="role">Governance</span>
          <GovernanceEventCard gov={msg.gov} />
          {msg.inspector && (
            <div style={{ width: "100%", marginTop: 4 }}>
              <InspectorCard {...msg.inspector} />
            </div>
          )}
        </div>
      );
    case "reaction": {
      const t = msg.trail;
      return (
        <div className="msg assistant" style={{ maxWidth: "100%" }}>
          <span className="role">Refusal reaction</span>
          <div className="gov-card retryable">
            <div className="gov-head">
              <span className="gov-type">donkey.on({t.on})</span>
              <span className="pill">.{t.reaction}</span>
            </div>
            <div className="gov-msg">
              1. The gateway refused the first request: <b>{t.refusal}</b>
              {t.policy ? ` (policy=${t.policy})` : ""}.
            </div>
            <div className="gov-msg">
              2. The handler removed{" "}
              {t.removed.length ? <code>{t.removed.join(" ")}</code> : "nothing"}{" "}
              and called <code>ctx.resend(json=...)</code>
              {t.resent_prompt ? (
                <>
                  : <code>{t.resent_prompt}</code>
                </>
              ) : null}
              .
            </div>
            <div className="gov-msg">
              3. That is a new governed request, judged by the gateway from
              scratch: <b>{t.outcome}</b>. {t.resends} re-send of max_times=
              {t.max_times}; the refused request itself was never let through.
            </div>
            {t.decisions && t.decisions.length > 0 && (
              <div className="gov-ids">
                <span>
                  <b>span decisions</b> {t.decisions.map((d) => d ?? "?").join(" → ")}
                </span>
              </div>
            )}
          </div>
        </div>
      );
    }
    case "note":
      return (
        <div className="msg assistant" style={{ maxWidth: "100%" }}>
          <span className="role">
            {msg.icon} {msg.title}
          </span>
          <div className="bubble">{msg.body}</div>
        </div>
      );
    case "pace":
      return (
        <div className="msg assistant" style={{ maxWidth: "100%" }}>
          <span className="role">
            Budget & pacing {msg.running && <Spinner />}
          </span>
          <PaceResult
            reserve={msg.reserve}
            calls={msg.calls}
            reserveReached={msg.reserveReached}
            budget={msg.budget}
          />
        </div>
      );
    case "conformance":
      return (
        <div className="msg assistant" style={{ maxWidth: "100%" }}>
          <span className="role">
            Conformance {msg.running && <Spinner />}
          </span>
          {msg.running && !msg.result ? (
            <div className="bubble">
              Running <code>pytest --donkey-conformance</code> against the demo's
              own agent…
            </div>
          ) : (
            msg.result && <ConformanceTable result={msg.result} />
          )}
        </div>
      );
    case "doctor":
      return (
        <div className="msg assistant" style={{ maxWidth: "100%" }}>
          <span className="role">
            donkey doctor {msg.running && <Spinner />}
          </span>
          {msg.running && !msg.output ? (
            <div className="bubble">Running diagnostics against the simulator…</div>
          ) : (
            <DoctorReport output={msg.output} />
          )}
        </div>
      );
    case "story":
      return (
        <div className="msg assistant" style={{ maxWidth: "100%" }}>
          <span className="role">{msg.title} {msg.running && <Spinner />}</span>
          {msg.error ? <div className="bubble" role="alert">{msg.error}</div>
            : msg.result ? <StoryReport result={msg.result} />
              : <div className="bubble">{msg.running
                ? "Executing the offline SDK protocol story..."
                : "Protocol story canceled."}</div>}
        </div>
      );
  }
}

function Composer({
  activeFeature,
  onClearFeature,
  busy,
  onSend,
  onCancel,
}: {
  activeFeature: Feature | null;
  onClearFeature: () => void;
  busy: boolean;
  onSend: (text: string) => void;
  onCancel: () => void;
}) {
  const [text, setText] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);

  // When a feature card loads its prepared prompt, drop it into the box.
  useEffect(() => {
    if (activeFeature && activeFeature.action === "chat") {
      setText(activeFeature.prompt);
      taRef.current?.focus();
    } else {
      setText("");
    }
  }, [activeFeature]);

  function submit() {
    const t = text.trim();
    if (!t || busy) return;
    onSend(t);
    setText("");
  }

  const model =
    activeFeature && activeFeature.action === "chat"
      ? activeFeature.model
      : "gpt-5.1";

  return (
    <div className="composer">
      {activeFeature && (
        <div className="active-feature">
          <span>{activeFeature.icon}</span>
          <span>
            {activeFeature.action === "story" ? "Protocol story: " : "Selected feature: "}
            <b>{activeFeature.title}</b>
          </span>
          <button
            className="clear"
            onClick={() => {
              setText("");
              onClearFeature();
            }}
          >
            clear
          </button>
        </div>
      )}
      <div className="composer-row">
        <textarea
          ref={taRef}
          value={text}
          aria-label="Model chat prompt"
          placeholder="Model chat: ask the governed agent..."
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          rows={2}
        />
        {busy ? (
          <button className="btn btn-secondary" onClick={onCancel}>
            Stop
          </button>
        ) : (
          <button className="btn btn-primary" onClick={submit} disabled={!text.trim()}>
            Model chat
          </button>
        )}
      </div>
      <div className="meta">
        <span>Model chat: {model}</span>
        <span>·</span>
        <span>via donkey mock @ 127.0.0.1:8080</span>
        <span>·</span>
        <span>Enter to send · Shift+Enter for newline</span>
      </div>
    </div>
  );
}

export function Chat({
  messages,
  activeFeature,
  onClearFeature,
  busy,
  onSend,
  onCancel,
  onCollapse,
  logoSrc,
}: {
  messages: Message[];
  activeFeature: Feature | null;
  onClearFeature: () => void;
  busy: boolean;
  onSend: (text: string) => void;
  onCancel: () => void;
  onCollapse: () => void;
  logoSrc: string;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  return (
    <div className="pane right">
      <div className="pane-head">
        <button
          className="icon-btn collapse-btn"
          title="Collapse chat"
          onClick={onCollapse}
        >
          »
        </button>
        <span className="eyebrow">Governed calls · Model / MCP / A2A</span>
      </div>
      <div className="chat-scroll scroll-fade" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <img src={logoSrc} alt="DDK" />
            <h2>Governance you can see</h2>
            <p>
              Pick a feature on the left to explore governed model calls, MCP
              tools or A2A delegation. Model chat uses LangGraph and donkey mock;
              protocol stories use the SDK's offline MCP and A2A simulation.
              The static build replays recorded results, not live requests.
            </p>
          </div>
        ) : (
          messages.map((m) => <MessageView key={m.id} msg={m} />)
        )}
      </div>
      <Composer
        activeFeature={activeFeature}
        onClearFeature={onClearFeature}
        busy={busy}
        onSend={onSend}
        onCancel={onCancel}
      />
    </div>
  );
}
