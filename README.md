# Donkey Development Kit (DDK) — Demos

Runnable demos for the [**Donkey Development Kit (DDK)**](https://github.com/Donkey-Development-Kit/donkey-development-kit).

This repo holds **two suites on purpose**. They cover the same SDK, but they
are not interchangeable:

| | [`demos/claude-made/`](demos/claude-made/) | [`demos/human-made/`](demos/human-made/) |
|---|---|---|
| **For** | A room, a recording, or CI that must stay offline | A terminal you type in, or paste from |
| **Shape** | Numbered narrative demos (`01`–`14`), each with `demo.py` + README | Straight-line OpenAI scripts (`01`–`15`), one file each |
| **Runner** | `make demo N=03`, `make offline`, `_harness` (redact, mock, pause) | `python "demos/human-made/openai/….py"` — not in `make` |
| **Network** | Thirteen of the fourteen need nothing. Demo 09 is live-only | Most need `DONKEY_LLM_PROXY_*`. 09, 11 and 15 need no gateway; 14 needs a wallet JWT |

For the per-framework *reference* snippets (one `main.py` per framework,
CI-gated), see [`python/examples/`](https://github.com/Donkey-Development-Kit/donkey-development-kit/tree/main/python/examples)
in the SDK repo. Those are not these demos.

What is still missing from either suite is tracked in **[roadmap.md](roadmap.md)**.

Presenting the narrative set? Read **[PRESENTING.md](PRESENTING.md)** — runbook,
talk tracks, failure playbook, and screen-recording rules.

```bash
pip install -e ".[sdk]"     # or point at your own donkey-kit checkout
make offline                # every claude-made demo that needs nothing
```

## Claude-made — the narrative suite

Each demo is a story with acts, a projector-safe narrator, and output masking.
`run.py` discovers `**/demo.py` under `demos/`, so **only this suite** is listed
by `make list` / `make offline`.

**Thirteen of the fourteen run with no credentials and no gateway**, against the SDK's
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

Every claude-made demo takes `--target mock` (default) or `--target live`. Demo
09 is live only: the simulator replays a captured `/responses` completion and
will not decide to call tools. The LangGraph adapter itself targets
`/responses` (`use_responses_api=True`), the same live-verified route as
`donkey.openai()`.

```bash
make list                   # claude-made table, from the filesystem
make demo N=03              # one narrative demo
make offline                # all thirteen offline claude-made demos
make doctor                 # what is installed, what will therefore run
make mock                   # simulator in the foreground, for a second pane

DEMO_PAUSE=1 make demo N=03 # pause between acts — use this when presenting
```

`python run.py 03` works too, and each demo is a plain script
(`python demos/claude-made/03_budget_and_pacing/demo.py`) once the repo is installed.

## Human-made — the OpenAI scripts

Short, top-to-bottom Python under [`demos/human-made/openai/`](demos/human-made/openai/).
No `_harness`, no redaction, no `make` target. Run with the same environment
you already use for the SDK:

```bash
python "demos/human-made/openai/02 - basic-responses-gw.py"
python "demos/human-made/openai/09 - governed-and-tool.py"   # no gateway
python "demos/human-made/openai/11 - gateway-unavailable.py" # no gateway
python "demos/human-made/openai/15 - start-gateway.py"       # local simulator
```

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

Filenames contain spaces; quote the path. This folder is OpenAI-only — other
frameworks live in claude-made 08/09 and in the SDK's `python/examples/`.

## Setup

```bash
# 1. The demo harness (adds _harness to the path; no SDK pinned)
pip install -e .

# 2. The SDK. Either your own checkout…
pip install -e ../donkey-development-kit/python[llm,local,test,otel,langgraph]

#    …or from git
pip install -e ".[full]"
```

Live demos additionally need three variables. Copy the template and fill it in:

```bash
cp .env.example .env.local     # .env.local is git-ignored
```

A shell `export` always beats a file value, so you can skip the file entirely.
`make doctor` will tell you what it found without printing any of it.

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
`X-Correlation-Id` echo, and six of the rejection shapes (auth, PII, token
rate limit, upstream, regex prompt guard, Azure content-safety). See
[`docs/verified-apis.md`](https://github.com/Donkey-Development-Kit/donkey-development-kit/blob/main/docs/verified-apis.md).

Three things the demos say out loud rather than gloss over:

- **Happy-path budget numbers on the simulator are illustrative.** A live 200
  (with the token-rate policy applied) carries the window as prose
  `x-llm-proxy-ratelimit` — that sentence is live-verified. The numeric
  `x-token-*` trio is verified on the 429. Claude-made 03 prints the distinction.
- **Header-based injection-protection and Bedrock guardrails stay typed from
  the documented wire shapes** — no proxy running those policies is deployed
  to capture. Regex prompt guard and Azure content-safety **are** live
  (2026-09-22). An undiscriminated `content-moderation` 4xx still falls through
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
