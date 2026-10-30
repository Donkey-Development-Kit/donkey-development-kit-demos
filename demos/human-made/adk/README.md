# Human-made — `adk/`

Google ADK with `donkey.adk.model("…")`, a `LiteLlm` model. LiteLLM calls
the proxy's **`/chat/completions`** route through the SDK's shared client, so
the run id goes on the wire. ADK's `Runner` runs the agent in a task of its
own, so **`last_call` is observed in `after_model_callback`** and reads
`unobserved` once the run returns (see 01). A refusal is typed in
`on_model_error_callback` (see 02).

## Install

```bash
python3.12 -m venv .venv-adk
source .venv-adk/bin/activate
python -m pip install -e "../donkey-development-kit/python[llm,adk]"
```

Use a separate Python 3.12 environment. The new native scripts were locally tested
there, not in the default Python 3.15 environment. ADK is a separate optional
extra, not part of the core `[full]` narrative install.

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
| 03 | `approvals.py` | none (scripted BaseLlm) | `[adk]`; no proxy variables |
| 04 | `bridged-observations.py` | none (scripted SSE MockTransport) | `[llm,adk]`; no proxy variables |

### 01 — basic-gw

```bash
python "demos/human-made/adk/01 - basic-gw.py"
```

One ADK `Agent` run through an `InMemoryRunner`. **You should see:** a
one-sentence answer, `total tokens`, `last_call observed <model> (in
after_model_callback)` and `after run unobserved (Runner's task)`.

### 02 — refusal-live

```bash
python "demos/human-made/adk/02 - refusal-live.py"
```

A PII prompt. LiteLLM re-raises the 403 as its own `APIError`, with the openai
error and its full response on the cause chain. ADK's `Runner` drops that chain,
so an `on_model_error_callback` finds the openai error and raises
`classify(err.response)` where the model call failed. **You should see:**
`PIIDetected ['Email']`. Without the policy it prints `NO REFUSAL`.

### 03 - approvals

```bash
python "demos/human-made/adk/03 - approvals.py"
```

A scripted `BaseLlm` requests a refund through real `App`, `Runner` and
`approval_plugin()`. Pending confirmation precedes the effect. Approve executes
once; reject returns an error function response without an effect. Replaying
the decision must not execute again. Sessions are in memory; no credentials or
live calls. This is advisory confirmation, not gateway authorization, an
authenticated approver service, restart durability or a production queue.

### 04 - bridged-observations

```bash
python "demos/human-made/adk/04 - bridged-observations.py"
```

Real streamed ADK runs compare `donkey.adk.model()` with hand-built
`last_call_bridged(LiteLlm)` using governed connection kwargs. Scripted local SSE
lets callbacks observe request IDs; partial responses have unknown usage and the
complete response has usage. The caller stays unobserved because the flow owns
its task. No credential reads or live calls.

`last_call_bridged` bridges observation, not typed refusals. `donkey.run()` or
`typed_refusals()` remains the separate refusal boundary. This complete scripted
stream does not change the default simulator's truncated-stream limitations.

## If something goes wrong

- LiteLLM logs a provider-list banner — harmless.
- ADK logs the refusal's traceback before 02 prints the typed error — harmless.
- `404` — the proxy's upstream has no `/chat/completions` route.
