# 08 — native framework objects

**Claim:** no adapter returns a wrapper. `donkey.langgraph.chat_model(...)` hands
back a real `langchain_openai.ChatOpenAI`.

```bash
make demo N=08
```

**Needs:** nothing at all. It constructs objects and makes no network calls, so
it supplies obviously-fake config rather than reading credentials or booting a
simulator it would never send a request to. Frameworks that are not installed are
reported with their exact `pip install` line.

**The roster is deliberately uneven.** LangGraph is the one deep,
conformance-gated adapter. The other seven are supported at `connection_kwargs()`
— the SDK gives you base URL, headers and client configuration, and you pass them
to the framework's own constructor. Name that first; it is much easier to defend
as a decision than to explain as a gap.

**Point at:** `connection_kwargs()` is the *entire supported surface* for seven
of the eight, which makes it the most load-bearing method here, not the least.
LangGraph is the only adapter held to the conformance bar, and it sets
`use_responses_api=True` so `ChatOpenAI` hits the live-verified `/responses`
route. The Agents SDK is the exception that proves the rule: it takes a
pre-built `AsyncOpenAI`, so `donkey.openai_agents.connection_kwargs()` is one
key — `openai_client` — not "no connection_kwargs()". Agent Framework's
`OpenAIChatClient` takes `model=` (verified against 1.19.0) and adds
`policy_middleware()`: a `PolicyViolation` is re-raised, not retried. And
`donkey.openai()` is still the raw client factory; `donkey.openai_agents` is
this adapter.

**Verified for Agent Framework:** `OpenAIChatClient(model=…, base_url, api_key,
default_headers)` against 1.19.0 — the kwarg is `model=`, not `model_id`.
**Not verified:** the other framework class names and constructor kwargs, and
the middleware *protocol* `policy_middleware()` wraps. The proxy contract is
confirmed; remaining signatures are checked by a nightly matrix, and an adapter
that cannot confirm one raises "blocked on verification".

Build guide: `BG §1.8`. See [PRESENTING.md](../../../PRESENTING.md#08--framework-objects).
