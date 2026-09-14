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

**Three acts.** The governed client and its injected headers; one call, plus the
budget/correlation/span it updated on the way past; then the same PII refusal
through a stock `openai` client and through this one, side by side.

**Point at:** the base URL has no `/v1`, and auth is a `client_id`/`client_secret`
header pair rather than a bearer token. Both are live-verified details that
people get wrong from first principles.

**Expect:** against the simulator the reply is a captured response and will not
answer the prompt. The demo prints a warning saying so; read it aloud.

Build guide: `BG §1.1`. See [PRESENTING.md](../../../PRESENTING.md#01--governed-client).
