# DDK Feature Showcase

An interactive, developer-facing demo of the **Donkey Development Kit** — the SDK
that makes MuleSoft Agent Fabric / Omni Gateway governance **legible and
actionable inside agent code**.

- **Left pane** — a clickable catalog of DDK's milestone-11 features. Each card
  carries a prepared prompt and a side-by-side **Without DDK vs With DDK** code
  comparison. Click one, run it, and watch the typed refusal, budget, and OTel
  span appear in the chat.
- **Right pane** — a live chat backed by a real **LangGraph** agent.

Everything runs against **`donkey mock`**, DDK's local gateway simulator, which
replays the *same captured gateway fixtures* DDK's error classifier is tested
against. So the refusals, budget windows, and spans are **real** — with **no
Anypoint account, no credentials, and no OpenAI key**.

```
┌────────────────────────────┬───────────────────────────┐
│  Features · milestone 11    │  Governed agent (chat)     │
│  ▸ Governed LLM client       │                            │
│  ▸ Typed refusals (PII, …)   │  You: …                    │
│  ▸ Budget & pacing           │  Agent: …                  │
│  ▸ OTel spans + cost tags    │   └ budget bar             │
│  ▸ Local simulator           │   └ last_call identity     │
│  ▸ Testing & conformance     │   └ donkey.llm.chat span   │
│  ▸ CLI & decorators          │                            │
│  Roadmap (documented)…       │  [ Send ]                  │
└────────────────────────────┴───────────────────────────┘
```

## Try it on GitHub Pages

**<https://donkey-development-kit.github.io/donkey-development-kit-demos/>**

The Pages build is a **static replay**. There is no backend in the browser, so
every feature card replays the responses the real backend returned against
`donkey mock`, recorded into [`frontend/public/replay/`](frontend/public/replay/).
The header shows a `static replay` pill. Free-form prompts typed into the chat
get a note pointing here instead of an answer. Run it locally for the live
version.

It deploys from `main` via
[`.github/workflows/pages.yml`](../../.github/workflows/pages.yml) whenever
anything under `demos/showcase/frontend/` changes.

### Usage stats

Click the **DDK logo** (top left) for site stats:

- visits for all time, the last 30 days and the last 7 days;
- the number of free-form prompts;
- the favourite demos, ranked by how often each card was opened, run and compared.

