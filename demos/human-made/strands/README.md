# Human-made — `strands/`

Strands Agents with `OpenAIModel(client=donkey.openai(), model_id=…)`. The
calls go to **`/chat/completions`, which is not live-verified on the DDK
proxies** (`/responses` is). Because the governed client is passed in, the SDK
owns the transport: run id, `last_call` and typed refusals all work.

**Why not `donkey.strands.model()`:** Strands opens and closes an OpenAI client
per request from `client_args`. That closes the shared transport after the
first call, so the second fails with "client has been closed". A pre-built
`client=` is reused and left open.

## Install

```bash
source .venv/bin/activate
python -m pip install -e "../donkey-development-kit/python[llm]" "strands-agents[openai]"
```

## Environment

```bash
set -a; source .env.local; set +a       # DONKEY_LLM_PROXY_URL / _CLIENT_ID / _CLIENT_SECRET
```

Change `"gpt-4o"` to a model your proxy routes (the provisioned DDK proxies
route `gpt-5-mini`), and use a proxy whose upstream serves
`/chat/completions`.

## Scripts

| # | Script | Gateway | Extra needs |
|---|---|---|---|
| 01 | `basic-gw.py` | live | — |
| 02 | `agent-and-tool.py` | live only | — |
| 03 | `typed-refusals-simulated.py` | none (in-process) | any `DONKEY_LLM_PROXY_*` values |
| 04 | `typed-refusals-live.py` | live | PII policy for the first case |

### 01 — basic-gw

```bash
python "demos/human-made/strands/01 - basic-gw.py"
```

**You should see:** a one-sentence answer, Strands' accumulated usage, then
`status observed` and the served model.

### 02 — agent-and-tool

```bash
python "demos/human-made/strands/02 - agent-and-tool.py"
```

One `@tool` + `@donkey.tool` (`lookup_sku`) inside `donkey.run(...)`. **Live
only.** **You should see:** `tool sees run id <id>`, the answer, `model calls
2`, and `last_call observed <model>`.

### 03 — typed-refusals-simulated

```bash
python "demos/human-made/strands/03 - typed-refusals-simulated.py"
```

**You should see:** `PIIDetected`, `PromptInjectionBlocked` and
`ContentSafetyBlocked`, each with policy and correlation
id. `TokenBudgetExceeded` is deliberately absent: Strands retries a 429 itself
(`ModelThrottledException`), so the one simulated 429 is absorbed and the
retry succeeds.

### 04 — typed-refusals-live

```bash
python "demos/human-made/strands/04 - typed-refusals-live.py"
```

Three cases: `PIIDetected` (needs `llm-pii-detection-policy` with `Email`,
action `Reject`), `UpstreamRequestError`, `AuthError`. **You should see:**
`<case> -> <Type> <entities>` or `<case> NO REFUSAL`.

## If something goes wrong

- `ModuleNotFoundError: strands.models.openai` — install `strands-agents[openai]`.
- `404` on every call — the proxy's upstream has no `/chat/completions` route.
- A live 429 takes a while to surface — Strands is retrying it.
