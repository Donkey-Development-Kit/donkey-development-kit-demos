# Donkey Development Kit (DDK) — Demos

Runnable demos for the [**Donkey Development Kit (DDK)**](https://github.com/Donkey-Development-Kit/donkey-development-kit).

This repo holds **two suites on purpose**. They cover the same SDK, but they
are not interchangeable:

| | [`demos/claude-made/`](demos/claude-made/) | [`demos/human-made/`](demos/human-made/) |
|---|---|---|
| **For** | A room, a recording, or CI that must stay offline | A terminal you type in, or paste from |
| **Shape** | Numbered narrative demos (`01`–`15`), each with `demo.py` + README | Straight-line scripts, one folder per framework, one file each |
| **Runner** | `make demo N=03`, `make offline`, `_harness` (redact, mock, pause) | `python "demos/human-made/<framework>/….py"` — not in `make` |
| **Network** | Fourteen of the fifteen need nothing. Demo 09 is live-only | Most need `DONKEY_LLM_PROXY_*`. `start-gateway`, `gateway-unavailable` and `simulated` scripts need no gateway |

For the per-framework *reference* snippets (one `main.py` per framework,
CI-gated), see [`python/examples/`](https://github.com/Donkey-Development-Kit/donkey-development-kit/tree/main/python/examples)
in the SDK repo. Those are not these demos.

What is still missing from either suite is tracked in **[roadmap.md](roadmap.md)**.

Presenting the narrative set? Read **[PRESENTING.md](PRESENTING.md)** — runbook,
talk tracks, failure playbook, and screen-recording rules.

```bash
python -m pip install -e ".[sdk]"   # inside a venv — see Setup
make offline                # every claude-made demo that needs nothing
```

## Claude-made — the narrative suite

Each demo is a story with acts, a projector-safe narrator, and output masking.
`run.py` discovers `**/demo.py` under `demos/`, so **only this suite** is listed
by `make list` / `make offline`.

**Fourteen of the fifteen run with no credentials and no gateway**, against the SDK's
local simulator — the same captured responses the SDK's own tests are written
against.

| # | Demo | Shows | Needs |
|---|------|-------|-------|
| 01 | [governed client](demos/claude-made/01_governed_client/) | Stock vs governed client (async and `sync=True`), then `@donkey.governed` / `@donkey.tool` | nothing |
| 02 | [typed refusals](demos/claude-made/02_typed_refusals/) | Captured rejection shapes through `classify()`, plus `GatewayUnavailable` | nothing |
| 03 | [budget and pacing](demos/claude-made/03_budget_and_pacing/) | The token window as an object; `pace(reserve=)` and `wait_for_reset()` (only when `reset_at` is known) | nothing |
| 04 | [simulating refusals](demos/claude-made/04_simulate_refusals/) | `donkey.simulate()`, `donkey mock --scenario`, and `start_gateway()` | nothing |
| 05 | [conformance suite](demos/claude-made/05_conformance/) | `pytest --donkey-conformance` (and `donkey test`) grading a naive agent, then the fixed one | nothing |
| 06 | [telemetry](demos/claude-made/06_telemetry/) | GenAI spans (`gen_ai.*` + `donkey.*`), `donkey.run(id=…)`, zero-config OTLP | nothing |
| 07 | [model handles](demos/claude-made/07_model_handles/) | Honest gaps: no `/models` catalog; points at `donkey doctor` (demo 14) | nothing |
| 08 | [framework objects](demos/claude-made/08_framework_objects/) | One deep adapter, seven at `connection_kwargs()` (Agents SDK: `{openai_client}`), `policy_middleware()` | nothing |
| 09 | [LangGraph agent](demos/claude-made/09_langgraph_agent/) | A real tool-calling loop, governed end to end | **credentials** |
| 10 | [last_call](demos/claude-made/10_last_call/) | Gateway identity, routing/usage on a 200; `ModelSubstituted` when you opt in | nothing |
| 11 | [donkey init](demos/claude-made/11_cli_init/) | Commented `.donkey-kit.toml`, every gap named at once, no secrets on disk | nothing (`[cli]`) |
| 12 | [ToolSet.filter](demos/claude-made/12_toolset_filter/) | Independent filtered views of MCP tools; binding still blocked on verification | nothing |
| 13 | [JWT / model-wallet](demos/claude-made/13_jwt_wallet/) | `llm_proxy_auth="jwt"`: `X-Client-Id` + rotating JWT, no `client_secret` | nothing (`[llm]`) |
| 14 | [donkey doctor](demos/claude-made/14_cli_doctor/) | Wrong URL / wrong creds / model-not-allowed, against the local simulator | nothing (`[cli]` `[local]`) |
| 15 | [provider passthrough](demos/claude-made/15_provider_passthrough/) | Per-provider request id, Azure vs Bedrock guardrails, OpenAI vs Gemini error envelopes, ingress Formats | nothing |

Every claude-made demo takes `--target mock` (default) or `--target live`. Demo
09 is live only: the simulator replays a captured `/responses` completion and
will not decide to call tools. The LangGraph adapter itself targets
`/responses` (`use_responses_api=True`), the same live-verified route as
`donkey.openai()`.

```bash
make list                   # claude-made table, from the filesystem
make demo N=03              # one narrative demo
make offline                # all fourteen offline claude-made demos
make doctor                 # what is installed, what will therefore run
make mock                   # simulator in the foreground, for a second pane

DEMO_PAUSE=1 make demo N=03 # pause between acts — use this when presenting
```

`python run.py 03` works too, and each demo is a plain script
(`python demos/claude-made/03_budget_and_pacing/demo.py`) once the repo is installed.

## Human-made — the straight-line scripts

Short, top-to-bottom Python under [`demos/human-made/`](demos/human-made/), one
folder per framework. No `_harness`, no redaction, no `make` target. Run with
the same environment you already use for the SDK. They do not read
`.env.local`, so export it first (see
[Filling the file](#filling-the-file-from-the-provisioned-proxies)). Filenames
contain spaces; quote the path.

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
| `langgraph` | `/responses` | yes | unobserved (LangChain's task) | `donkey.langgraph.typed_refusals()` |
| `openai-agents` | `/responses` | yes | unobserved (Runner's task) | `classify(err.response)` |
| `agent-framework` | `/responses` | no | unavailable | `classify(err.__cause__.response)` |
| `strands` | `/chat/completions` | yes | observed | `classify(err.response)` |
| `crewai` | `/chat/completions` | no | unavailable | `classify(err.response)` |
| `llamaindex` | `/chat/completions` | no | unavailable | `classify(err.response)` |
| `adk` | `/chat/completions` (LiteLLM) | no | unavailable | none — LiteLLM drops the headers |
| `anthropic` | `/v1/messages` (`Format=Anthropic`) | yes | observed | `classify(err.response)` |
| `gemini` | `:generateContent` (`Format=Gemini`, plain `httpx`) | — | — | `classify(response)` |

Only `/responses` is live-verified on the DDK proxies; the `/chat/completions`
folders were checked against the installed framework versions and a local
chat-completions stub, not a real gateway.

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
| 10 | [zero-config-otlp](demos/human-made/openai/10%20-%20zero-config-otlp.py) | `Donkey.from_env()` installs OTLP when the env var is set | proxy creds |
| 11 | [gateway-unavailable](demos/human-made/openai/11%20-%20gateway-unavailable.py) | Dead origin → `GatewayUnavailable` as `__cause__` | nothing |
| 12 | [streaming](demos/human-made/openai/12%20-%20streaming.py) | `responses` SSE; `last_call` usage after the terminal event | proxy creds (live) |
| 13 | [regex-and-content-safety](demos/human-made/openai/13%20-%20regex-and-content-safety.py) | Live regex-prompt-guard and Azure content-safety | proxy + those policies |
| 14 | [jwt-wallet](demos/human-made/openai/14%20-%20jwt-wallet.py) | `llm_proxy_auth="jwt"` + `StaticToken` (async-only) | wallet URL, `DONKEY_LLM_PROXY_WALLET_CLIENT_ID`, `DONKEY_LLM_JWT` |
| 15 | [start-gateway](demos/human-made/openai/15%20-%20start-gateway.py) | `start_gateway()` + stock `httpx`; same fixtures as 03 | nothing (`[local]`) |
| 16 | [bedrock-guardrails](demos/human-made/openai/16%20-%20bedrock-guardrails.py) | Live Bedrock Guardrails → `ContentSafetyBlocked`; `request_id` from `x-amzn-requestid` | proxy + Bedrock Guardrails |

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

### `openai-agents/`

| # | Script | Shows | Needs |
|---|--------|-------|-------|
| 01 | [agent-and-tool](demos/human-made/openai-agents/01%20-%20agent-and-tool.py) | `OpenAIResponsesModel` + a tool; usage from `context_wrapper` | proxy creds |
| 02 | [typed-refusals-simulated](demos/human-made/openai-agents/02%20-%20typed-refusals-simulated.py) | `simulate()` through `Runner.run` | proxy creds (no network) |
| 03 | [start-gateway](demos/human-made/openai-agents/03%20-%20start-gateway.py) | Agent against `start_gateway()`, every 2nd call PII | nothing (`[local]`) |

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

### `crewai/`, `llamaindex/`, `adk/`

| # | Script | Shows | Needs |
|---|--------|-------|-------|
| 01 | [basic-gw](demos/human-made/crewai/01%20-%20basic-gw.py) | `crewai.llm(...).call` and `Agent.kickoff` | proxy creds |
| 02 | [typed-refusals-live](demos/human-made/crewai/02%20-%20typed-refusals-live.py) | PII / unknown model / bad creds | proxy creds + policies |
| 01 | [basic-gw](demos/human-made/llamaindex/01%20-%20basic-gw.py) | `OpenAILike` `complete` and `chat` | proxy creds |
| 02 | [typed-refusals-live](demos/human-made/llamaindex/02%20-%20typed-refusals-live.py) | PII / unknown model / bad creds | proxy creds + policies |
| 01 | [basic-gw](demos/human-made/adk/01%20-%20basic-gw.py) | `LiteLlm` agent through `InMemoryRunner` | proxy creds |
| 02 | [refusal-live](demos/human-made/adk/02%20-%20refusal-live.py) | PII 403 as a LiteLLM `APIError` — status only | proxy creds + PII policy |

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

# 2. The SDK. Either your own checkout…
python -m pip install -e "../donkey-development-kit/python[llm,local,test,otel,langgraph,cli]"
python -m pip install "langchain>=1.0"   # demo 09 only; no donkey-kit extra ships it

#    …or from git
python -m pip install -e ".[full]"

#    …or a published dev build from TestPyPI (its deps come from PyPI)
python -m pip install -i https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ "donkey-kit[llm,local,test,otel,langgraph,cli]"
```

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

**The human-made scripts do not load `.env` / `.env.local`**. Only `_harness`
does, and the SDK never reads dotenv files on its own. Export the file into
your shell before running them:

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

The proxy contract these demos exercise is live-verified: the base URL shape
(no `/v1`), the `client_id`/`client_secret` header pair, streaming, inbound
`X-Correlation-Id` echo, the Anthropic- and Gemini-native ingress routes, and
seven rejection shapes (auth, PII, token rate limit, upstream including
Gemini's list envelope, regex prompt guard, Azure content-safety, Bedrock
Guardrails). See
[`docs/verified-apis.md`](https://github.com/Donkey-Development-Kit/donkey-development-kit/blob/main/docs/verified-apis.md).

Three things the demos say out loud rather than gloss over:

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
- **Most framework class names are unverified.** Agent Framework's
  `OpenAIChatClient(model=…, base_url, api_key, default_headers)` is verified
  against 1.19.0. The rest are checked by a nightly matrix, and an adapter
  that cannot confirm a signature raises "blocked on verification" rather than
  guessing. Cost tags live on `donkey.cost.*` spans; the gateway has no inbound
  cost-tag ingestion (verified-negative).

Not demoed at all, because the SDK raises `NotImplementedError("blocked on
verification")`: Exchange discovery, MCP tool binding, and every provisioning
verb except `validate` and `mock`. Do not add demos for those until the SDK
unblocks them — see [roadmap.md](roadmap.md).
