# Donkey Development Kit (DDK) — Demos

Runnable demos for the [**Donkey Development Kit (DDK)**](https://github.com/Donkey-Development-Kit/donkey-development-kit).

This repo holds **two suites on purpose**. They cover the same SDK, but they
are not interchangeable:

| | [`demos/claude-made/`](demos/claude-made/) | [`demos/human-made/`](demos/human-made/) |
|---|---|---|
| **For** | A room, a recording, or CI that must stay offline | A terminal you type in, or paste from |
| **Shape** | Numbered narrative demos (`01`–`10`), each with `demo.py` + README | Straight-line OpenAI scripts (`01`–`11`), one file each |
| **Runner** | `make demo N=03`, `make offline`, `_harness` (redact, mock, pause) | `python "demos/human-made/openai/….py"` — not in `make` |
| **Network** | Nine of the ten need nothing (local simulator). Demo 09 is live-only | Most need `DONKEY_LLM_PROXY_*`. 09 and 11 need no gateway |

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

**Nine of the ten run with no credentials and no gateway**, against the SDK's
local simulator — the same captured responses the SDK's own tests are written
against.

| # | Demo | Shows | Needs |
|---|------|-------|-------|
| 01 | [governed client](demos/claude-made/01_governed_client/) | Stock vs governed client, then `@donkey.governed` / `@donkey.tool` | nothing |
| 02 | [typed refusals](demos/claude-made/02_typed_refusals/) | Captured rejection shapes through `classify()`, plus `GatewayUnavailable` | nothing |
| 03 | [budget and pacing](demos/claude-made/03_budget_and_pacing/) | The token window as an object; `pace(reserve=)` and `wait_for_reset()` | nothing |
| 04 | [simulating refusals](demos/claude-made/04_simulate_refusals/) | `donkey.simulate()` and `donkey mock --scenario` parsing | nothing |
| 05 | [conformance suite](demos/claude-made/05_conformance/) | `pytest --donkey-conformance` grading a naive agent, then the fixed one | nothing |
| 06 | [telemetry](demos/claude-made/06_telemetry/) | GenAI spans (`gen_ai.*` + `donkey.*`), `donkey.run(id=…)`, zero-config OTLP | nothing |
| 07 | [model handles](demos/claude-made/07_model_handles/) | Honest gaps: no `/models` catalog; points at `donkey doctor` | nothing |
| 08 | [framework objects](demos/claude-made/08_framework_objects/) | One deep adapter (LangGraph), seven at `connection_kwargs()`, no wrappers | nothing |
| 09 | [LangGraph agent](demos/claude-made/09_langgraph_agent/) | A real tool-calling loop, governed end to end | **credentials** |
| 10 | [last_call](demos/claude-made/10_last_call/) | Gateway identity, routing/usage on a 200; `ModelSubstituted` when you opt in | nothing |

Every claude-made demo takes `--target mock` (default) or `--target live`. Demo
09 is live only: the simulator replays a captured `/responses` completion and
will not decide to call tools. The LangGraph adapter itself targets
`/responses` (`use_responses_api=True`), the same live-verified route as
`donkey.openai()`.

```bash
make list                   # claude-made table, from the filesystem
make demo N=03              # one narrative demo
make offline                # all nine offline claude-made demos
make doctor                 # what is installed, what will therefore run
make mock                   # simulator in the foreground, for a second pane

DEMO_PAUSE=1 make demo N=03 # pause between acts — use this when presenting
```

`python run.py 03` works too, and each demo is a plain script
(`python demos/claude-made/03_budget_and_pacing/demo.py`) once the repo is installed.

## Human-made — the OpenAI scripts

Short, top-to-bottom Python under [`demos/human-made/openai/`](demos/human-made/openai/).
No `_harness`, no redaction, no `make` target. Run with the same environment
you already use for the SDK. They do not read `.env.local`, so export it first
(see [Filling the file](#filling-the-file-from-the-provisioned-proxies)):

```bash
python "demos/human-made/openai/02 - basic-responses-gw.py"
python "demos/human-made/openai/09 - governed-and-tool.py"   # no gateway
python "demos/human-made/openai/11 - gateway-unavailable.py" # no gateway
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

Filenames contain spaces; quote the path. This folder is OpenAI-only — other
frameworks live in claude-made 08/09 and in the SDK's `python/examples/`.

## Setup

```bash
# 0. A virtual environment (see below for why this is not optional)
python3 -m venv .venv          # .venv/ is git-ignored
source .venv/bin/activate      # once per terminal

# 1. The demo harness (adds _harness to the path; no SDK pinned)
python -m pip install -e .

# 2. The SDK. Either your own checkout…
python -m pip install -e "../donkey-development-kit/python[llm,local,test,otel,langgraph,cli]"

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
(no `/v1`), the `client_id`/`client_secret` header pair, streaming, and four of
the rejection shapes. See
[`docs/verified-apis.md`](https://github.com/Donkey-Development-Kit/donkey-development-kit/blob/main/docs/verified-apis.md).

Three things the demos say out loud rather than gloss over:

- **Happy-path budget numbers on the simulator are illustrative.** A live 200
  (with the token-rate policy applied) carries the window as prose
  `x-llm-proxy-ratelimit` — that sentence is live-verified. The numeric
  `x-token-*` trio is verified on the 429. Claude-made 03 prints the distinction.
- **Content-safety and regex-prompt-guard are typed from the documented wire
  shapes**, pending a live capture — the same posture as header-based injection.
  An undiscriminated `content-moderation` 4xx still falls through to a generic
  `PolicyViolation`.
- **Framework class names are unverified.** The proxy contract is confirmed; the
  exact constructor signatures are checked by a nightly matrix, and an adapter
  that cannot confirm one raises "blocked on verification" rather than guessing.

Not demoed at all, because the SDK raises `NotImplementedError("blocked on
verification")`: Exchange discovery, MCP tool binding, and every provisioning
verb except `validate` and `mock`. Do not add demos for those until the SDK
unblocks them — see [roadmap.md](roadmap.md).
