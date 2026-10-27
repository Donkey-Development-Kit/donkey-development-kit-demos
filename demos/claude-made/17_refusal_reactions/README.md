# 17 - Refusal Reactions

**Claim:** centralize reactions with `donkey.on(...)`; only a new governed
request can succeed. A handler never grants permission for a refused request.

From the demos worktree root:

```bash
PYTHONPATH="$PWD" .venv/bin/python demos/claude-made/17_refusal_reactions/demo.py
PYTHONPATH="$PWD" .venv/bin/python run.py 17
PYTHONPATH="$PWD" .venv/bin/python "demos/human-made/openai/17 - refusal-handlers.py"
```

Needs `donkey-kit[llm,local,test]`. No credentials or live services. The narrative
starts the SDK's loopback simulator on an ephemeral port and closes it on exit.
The harness's generic offline banner means no external gateway, not no local
listener in this particular story. The short OpenAI companion uses only
in-process `simulate()` and opens no listener. Config is explicit, uses fake
credentials, and does not read `.env` or `Donkey.from_env()`.
The standalone entry point temporarily clears uppercase/lowercase proxy
variables and sets `NO_PROXY=*` before constructing SDK clients, restoring all
values on exit. Donkey exposes no public `trust_env` constructor setting. This
process-wide isolation is for a standalone demo, not concurrent embedded use.

## Acceptance Evidence

- Bounded wait: a captured token-budget refusal with a synthetic 10ms reset
  waits and resends once. Repeated refusal stops at `max_times=1`; a 10ms reset
  beyond `max_wait="1ms"` propagates without resending. The story has a 15-second
  watchdog, a 2-second request timeout, and no long sleeps.
- Resend: `on(PIIDetected).call(...)` revises a copy of the request through
  `RefusalContext.resend(json=...)`. Assertions compare the injected refusal's
  correlation/call IDs with the simulator's received request: same correlation,
  fresh call ID. A second injected refusal still propagates.
- Model fallback: `on(TokenBudgetExceeded).fallback(...)` sends a new request;
  `donkey.last_call.requested_model` asserts the fallback model was requested.
- Escalation: `on(ContentSafetyBlocked).escalate(to=sink.append)` records in a
  local list and still raises, with no resend or external notification.
- No manufactured success: a handler returning a fabricated `httpx.Response(200)`
  still leaves the caller with `PIIDetected`. The successful stories assert a
  separate governed request reached the simulator.
- Custom policy: `DemoExportBlocked` defines its own remediation and synthetic
  discriminator. `classify.register(...)` types it through the actual OpenAI
  client under `donkey.run()`. `finally` calls `classify.unregister(...)` and
  asserts the original registry was restored.
- Scope: two Donkeys share the process-wide classifier, but only the Donkey
  with a registered reaction escalates. Both raise the custom typed refusal.

The reset overrides and custom-policy shape are **synthetic demo inputs**, not
live captures or newly verified platform contracts. The simulator evaluates
scripted outcomes, not prompt safety; revising a body is application behavior,
not a replacement PII policy. A fallback name is local illustrative configuration,
not a claim that a real proxy routes it. Registrations affect all clients in the
process and should be installed deliberately and removed when temporary.

SDK research: `tests/unit/test_refusal_handlers.py`,
`tests/unit/test_classifier.py`; `BG §2.1`, `BG §2.2`.
