# Human-made — `llamaindex/`

LlamaIndex `donkey.llamaindex.llm("…")` (an `OpenAILike`). The
adapter sets `is_chat_model=True` (the default `False` hits `/completions`), so
calls go to **`/chat/completions`, which is not live-verified on the DDK
proxies**. Only `default_headers` are handed over: **no run id and no
`last_call`**.

## Install

```bash
source .venv/bin/activate
python -m pip install -e "../donkey-development-kit/python[llm,llamaindex]"
```

## Environment

```bash
set -a; source .env.local; set +a       # DONKEY_LLM_PROXY_URL / _CLIENT_ID / _CLIENT_SECRET
```

Change `"gpt-4o"` to a model your proxy routes.

## Scripts

| # | Script | Gateway | Extra needs |
|---|---|---|---|
| 01 | `basic-gw.py` | live | — |
| 02 | `typed-refusals-live.py` | live | PII policy for the first case |

### 01 — basic-gw

```bash
python "demos/human-made/llamaindex/01 - basic-gw.py"
```

`complete(...)` then `chat(...)`. **You should see:** two greetings, `total
tokens`, and `last_call unavailable …`.

### 02 — typed-refusals-live

```bash
python "demos/human-made/llamaindex/02 - typed-refusals-live.py"
```

Three cases: `PIIDetected` (needs `llm-pii-detection-policy` with `Email`,
action `Reject`), `UpstreamRequestError`, `AuthError`. `OpenAILike` re-raises
the openai error unchanged, so `classify()` types it. **You should see:**
`<case> -> <Type> <entities>` or `<case> NO REFUSAL`.

## If something goes wrong

- `404 … /completions` — `is_chat_model` was overridden to `False`.
- `404 … /chat/completions` — the proxy's upstream has no chat route.
