// The left pane: the governed-agent chat timeline + the composer. Purely
// presentational — App owns the message list and the run orchestration and
// passes send/cancel handlers down.
import { useEffect, useRef, useState } from "react";
import type { Feature } from "../features";
import type { Message } from "../messages";
import { GovernanceEventCard } from "./GovernanceEventCard";
import { InspectorCard } from "./InspectorCard";
import { ConformanceTable, DoctorReport, PaceResult } from "./results";
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
            Prepared prompt from <b>{activeFeature.title}</b>
          </span>
          <button className="clear" onClick={onClearFeature}>
            clear
          </button>
        </div>
      )}
      <div className="composer-row">
        <textarea
          ref={taRef}
          value={text}
          placeholder="Ask the governed agent… or click a feature on the right."
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
            Send
          </button>
        )}
      </div>
      <div className="meta">
        <span>model: {model}</span>
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
    <div className="pane left">
      <div className="pane-head">
        <span className="eyebrow">Governed agent · LangGraph</span>
        <span className="spacer" />
        <button
          className="icon-btn collapse-btn"
          title="Collapse chat"
          onClick={onCollapse}
        >
          «
        </button>
      </div>
      <div className="chat-scroll scroll-fade" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <img src={logoSrc} alt="DDK" />
            <h2>Governance you can see</h2>
            <p>
              Every message runs through a real LangGraph agent pointed at DDK's
              local gateway simulator. Ask anything, or pick a feature on the
              right to fire a prepared prompt and watch the typed refusals,
              budget and OTel spans appear here.
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
