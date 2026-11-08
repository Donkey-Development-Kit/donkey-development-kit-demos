# 24 — outbound A2A

**Claim:** `donkey.a2a.send()` and `stream()` delegate to a governed agent by
Exchange reference using the official `a2a-sdk`. A gateway refusal of that call
raises the same typed exceptions as a model call, and each delegation is one
`donkey.a2a.call` span with no refusal diagnostics.

```bash
make demo N=24
```

**Needs:** `donkey-kit[a2a,otel]`, SDK 0.2.1 or later. No gateway, no Exchange,
no credentials: `donkey.simulate_a2a()` declares the agent and replays the
packaged Omni Gateway captures.

**Four acts.**

1. The tracing gate: with `OTEL_INSTRUMENTATION_A2A_SDK_ENABLED` unset, the
   first call is a `ConfigError` before any request. This runs in a fresh child
   process because the SDK reads the variable when `a2a` is imported.
2. `send()` returns an SDK `SendMessageResponse`, and `stream()` yields
   `StreamResponse` items inside `async with`. `reply=` answers the calls that are
   not injected. An undeclared ref is a `RegistryError` and sends nothing.
3. Captured refusals, v1.0 and v0.3: Azure prompt shield is
   `ContentSafetyBlocked`, and token rate limiting is `TokenBudgetExceeded` with
   `retry_after`. PII stays a generic `ToolInvocationError`, and the echoed
   address is absent from the exception text.
4. One CLIENT span per delegation: `error.type` only on failure, no message, no
   exception event, no echoed value.

**Point at:** the call site needs no A2A-specific error handling. It catches the
same `PolicyViolation` subclasses the model client raises.

**Boundary.** These are replayed request-phase captures. Successful gateway
send and SSE are **not live-verified**, and `donkey.a2a` and `simulate_a2a()`
are **Provisional**. `GatewayAuthRequired` (v0.3 In-Task Authorization) is typed
by the SDK but has no packaged capture, so it is described, not run. Quality
Evaluation span attributes come only from successful gateway replies, so this
demo does not show them. Framework-native `as_tool()` is still planned. For the
inbound side, use `donkey dev` (see demo 21).

## How to run

```bash
python -m pip install -e "../donkey-development-kit/python[a2a,otel]"
make demo N=24
```

**What you should see:** fourteen `PASS` lines.

**If something goes wrong:**

- `Missing prerequisites`: install the line above.
- `AttributeError` on `simulate_a2a`: your SDK is older than 0.2.1.
- `needs a fresh process`: another OTel provider is installed. Run the demo on its own.
- `The demo raised`: re-run with `DEMO_TRACEBACK=1`.

Docs: [Outbound A2A](https://docs.donkey-kit.dev/tool-access/a2a).
Build guide: `BG §1.5`. See [PRESENTING.md](../../../PRESENTING.md#24---outbound-a2a).
