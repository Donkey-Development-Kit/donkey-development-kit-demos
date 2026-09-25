# Human-made — `adk/`

Google ADK with `donkey.adk.model("…")`, a `LiteLlm` model. LiteLLM calls
**`/chat/completions`, which is not live-verified on the DDK proxies**, and
owns the transport: the credentials go on the wire, but **no run id, no
`last_call`, and no typed refusals**.

## Install

```bash
source .venv/bin/activate
python -m pip install -e "../donkey-development-kit/python[llm,adk]"
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
| 02 | `refusal-live.py` | live | `llm-pii-detection-policy` (`Email`, `Reject`) |

### 01 — basic-gw

```bash
python "demos/human-made/adk/01 - basic-gw.py"
```

One ADK `Agent` run through an `InMemoryRunner`. **You should see:** a
one-sentence answer, `total tokens`, and `last_call unavailable …`.

### 02 — refusal-live

```bash
python "demos/human-made/adk/02 - refusal-live.py"
```

A PII prompt. LiteLLM keeps the status and message but drops the response
headers, so `classify()` has nothing to read. **You should see:** `APIError
403` and the first line of the proxy's message — **not** `PIIDetected`. That
gap is the point of the script. Without the policy it prints `NO REFUSAL`.

## If something goes wrong

- LiteLLM logs a provider-list banner — harmless.
- `404` — the proxy's upstream has no `/chat/completions` route.
