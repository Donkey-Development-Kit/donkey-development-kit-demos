# Human-made — `langgraph/`

`donkey.langgraph("…")` returns a real `langchain_openai.ChatOpenAI`
with `use_responses_api=True`, so calls go to the live-verified `/responses`
route. This is the one deep, conformance-gated adapter.

## Install

```bash
source .venv/bin/activate
python -m pip install -e "../donkey-development-kit/python[llm,local,langgraph]" "langchain>=1.0"
python -m pip install -e "../donkey-development-kit/python[otel]"   # 06 only
```

`langchain>=1.0` provides `create_agent` (05, 09); it is not part of any
donkey-kit extra.

## Environment

```bash
set -a; source .env.local; set +a       # DONKEY_LLM_PROXY_URL / _CLIENT_ID / _CLIENT_SECRET
```

Change `"gpt-4o"` / `MODEL` to a model your proxy routes (the provisioned DDK
proxies route `gpt-5-mini`).

**Async only.** The governed transport is `ChatOpenAI`'s `http_async_client`,
so every gateway script uses `ainvoke` / `astream`. A sync `.invoke()` would
bypass governance.

## Scripts

| # | Script | Gateway | Extra needs |
|---|---|---|---|
| 01 | `basic-no-gw.py` | none — api.openai.com | `OPENAI_API_KEY` |
| 02 | `basic-gw.py` | live | — |
| 03 | `typed-refusals-simulated.py` | none (in-process) | any `DONKEY_LLM_PROXY_*` values |
| 04 | `typed-refusals-live.py` | live | PII policy for the first case |
| 05 | `agent-and-tool.py` | live only | `langchain>=1.0` |
| 06 | `otel exporter simple.py` | live | `[otel]`, OTLP endpoint |
| 07 | `streaming.py` | live only | — |
| 08 | `gateway-unavailable.py` | none (closed port) | — |
| 09 | `start-gateway.py` | local simulator | `[local]`, `langchain>=1.0` |

### 01 — basic-no-gw

```bash
export OPENAI_API_KEY=…
python "demos/human-made/langgraph/01 - basic-no-gw.py"
```

Stock `ChatOpenAI`, no gateway. **You should see:** a three-word greeting.

### 02 — basic-gw

```bash
python "demos/human-made/langgraph/02 - basic-gw.py"
```

**You should see:** the reply, `model_name`, LangChain's `usage` dict, and
`last_call unobserved`. That last line is expected: LangChain drives the call
on its own task, so the SDK's per-task `last_call` never sees it. Use
`usage_metadata` instead.

### 03 — typed-refusals-simulated

```bash
python "demos/human-made/langgraph/03 - typed-refusals-simulated.py"
```

`donkey.simulate(...)` replays five captured refusals; `typed_refusals()`
re-raises each out of LangChain as the SDK type. **You should see:** one line
per refusal — type, policy, correlation id.

### 04 — typed-refusals-live

```bash
python "demos/human-made/langgraph/04 - typed-refusals-live.py"
```

Three cases: `PIIDetected` (needs `llm-pii-detection-policy` with `Email`,
action `Reject`), `UpstreamRequestError` (a model that does not exist) and
`AuthError` (deliberately wrong credentials). **You should see:** `<case> ->
<Type> <policy> <entities>` per case, or `<case> NO REFUSAL` when the policy is
not applied.

### 05 — agent-and-tool

```bash
python "demos/human-made/langgraph/05 - agent-and-tool.py"
```

`create_agent` with one `@donkey.tool` (`lookup_sku`) inside `donkey.run(...)`.
**Live only** — the simulator replays one completion and never decides to call
a tool. **You should see:** `run id`, then `tool sees run id` with the **same**
id (LangGraph copies the context into every node), the final answer and the
message count.

### 06 — otel exporter simple

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=https://<collector>   OTEL_EXPORTER_OTLP_HEADERS=…
python "demos/human-made/langgraph/06 - otel exporter simple.py"
```

The host owns the `TracerProvider`; Donkey rides it. **You should see:** two
replies locally and two spans with one correlation id in the collector.

### 07 — streaming

```bash
python "demos/human-made/langgraph/07 - streaming.py"
```

`astream` chunks joined, then usage from the terminal event. **Live only** —
the simulator's truncated SSE is rejected by `ChatOpenAI`. **You should see:**
the reply and a `usage` dict.

### 08 — gateway-unavailable

```bash
python "demos/human-made/langgraph/08 - gateway-unavailable.py"
```

A governed model aimed at `127.0.0.1:9`, where nothing listens. LangChain
wraps openai's `APIConnectionError`, so `GatewayUnavailable` is two causes
down. **You should see:** `raised APIConnectionError`, `cause
GatewayUnavailable`, the base URL and the remediation text.

### 09 — start-gateway

```bash
python "demos/human-made/langgraph/09 - start-gateway.py"
```

`start_gateway()` with `pii_block:every=2`, driving a `create_agent` loop over
two tickets. **You should see:** `ok …` for the first, `refused PIIDetected
['Email']` for the second, then `requests 2`.

## If something goes wrong

- `ModuleNotFoundError: langchain.agents` — install `langchain>=1.0`.
- `last_call unobserved` — expected with LangChain; see 02.
- `ConfigError … llm_proxy_url` — the variables are not exported in this shell.
- 07 fails against the simulator — expected; it is live only.
