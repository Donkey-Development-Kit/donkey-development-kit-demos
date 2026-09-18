# 03 — budget and pacing

**Claim:** the token window is an object, not a header you parse; and you can
refuse to cross your own reserve *before* issuing the request, instead of
recovering from a 429 afterwards.

```bash
make demo N=03
```

**Needs:** nothing (`[llm]` + `[local]`).

**Four acts.** A cold process knowing nothing; the window updating in-band from
each response; `pace(reserve=0.05)` tripping `BudgetReserveReached` before the
request goes out, then `wait_for_reset()` actually sleeping until `reset_at`;
and the terminal 429 if you do cross it.

**Point at:** an unobserved budget reports `None` for every field, never `0` —
because `0` would be a lie that stops an agent that could have run. And
`BudgetReserveReached` is deliberately not a `PolicyViolation`: a refusal is the
gateway saying no and is terminal, this is a local signal you are expected to
recover from.

**Two header shapes, both live-verified.** A successful 200 (with the token-rate
policy applied) carries the window as prose `x-llm-proxy-ratelimit`. The numeric
`x-token-*` trio is verified on the 429. The simulator synthesises a decreasing
window in the prose shape so pacing can be exercised locally; act 3 also observes
a crafted near-exhausted window rather than issuing the ~200 calls it would take
to drain it.

Build guide: `BG §1.3`. See [PRESENTING.md](../../../PRESENTING.md#03--budget-and-pacing).
