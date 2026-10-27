# 03 - Gateway Budgets and Observe-Only Provider Quotas

Issue #59: distinguish the gateway's consumer window from the routed provider
key's shared quota. No external calls, dotenv reads or real secrets.

```bash
.venv/bin/python demos/claude-made/03_budget_and_pacing/demo.py
```

Requires SDK `[llm,test]`. Offline `_harness.preflight.cli` checks prerequisites,
states masking, and contains errors; it never loads dotenv. Narrated acts support
`DEMO_PAUSE=1`. This is not a live harness mode. Crafted `httpx.Response` headers exercise the real SDK parser;
the terminal 429 uses public `donkey.simulate(TokenBudgetExceeded)`.

## Assertions

- Cold gateway and provider windows are unknown (`None`), not exhausted (`0`).
- Three synthetic successful responses reproduce decreasing prose
  `x-llm-proxy-ratelimit` observations. The final observation agrees with the
  numeric `x-token-*` trio, whose gateway contract is verified on 429s, not 200s.
- One response populates gateway token/request budgets and **separate**
  `budget.upstream.requests` / `.tokens`. OpenAI provider identity is observed;
  duration resets `1m30s` and `1.5s` become reset timestamps. Gateway reset is
  milliseconds (`60000`), not a Go duration.
- Both provider windows are exhausted with future resets, yet `pace()` allows
  the guarded block. **Provider quota is observe-only**: it is shared by users
  of the routed provider key and does not drive gateway pacing.
- A near-exhausted gateway token window stops the block. Unknown reset returns
  immediately; elapsed reset permits another observation, not an invented fresh
  window. Do not implement an unconditional wait/retry loop.
- A known future reset actually sleeps for a small local window; waiting leaves
  the budget at its last observed value rather than inventing a fresh allowance.
- Switching to Azure OpenAI replaces provider identity/counts without changing
  the gateway budget. Azure's **unitless `0` reset is unknown**; do not infer
  seconds, milliseconds or an epoch from it, or inherit OpenAI's prior reset.
- A partial provider observation leaves absent limit/provider/reset fields
  unknown and `fraction_used=None`, rather than retaining a stale route.
- A simulated gateway 429 emerges as typed `TokenBudgetExceeded`.

Synthetic values illustrate parser/SDK behavior, not current provider capacity
or live verification. Header spellings follow SDK `core._wire`; semantics follow
`test_budget_upstream.py` and `test_budget.py`. Related straight-line local
configuration example: `demos/human-made/openai/18 - dynamic-provider-key.py`.
