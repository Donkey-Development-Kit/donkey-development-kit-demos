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

Build guide: `BG §1.1`. See [PRESENTING.md](../../../PRESENTING.md#01--governed-client).
