# Donkey Development Kit (DDK) — Demos

Runnable demos for the [**Donkey Development Kit (DDK)**](https://github.com/Donkey-Development-Kit/donkey-development-kit).

This repo holds **two suites on purpose**. They cover the same SDK, but they
are not interchangeable:

| | [`demos/claude-made/`](demos/claude-made/) | [`demos/human-made/`](demos/human-made/) |
|---|---|---|
| **For** | A room, a recording, or CI that must stay offline | A terminal you type in, or paste from |
| **Shape** | Numbered narrative demos (`01`-`21`), each with `demo.py` + README | Straight-line framework scripts, compact pytest conformance and a local A2A launcher/verifier |
| **Runner** | `make demo N=03`, `make offline`, `_harness` (redact, mock, pause) | `python "demos/human-made/<framework>/….py"`; new local checks via `make coverage` |
| **Network** | Twenty of twenty-one need no credentials or external gateway. Demo 09 is live-only | Live scripts need proxy variables; new approval/observation examples use real framework runners with scripted local models or transports |

There is also a browser demo, the **[feature showcase](demos/showcase/)**: a
LangGraph chat on one side and a clickable catalog of DDK features on the other,
running against `donkey mock`. Try the static replay on
**[GitHub Pages](https://donkey-development-kit.github.io/donkey-development-kit-demos/)**,
or run it live locally with `demos/showcase/run.sh`. The catalog covers SDK
`develop` (44 cards): live chat cards for typed refusals (including regex prompt
guard, request rate limit, CIBA pending/denied, terminal kill handling and
refusal reactions, all against the simulator) plus descriptive-only cards that
state what is verified and what is not. `make check-showcase` fails if the
catalog and its static replay drift apart.

For the per-framework *reference* snippets (one `main.py` per framework,
CI-gated), see [`python/examples/`](https://github.com/Donkey-Development-Kit/donkey-development-kit/tree/main/python/examples)
in the SDK repo. Those are not these demos.

What is still missing from either suite is tracked in **[roadmap.md](roadmap.md)**.

Presenting the narrative set? Read **[PRESENTING.md](PRESENTING.md)** — runbook,
talk tracks, failure playbook, and screen-recording rules.

```bash
python -m pip install -e ".[full]"  # full narrative dependencies; see Setup
make offline                # every claude-made demo that needs nothing
```

## Claude-made — the narrative suite

Each demo is a story with acts, a projector-safe narrator, and output masking.
`run.py` discovers `**/demo.py` under `demos/`, so **only this suite** is listed
by `make list` / `make offline`.

**Twenty of twenty-one run without credentials or an external gateway.** Depending
on the story, they use SDK fixture replay, synthetic MockTransport responses,
real loopback HTTP, or local framework/protocol execution. None of those local
checks upgrades a surface to live-verified status.

| # | Demo | Shows | Needs |
|---|------|-------|-------|
| 01 | [governed client](demos/claude-made/01_governed_client/) | Stock vs governed client (async and `sync=True`), then `@donkey.governed` / `@donkey.tool` | nothing |
| 02 | [typed refusals](demos/claude-made/02_typed_refusals/) | Captured rejection shapes through `classify()`, plus `GatewayUnavailable` | nothing |
| 03 | [budget and pacing](demos/claude-made/03_budget_and_pacing/) | Gateway token/request windows vs observe-only provider quotas; bounded reset waits, route changes and unknown fields | offline-only (`[llm,test]`) |
| 04 | [simulating refusals](demos/claude-made/04_simulate_refusals/) | `donkey.simulate()`, `donkey mock --scenario`, and `start_gateway()` | nothing |
| 05 | [conformance suite](demos/claude-made/05_conformance/) | Naive vs corrected agent in both in-process and server modes, matching verdicts and exemption errors | nothing (`[llm,test,local]`) |
| 06 | [telemetry](demos/claude-made/06_telemetry/) | Cross-hop correlation, isolated attribution, real loopback OTLP and DDK-owned vs host-owned flush | offline-only (`[llm,local,test,cli,otel]`) |
| 07 | [model handles](demos/claude-made/07_model_handles/) | Honest gaps: no `/models` catalog; points at `donkey doctor` (demo 14) | nothing |
| 08 | [framework objects](demos/claude-made/08_framework_objects/) | Two deep adapters, six at `connection_kwargs()` (Agents SDK: `{openai_client}`), an Agent Framework `Agent` whose `policy_middleware()` ends a simulated PII refusal as `PIIDetected` | nothing |
| 09 | [LangGraph agent](demos/claude-made/09_langgraph_agent/) | A real tool-calling loop, governed end to end | **credentials** |
| 10 | [last_call](demos/claude-made/10_last_call/) | Gateway identity, routing/usage on a 200 (model-based and semantic); `ModelSubstituted` when you opt in | nothing |
| 11 | [donkey init](demos/claude-made/11_cli_init/) | Commented `.donkey-kit.toml`, every gap named at once, no secrets on disk | nothing (`[cli]`) |
| 12 | [ToolSet.filter](demos/claude-made/12_toolset_filter/) | Independent filtered views of MCP tools; binding refuses ungoverned servers before connecting | nothing |
| 13 | [JWT / model-wallet](demos/claude-made/13_jwt_wallet/) | `llm_proxy_auth="jwt"`: `X-Client-Id` + rotating JWT, no `client_secret` | nothing (`[llm]`) |
| 14 | [donkey doctor](demos/claude-made/14_cli_doctor/) | Wrong URL / wrong creds / model-not-allowed, against the local simulator | nothing (`[cli]` `[local]`) |
| 15 | [provider passthrough](demos/claude-made/15_provider_passthrough/) | Vendor guardrail fields/spans, Model Armor live capture vs CrowdStrike source-derived shape, outage vs content verdict | nothing (`[llm,otel]`) |
| 16 | [publish from CI](demos/claude-made/16_publish_from_ci/) | Deterministic static scan/dry-run, digest semantics and invalid declarations; existing CI publication path is separate | nothing (`[cli]`) |
| 17 | [refusal reactions](demos/claude-made/17_refusal_reactions/) | Bounded wait/resend/fallback, escalation and custom classification; no manufactured success | nothing (`[llm,local,test]`) |
| 18 | [kill handling](demos/claude-made/18_kill_switch/) | `AgentKilled` wakes a budget waiter and latches paced work; no local recovery | nothing (`[llm,local]`) |
| 19 | [tool approvals](demos/claude-made/19_tool_approvals/) | Base pending/resolve/reject/timeout, native LangGraph checkpoint resume, private-argument-free approval spans | nothing (`[llm,local,langgraph,otel]`) |
| 20 | [descriptor fidelity](demos/claude-made/20_descriptor_fidelity/) | Framework-owned schemas, `auto:check` drift and local MCP `tools/list` fidelity | nothing (`[langgraph]` + `mcp`) |
| 21 | [local A2A serving](demos/claude-made/21_a2a_serving/) | Official SDK app/card/tasks, typed failed task, inbound/downstream trace parentage and lifespan cleanup | nothing (`[llm,local,test,otel,a2a]`) |

Harness-backed gateway stories can select `--target mock` (default) or
`--target live`; local-only stories do not become live tests with that flag.
In particular, 03 and 06 do not support live mode. Demo 09 is live only:
the simulator replays a captured completion and will not
decide to call tools. The LangGraph adapter calls `/chat/completions`
(`use_responses_api=False`), the one route every upstream behind an
OpenAI-format proxy serves.

```bash
make list                   # claude-made table, from the filesystem
make demo N=03              # one narrative demo
make offline                # all twenty credential-free narratives
make doctor                 # what is installed, what will therefore run
make mock                   # simulator in the foreground, for a second pane

DEMO_PAUSE=1 make demo N=03 # pause between acts — use this when presenting
```

`python run.py 03` works too, and each demo is a plain script
(`python demos/claude-made/03_budget_and_pacing/demo.py`) once the repo is installed.

## Human-made — the straight-line scripts

Short, top-to-bottom Python under [`demos/human-made/`](demos/human-made/), one
folder per framework. No `_harness`, no redaction, no individual `make demo` target. Run with
the same environment you already use for the SDK. They do not read
`.env.local`, so export it for live scripts (see
[Filling the file](#filling-the-file-from-the-provisioned-proxies)). Filenames
contain spaces; quote the path. Each folder has a README with its install
line, required environment and what every script prints — start at
[`demos/human-made/README.md`](demos/human-made/README.md).

```bash
python "demos/human-made/openai/02 - basic-responses-gw.py"
python "demos/human-made/openai/15 - start-gateway.py"       # local simulator
python "demos/human-made/langgraph/09 - start-gateway.py"    # local simulator
```

How each framework reaches the gateway differs, and the scripts print it
rather than hide it:

| Folder | Route | `X-Correlation-Id` per run | `donkey.last_call` | Typed refusal |
|---|---|---|---|---|
| `openai` | `/responses` | yes | observed | `classify(err.response)` |
| `langgraph` | `/chat/completions` | yes | unobserved (LangChain's task) | `donkey.langgraph.typed_refusals()` |
| `openai-agents` | `/responses` (01); `/chat/completions` (05) | yes | task-dependent; observe in `on_llm_end` | `classify(err.response)` / `donkey.run()` |
| `agent-framework` | `/chat/completions` | yes | observed | `classify(err.__cause__.response)` |
| `strands` | `/chat/completions` | yes | observed | `classify(err.response)` |
| `crewai` | `/chat/completions` | no | unavailable | `classify(err.response)` |
| `llamaindex` | `/chat/completions` | yes | observed | `classify(err.response)` |
| `adk` | `/chat/completions` (LiteLLM) | yes | in `after_model_callback` (Runner's task) | `classify()` in `on_model_error_callback` |
| `anthropic` | `/v1/messages` (`Format=Anthropic`) | yes | observed | `classify(err.response)` |
| `gemini` | `:generateContent` (`Format=Gemini`, plain `httpx`) | — | — | `classify(response)` |

The typed-refusal column is the explicit pattern each script uses; it works on
SDK 0.1.1 and later. From SDK 0.1.2, an error leaving
`donkey.run()` or `@donkey.governed` is already typed (`PIIDetected` and the
rest, with the framework's own error on `exc.framework_error`), and
`donkey_kit.typed_refusals()` does the same around any block. The older ADK 02
script retains its explicit error callback; ADK 04's observation bridge is a
separate concern and does not replace a refusal boundary.

The local simulator serves `/chat/completions` as well as `/responses`.
LangGraph and Agent Framework have `start-gateway` scripts; Strands 03 uses
in-process `simulate()`. Native approval scripts use deterministic framework
models, not a simulator that decides to call tools.

### `a2a/`

The [local A2A launcher and verifier](demos/human-made/a2a/) exercise the real
blocking `Donkey.serve()` facade on loopback TCP: generated card, completed task,
synthetic handler refusal, recovery, correlation IDs and bounded graceful SIGINT
shutdown with the listener closed. Unlike narrative 21's ASGI checks, this crosses
a real local socket. It requires `[a2a]`, uses no dotenv, credentials, model calls
or external collectors, and establishes local verification only, not live gateway
verification, streaming or exposure.

```bash
python "demos/human-made/a2a/01 - serve.py" --port 8000  # blocks until Ctrl-C
python demos/human-made/a2a/verify.py                   # isolated subprocess checks
```

### `openai/`

| # | Script | Shows | Needs |
|---|--------|-------|-------|
| 01 | [basic-responses-no-gw](demos/human-made/openai/01%20-%20basic-responses-no-gw.py) | Stock OpenAI, no gateway | `OPENAI_API_KEY` |
| 02 | [basic-responses-gw](demos/human-made/openai/02%20-%20basic-responses-gw.py) | `donkey.openai()` + `last_call` on a 200 | proxy creds |
| 03 | [typed-refusals-simulated](demos/human-made/openai/03%20-%20typed-refusals-simulated.py) | `simulate()` loop, including `ContentSafetyBlocked` | proxy creds (no network) |
| 04 | [typed-refusals-live](demos/human-made/openai/04%20-%20typed-refusals-live.py) | Live refusals, blocking client, no `async` | proxy creds + policies |
| 05 | [budget_and_pacing](demos/human-made/openai/05%20-%20budget_and_pacing.py) | `pace(reserve=)` then `wait_for_reset()` | proxy creds |
| 06 | [otel exporter simple](demos/human-made/openai/06%20-%20otel%20exporter%20simple.py) | Host-owned `TracerProvider` (Donkey rides it) | proxy + OTLP |
| 07 | [otel exporter advanced](demos/human-made/openai/07%20-%20otel%20exporter%20advanced.py) | Several `donkey.run(team=…, project=…)` + a refusal span | proxy + OTLP |
| 08 | [last-call](demos/human-made/openai/08%20-%20last-call.py) | Full `last_call` record; `on_model_substitution="raise"` | proxy creds |
| 09 | [governed-and-tool](demos/human-made/openai/09%20-%20governed-and-tool.py) | `@donkey.governed` and `@donkey.tool` | nothing |
| 10 | [zero-config-otlp](demos/human-made/openai/10%20-%20zero-config-otlp.py) | `Donkey.from_env()` exports Donkey's own spans over OTLP when the env var is set | proxy creds |
| 11 | [gateway-unavailable](demos/human-made/openai/11%20-%20gateway-unavailable.py) | Dead origin → `GatewayUnavailable` as `__cause__` | nothing |
| 12 | [streaming](demos/human-made/openai/12%20-%20streaming.py) | `responses` SSE; `last_call` usage after the terminal event | proxy creds (live) |
| 13 | [regex-and-content-safety](demos/human-made/openai/13%20-%20regex-and-content-safety.py) | Live regex-prompt-guard and Azure content-safety | proxy + those policies |
| 14 | [jwt-wallet](demos/human-made/openai/14%20-%20jwt-wallet.py) | `llm_proxy_auth="jwt"` + `StaticToken` (async-only) | wallet URL, `DONKEY_LLM_PROXY_WALLET_CLIENT_ID`, `DONKEY_LLM_JWT` |
| 15 | [start-gateway](demos/human-made/openai/15%20-%20start-gateway.py) | `start_gateway()` + stock `httpx`; same fixtures as 03 | nothing (`[local]`) |
| 16 | [bedrock-guardrails](demos/human-made/openai/16%20-%20bedrock-guardrails.py) | Live Bedrock Guardrails → `ContentSafetyBlocked`; `request_id` from `x-amzn-requestid` | proxy + Bedrock Guardrails |
| 17 | [refusal-handlers](demos/human-made/openai/17%20-%20refusal-handlers.py) | Local escalation, custom classifier cleanup and handler return cannot grant success | nothing (`[llm,local]`) |
| 18 | [dynamic-provider-key](demos/human-made/openai/18%20-%20dynamic-provider-key.py) | Customer-chosen provider header beside consumer auth, origin stripping and JWT omission | nothing (`[llm]`) |

### `langgraph/`

| # | Script | Shows | Needs |
|---|--------|-------|-------|
| 01 | [basic-no-gw](demos/human-made/langgraph/01%20-%20basic-no-gw.py) | Stock `ChatOpenAI`, no gateway | `OPENAI_API_KEY` |
| 02 | [basic-gw](demos/human-made/langgraph/02%20-%20basic-gw.py) | `donkey.langgraph("gpt-4o")`; usage from `usage_metadata` | proxy creds |
| 03 | [typed-refusals-simulated](demos/human-made/langgraph/03%20-%20typed-refusals-simulated.py) | `simulate()` through a `create_agent` graph + `typed_refusals()` | proxy creds (no network) |
| 04 | [typed-refusals-live](demos/human-made/langgraph/04%20-%20typed-refusals-live.py) | PII / unknown model / bad creds out of a graph | proxy creds + policies |
| 05 | [agent-and-tool](demos/human-made/langgraph/05%20-%20agent-and-tool.py) | Tool sees the `donkey.run()` id with nothing threaded through state | proxy creds (live) |
| 06 | [otel exporter simple](demos/human-made/langgraph/06%20-%20otel%20exporter%20simple.py) | Host `TracerProvider`, two governed calls | proxy + OTLP |
| 07 | [streaming](demos/human-made/langgraph/07%20-%20streaming.py) | `astream`; usage on the terminal chunk | proxy creds (live) |
| 08 | [gateway-unavailable](demos/human-made/langgraph/08%20-%20gateway-unavailable.py) | `GatewayUnavailable` two causes down | nothing |
| 09 | [start-gateway](demos/human-made/langgraph/09%20-%20start-gateway.py) | Graph against `start_gateway()`, every 2nd call PII | nothing (`[local]`) |
| 10 | [tool-approvals](demos/human-made/langgraph/10%20-%20tool-approvals.py) | Native checkpoint interrupt, approve/reject and recompile/resume; no DDK native expiry | nothing (`[langgraph]`) |

### `openai-agents/`

| # | Script | Shows | Needs |
|---|--------|-------|-------|
| 01 | [agent-and-tool](demos/human-made/openai-agents/01%20-%20agent-and-tool.py) | `OpenAIResponsesModel` + a tool; usage from `context_wrapper` | proxy creds |
| 02 | [typed-refusals-simulated](demos/human-made/openai-agents/02%20-%20typed-refusals-simulated.py) | `simulate()` through `Runner.run` | proxy creds (no network) |
| 03 | [start-gateway](demos/human-made/openai-agents/03%20-%20start-gateway.py) | Agent against `start_gateway()`, every 2nd call PII | nothing (`[local]`) |
| 04 | [approvals](demos/human-made/openai-agents/04%20-%20approvals.py) | Real Runner pause, serialized `RunState`, approve/reject/resume with scripted model | nothing (`[openai-agents]`) |
| 05 | [governed-observations](demos/human-made/openai-agents/05%20-%20governed-observations.py) | Customer conformance and `on_llm_end` observation; post-run visibility depends on path | nothing (`[llm,openai-agents,test]`) |

### `agent-framework/`

| # | Script | Shows | Needs |
|---|--------|-------|-------|
| 01 | [basic-gw](demos/human-made/agent-framework/01%20-%20basic-gw.py) | `Agent(client=donkey.agent_framework.chat_client(...))` | proxy creds |
| 02 | [typed-refusals-live](demos/human-made/agent-framework/02%20-%20typed-refusals-live.py) | `ChatClientException` → `classify(__cause__.response)` | proxy creds + policies |
| 03 | [start-gateway](demos/human-made/agent-framework/03%20-%20start-gateway.py) | Agent against `start_gateway()`, every 2nd call PII | nothing (`[local]`) |

### `strands/`

| # | Script | Shows | Needs |
|---|--------|-------|-------|
| 01 | [basic-gw](demos/human-made/strands/01%20-%20basic-gw.py) | `OpenAIModel(client=donkey.openai())` — see the note below | `strands-agents[openai]` + proxy |
| 02 | [agent-and-tool](demos/human-made/strands/02%20-%20agent-and-tool.py) | Tool loop; run id in the tool; `last_call` observed | proxy creds (live) |
| 03 | [typed-refusals-simulated](demos/human-made/strands/03%20-%20typed-refusals-simulated.py) | `simulate()` through `invoke_async` (no 429: Strands retries it) | proxy creds (no network) |
| 04 | [typed-refusals-live](demos/human-made/strands/04%20-%20typed-refusals-live.py) | PII / unknown model / bad creds | proxy creds + policies |
| 05 | [approvals](demos/human-made/strands/05%20-%20approvals.py) | Native interrupt decisions; approved governed tool still propagates `PIIDetected` | nothing (`[llm,strands]`, Python 3.12 environment) |

### `crewai/`, `llamaindex/`, `adk/`

| # | Script | Shows | Needs |
|---|--------|-------|-------|
| 01 | [basic-gw](demos/human-made/crewai/01%20-%20basic-gw.py) | `crewai.llm(...).call` and `Agent.kickoff` | proxy creds |
| 02 | [typed-refusals-live](demos/human-made/crewai/02%20-%20typed-refusals-live.py) | PII / unknown model / bad creds | proxy creds + policies |
| 01 | [basic-gw](demos/human-made/llamaindex/01%20-%20basic-gw.py) | `OpenAILike` `complete` and `chat` | proxy creds |
| 02 | [typed-refusals-live](demos/human-made/llamaindex/02%20-%20typed-refusals-live.py) | PII / unknown model / bad creds | proxy creds + policies |
| 01 | [basic-gw](demos/human-made/adk/01%20-%20basic-gw.py) | `LiteLlm` agent through `InMemoryRunner` | proxy creds |
| 02 | [refusal-live](demos/human-made/adk/02%20-%20refusal-live.py) | PII 403 typed as `PIIDetected` in `on_model_error_callback` | proxy creds + PII policy |
| 03 | [approvals](demos/human-made/adk/03%20-%20approvals.py) | Real App/Runner confirmation, decisions and replay protection with scripted model | nothing (`[adk]`, Python 3.12 environment) |
| 04 | [bridged-observations](demos/human-made/adk/04%20-%20bridged-observations.py) | Factory/hand-built LiteLLM streamed callback observation, terminal usage | nothing (`[llm,adk]`, Python 3.12 environment) |

The [human-made conformance example](demos/human-made/conformance/) adds a compact
agent, ordinary pytest assertions and both public conformance modes. Run
`python demos/human-made/conformance/verify.py` from the root for isolated local
verification. Native approvals are advisory local gates, not gateway authorization
or an approval service. Rejection formats remain framework-native.

### `anthropic/`, `gemini/`

| # | Script | Shows | Needs |
|---|--------|-------|-------|
| 01 | [native-messages](demos/human-made/anthropic/01%20-%20native-messages.py) | `donkey.anthropic.client()` on `/v1/messages`; `request-id` vs `request_id` | `Format=Anthropic` proxy |
| 02 | [typed-refusals-simulated](demos/human-made/anthropic/02%20-%20typed-refusals-simulated.py) | `simulate()` through the native Anthropic client | proxy creds (no network) |
| 01 | [native-generate-content](demos/human-made/gemini/01%20-%20native-generate-content.py) | `:generateContent` via `httpx` (no adapter ships) | `Format=Gemini` proxy |
| 02 | [openai-shape-rejected](demos/human-made/gemini/02%20-%20openai-shape-rejected.py) | Gemini's list envelope → `UpstreamRequestError` | `Format=Gemini` proxy |

**Strands note.** `donkey.strands.model()` hands Strands `client_args`, and
Strands opens and closes an OpenAI client from them on every request — which
closes the SDK's shared transport after the first call. The scripts pass a
pre-built `client=donkey.openai()` instead, which Strands reuses and leaves open.

## Setup

```bash
# 0. A virtual environment (see below for why this is not optional)
python3 -m venv .venv          # .venv/ is git-ignored
source .venv/bin/activate      # once per terminal

# 1. The demo harness (adds _harness to the path; no SDK pinned)
python -m pip install -e .

# 2. The SDK. Either the release this branch tracks, from PyPI…
python -m pip install -e ".[full]"      # donkey-kit 0.2.0 + langchain + mcp

#    …or your own checkout, on the matching SDK branch (main here)
python -m pip install -e "../donkey-development-kit/python[llm,local,test,cli,otel,langgraph,openai-agents,a2a]" "mcp"
python -m pip install "langchain>=1.0"   # demo 09 only; no donkey-kit extra ships it
```

The full narrative environment does not include every optional framework.
Strands and ADK scripts need their separate extras and a Python 3.12 environment;
they were locally tested there, not in the default Python 3.15 environment.
See their folder READMEs for installation and runner commands. Do not install
every framework into the default environment and assume compatible dependencies.

### Local coverage verification

From the repo root, run the new straight-line examples in fresh processes:

```bash
make coverage PY=.venv/bin/python
.venv-frameworks/bin/python scripts/verify_sdk_coverage.py --frameworks
```

`make coverage` includes OpenAI reactions/dynamic keys, LangGraph and Agents
companions, conformance and the A2A TCP launcher verifier. `--frameworks` runs
only Strands/ADK companions; use a separate Python 3.12 environment with their
extras installed. Neither command loads dotenv or establishes live verification.

**Which SDK each branch tracks.** `main` (this branch) runs against the SDK's
latest release (`main`, on PyPI), so here `[sdk]` and `[full]` pin it exactly.
`develop` tracks the SDK's `develop`, so there they pin the git ref `@develop`.
Don't mix the two: module paths and CLI flags change between releases.
CI enforces this: the `SDK alignment` workflow checks the pin
(`make check-sdk`) and runs `make offline` against it on every PR, and nightly
on both branches, so an SDK release or a breaking SDK `develop` change shows up
the next morning.

**Why a virtual environment.** Homebrew's `python3` (and most Linux distro
Pythons) is marked *externally managed* (PEP 668),
so a global `pip3 install …` stops with `error: externally-managed-environment`.
Do not work around it with `--break-system-packages`; install into `.venv`
instead. Without it, the demos fail with `ModuleNotFoundError: No module named
'openai'` or `'donkey_kit'`, and `make doctor` reports every package as `FAIL`.
Homebrew ships no bare `pip` or `python` command, only `pip3` and `python3`;
both short names work once `.venv` is active.

Quote the `[...]` extras: zsh, the macOS default shell, treats unquoted brackets
as a glob and fails with `no matches found`. `uv` users can replace the first
two lines with `uv venv` and `pip install` with `uv pip install`.

To have Cursor / VS Code activate the environment in every new terminal, set
`"python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python"` in
your local `.vscode/settings.json`, which you copy from `settings.shared.json`.

Live demos additionally need three variables. Copy the template and fill it in:

```bash
cp .env.example .env.local     # .env.local is git-ignored
```

A shell `export` always beats a file value, so you can skip the file entirely.
`make doctor` will tell you what it found without printing any of it.

### Filling the file from the provisioned proxies

The proxies these demos talk to are the ones created by
`donkey-development-kit-provisioning` and exercised by
`donkey-development-kit-acceptance`. Take the values from those sibling
checkouts instead of minting new ones:

| Variable | Where it comes from |
|----------|---------------------|
| `DONKEY_LLM_PROXY_URL` | `base_url` of a `[[proxy]]` entry in `../donkey-development-kit-acceptance/acceptance/proxies.toml`, **plus a trailing `/`** |
| `DONKEY_LLM_PROXY_CLIENT_ID` / `_SECRET` | The `client_id_env` / `client_secret_env` names on that same entry, looked up in `../donkey-development-kit-acceptance/.env` |
| `OPENAI_API_KEY` (human-made 01 only) | `OPENAI_KEY` in `../donkey-development-kit-provisioning/.env` |
| `DEMO_MODEL` | The `model` on that same entry, e.g. `openai/gpt-5-mini` |

Start with `openai-model-routing`: it is the one tagged `responses`,
`streaming` and `attribution`, which is what most demos exercise. Only one
proxy can be active at a time, so keep the others as commented-out blocks and
swap by uncommenting. `injection-guard` and `azure-content-safety` are the ones
human-made 04 refuses against; `token-rate-limit` is the only proxy that emits
the `x-llm-proxy-ratelimit` header human-made 05 reads.

The provisioning `.env` is `Key: value`, the acceptance `.env` is `KEY=value`,
and neither can be copied wholesale into this one. Do not print either file
while screen-sharing: the provisioning one holds Anypoint, provider and
Keycloak admin secrets.

**The human-made scripts do not load `.env` / `.env.local`**. Harness mock/live
preflight loads dotenv, but offline preflight does not; the SDK never reads dotenv
files on its own. Export the file into your shell before running live scripts:

```bash
set -a; source .env.local; set +a
python "demos/human-made/openai/02 - basic-responses-gw.py"
```

The provisioned proxies route `gpt-5-mini` only, while the human-made scripts
hardcode `model="gpt-4o"`. Expect a routing refusal or a `ModelSubstituted`
until the script's model matches the proxy's.

## Credentials never leave your machine

The **claude-made** suite is built on the assumption that a demo will be
screen-shared, recorded, and committed to by someone in a hurry. Four things
guard that:

- **Output is masked by default.** Every value a narrative demo prints goes
  through `_harness/redact.py`, which masks gateway hostnames, the
  `client_id`/`client_secret` pair, and the tenant identifiers that ride along
  in captured responses (`x-envoy-decorator-operation`, `openai-organization`,
  `cf-ray`). Header *names* are always shown; their values never are.
- **`DEMO_REDACT=0` announces itself.** Turning masking off prints a warning
  banner in the run context of every narrative demo.
- **No captured traffic is vendored.** Demo 02 loads fixtures from the installed
  SDK (`donkey_kit.simulator.fixtures`) rather than keeping copies here.
- **`make scan` reads content, not filenames.** `scripts/scan_secrets.py` fails
  on assigned credential values, Anypoint instance ids, bearer tokens, UUIDs and
  non-allowlisted hostnames. `make hooks` installs it as a pre-commit hook.

**Human-made scripts do not redact.** They print completions and error strings
as the SDK returned them. Use them on a private terminal, not on a shared
recording.

```bash
make scan       # everything tracked
make hooks      # then it runs on every commit
```

## Honest status

**The DDK is evolving fast, and these demos change with it.** Scripts, extras
and expected output can shift between SDK releases, sometimes within days. When
something here disagrees with the SDK, the SDK wins: check the
[DDK main repository](https://github.com/Donkey-Development-Kit/donkey-development-kit)
— its commit history, [`docs/verified-apis.md`](https://github.com/Donkey-Development-Kit/donkey-development-kit/blob/main/docs/verified-apis.md)
and [`python/examples/`](https://github.com/Donkey-Development-Kit/donkey-development-kit/tree/main/python/examples)
— before assuming a demo is right.

The proxy contract these demos exercise is live-verified: the base URL shape
(no `/v1`), the `client_id`/`client_secret` header pair, streaming, inbound
`X-Correlation-Id` echo, the Anthropic- and Gemini-native ingress routes, and
seven rejection shapes (auth, PII, token rate limit, upstream including
Gemini's list envelope, regex prompt guard, Azure content-safety, Bedrock
Guardrails). See
[`docs/verified-apis.md`](https://github.com/Donkey-Development-Kit/donkey-development-kit/blob/main/docs/verified-apis.md).

The demos say these boundaries out loud rather than gloss over:

- **Happy-path budget numbers on the simulator are illustrative.** A live 200
  (with the token-rate policy applied) carries the window as prose
  `x-llm-proxy-ratelimit` — that sentence is live-verified. The numeric
  `x-token-*` trio is verified on the 429. Claude-made 03 prints the distinction.
- **Header-based injection-protection is the one guardrail still typed from
  the documented wire shape** — no proxy running that policy is deployed to
  capture. Regex prompt guard and Azure content-safety are live (2026-09-22),
  Bedrock Guardrails too (2026-09-24). An undiscriminated `content-moderation` 4xx still falls through
  to a generic `PolicyViolation`. `simulate(PromptInjectionBlocked)` injects
  the documented injection-protection representative, not the live regex
  capture — one fixture per exception type.
- **Model Armor and CrowdStrike have different provenance.** Demo 15 replays
  Google Model Armor's live capture (2026-10-19); CrowdStrike AIDR and its
  fail-closed 503 are policy-source-derived. The 503 is `UpstreamModelError`,
  not a content verdict. Neither sibling contract is a simulator vendor selector.
- **Only one framework adapter has reached live-verified status; the rest have not.** The
  raw client and LangGraph are conformance-tested against the simulator; every
  other adapter constructor, ADK's `model()` included, is signature-confirmed
  offline by the SDK's `scripts/verify_frameworks.py`. New native approval and
  observation companions add local runner evidence, including Agents customer
  conformance, not live verification. ADK's `gemini()` is
  live-verified through a `Format=Gemini` proxy. An adapter raises "blocked on
  verification" only when the installed framework version lacks the class or
  field it depends on. Cost tags live on `donkey.cost.*` spans; the gateway has no inbound
  cost-tag ingestion (verified-negative).

Exchange discovery and governed MCP binding remain verification-blocked.
Static scan and publication planning are demonstrated in 16, descriptor fidelity
in 20, and local A2A serving in 21 plus the human-made blocking TCP launcher
verifier; none proves remote discovery, provisioning or live gateway enforcement.
Connected-app publication authentication is still unverified live, agent
publication is skipped, and gateway exposure / `donkey expose` / `donkey dev`
remain outside implemented scope. See [roadmap.md](roadmap.md) for remaining gaps.
