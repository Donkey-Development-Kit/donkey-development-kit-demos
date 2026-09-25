# Human-made — `openai-agents/`

The OpenAI Agents SDK. The agent is given
`OpenAIResponsesModel(model=…, **donkey.openai_agents.connection_kwargs())`.
`connection_kwargs()` is one key, `openai_client`, a governed `AsyncOpenAI`.
That keeps the agent on the live-verified `/responses` route.
`donkey.openai_agents.model()` builds a chat-completions model instead.

## Install

```bash
source .venv/bin/activate
python -m pip install -e "../donkey-development-kit/python[llm,local,openai-agents]"
```

## Environment

```bash
set -a; source .env.local; set +a       # DONKEY_LLM_PROXY_URL / _CLIENT_ID / _CLIENT_SECRET
```

Change `"gpt-4o"` to a model your proxy routes (the provisioned DDK proxies
route `gpt-5-mini`).

## Scripts

| # | Script | Gateway | Extra needs |
|---|---|---|---|
| 01 | `agent-and-tool.py` | live only | — |
| 02 | `typed-refusals-simulated.py` | none (in-process) | any `DONKEY_LLM_PROXY_*` values |
| 03 | `start-gateway.py` | local simulator | `[local]` |

### 01 — agent-and-tool

```bash
python "demos/human-made/openai-agents/01 - agent-and-tool.py"
```

An `Agent` with one `@function_tool` (`get_weather`) run by `Runner.run` inside
`donkey.run(...)`. **Live only** — the simulator never calls tools. **You
should see:** the final answer, `model calls 2` (tool call plus answer), total
tokens from the Agents SDK's own usage, and `last_call unobserved`. The runner
calls the model on its own task, so trust the SDK usage line here.

### 02 — typed-refusals-simulated

```bash
python "demos/human-made/openai-agents/02 - typed-refusals-simulated.py"
```

Five simulated refusals through `Runner.run`. The runner re-raises the openai
error unchanged, so `classify()` types it. **You should see:** one line per
refusal — type, policy, correlation id.

### 03 — start-gateway

```bash
python "demos/human-made/openai-agents/03 - start-gateway.py"
```

No gateway, no credentials: `start_gateway()` with `pii_block:every=2` over
two tickets. **You should see:** `ok …` for the first, `refused PIIDetected
['Email']` for the second, then `requests 2`.

## If something goes wrong

- `ModuleNotFoundError: agents` — install the `[openai-agents]` extra.
- `last_call unobserved` in 01 — expected; the runner owns the task.
