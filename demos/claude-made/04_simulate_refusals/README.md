# 04 — simulating refusals in-process

**Claim:** the `except PIIDetected:` branch in your agent has never executed, and
this is how it gets to.

```bash
make demo N=04
```

**Needs:** nothing (`[llm]` + `[local]`). The LangGraph act runs only if
`[langgraph]` is installed and is skipped silently otherwise.

**Eight acts.** The happy path being all you normally exercise; one context
manager running the refusal branch; each refusal type in one line (PII, token
budget, prompt-injection, Azure content-safety); `times=` counting calls and
normal service resuming; what `simulate()` actually injects versus what it
refuses to fake (`ToolInvocationError`, `GatewayUnavailable`); the same
injection working through LangChain's own `ChatOpenAI`; `donkey mock --scenario`
scripting the running simulator; and `start_gateway()` — a real port, a stock
httpx client, `requests_received`, and a spy that redacts `client_secret`.

**Point at:** `donkey.simulate(ContentSafetyBlocked)` injecting the
live-captured Azure content-safety fixture — the branch runs, categories and
all. Then `simulate(PromptInjectionBlocked)`: that maps to the documented
`injection-protection` representative (`x-injection-protection: blocked`),
**not** the live-verified regex-prompt-guard. Walk regex in demo 02;
`simulate()` picks one fixture per exception type. Then act 5's last beats,
where `ToolInvocationError` still raises `ValueError`: that is not a gateway
refusal and has no captured wire shape, so injecting a plausible body would let
you write a handler against a body that does not exist. `GatewayUnavailable` is
the same refusal-to-fake for a different reason: there is no HTTP response, so
there is nothing to replay. And act 6 — the
injection sits on the transport, which is why it reaches a framework object the
SDK does not wrap. Act 7 is the other half: `donkey mock --scenario` scripts
the running simulator (PII every Nth call, injection on a substring, a real
wall-clock budget window) so a stock client with no SDK in the process sees
the same fixtures. Act 8 is that idea as a pytest-shaped object:
`start_gateway()` binds an ephemeral port; `set_scenarios("pii_block:every=1")`
arms it live; the spy records the request with `client_secret` already `***`.

**Why it matters:** this needs no gateway, so it belongs in your unit tests
rather than in a manual pre-release checklist.

Build guide: `BG §1.5`. See [PRESENTING.md](../../../PRESENTING.md#04--simulate).
