"""Demo 10 — donkey.last_call: the success-path counterpart to a typed refusal.

On a refusal, classify() already hands you the gateway's ids. On a 200 the same
facts used to vanish: consumed by the budget object, turned into a span attribute
that needs a backend to read, or dropped. So "which gateway served this, what
did it actually route to, and what did it cost?" was answerable after a failure
and unanswerable after a success.

donkey.last_call is one named container for that, populated on every governed
model call from the live-verified response headers and the body's usage object.
Three honest states, never a bare None: UNOBSERVED (cold), OBSERVED (we saw a
response — fields may still be None if the gateway said nothing), UNAVAILABLE
(this adapter never routes through our transport).

    python demos/claude-made/10_last_call/demo.py
"""

from __future__ import annotations

import asyncio
import os

from donkey_kit import Donkey, ModelSubstituted
from donkey_kit.core.lastcall import LastCall, LastCallStatus

from _harness import narrate as say
from _harness import preflight

MODEL = os.environ.get("DEMO_MODEL", "gpt-4o")


def _unwrap_substituted(exc: BaseException) -> ModelSubstituted | None:
    """ModelSubstituted is raised on the httpx transport. The OpenAI client wraps
    that as APIConnectionError, so the typed error is on __cause__ — the same
    'the raw client does not remap' story as classify() in demo 01."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        if isinstance(current, ModelSubstituted):
            return current
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return None


def _show(record: LastCall, *, label: str) -> None:
    say.field(label, record.status.value, raw=True)
    say.field("  observed", record.observed, raw=True)
    say.field("  request_id", record.request_id)
    say.field("  requested_model", record.requested_model, raw=True)
    say.field("  served_model", record.served_model, raw=True)
    say.field("  served_provider", record.served_provider, raw=True)
    say.field("  routing_type", record.routing_type, raw=True)
    say.field("  fallback", record.fallback, raw=True)
    say.field("  substituted", record.substituted, raw=True)
    say.field("  input_tokens", record.input_tokens, raw=True)
    say.field("  output_tokens", record.output_tokens, raw=True)
    say.field("  total_tokens", record.total_tokens, raw=True)
    say.field("  cached_tokens", record.cached_tokens, raw=True)
    say.field("  cache_write_tokens", record.cache_write_tokens, raw=True)
    say.field("  reasoning_tokens", record.reasoning_tokens, raw=True)


async def act_1_cold_start(donkey: Donkey) -> None:
    say.step(1, "A new process has not observed a call yet — and it says so")
    record = donkey.last_call
    say.field("status", record.status.value, raw=True)
    say.field("observed", record.observed, raw=True)
    say.field("available", record.available, raw=True)
    say.field("request_id", record.request_id, raw=True)
    print()
    if record.status is LastCallStatus.UNOBSERVED and record.request_id is None:
        say.ok("UNOBSERVED — not None, not 0, not 'unknown'. A cold read is a named state.")
    say.note(
        "A bare None would be a lie of omission: you could not tell 'the gateway "
        "sent no id' from 'we never saw a response'. Budget uses the same honesty "
        "rule for an unobserved window (demo 03). UNAVAILABLE is the third state, "
        "for adapters that never route through our transport — LiteLLM-backed ADK "
        "and CrewAI, default_headers-only LlamaIndex, or Agent Framework "
        "(observes_last_call = False). Those surfaces report UNAVAILABLE by name "
        "rather than looking like a cold read."
    )


async def act_2_one_call(donkey: Donkey) -> None:
    say.step(2, "One governed call, and the record is the success-path counterpart")
    say.code(
        """
        await client.responses.create(model=..., input=...)
        donkey.last_call.served_model
        donkey.last_call.total_tokens
        donkey.last_call.substituted
        """
    )
    client = donkey.openai()
    await client.responses.create(model=MODEL, input="hello")
    record = donkey.last_call
    _show(record, label="status")
    print()
    if record.status is LastCallStatus.OBSERVED:
        say.ok("OBSERVED — the SDK saw the response, even if some fields stayed None")
    say.note(
        "request_id is the upstream provider's own id, passed through — "
        "x-request-id on OpenAI, x-amzn-requestid on Bedrock (demo 15). Quote it "
        "to the provider. The gateway-side join key is the run correlation_id. "
        "request_id is the same field classify() puts on a DonkeyError after a "
        "refusal, resolved the same way. api_instance_id and environment_id are "
        "parsed from x-envoy-decorator-operation; they are masked in this output."
    )


async def act_3_routing_and_usage(donkey: Donkey) -> None:
    say.step(3, "Routing, fallback, and the cost-relevant token counts")
    record = donkey.last_call
    print()
    say.section("What the gateway did with the request")
    say.field("requested", record.requested_model, raw=True)
    say.field("served", f"{record.served_provider}/{record.served_model}", raw=True)
    say.field("routing_type", record.routing_type, raw=True)
    say.field("fallback", record.fallback, raw=True)
    say.field("substituted", record.substituted, raw=True)
    print()
    if record.substituted:
        say.ok(
            f"substituted — asked for {record.requested_model}, gateway served "
            f"{record.served_model}"
        )
        say.note(
            "Against the simulator this is the captured happy-path fixture talking: "
            "it was recorded against gpt-5.1, and we asked for a different id. That "
            "is not a live failover — and it is exactly the mismatch last_call is "
            "for. A silent substitution is otherwise invisible to your cost model, "
            "your eval, and your latency dashboard."
        )
    else:
        say.ok("served model matches requested — no substitution on this call")
        say.note(
            "fallback is tri-state: True / False when the gateway stated it, None "
            "when the header is absent. False is a real observation ('we routed "
            "normally'), not the same as 'we do not know'."
        )

    print()
    say.section("What this call cost")
    say.field("input / output / total",
              f"{record.input_tokens} / {record.output_tokens} / {record.total_tokens}",
              raw=True)
    say.field("cached_tokens", record.cached_tokens, raw=True)
    say.field("cache_write_tokens", record.cache_write_tokens, raw=True)
    say.field("reasoning_tokens", record.reasoning_tokens, raw=True)
    print()
    say.note(
        "cached_tokens are billed at the cached rate; reasoning_tokens are output "
        "the developer never sees. Reading only total_tokens draws the wrong "
        "conclusion about both cost and latency. An absent count is None, never 0 "
        "— 0 here means the gateway reported zero, which is a different statement. "
        "These are per-call; donkey.budget is the shared window (demo 03)."
    )
    say.note(
        "The SDK never double-retries a fallback. It retries 502/503/504 with "
        "backoff, but a 503 the gateway already marked as a failover is left "
        "alone — a second recovery layer stacked on a working first one just "
        "multiplies latency against an outage the gateway already handled."
    )


async def act_4_opt_in_determinism() -> None:
    say.step(4, "Opt in, and a substitution is a hard error instead of a flag")
    say.code(
        """
        donkey = Donkey.from_env(on_model_substitution="raise")
        # raises ModelSubstituted when served_model != requested_model
        """
    )
    say.note(
        "Off by default: the call succeeds and last_call.substituted is True. "
        "Raise is for callers whose eval, cost model and token assumptions are "
        "pinned to one model. ModelSubstituted is deliberately not a "
        "PolicyViolation — the request was neither refused nor failed, it "
        "succeeded against a model you did not choose. Same shape as "
        "BudgetReserveReached: a client-side signal you opted into."
    )
    print()
    async with Donkey.from_env(on_model_substitution="raise") as donkey:
        client = donkey.openai()
        try:
            await client.responses.create(model=MODEL, input="hello")
        except Exception as exc:  # noqa: BLE001 — OpenAI wraps the transport error
            substituted = _unwrap_substituted(exc)
            if substituted is None:
                raise
            if type(exc) is ModelSubstituted:
                say.ok("ModelSubstituted — the 200 never reached the caller")
            else:
                say.field("raised", type(exc).__name__)
                say.ok(
                    "cause is ModelSubstituted — the OpenAI client wraps the "
                    "transport error, same as a 403 arriving as APIStatusError"
                )
            say.field("requested_model", substituted.requested_model, raw=True)
            say.field("served_model", substituted.served_model, raw=True)
            say.field("served_provider", substituted.served_provider, raw=True)
            say.field("request_id", substituted.request_id)
            record = donkey.last_call
            say.field("last_call.substituted", record.substituted, raw=True)
            say.note(
                "The record still populated — observe happens before the raise — "
                "so a handler that decides to accept the served completion can "
                "read last_call the same way. The exception also carries the "
                "response."
            )
            return
        record = donkey.last_call
        if record.substituted:
            say.warn("substitution was visible on last_call but did not raise")
        else:
            say.note(
                "No substitution on this call (served matched requested), so "
                "on_model_substitution='raise' stayed silent. Against the "
                "simulator, ask for a model other than the captured fixture's "
                "served id to see ModelSubstituted."
            )


async def _main() -> None:
    async with Donkey.from_env() as donkey:
        await act_1_cold_start(donkey)
        say.pause()
        await act_2_one_call(donkey)
        say.pause()
        await act_3_routing_and_usage(donkey)
        say.pause()
        await act_4_opt_in_determinism()

        print()
        say.section("The point")
        say.note(
            "The refusal path already told you which gateway said no. The success "
            "path now tells you which gateway said yes, what it actually served, "
            "and what that call cost — without a span backend, without parsing "
            "headers, and without a second accessor for routing or usage."
        )


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 10 — last_call, routing, and per-call usage",
        subtitle="The success-path counterpart to a typed refusal: who served this, what they served, and what it cost.",
        target="mock",
        extras=("openai",),
    )
