# 19 - Tool Approvals

**Claim:** a required approval prevents a premature local side effect; native
LangGraph checkpoints hold a resumable pause. Approval never overrides gateway
governance.

From the demos worktree root:

```bash
PYTHONPATH="$PWD" .venv/bin/python demos/claude-made/19_tool_approvals/demo.py
PYTHONPATH="$PWD" .venv/bin/python run.py 19
PYTHONPATH="$PWD" .venv/bin/python "demos/human-made/langgraph/10 - tool-approvals.py"
```

Needs `donkey-kit[llm,local,langgraph,otel]`. No live operations, model generation,
credentials, listener, or environment-loaded proxy configuration. The graph
chooses its tool deterministically. Its only model request is a governed OpenAI
call inside `donkey.simulate(PIIDetected)`, targeting an explicit reserved
`.invalid` URL. In-memory OTel is installed by this standalone demo process;
`telemetry=False` prevents environment-driven OTLP export, while SDK approval
events use the host's in-memory provider. Run in a fresh process, not a notebook
that already owns the global OTel provider. The entry point rejects an existing
concrete provider before any approval operations and confirms its own provider
was installed; it never silently exports approval audit to a host exporter.

## Acceptance Evidence

- `@donkey.tool(approval="required", risk="financial")` raises
  `ApprovalRequired` and appears in `donkey.approvals.pending()` with zero effects.
- `resolve(..., approved_by=...)` executes exactly once under the original
  correlation; resolving twice raises `KeyError`. `reject(..., rejected_by=...)`
  removes a pending call without effects. Base rejection returns the approval,
  rather than raising `ApprovalRejected`.
- A separate `approval_timeout="10ms"` tool is observed through public
  `Approval.expired`, yielding with `asyncio.sleep(0)` under a one-second bound.
  Resolving after expiry raises `ApprovalTimedOut` without running the tool.
  The story has a fifteen-second watchdog, with no long sleeps or SDK clock patch.
- Native `interrupt()` is reached through the decorator's SDK LangGraph hook.
  Assert `__interrupt__`, `APPROVAL_INTERRUPT`, and the saved graph task's
  interrupts. Recompile with the same `MemorySaver`, then use
  `Command(resume={"approved": True, "by": ...})` to execute once.
  A separate rejected thread raises native `ApprovalRejected` without effects.
- Twelve actual in-memory `donkey.tool.approval` spans join six pending/decision
  pairs by approval ID and correlation. Assertions check the reviewer identity
  on approved/rejected events and that serialized spans contain neither the
  private argument sentinel nor an arguments attribute. Only counts are printed.
- A separately checkpointed summary tool is approved, then its governed model
  call raises simulated `PIIDetected`. The post-request effect never runs and
  the refusal retains the approval run's correlation.

## Persistence And Timeouts

`donkey.approvals` is **process-global memory**, shared across Donkeys. A restart
forgets pending calls. Expiry is lazy: `pending()` sweeps expired entries;
`resolve()`/`reject()` raise `ApprovalTimedOut` if the entry still exists but is
expired. If it was already swept, lookup raises `KeyError` instead. This demo
resolves the expired entry before a sweep so the typed timeout is explicit.

Native LangGraph pauses use the framework checkpointer, not that registry, and
**DDK `approval_timeout` does not apply**. Their pending span has no expiry.
The framework/application must define cancellation and stale-decision policy.
The copyable companion explicitly declares a short timeout to illustrate that
the native path still has no DDK expiry.

`MemorySaver` demonstrates checkpoint ownership and recompilation only, **not
restart durability**. Use a durable LangGraph checkpointer to survive a process
restart. No durable storage or restart test is claimed here. Nodes replay on
resume, so keep side effects after the gated call (or make replayed work
idempotent). Tool arguments are absent from spans but **present in approval and
checkpoint/interrupt payloads**; protect access to those stores and approver
interfaces. Reviewer names are illustrative audit metadata, not authentication.

These are advisory local approvals, not a platform approval service, queue, UI,
or gateway step-up implementation. No SDK or live verification status changes.

SDK research: `tests/unit/test_approvals.py`,
`tests/unit/test_langgraph_approvals.py`; `BG §2.3`.
