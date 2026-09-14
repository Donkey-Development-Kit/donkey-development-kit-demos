# Donkey Development Kit (DDK) — Demos

Runnable demos for the [**Donkey Development Kit (DDK)**](https://github.com/Donkey-Development-Kit/donkey-development-kit).

**Eight of the nine run with no credentials and no gateway**, against the SDK's
local simulator — which replays the same captured responses the SDK's own tests
are written against. So you can clone this, install, and see the whole
governance story in about a minute.

```bash
pip install -e ".[sdk]"     # or point at your own donkey-kit checkout
make offline                # every demo that needs nothing
```

For the per-framework *reference* snippets (one `main.py` per framework,
CI-gated), see [`python/examples/`](https://github.com/Donkey-Development-Kit/donkey-development-kit/tree/main/python/examples)
in the SDK repo. These are the narrative demos.

Presenting one of these? Read **[PRESENTING.md](PRESENTING.md)** — it has the
runbook, the three talk tracks, the failure playbook, and the rules for keeping
credentials off a screen recording.

## The demos

| # | Demo | Shows | Needs |
|---|------|-------|-------|
| 01 | [governed client](demos/claude-made/01_governed_client/) | The two-line ergonomic, and a side-by-side of what the raw client leaves you holding | nothing |
| 02 | [typed refusals](demos/claude-made/02_typed_refusals/) | Seven captured rejection shapes through `classify()`, and why the hierarchy is shaped that way | nothing |
| 03 | [budget and pacing](demos/claude-made/03_budget_and_pacing/) | The token window as an object; `pace(reserve=)` refusing before the request goes out | nothing |
| 04 | [simulating refusals](demos/claude-made/04_simulate_refusals/) | `donkey.simulate()` running the `except` branch that has never executed | nothing |
| 05 | [conformance suite](demos/claude-made/05_conformance/) | `pytest --donkey-conformance` grading a naive agent, then the fixed one | nothing |
| 06 | [telemetry](demos/claude-made/06_telemetry/) | OTel GenAI spans, dual `gen_ai.*` + `donkey.*` attributes, and `donkey.run(id=…)` binding your own id across every call in a run | nothing |
| 07 | [model handles](demos/claude-made/07_model_handles/) | What the SDK does when the platform has no endpoint for what you asked | nothing |
| 08 | [framework objects](demos/claude-made/08_framework_objects/) | One deep adapter, seven at `connection_kwargs()`, no wrappers | nothing |
| 09 | [LangGraph agent](demos/claude-made/09_langgraph_agent/) | A real tool-calling loop, governed end to end | **credentials** |

Every demo takes `--target mock` (default) or `--target live`. Demo 09 is live
only, because LangChain's `ChatOpenAI` calls `/chat/completions` and the
simulator deliberately does not implement a route it has never captured.

## Running them

```bash
make list                   # the table above, from the filesystem
make demo N=03              # one demo
make offline                # all eight offline ones
make doctor                 # what is installed, what will therefore run
make mock                   # simulator in the foreground, for a second pane

DEMO_PAUSE=1 make demo N=03 # pause between acts — use this when presenting
```

`python run.py 03` works too, and each demo is a plain script
(`python demos/claude-made/03_budget_and_pacing/demo.py`) once the repo is installed.

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

This repo is built on the assumption that a demo will be screen-shared,
recorded, and committed to by someone in a hurry. Four things guard that:

- **Output is masked by default.** Every value a demo prints goes through
  `_harness/redact.py`, which masks gateway hostnames, the
  `client_id`/`client_secret` pair, and the tenant identifiers that ride along
  in captured responses (`x-envoy-decorator-operation`, `openai-organization`,
  `cf-ray`). Header *names* are always shown, because which headers the SDK
  injects is the lesson; their values never are. Loopback URLs and
  reserved-for-documentation hostnames pass through unmasked, so a placeholder
  still looks like a placeholder.
- **`DEMO_REDACT=0` announces itself.** Turning masking off prints a warning
  banner in the run context of every demo, so a recording contains proof of
  which mode it was in.
- **No captured traffic is vendored.** Demo 02 loads fixtures from the installed
  SDK (`donkey_kit.simulator.fixtures`) rather than keeping copies here. Live
  captures carry real Anypoint instance and organisation identifiers, and
  `.gitignore` denies `**/_fixtures/`, `*.headers.txt` and `*.body.json` so a
  copy cannot drift back in.
- **`make scan` reads content, not filenames.** `scripts/scan_secrets.py` fails
  on assigned credential values, Anypoint instance ids, bearer tokens, UUIDs and
  non-allowlisted hostnames. `make hooks` installs it as a pre-commit hook.

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

- **Happy-path budget headers are synthesised by the simulator.** `x-token-*` on
  a 200 is not yet confirmed against a real proxy; it is verified on the 429.
  Demo 03 prints that warning itself.
- **Content moderation has no captured shape**, so it falls through to a generic
  `PolicyViolation` and `simulate()` refuses to inject `ContentSafetyBlocked`.
- **Framework class names are unverified.** The proxy contract is confirmed; the
  exact constructor signatures are checked by a nightly matrix, and an adapter
  that cannot confirm one raises "blocked on verification" rather than guessing.

Not demoed at all, because the code raises `NotImplementedError("blocked on
verification")`: Exchange discovery, MCP tool binding, and every provisioning
verb except `validate` and `mock`.
