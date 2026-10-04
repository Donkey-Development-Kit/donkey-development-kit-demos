# Human-made — `adk/`

Google ADK with `donkey.adk.model("…")`, a `LiteLlm` model. LiteLLM calls
the proxy's **`/chat/completions`** route through the SDK's shared client, so
the run id goes on the wire and **`last_call` is observed**. A refusal is typed
in `on_model_error_callback` (see 02).

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
one-sentence answer, `total tokens`, and `last_call observed …`.

### 02 — refusal-live

```bash
python "demos/human-made/adk/02 - refusal-live.py"
```

A PII prompt. LiteLLM re-raises the 403 as its own `APIError`, with the openai
error and its full response on the cause chain. ADK's `Runner` drops that chain,
so an `on_model_error_callback` finds the openai error and raises
`classify(err.response)` where the model call failed. **You should see:**
`PIIDetected ['Email']`. Without the policy it prints `NO REFUSAL`.

## If something goes wrong

- LiteLLM logs a provider-list banner — harmless.
- ADK logs the refusal's traceback before 02 prints the typed error — harmless.
- `404` — the proxy's upstream has no `/chat/completions` route.
