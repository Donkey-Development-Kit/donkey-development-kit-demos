# 10 — last_call, routing, and per-call usage

**Claim:** a successful call now answers the same question a refusal already
did — which gateway served this, what it actually routed to, and what it cost —
without parsing headers or needing a span backend.

```bash
make demo N=10
```

**Needs:** nothing (`[llm]` + `[local]`).

**Four acts.** A cold process reporting `UNOBSERVED` rather than `None`; one
governed call populating `donkey.last_call` with the gateway's identity, routing
and usage; the substitution flag lighting up because the captured fixture was
served by a different model than the one we asked for; and
`on_model_substitution="raise"` turning that flag into `ModelSubstituted`.

**Point at:** three honest states, never a bare `None`. `UNOBSERVED` is a cold
read; `OBSERVED` means the SDK saw a response (fields may still be `None` if the
gateway said nothing); `UNAVAILABLE` names the adapter surfaces that never route
through our transport. Then `substituted` — a silent model swap is otherwise
invisible to your cost model and your eval. Then `cached_tokens` /
`reasoning_tokens`: reading only `total_tokens` draws the wrong conclusion about
both cost and latency. An absent count is `None`, never `0`.

`ModelSubstituted` is deliberately not a `PolicyViolation`. The request
succeeded, against a model you did not choose. Same shape as
`BudgetReserveReached`: a client-side signal you opted into.

**Simulator honesty.** The captured happy-path fixture was recorded against
`gpt-5.1`. Asking for a different model id therefore looks like a substitution.
That is the fixture, not a live failover — and it is exactly the mismatch
`last_call` exists to surface. The SDK also never double-retries a `503` the
gateway already marked as a failover.

Build guide: `BG §1.1`. See [PRESENTING.md](../../../PRESENTING.md#10--last_call).
