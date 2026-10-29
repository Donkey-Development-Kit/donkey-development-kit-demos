# DDK Feature Showcase

An interactive, developer-facing demo of the **Donkey Development Kit** — the SDK
that makes MuleSoft Agent Fabric / Omni Gateway governance **legible and
actionable inside agent code**.

- **Left pane** — a clickable catalog with side-by-side **Without DDK vs With
  DDK** code comparisons. **Live** cards are wired into this showcase; run them
  to watch typed refusals, budgets and OTel spans. Descriptive-only cards state
  which SDK capabilities shipped and which limits still apply.
- **Right pane** — a live chat backed by a real **LangGraph** agent.

Everything runs against **`donkey mock`**, DDK's local gateway simulator, which
replays the *same captured gateway fixtures* DDK's error classifier is tested
against. So the refusals, budget windows, and spans are **real** — with **no
Anypoint account, no credentials, and no OpenAI key**.

```
┌────────────────────────────┬───────────────────────────┐
│  Features · showcase        │  Governed agent (chat)     │
│  ▸ Governed LLM client       │                            │
│  ▸ Typed refusals (PII, …)   │  You: …                    │
│  ▸ Budget & pacing           │  Agent: …                  │
│  ▸ OTel spans + cost tags    │   └ budget bar             │
│  ▸ Local simulator           │   └ last_call identity     │
│  ▸ Testing & conformance     │   └ donkey.llm.chat span   │
│  ▸ CLI & decorators          │                            │
│  SDK shipped (documented)…   │  [ Send ]                  │
└────────────────────────────┴───────────────────────────┘
```

## Try it on GitHub Pages

**<https://donkey-development-kit.github.io/donkey-development-kit-demos/>**

The Pages build is a **static replay**. There is no backend in the browser, so
interactive feature cards replay the responses the real backend returned against
`donkey mock`, recorded into [`frontend/public/replay/`](frontend/public/replay/).
The header shows a `static replay` pill. Free-form prompts typed into the chat
get a note pointing here instead of an answer. Run it locally for the live
version. Descriptive-only cards have no run/compare controls and no fabricated
recordings. Cards carry one of three badges: **Live** means the capability is wired into
this showcase; **SDK shipped** means it is on SDK `develop` but the card is
descriptive-only here (not wired); **Roadmap** means it is not on SDK `develop`.
None of the three asserts live gateway verification; each card's *Watch* text
states what was and was not verified.

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

For catalog-only changes, manually synchronize `backend/app/features.py` with
`frontend/public/replay/features.json`; do not regenerate response recordings.
The live API wraps the catalog in `{"features": [...]}`; the replay file is the
same list without that wrapper. Preserve IDs, prompts and models for existing
interactive cards because chat/compare recordings key on `model::prompt`.

Only when interactive behavior changes, refresh what Pages replays:

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
| **Refusal reactions / custom classifier** | `donkey.on(...)`, `classify.register(...)` | SDK shipped, descriptive-only. Reactions are bounded and cannot manufacture success; custom classification is process-wide. |
| **Terminal kill handling** | `AgentKilled`, budget pacing/reset latch | SDK shipped, descriptive-only. No recovery handler; consumes a platform decision, not a kill-switch administration API or HTTP firewall. |
| **Local tool approvals** | `@donkey.tool(approval="required")`, `donkey.approvals`, native LangGraph interrupts | SDK shipped, descriptive-only. Base approvals are process-global memory; native pauses use the framework checkpointer with no DDK expiry. Advisory, not a platform queue/UI/step-up service. |
| **Local A2A serving** | `@donkey.agent`, `donkey.serve(handler)`, `build_app()` | SDK shipped, descriptive-only. Official A2A app; demo evidence is in-process ASGI/lifespan, not a tested TCP launcher or gateway exposure. |
| **Scan & MCP publication** | `donkey scan`, `publish --dry-run`, `--if-changed` | SDK shipped, descriptive-only. Offline plans are not publication outcomes; agents are skipped and connected-app publication authentication is unconfirmed live. |
| **Descriptor fidelity / tool filtering** | `derive_descriptor()`, `ToolSet.filter()`, `descriptor_tokens()` | SDK shipped, descriptive-only. Auto modes execute imports/factories; local protocol/schema fidelity does not unblock remote discovery/bind. Token cost is an estimate, not a bill. |
| **Server-mode conformance** | `--donkey-mode=server` | SDK shipped, descriptive-only. Real loopback HTTP; uncaptured custom shapes require in-process mode. The existing showcase button is unchanged. |
| **Telemetry flush** | `flush_telemetry(timeout_s=...)` | SDK shipped, descriptive-only. Flushes DDK-owned spans only; host providers need host flush/shutdown. `True` can be a no-op; `False` is timeout/failure. |
| **Upstream budget / dynamic key** | `budget.upstream`, `llm_proxy_key_header` | SDK shipped, descriptive-only. Provider quota is observe-only; dynamic header names belong to customer routes, not a universal gateway contract. |
| **Verification gates / roadmap** | remote MCP discovery/bind, A2A expose/dev, agent publication, on-behalf-of identity | **Not** wired. Remote MCP discovery/bind remain verification-blocked; expose/dev are outside implemented scope and agents are skipped on publication. |

### Narrative Companions

These are separate local scripts, not showcase recordings. See each linked README
for dependencies, asserted evidence and synthetic-input boundaries.

| Demo | Real files and scope |
| --- | --- |
| [17 - Refusal reactions](../claude-made/17_refusal_reactions/README.md) | `17_refusal_reactions/demo.py`: bounded wait/resend/fallback/escalation, synthetic custom classification and registry cleanup. |
| [18 - Terminal kill handling](../claude-made/18_kill_switch/README.md) | `18_kill_switch/demo.py`: simulated `AgentKilled`, waiter wakeup and stopped paced effects. |
| [19 - Tool approvals](../claude-made/19_tool_approvals/README.md) | `19_tool_approvals/demo.py`: base approval lifecycle, native checkpoint resume and downstream governance after approval. In-memory checkpoints do not prove restart durability. |
| [20 - Descriptor fidelity](../claude-made/20_descriptor_fidelity/README.md) | `20_descriptor_fidelity/demo.py`, `example.py`, `tools.py`, `memory_server.py`, `descriptor.json`: real framework schemas, drift and in-memory official MCP `tools/list`. No remote discovery/bind. |
| [21 - Local A2A serving](../claude-made/21_a2a_serving/README.md) | `21_a2a_serving/demo.py`: official SDK app through ASGITransport/lifespan, card/tasks/refusals/trace relationships and worker cleanup. No socket launcher, streaming or gateway exposure claim. |

Related evidence: [03 - budgets](../claude-made/03_budget_and_pacing/README.md),
[05 - conformance](../claude-made/05_conformance/README.md),
[06 - telemetry](../claude-made/06_telemetry/README.md),
[16 - static CI registration](../claude-made/16_publish_from_ci/README.md), and
[`18 - dynamic-provider-key.py`](../human-made/openai/18%20-%20dynamic-provider-key.py).

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

- The wired showcase actions remain chat, pacing, conformance and doctor. New
  SDK capabilities are descriptive-only (`action: "info"`, `badge: "shipped"`),
  with explicit shipped status and limits. No new endpoint or recording is added.
- This demo consumes the installed `donkey-kit` package; it never modifies the
  SDK repo.
- Docs: <https://donkey-development-kit.github.io/donkey-development-kit> ·
  Source: <https://github.com/Donkey-Development-Kit/donkey-development-kit>
