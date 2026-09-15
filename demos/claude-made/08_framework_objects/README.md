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
route. And `donkey.openai_agents` is the OpenAI Agents SDK adapter —
`donkey.openai()` is the raw client factory and got the good name.

**Not verified:** the exact framework class names and constructor kwargs. The
proxy contract is confirmed; the signatures are checked by a nightly matrix, and
an adapter that cannot confirm one raises "blocked on verification".

Build guide: `BG §1.8`. See [PRESENTING.md](../../../PRESENTING.md#08--framework-objects).