Counts come from [GoatCounter](https://www.goatcounter.com) (site `ddk`). It is
cookie-less and collects no personal data. It counts once per visitor session,
so the numbers are visits, not raw hits. The public counter caches for up to
four hours. Tracking is only compiled in when the build sets `VITE_GOATCOUNTER`
(the Pages workflow does), so local runs send nothing. The events are
`open-<feature id>`, `run-<feature id>`, `compare-<feature id>` and
`chat-freeform`. The panel reads them through the public counter, which needs
**"Allow adding visitor counts on your website"** switched on in the
GoatCounter site settings. Maintainers get the full dashboard at
<https://ddk.goatcounter.com>.

## Run it locally (live)

From this folder, inside the repo's virtual environment (see the top-level
[Setup](../../README.md#setup)):

```bash
cd demos/showcase
python -m pip install -e "../../../donkey-development-kit/python[llm,local,otel,langgraph,cli,test]" starlette uvicorn
./run.sh          # builds the frontend, serves everything on http://127.0.0.1:8000
# or
./run.sh --dev    # backend on :8000, Vite dev server on :5173 (hot reload)
```

Then open **http://127.0.0.1:8000** (or **:5173** in dev). The backend spawns
`donkey mock` on `:8080` for you and tears it down on exit. `run.sh` also runs
`pip install -r backend/requirements.txt`; with the SDK already installed from
the sibling checkout, that is a no-op.

**Requirements:** Python 3.11+, Node 18+, and the `donkey` CLI on `PATH`
(installed with `donkey-kit[cli]`). No API keys and no gateway credentials —
the backend points DDK at the simulator with placeholder values.

**Ports taken?** `DDK_SIM_PORT=8091` moves the simulator. Start the backend by
hand to move it too:
`cd backend && PYTHONPATH=. python3 -m uvicorn app.main:app --port 8001`.

## Re-record the static replay

After an SDK or feature-catalog change, refresh what Pages replays:

```bash
cd demos/showcase/backend
env -u DONKEY_LLM_PROXY_URL -u DONKEY_LLM_PROXY_CLIENT_ID -u DONKEY_LLM_PROXY_CLIENT_SECRET \
  PYTHONPATH=. python3 -m uvicorn app.main:app --port 8000 &
cd .. && python3 scripts/record_replay.py http://127.0.0.1:8000
kill %1
```

Clearing the three variables guarantees the recording only ever sees
`donkey mock`. Run `python3 scripts/scan_secrets.py --all` from the repo root
before committing the new JSON. To preview the Pages build locally:

```bash
cd frontend && VITE_STATIC=1 VITE_BASE=/donkey-development-kit-demos/ npm run build
VITE_BASE=/donkey-development-kit-demos/ npx vite preview   # http://localhost:4173/donkey-development-kit-demos/
```

## What each feature demonstrates

| Card | DDK surface | What to watch |
| --- | --- | --- |
| **Governed LLM client** | `donkey.langgraph.chat_model()` → native `ChatOpenAI` | A normal answer streams; a budget bar and one `donkey.llm.chat` span with `donkey.policy.decision=allow` appear. |
| **Typed refusals** (PII / injection / content-safety / budget) | `PIIDetected`, `PromptInjectionBlocked`, `ContentSafetyBlocked`, `TokenBudgetExceeded` | The chat shows a typed refusal card with entities/categories/`retry_after` and a remediation — not an opaque 403/429. **Compare live** shows the raw HTTP body a non-DDK app gets. |
| **Budget & pacing** | `donkey.budget.pace(reserve=)`, `wait_for_reset()` | `fraction_used` climbs call-by-call; `BudgetReserveReached` fires *before* the limit. |
| **OTel spans + cost tags** | zero-config OTel GenAI spans in the `donkey.*` namespace | The exact span JSON: `gen_ai.usage.*`, `donkey.policy.decision`, `donkey.budget.remaining`, `donkey.cost.team/project`, correlation id. |
| **Correlation & identity** | `donkey.run(id=)`, `donkey.last_call` | Which gateway served the call and how it routed; the same correlation id joins log, span and gateway record. |
| **Local simulator** | `donkey mock` | Sentinel model `donkey-sim/<shape>` forces one exact refusal; `--scenario` fires them on a rule. |
| **Testing & conformance** | `simulate()`, `pytest --donkey-conformance` | Grades this demo's own agent against every refusal shape → a pass/fail/exempt table. |
| **CLI & decorators** | `donkey doctor`, `@donkey.governed` | `doctor` tells wrong URL from wrong credentials from unallowed model — one diagnosis. |
| **Roadmap** | MCP tools, A2A, on-behalf-of, HITL, publish | Documented, clearly marked, **not** wired — the demo is honest about what milestone 11 shipped. |

## Architecture

```
demos/showcase/
  run.sh                    boot: (build frontend) + backend (+ dev vite)
  scripts/record_replay.py  records the backend's responses for the Pages build
  backend/                  Starlette + Uvicorn
    app/
      main.py               app, CORS, lifespan (boots donkey mock), serves frontend/dist
      simulator.py          spawns `donkey mock --port 8080` with scenarios
      donkeys.py            Donkey.from_env() factory + budget/last_call/message helpers
      telemetry.py          in-memory OTel exporter for the in-UI span viewer
      agent.py              the LangGraph graph (call_model inside typed_refusals())
      features.py           the feature catalog (single source of truth)
      routes/               chat (SSE), cli, compare, conformance, features, pace (SSE), telemetry
    tests/
      agent_app.py          the agent factory the conformance suite grades
  frontend/                 Vite + React + TypeScript
    public/replay/          recorded responses the static (Pages) build replays
    src/
      App.tsx               two-pane shell + run orchestration
      api.ts                fetch + hand-rolled SSE client; replay when VITE_STATIC=1
      components/           Chat, FeatureCatalog, FeatureCard, ComparePanel, …
```

The frontend and backend share an origin: in production the backend serves the
built SPA from `frontend/dist`; in `--dev`, Vite proxies `/api` to `:8000`.

## Grafana / Tempo (optional)

The primary observability story is the **live in-UI span viewer**. To also see
the same spans land in Grafana Explore → Tempo, bring up the optional stack and
point DDK's zero-config OTLP export at it:

```bash
cd grafana && docker compose up -d
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_SERVICE_NAME=ddk-demo
./run.sh
```

See [`grafana/README.md`](grafana/README.md). Without these env vars the demo
stays entirely on the in-memory exporter — no Docker required.

## Notes

- Only the two conformance-tested surfaces (the LangGraph adapter and the raw
  client) are wired; everything else is presented as documented **Roadmap**.
- This demo consumes the installed `donkey-kit` package; it never modifies the
  SDK repo.
- Docs: <https://donkey-development-kit.github.io/donkey-development-kit> ·
  Source: <https://github.com/Donkey-Development-Kit/donkey-development-kit>
