# Human-made — `agent-framework/`

Microsoft Agent Framework. `donkey.agent_framework.chat_client("…")` builds an `OpenAIChatClient`
(verified against 1.19.0 — the kwarg is `model=`) calls `/responses`. Only
`default_headers` are handed over, so the proxy sees your credentials but the
SDK does not own the transport: **no run id and no `last_call`**.

## Install

```bash
source .venv/bin/activate
python -m pip install -e "../donkey-development-kit/python[llm,local,agent_framework]"
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
| 01 | `basic-gw.py` | live | — |
| 02 | `typed-refusals-live.py` | live | PII policy for the first case |
| 03 | `start-gateway.py` | local simulator | `[local]` |

### 01 — basic-gw

```bash
python "demos/human-made/agent-framework/01 - basic-gw.py"
```

**You should see:** the reply, `total tokens` from Agent Framework's
`usage_details`, and `last_call unavailable …` — the honest answer when the SDK
only supplied headers.

### 02 — typed-refusals-live

```bash
python "demos/human-made/agent-framework/02 - typed-refusals-live.py"
```

Three cases: `PIIDetected` (needs `llm-pii-detection-policy` with `Email`,
action `Reject`), `UpstreamRequestError`, `AuthError`. Agent Framework wraps
the openai error in `ChatClientException`; the response rides on `__cause__`,
so the script calls `classify(err.__cause__.response)`. **You should see:**
`<case> -> <Type> <entities>` or `<case> NO REFUSAL`.

### 03 — start-gateway

```bash
python "demos/human-made/agent-framework/03 - start-gateway.py"
```

No gateway: `start_gateway()` with `pii_block:every=2` over two tickets.
**You should see:** `ok …`, then `refused PIIDetected ['Email']`, then
`requests 2`.

## If something goes wrong

- `TypeError … model_id` — an older Agent Framework; the scripts target the
  1.19.0 `model=` kwarg.
- `last_call unavailable` — expected; see 01.
