# Human-made — `gemini/`

No Gemini adapter ships, so these are plain `httpx` against a proxy
provisioned **`Format=Gemini`** (e.g. `ddk-gemini-inbound`) with the same
`client_id` / `client_secret` pair. The route is
`<proxy URL>/models/<model>:generateContent`.

## Install

```bash
source .venv/bin/activate
python -m pip install -e "../donkey-development-kit/python[llm]"   # httpx + classify()
```

## Environment

```bash
set -a; source .env.local; set +a
export DONKEY_LLM_PROXY_URL=https://REPLACE-ME.example.invalid/ddk-gemini-inbound/   # overrides the file
```

The model is `gemini-2.5-flash` (the `MODEL` constant).

## Scripts

| # | Script | Gateway |
|---|---|---|
| 01 | `native-generate-content.py` | live, `Format=Gemini` |
| 02 | `openai-shape-rejected.py` | live, `Format=Gemini` |

### 01 — native-generate-content

```bash
python "demos/human-made/gemini/01 - native-generate-content.py"
```

A Gemini-shaped `contents` body. **You should see:** the reply, `total
tokens` from `usageMetadata`, and the proxy's model-based `routing` header.

### 02 — openai-shape-rejected

```bash
python "demos/human-made/gemini/02 - openai-shape-rejected.py"
```

An OpenAI-shaped request (`/chat/completions`) sent to the Gemini proxy. It comes back as
Gemini's error envelope. **You should see:** `UpstreamRequestError`, the HTTP status,
the upstream code and error type, and the message. It is not a policy refusal:
`classify()` types it as a bad request (0.1.0.dev9 and later).

## If something goes wrong

- `404` — the URL points at a `Format=OpenAI` proxy.
- `KeyError: 'candidates'` in 01 — the proxy refused; print `ok.text` to see why.
