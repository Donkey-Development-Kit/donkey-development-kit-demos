// Typed client for the demo backend. The streaming endpoints (/api/chat,
// /api/pace) are POSTs that emit `text/event-stream`, so we can't use the
// browser EventSource (it's GET-only) — we read the fetch body and parse the
// `event:`/`data:` frames by hand, matching the backend's `_sse()` helper.

import type {
  Budget,
  CompareResult,
  ConformanceResult,
  Feature,
  SimulatorInfo,
} from "./features";

export interface SSEEvent {
  event: string;
  data: unknown;
}

// The GitHub Pages build (VITE_STATIC=1) has no backend: it replays what the
// real backend returned against `donkey mock`, recorded by
// scripts/record_replay.py into public/replay/.
export const STATIC = import.meta.env.VITE_STATIC === "1";
const REPLAY = `${import.meta.env.BASE_URL}replay/`;

const STATIC_NOTE =
  "This is the static GitHub Pages build, which replays recorded responses for " +
  "the feature cards only. Free-form prompts need the live backend: clone the " +
  "repo and run demos/showcase/run.sh.";

async function replayJson<T>(name: string): Promise<T> {
  const res = await fetch(REPLAY + name);
  return res.json();
}

async function replaySSE(
  events: SSEEvent[],
  onEvent: (ev: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  for (const ev of events) {
    if (signal?.aborted) return;
    await new Promise((r) => setTimeout(r, ev.event === "token" ? 12 : 150));
    onEvent(ev);
  }
}

const replayKey = (body: { prompt: string; model?: string }) =>
  `${body.model}::${body.prompt}`;

async function streamSSE(
  url: string,
  body: unknown,
  onEvent: (ev: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`${url} responded ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Frames are separated by a blank line.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let event = "message";
      const dataLines: string[] = [];
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (dataLines.length === 0) continue;
      let data: unknown = dataLines.join("\n");
      try {
        data = JSON.parse(data as string);
      } catch {
        /* leave as string */
      }
      onEvent({ event, data });
    }
  }
}

export const api = {
  async features(): Promise<Feature[]> {
    if (STATIC) return replayJson("features.json");
    const res = await fetch("/api/features");
    const json = await res.json();
    return json.features ?? json;
  },

  async simulator(): Promise<SimulatorInfo> {
    if (STATIC) return replayJson("simulator.json");
    const res = await fetch("/api/simulator");
    return res.json();
  },

  async budget(): Promise<Budget> {
    if (STATIC) return replayJson("budget.json");
    const res = await fetch("/api/budget");
    return res.json();
  },

  async chat(
    body: { prompt: string; model?: string; run_id?: string },
    onEvent: (ev: SSEEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    if (STATIC) {
      const recorded = await replayJson<Record<string, SSEEvent[]>>("chat.json");
      const events = recorded[replayKey(body)] ?? [
        { event: "token", data: { text: STATIC_NOTE } },
        { event: "done", data: { ok: true } },
      ];
      return replaySSE(events, onEvent, signal);
    }
    return streamSSE("/api/chat", body, onEvent, signal);
  },

  async pace(
    body: { calls?: number; reserve?: number },
    onEvent: (ev: SSEEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    if (STATIC) return replaySSE(await replayJson("pace.json"), onEvent, signal);
    return streamSSE("/api/pace", body, onEvent, signal);
  },

  async compare(body: {
    prompt: string;
    model?: string;
  }): Promise<CompareResult> {
    if (STATIC) {
      const recorded = await replayJson<Record<string, CompareResult>>("compare.json");
      return recorded[replayKey(body)];
    }
    const res = await fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return res.json();
  },

  async conformance(): Promise<ConformanceResult> {
    if (STATIC) return replayJson("conformance.json");
    const res = await fetch("/api/conformance", { method: "POST" });
    return res.json();
  },

  async doctor(): Promise<{ output: string; ok: boolean }> {
    if (STATIC) return replayJson("doctor.json");
    const res = await fetch("/api/doctor", { method: "POST" });
    return res.json();
  },
};
