# 18 - Terminal Kill Handling

**Claim:** consume the platform's kill decision, wake a budget waiter, and stop
paced batch work. Do not retry or attempt a local recovery from `AgentKilled`.

From the demos worktree root:

```bash
PYTHONPATH="$PWD" .venv/bin/python demos/claude-made/18_kill_switch/demo.py
PYTHONPATH="$PWD" .venv/bin/python run.py 18
```

Needs `donkey-kit[llm,local]` for OpenAI and fixture injection. Entirely in-process:
no listener, credentials, live model, control-plane operation, or `.env` lookup.
The explicit proxy URL is a reserved `.invalid` address; every model call is
inside `donkey.simulate(AgentKilled)` and returns the SDK's refusal fixture.

## Acceptance Evidence

- Inject `AgentKilled` with `donkey.simulate()` and make a real governed OpenAI
  Responses call inside `donkey.run(id="killed-batch")`. Assert the typed error's
  correlation and call IDs.
- Observe an exhausted synthetic token window resetting an hour later. The batch
  trips `BudgetReserveReached` before any effect and enters `wait_for_reset()`.
  An `asyncio.Event` signals before that await; because setting the event does
  not yield, the batch reaches its first wait suspension before the main task
  resumes. No private budget state is inspected.
- Injecting the kill on the same Donkey wakes that already-waiting task with
  `AgentKilled` within a one-second watchdog, not the one-hour reset.
- After the simulation context exits, subsequent `pace()` and `wait_for_reset()`
  on the same budget both raise. Assert the batch-effect list remains empty.
- `on(PolicyViolation).call(...)` never receives the kill. Registering
  `on(AgentKilled)` itself raises `TypeError`, so generic or specific recovery
  cannot lift the decision.

All task waits are bounded; the story has a five-second outer watchdog and
cancels/drains its worker on every exit. The hour is a synthetic observation,
not an actual sleep. There are no SDK clock patches or private reach-ins.

This **consumes**, rather than administers, the platform kill switch. The latch
guards budget pacing and reset waits; it does not prohibit every arbitrary HTTP
request or implement a process-wide network firewall. An ungated request is
still judged by the gateway. No live verification status changes.

SDK research: `tests/unit/test_kill_switch.py`,
`tests/unit/test_refusal_handlers.py`; `BG §2.6`.
