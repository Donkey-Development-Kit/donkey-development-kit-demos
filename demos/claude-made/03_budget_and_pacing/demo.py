"""Gateway pacing versus observe-only provider quotas, all local and synthetic.

Header spellings follow SDK core._wire and test_budget_upstream.py. The crafted
responses exercise real Budget.observe(), not a live provider/gateway.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone

import httpx
from donkey_kit import Budget, BudgetReserveReached, Donkey, TokenBudgetExceeded
from donkey_kit.core import _wire
from donkey_kit.core.config import DonkeyConfig

from _harness import narrate as say
from _harness import preflight


def _show(window, label):
    say.field(
        label,
        f"remaining={window.remaining}, limit={window.limit}, used={window.fraction_used}",
    )


async def _main() -> None:
    say.note(
        "Synthetic response headers and an injected refusal: no gateway or provider calls."
    )
    say.step(1, "A cold process knows nothing until a response returns")
    now = datetime.now(timezone.utc)
    budget = Budget()
    for window in (
        budget,
        budget.requests,
        budget.upstream.requests,
        budget.upstream.tokens,
    ):
        assert window.limit is None and window.remaining is None
        assert window.observed_at is None and window.reset_at is None
        assert window.fraction_used is None
    _show(budget, "gateway before call")
    say.ok("Cold gateway/provider windows are unknown (None), not exhausted (0)")
    say.pause()
    say.step(2, "Two header shapes, one in-band gateway token window")
    say.code("""
        budget.observe(response)
        budget.remaining, budget.limit, budget.observed_at
        # Numeric x-token-* on a 429; prose x-llm-proxy-ratelimit on a 200.
    """)
    prose = Budget()
    for remaining in (900, 850, 800):
        prose.observe(
            httpx.Response(
                200,
                headers={
                    _wire.RATELIMIT_HEADER: f"Token rate limit: {remaining} tokens remaining of 1000 limit. Reset in 60000ms.",
                },
            ),
            now=now,
        )
        assert prose.remaining == remaining
        assert prose.limit == 1000
        assert prose.observed_at == now
        _show(prose, "prose 200 response")

    budget.observe(
        httpx.Response(
            200,
            headers={
                _wire.TOKEN_LIMIT_HEADER: "1000",
                _wire.TOKEN_REMAINING_HEADER: "800",
                _wire.TOKEN_RESET_HEADER: "60000",
                _wire.REQUEST_LIMIT_HEADER: "10",
                _wire.REQUEST_REMAINING_HEADER: "9",
                _wire.REQUEST_RESET_HEADER: "60000",
                _wire.LLM_PROVIDER_HEADER: "openai",
                _wire.UPSTREAM_REQUEST_LIMIT_HEADER: "5000",
                _wire.UPSTREAM_REQUEST_REMAINING_HEADER: "0",
                _wire.UPSTREAM_REQUEST_RESET_HEADER: "1m30s",
                _wire.UPSTREAM_TOKEN_LIMIT_HEADER: "2000000",
                _wire.UPSTREAM_TOKEN_REMAINING_HEADER: "0",
                _wire.UPSTREAM_TOKEN_RESET_HEADER: "1.5s",
            },
        ),
        now=now,
    )
    assert (budget.limit, budget.remaining) == (1000, 800)
    assert (budget.requests.limit, budget.requests.remaining) == (10, 9)
    assert budget.reset_at == now + timedelta(seconds=60)
    assert (prose.limit, prose.remaining, prose.reset_at) == (
        budget.limit,
        budget.remaining,
        budget.reset_at,
    )
    _show(budget, "numeric token headers")
    say.field("observed_at", budget.observed_at)
    say.field("reset_at", budget.reset_at)
    say.note(
        "These values are synthetic. Successful token-policy responses use prose; numeric x-token-* is verified on gateway 429s. There is no out-of-band budget endpoint."
    )
    say.pause()
    say.step(3, "Provider quota is a separate source, never a pacing guard")
    req, tok = budget.upstream.requests, budget.upstream.tokens
    assert (req.limit, req.remaining, req.provider) == (5000, 0, "openai")
    assert (tok.limit, tok.remaining, tok.provider) == (2000000, 0, "openai")
    assert req.reset_at == now + timedelta(seconds=90)
    assert tok.reset_at == now + timedelta(seconds=1.5)
    assert req.observed_at == tok.observed_at == now
    _show(budget.requests, "gateway requests")
    _show(req, "upstream requests")
    _show(tok, "upstream tokens")
    say.field("provider", req.provider)
    say.note(
        "Gateway reset is milliseconds; provider resets are durations such as 1m30s and 1.5s. Provider keys can be shared across consumers and routes."
    )

    ran = False
    async with budget.pace(reserve=0.05, now=now):
        ran = True
    assert ran
    assert req.fraction_used == tok.fraction_used == 1.0
    say.ok(
        "Exhausted upstream quotas did NOT block pace(); provider quotas are observe-only"
    )
    say.pause()
    say.step(4, "Gateway pacing refuses locally, and known resets permit waiting")
    say.code("""
        async with budget.pace(reserve=0.05):
            await enrich(batch)  # does not run if the gateway reserve is crossed
        # On BudgetReserveReached: wait only if reset_at is known.
    """)

    short_window = Budget()
    short_window.observe(
        httpx.Response(
            200,
            headers={
                _wire.TOKEN_LIMIT_HEADER: "1000",
                _wire.TOKEN_REMAINING_HEADER: "40",
                _wire.TOKEN_RESET_HEADER: "20",
            },
        ),
        now=now,
    )
    start = time.monotonic()
    await short_window.wait_for_reset(now=now)
    assert time.monotonic() - start >= 0.015
    assert short_window.remaining == 40
    say.ok("Known future reset actually sleeps; last observation remains unchanged")

    budget.observe(
        httpx.Response(
            200,
            headers={
                _wire.TOKEN_LIMIT_HEADER: "1000",
                _wire.TOKEN_REMAINING_HEADER: "40",
            },
        ),
        now=now + timedelta(milliseconds=1),
    )
    ran = False
    try:
        async with budget.pace(reserve=0.05, now=now):
            ran = True
    except BudgetReserveReached as exc:
        assert exc.fraction_used == 0.96
        assert exc.reserve == 0.05
        assert exc.reset_at == now + timedelta(seconds=60)
    else:
        raise AssertionError("gateway reserve must stop the guarded block")
    assert not ran
    unknown = Budget()
    unknown.observe(
        httpx.Response(
            200,
            headers={
                _wire.TOKEN_LIMIT_HEADER: "1000",
                _wire.TOKEN_REMAINING_HEADER: "40",
            },
        ),
        now=now,
    )
    assert unknown.reset_at is None
    try:
        async with unknown.pace(reserve=0.05, now=now):
            raise AssertionError("unknown reset must not release the reserve guard")
    except BudgetReserveReached as exc:
        assert exc.reset_at is None
    await unknown.wait_for_reset()
    say.ok(
        "Gateway reserve stops block; unknown reset returns immediately, never spin-retry"
    )
    say.note(
        "BudgetReserveReached is a local recovery signal, not a PolicyViolation. Propagate or checkpoint when reset_at is unknown; an unconditional retry loop cannot make progress."
    )

    # Elapsed gateway window is stale; pacing permits the next observation.
    budget.observe(
        httpx.Response(
            200,
            headers={
                _wire.TOKEN_LIMIT_HEADER: "1000",
                _wire.TOKEN_REMAINING_HEADER: "40",
                _wire.TOKEN_RESET_HEADER: "1",
            },
        ),
        now=now + timedelta(milliseconds=2),
    )
    async with budget.pace(reserve=0.05, now=now + timedelta(seconds=1)):
        ran = True
    assert ran
    await budget.wait_for_reset(now=now + timedelta(seconds=1))
    assert budget.remaining == 40
    say.ok("Elapsed gateway reset permits refresh; waiting does not invent a new window")
    say.pause()
    say.step(5, "A routed provider can change: missing fields must stay unknown")

    budget.observe(
        httpx.Response(
            200,
            headers={
                _wire.LLM_PROVIDER_HEADER: "azureopenai",
                _wire.UPSTREAM_REQUEST_LIMIT_HEADER: "250",
                _wire.UPSTREAM_REQUEST_REMAINING_HEADER: "249",
                _wire.UPSTREAM_REQUEST_RESET_HEADER: "0",
                _wire.UPSTREAM_TOKEN_LIMIT_HEADER: "250000",
                _wire.UPSTREAM_TOKEN_REMAINING_HEADER: "249987",
                _wire.UPSTREAM_TOKEN_RESET_HEADER: "0",
            },
        ),
        now=now + timedelta(seconds=2),
    )
    assert req.provider == tok.provider == "azureopenai"
    assert (req.limit, req.remaining) == (250, 249)
    assert (tok.limit, tok.remaining) == (250000, 249987)
    assert req.reset_at is tok.reset_at is None
    assert budget.remaining == 40  # provider response did not overwrite gateway budget
    _show(req, "Azure requests")
    _show(tok, "Azure tokens")
    say.field("Azure reset_at", req.reset_at)
    say.ok("Azure unitless reset '0' is unknown, NOT seconds/ms or a timestamp")

    budget.observe(
        httpx.Response(
            200,
            headers={
                _wire.UPSTREAM_REQUEST_REMAINING_HEADER: "7",
            },
        ),
        now=now + timedelta(seconds=3),
    )
    assert req.remaining == 7
    assert req.limit is req.reset_at is req.provider is None
    assert req.fraction_used is None
    say.ok(
        "Partial provider observation keeps absent fields unknown; no stale provider/reset inherited"
    )
    say.pause()
    say.step(6, "If the gateway refuses, the 429 remains a typed terminal failure")

    async with Donkey(
        DonkeyConfig(
            llm_proxy_url="https://model.example.invalid/",
            llm_proxy_client_id="demo-client-not-a-real-credential",
            llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
            telemetry=False,
            max_retries=0,
        )
    ) as donkey:
        with donkey.simulate(TokenBudgetExceeded):
            try:
                async with donkey.run(id="budget-refusal"):
                    await donkey.llm.client().chat.completions.create(
                        model="local-model",
                        messages=[{"role": "user", "content": "synthetic"}],
                    )
            except TokenBudgetExceeded as exc:
                say.field("classified as", type(exc).__name__)
                say.field("retry_after", exc.retry_after)
            else:
                raise AssertionError("simulated refusal must be typed")
        assert donkey.budget.remaining == 0
    say.ok("Simulated gateway 429 is typed TokenBudgetExceeded, not upstream pacing")
    say.note(
        "Retrying a terminal budget refusal only burns the same window. The SDK injected a captured refusal locally; no live capacity or verification claim is made."
    )


def main() -> None:
    """Run the local budget story after offline preflight checks prerequisites."""
    asyncio.run(_main())


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 03 - budget and pacing",
        subtitle="Gateway reserves and observe-only routed provider quotas.",
        target="offline",
        extras=("openai",),
    )
