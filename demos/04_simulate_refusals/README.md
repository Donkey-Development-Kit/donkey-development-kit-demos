# 04 — simulating refusals in-process

**Claim:** the `except PIIDetected:` branch in your agent has never executed, and
this is how it gets to.

```bash
make demo N=04
```

**Needs:** nothing (`[llm]` + `[local]`). The LangGraph act runs only if
`[langgraph]` is installed and is skipped silently otherwise.

**Six acts.** The happy path being all you normally exercise; one context manager
running the refusal branch; each refusal type in one line; `times=` counting
calls and normal service resuming; the refusal it *refuses* to fake; and the same
injection working through LangChain's own `ChatOpenAI`.

**Point at:** `donkey.simulate(ContentSafetyBlocked)` raising `ValueError`. The
content-moderation shape has not been captured, so injecting a plausible body
would let you write a handler against a body that does not exist. And act 6 —
the injection sits on the transport, which is why it reaches a framework object
the SDK does not wrap.

**Why it matters:** this needs no gateway, so it belongs in your unit tests
rather than in a manual pre-release checklist.

Build guide: `BG §1.5`. See [PRESENTING.md](../../PRESENTING.md#04--simulate).
