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
| **Typed refusals — Model Armor / CrowdStrike AIDR** | `ContentSafetyBlocked` (`.provider == "google-model-armor"` / `"crowdstrike-aidr"`, `.categories`) | SDK shipped, descriptive-only; no simulator sentinel serves these shapes. Model Armor's 403 is VERIFIED (LIVE); AIDR's is read from the policy source, not live-captured. Either fail-closed 503 stays a retryable `UpstreamModelError`. |
| **Typed refusals — regex prompt guard / request rate limit** | `PromptInjectionBlocked` (`policy="regex-prompt-guard"`), `RequestRateLimitExceeded.retry_after`, `donkey.budget.requests` | SDK shipped, descriptive-only; both shapes VERIFIED (LIVE). A deny-list match is typed and names its patterns; a request-count 429 is never confused with a token-budget 429. Simulator wiring (`donkey-sim/regex-prompt-guard`, `donkey-sim/request-rate-limit`) is planned. |
| **Step-up approval pending / denied (CIBA)** | `GatewayApprovalPending.retry_after`, `donkey_kit.core.step_up.wait_for_approval()`, `GatewayApprovalDenied` (`policy="oauth2-obo-ciba"`) | SDK shipped, descriptive-only. The OBO policy's 401 `authorization_pending` is a wait, not an auth failure; the 403 denial is terminal and never retried. Captured live on an A2A route, not an LLM proxy route. Live wiring via `donkey-sim/ciba-pending` / `ciba-denied` is planned. |
| **Budget & pacing** | `donkey.budget.pace(reserve=)`, `wait_for_reset()` | `fraction_used` climbs call by call, and `BudgetReserveReached` fires *before* the limit. Under fan-out the shared budget never moves backwards. `pace()` admits calls, it does not reserve for them, so size `reserve` to the fan-out width. |
| **OTel spans + cost tags** | zero-config OTel GenAI spans in the `donkey.*` namespace | The exact span JSON: `gen_ai.usage.*`, `donkey.policy.decision`, `donkey.budget.remaining`, `donkey.cost.team/project`, correlation id. |
| **Content-safety provider & categories on spans** | `donkey.policy.provider`, `donkey.policy.categories` (`DONKEY_POLICY_PROVIDER` / `DONKEY_POLICY_CATEGORIES`) | SDK shipped, descriptive-only. Refusal spans can be grouped by moderation vendor and category without parsing headers; reproducible offline with `simulate(ContentSafetyBlocked)`. |
| **Correlation & identity** | `donkey.run(id=)`, `donkey.last_call` | Which gateway served the call and how it routed; the same correlation id joins log, span and gateway record. |
| **Inbound correlation across hops** | `donkey.run_from_headers(headers)`, `donkey.correlation_headers()` | SDK shipped, descriptive-only. Adopts a well-formed caller id or mints a new one, and spans record `adopted`/`minted`. You pass the id explicitly to your own MCP/A2A client. Whether the A2A proxy forwards it is UNVERIFIED. |
| **Per-request business group** | `donkey.attribution(business_group=)`, `run(business_group=)`, `@donkey.governed(business_group=)` | SDK shipped, descriptive-only. One `Donkey` serves many tenants and concurrent scopes stay isolated. The header name is an unverified placeholder, gateway ingestion is unverified, and snapshot adapters keep the configured group. |
| **Local simulator** | `donkey mock` | Sentinel model `donkey-sim/<shape>` forces one exact refusal; `--scenario` fires them on a rule. |
| **Testing & conformance** | `simulate()`, `pytest --donkey-conformance` | Grades this demo's own agent against every refusal shape → a pass/fail/exempt table. |
| **CLI & decorators** | `donkey doctor`, `@donkey.governed` | `doctor` tells wrong URL from wrong credentials from unallowed model — one diagnosis. |
| **Refusal reactions / custom classifier** | `donkey.on(...)`, `classify.register(...)` | SDK shipped, descriptive-only. Reactions are bounded and cannot manufacture success; custom classification is process-wide. |
| **Terminal kill handling** | `AgentKilled`, budget pacing/reset latch | SDK shipped, descriptive-only. No recovery handler; consumes a platform decision, not a kill-switch administration API or HTTP firewall. |
| **Local tool approvals** | `@donkey.tool(approval="required")`, `donkey.approvals`, native LangGraph interrupts | SDK shipped, descriptive-only. Base approvals are process-global memory; native pauses use the framework checkpointer with no DDK expiry. Advisory, not a platform queue/UI/step-up service. |
| **Governed tool access (MCP)** | `donkey.tools.discover(governed=True)`, `ToolSet.<framework>()` bindings | SDK shipped, descriptive-only. Discovery plus every binding is VERIFIED (LIVE) through the governed gateway, for framework-built and Mule-hosted servers. `domain=` and `locked=True` are not supported yet. An audience-scoped token is good for one instance, so narrow with `filter(servers=[...])`. |
| **On-behalf-of user token** | `donkey.as_user(id_token=...)` | SDK shipped, descriptive-only. The user's token is forwarded unchanged on model calls and MCP bindings (VERIFIED (LIVE) header). The gateway's OBO policy does the exchange, not the SDK, so the token must already be issued for the gateway's audience. |
| **Registry search, resolve & explain** | `donkey.registry.search()`, `resolve_mcp()`, `explain(criteria=STRICT)` | SDK shipped, descriptive-only. Verified live against a sandbox. `domain`/`environment`/`governed` filters and the `a2a-agent` type are still blocked. A refused read is UNKNOWN, not a pass. |
| **Ungoverned refusal & tool approvals** | `UngovernedMcpServer`, `ToolSet.require_approval()`, `@donkey.tool(server=)` | SDK shipped, descriptive-only. A server the gateway does not front is refused before any credential is sent, with no opt-out. Approval gates are verified locally on the LangGraph, LlamaIndex and Anthropic bindings only, and are client-side and advisory. `server=` is attribution metadata for `donkey scan`. |
| **Tool not in access profile** | `ToolNotInProfile`, `tool_access_denial()` | SDK shipped, descriptive-only. The gateway's HTTP 200 + JSON-RPC `-32008` denial (live-verified) becomes a typed, never-retried refusal on the per-tool bindings. ADK and Strands return text that the SDK does not classify, and `profile` is always `None`. |
| **A2A serving & donkey dev** | `@donkey.agent`, `donkey.serve()`, `build_app()`, `donkey dev` | SDK shipped, descriptive-only. `serve`/`dev` are local round-trips, and the `dev` ingress is simulated. No streaming. Gateway forwarding of the inbound correlation id is UNVERIFIED. Gateway exposure is the Expose & preflight row. |
| **Scan & publication** | `donkey scan`, `donkey publish --dry-run`, `--if-changed` | SDK shipped, descriptive-only. MCP and agent publish are VERIFIED (LIVE). The card shows only offline dry-run plans and publishes nothing. Changed content needs a new version. CI and the Exchange page are the Publish from CI row. |
| **Expose & preflight** | `donkey expose`, `donkey preflight`, `[donkey.expose]` | SDK shipped, descriptive-only. Verified live (2026-10-28) with a seven-scope connected app. Only adds: never deletes, never edits policies, never creates the gateway or environment. |
| **Publish from CI** | `donkey publish --json`, the GitHub Action, GitLab CI / Bitbucket recipes | SDK shipped, descriptive-only. MCP and agent assets, each with a generated Exchange page (Overview, tool governance, "Changes since"). The changelog was tested offline only, and the GitLab/Bitbucket YAML has not run on those platforms. |
| **Verify published vs live** | `donkey verify`, `Publication.verify(raise_on_drift=)` | SDK shipped, descriptive-only. Read-only drift check of MCP tools and A2A cards through the governed gateway. Parameter types and deployment-specific card fields are not compared. |
| **Missing connected-app scope, named** | `AuthError.remediation` from `resolve_mcp()` / `explain()` / `donkey publish` / `donkey expose` | SDK shipped, descriptive-only. A control-plane 401/403 names the scope to grant (scope table VERIFIED (LIVE)). The showcase makes no control-plane call. |
| **Descriptor fidelity / tool filtering** | `derive_descriptor()`, `ToolSet.filter()`, `describe()`, `descriptor_tokens()` | SDK shipped, descriptive-only. Descriptor reads are local captures. The auto modes run imports and factories, and `auto:static` is unsupported. `filter(servers=)` was used in the live gateway binds. The token count is an estimate, not a bill. |
| **MCP bindings & discovery warm-up** | `ToolSet.langgraph()` / `llamaindex()` / `anthropic()` / `adk()` / `strands()` / `openai()` / `agent_framework()` / `crewai()`, `donkey.tools.warm()`, `donkey.tools.discover` span | SDK shipped, descriptive-only. Each binding returns that framework's own tool objects. Live-verified through Omni Gateway for framework-built and Mule-hosted servers. Collision renames and approval gates were not re-run through the gateway, and whole-server bindings refuse renames. The span records `donkey.discover.cache=hit/miss`, `.servers` and `.left_out`. |
| **Descriptor cost warning** | `DONKEY_TOOL_WARN_COUNT` / `DONKEY_TOOL_WARN_TOKENS`, `descriptor_tokens()` | SDK shipped, descriptive-only. Each bind logs its tool count and estimated descriptor tokens, and warns above 20 tools or 10,000 tokens. The figure is an estimate, not a bill. |
| **Server-mode conformance** | `--donkey-mode=server` | SDK shipped, descriptive-only. Real loopback HTTP; uncaptured custom shapes require in-process mode. The existing showcase button is unchanged. |
| **Telemetry flush** | `flush_telemetry(timeout_s=...)` | SDK shipped, descriptive-only. Flushes DDK-owned spans only; host providers need host flush/shutdown. `True` can be a no-op; `False` is timeout/failure. |
| **Upstream budget / dynamic key** | `budget.upstream`, `llm_proxy_key_header` | SDK shipped, descriptive-only. Provider quota is observe-only; dynamic header names belong to customer routes, not a universal gateway contract. |

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
- No card carries the Roadmap badge today: MCP tool access and on-behalf-of
  identity are on SDK `develop`. The badge and group stay for future cards.
- The CIBA, regex-prompt-guard and request-rate-limit cards already carry a
  `donkey-sim/<shape>` model and a prepared prompt so they can be wired later
  by changing only `badge`/`action`. `info` cards ignore both, and the replay
  recorder only records `chat` cards, so no recording keys change.
- This demo consumes the installed `donkey-kit` package; it never modifies the
  SDK repo.
- Docs: <https://donkey-development-kit.github.io/donkey-development-kit> ·
  Source: <https://github.com/Donkey-Development-Kit/donkey-development-kit>
