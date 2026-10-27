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
| 04 | `approvals.py` | none (scripted model) | `[openai-agents]`; no proxy variables |
| 05 | `governed-observations.py` | none (MockTransport + conformance) | `[llm,openai-agents,test]` |

### 01 — agent-and-tool

```bash
python "demos/human-made/openai-agents/01 - agent-and-tool.py"
```

An `Agent` with one `@function_tool` (`get_weather`) run by `Runner.run` inside
`donkey.run(...)`. **Live only**: the simulator never decides to call tools.
It prints the answer, call count, framework usage and `last_call` status. First
turns and streamed runs use Runner's task; later non-streamed turns can reach the
caller. Do not promise blanket post-run visibility; observe in `on_llm_end` (05).

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

### 04 - approvals

```bash
python "demos/human-made/openai-agents/04 - approvals.py"
```

A scripted `Model` asks for a refund through real `Agent`/`Runner` and the DDK
`function_tool` integration. Pending approval precedes the effect. `RunState`
is serialized/deserialized before approve/reject and resume. Approval runs once;
rejection runs none and supplies its message as a function-call output to the
model. Tracing is disabled; no config files or credentials are read.
This is advisory approval, not a policy refusal, authenticated reviewer service
or gateway authorization. Serialization alone is not a durable approval store.

### 05 - governed-observations

```bash
python -m pip install -e "../donkey-development-kit/python[llm,openai-agents,test]"
python "demos/human-made/openai-agents/05 - governed-observations.py"
```

A customer-style agent runs real conformance with explicit local configuration.
Then actual Runner one-turn and tool-loop calls use synthetic chat completions
through MockTransport. `on_llm_end` sees each task-local record and usage. The
one-turn caller stays unobserved; the later non-streamed tool-loop answer reaches
the caller. No live model, provider trace export or credential reads. Observation
hooks are not the typed-refusal boundary; `donkey.run()` is.

## If something goes wrong

- `ModuleNotFoundError: agents` — install the `[openai-agents]` extra.
- `last_call` differs after 01: task ownership depends on the execution path;
  see 05 rather than assuming a single post-run status.
