# 01 — the governed client

**Claim:** reaching the gateway is easy and the SDK does not pretend otherwise.
What it sells is the single point every request passes through, and the things
that can therefore attach to it.

```bash
make demo N=01                 # offline, against the local simulator
make demo N=01 ARGS="--target live"
```

**Needs:** nothing (`[llm]` + `[local]`). Act 3 against `--target live` additionally
needs the PII-detection policy applied with `Email` among its entities and its action
set to `Reject` — the default action is `Log`, which does not block.

**Four acts.** The governed client and its injected headers (async by default,
`sync=True` for a blocking `OpenAI`); one call, plus the budget / last_call /
correlation / span it updated on the way past; the same PII refusal through
a stock `openai` client and through this one, side by side; then the one-line
on-ramps — `@donkey.governed` wrapping a handler in `donkey.run()`, and
`@donkey.tool` recording a callable without wrapping it (a missing docstring is
rejected at decoration time). `last_call` is the success-path counterpart to a
typed refusal — demo 10 walks the whole record.

**Point at:** the base URL has no `/v1`, and default auth (`llm_proxy_auth='client-id'`)
is a `client_id`/`client_secret` header pair rather than a bearer token. The
parallel model-wallet JWT ingress is [demo 13](../13_jwt_wallet/). Act 4: there
is no `id=` on `@donkey.governed` on purpose, and `@donkey.tool` returns the
same function.

**Expect:** against the simulator the reply is a captured response and will not
answer the prompt. The demo prints a warning saying so; read it aloud.

## How to run

**Simulator or live.** Defaults to the local simulator; `--target live` uses `DONKEY_LLM_PROXY_*` from your shell or `.env.local`.

**1. Set up once** (from the repo root):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
python -m pip install -e "../donkey-development-kit/python[llm,local]"   # or: python -m pip install -e ".[sdk]"
make doctor                    # what is installed; prints no secrets
```

**2. Run it:**

```bash
make demo N=01                              # local simulator, auto-started
make demo N=01 ARGS="--target live"         # your proxy
python run.py 01                           # same thing without make
```

Live runs read three variables from your shell or a git-ignored `.env.local`
(see [Setup](../../../README.md#setup) for where the values come from):

```bash
cp .env.example .env.local     # then fill in:
# DONKEY_LLM_PROXY_URL=https://REPLACE-ME.example.invalid/REPLACE-ME/   (trailing /, no /v1)
# DONKEY_LLM_PROXY_CLIENT_ID=…
# DONKEY_LLM_PROXY_CLIENT_SECRET=…
```

**Live note:** Act 3 only refuses live if the PII-detection policy is applied with `Email` and action `Reject`; otherwise it reports no refusal.

**3. What you should see:**

1. `Run context` — target `mock`, masked base URL, masking on.
2. A warning that the simulator reply is a captured response and will not answer the prompt.
3. Act 1: the governed `AsyncOpenAI` and the headers injected on it, then the blocking `sync=True` twin.
4. Act 2: one call, then the budget, `last_call`, correlation id and span it updated.
5. Act 3: the same PII 403 through a stock `openai` client (a raw error) and through this one (`PIIDetected`).
6. Act 4: `@donkey.governed` and `@donkey.tool`, including a tool rejected for having no docstring.
7. `The point`.

**4. If something goes wrong:**

- `No simulator at http://127.0.0.1:8080` — the port is taken or `[local]` is missing. Use another port: `DEMO_MOCK_URL=http://127.0.0.1:8099 make demo N=01`.
- Want the simulator in its own pane? Run `make mock` there, then `make demo N=01 ARGS="--no-autostart"`. `DEMO_QUIET_MOCK=0` shows its log.
- `Missing prerequisites` — the demo names the module and the `pip install` line; it exits 0 without running anything.
- `The demo raised` — re-run with `DEMO_TRACEBACK=1` for the full, still-masked traceback.
- Presenting? `DEMO_PAUSE=1` waits for Enter between acts. Leave `DEMO_REDACT` unset (masking on) when recording.

Build guide: `BG §1.1`. See [PRESENTING.md](../../../PRESENTING.md#01--governed-client).
