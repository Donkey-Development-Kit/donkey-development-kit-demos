"""Demo 01 — the governed client, and what the wrapper is actually for.

The honest starting point: you do not need this SDK to reach the Omni Gateway.
A stock OpenAI client with a `base_url` and two headers gets there. This demo
shows that first, on purpose.

What it then shows is what the raw client leaves you holding. Both clients hit
the same gateway and both get the same 403 back. The raw one gives you an
`openai.APIStatusError` and a JSON body to parse; the governed one gives you a
`PIIDetected` with the flagged entity types and a remediation string. And
because every request left through one place, that same call also updated the
budget window, stamped a correlation id, and opened a GenAI span — none of which
the developer wired up.

Runs offline against the local simulator by default:

    python demos/claude-made/01_governed_client/demo.py
    python demos/claude-made/01_governed_client/demo.py --target live
"""

from __future__ import annotations

import asyncio
import os

import openai
from donkey_kit import Donkey, PIIDetected, registered_tools
from donkey_kit.core.errors import classify
from donkey_kit.core.telemetry import current_correlation_id, current_cost_tags

from _harness import mock, preflight, redact
from _harness import narrate as say

MODEL = os.environ.get("DEMO_MODEL", "gpt-4o")
PROMPT = "Say hello in exactly three words."
# Act 3 needs a prompt the PII policy actually blocks. The Email entity is the one
# the captured rejection carries, so it is the one to configure for a live run.
PII_PROMPT = "My email is a@b.com"


def _injected_headers(client: openai.AsyncOpenAI) -> dict[str, str]:
    """The headers worth showing: what the SDK put there, minus the `X-Stainless-*`
    telemetry the OpenAI SDK adds to every client whether or not it is governed."""
    return {
        k: v
        for k, v in client.default_headers.items()
        if not k.lower().startswith("x-stainless-")
    }


def _text_of(response: object) -> str:
    """The assistant text from a Responses API result, tolerating either the
    SDK's `output_text` convenience or the raw output structure."""
    convenience = getattr(response, "output_text", None)
    if isinstance(convenience, str) and convenience:
        return convenience
    try:
        return response.output[0].content[0].text  # type: ignore[attr-defined,index]
    except (AttributeError, IndexError, TypeError):
        return "<no text in response>"


async def act_1_the_governed_client(donkey: Donkey) -> None:
    say.step(1, "donkey.openai() returns a real OpenAI client, already governed")
    say.code(
        """
        donkey = Donkey.from_env()
        client = donkey.openai()          # -> openai.AsyncOpenAI
        blocking = donkey.openai(sync=True)  # -> openai.OpenAI, same governance
        """
    )

    client = donkey.openai()
    say.field("type", f"{type(client).__module__}.{type(client).__name__}")
    blocking = donkey.openai(sync=True)
    say.field("sync=True", f"{type(blocking).__module__}.{type(blocking).__name__}")
    say.field("base_url", redact.url(str(client.base_url)))
    print()
    say.table(redact.headers(_injected_headers(client)), title_="headers the SDK injects:")
    print()
    say.note(
        "Note the base URL has no /v1 — the ingress is https://<host>/<instance>/ "
        "and the OpenAI SDK appends /responses itself. Auth is the client_id / "
        "client_secret header pair, not a bearer token. sync=True is the same "
        "client without asyncio — useful for a straight-line script."
    )


async def act_2_a_governed_call(donkey: Donkey) -> None:
    say.step(2, "One call. Nothing new to learn — it is the OpenAI SDK.")
    say.code(
        f"""
        response = await client.responses.create(
            model={MODEL!r},
            input={PROMPT!r},
        )
        """
    )

    client = donkey.openai()
    response = await client.responses.create(model=MODEL, input=PROMPT)

    if _is_mock():
        say.warn(
            "The simulator replays a captured success response, so the reply below "
            "answers the prompt that was recorded, not the one just sent. Run with "
            "--target live for a real completion."
        )
    say.field("reply", _text_of(response))
    usage = getattr(response, "usage", None)
    if usage is not None:
        say.field("input tokens", usage.input_tokens, raw=True)
        say.field("output tokens", usage.output_tokens, raw=True)

    print()
    say.note(
        "That call also did these things nobody asked for, because every request "
        "leaves through one client:"
    )
    budget = donkey.budget
    say.field("budget.remaining", budget.remaining, raw=True)
    say.field("budget.limit", budget.limit, raw=True)
    say.field(
        "budget.fraction_used",
        f"{budget.fraction_used:.1%}" if budget.fraction_used is not None else "unobserved",
        raw=True,
    )
    say.field("budget.observed_at", budget.observed_at, raw=True)
    last = donkey.last_call
    say.field("last_call.status", last.status.value, raw=True)
    say.field("last_call.served_model", last.served_model, raw=True)
    say.field("last_call.total_tokens", last.total_tokens, raw=True)
    say.bullet("a correlation id went out on the request")
    say.bullet("a gen_ai.* span opened and closed around it (demo 06)")
    say.note(
        "donkey.last_call is the success-path counterpart to a typed refusal: "
        "who served this, what they actually routed to, and what the call cost. "
        "Demo 10 walks the whole record — routing, fallback, cached/reasoning "
        "tokens, and the opt-in ModelSubstituted error."
    )


async def act_3_raw_vs_governed(donkey: Donkey) -> None:
    say.step(3, "The same refusal, through both clients")

    if _is_mock():
        pii_model = mock.sentinel("pii-detected")
        say.note(
            "The simulator serves a real captured PII rejection when the model id is "
            "the sentinel below. This is the byte-identical body a live gateway sent."
        )
    else:
        pii_model = MODEL
        say.note(
            "There is no sentinel against a live proxy, so this act needs the "
            "PII-detection policy in force with Email among its entities and its "
            "action set to Reject — the default action is Log, which does not block."
        )

    say.code(
        f"""
        # A: stock OpenAI client, no SDK — just base_url + headers
        raw = openai.AsyncOpenAI(base_url=..., api_key=..., default_headers=...)
        await raw.responses.create(model={pii_model!r}, input={PII_PROMPT!r})
        """
    )

    raw = openai.AsyncOpenAI(
        base_url=os.environ["DONKEY_LLM_PROXY_URL"],
        api_key="unused-the-proxy-authenticates-on-headers",
        default_headers={
            "client_id": os.environ["DONKEY_LLM_PROXY_CLIENT_ID"],
            "client_secret": os.environ["DONKEY_LLM_PROXY_CLIENT_SECRET"],
        },
        max_retries=0,
    )
    try:
        await raw.responses.create(model=pii_model, input=PII_PROMPT)
    except openai.APIStatusError as exc:
        say.field("A: raised", f"openai.{type(exc).__name__}")
        say.field("A: status", exc.status_code, raw=True)
        say.field("A: you get", "a JSON body to parse, and a status code to guess from")
    else:
        say.warn("expected a refusal and did not get one")
        if not _is_mock():
            say.note(
                "The prompt was not blocked, so nothing is refusing it. Check that "
                "the PII-detection policy is applied to this API instance and that "
                "its action is Reject rather than Log."
            )
        return
    finally:
        await raw.close()

    print()
    say.code(
        """
        # B: the same request, through the governed client
        try:
            await client.responses.create(model=..., input="...")
        except openai.APIStatusError as exc:
            raise classify(exc.response) from exc
        """
    )

    client = donkey.openai()
    try:
        await client.responses.create(model=pii_model, input=PII_PROMPT)
    except openai.APIStatusError as exc:
        governed = classify(exc.response)
        say.field("B: raised", type(governed).__name__)
        say.field("B: policy", getattr(governed, "policy", "—"))
        say.field("B: entities", getattr(governed, "entities", []), raw=True)
        say.field("B: remediation", getattr(governed, "remediation", "—"))
        print()
        if isinstance(governed, PIIDetected):
            say.ok("A 403 that is a policy refusal, not an auth failure — and it says so.")
        else:
            say.warn(
                f"refused, but as {type(governed).__name__} rather than PIIDetected"
            )
        say.note(
            "classify() is the bridge, because the raw client raises openai.* errors "
            "and the SDK does not silently re-map them. Demo 02 walks the full taxonomy."
        )
    else:
        say.warn("the governed client was not refused either")


async def act_4_the_one_line_onramps(donkey: Donkey) -> None:
    say.step(4, "@donkey.governed and @donkey.tool — the one-line on-ramps")
    say.code(
        """
        @donkey.governed(team="support")
        async def handle_ticket(ticket):
            ...  # every model call inside shares one run id
        """
    )
    say.note(
        "There is deliberately no id= on the decorator: a fixed id pinned across "
        "every call would collapse unrelated tickets into one correlation. When "
        "you need to pin a business id, use donkey.run(id=...) directly (demo 06)."
    )

    seen: list[str | None] = []
    outer = current_correlation_id()

    @donkey.governed(team="support", project="triage")
    async def handle_ticket(ticket: str) -> str:
        seen.append(current_correlation_id())
        tags = current_cost_tags()
        say.field("run id inside", current_correlation_id(), raw=True)
        say.field(
            "cost tags",
            f"team={tags.team} project={tags.project}" if tags else "—",
        )
        return ticket

    await handle_ticket("4417")
    await handle_ticket("4418")
    after = current_correlation_id()
    if seen[0] and seen[1] and seen[0] != seen[1]:
        say.ok("each invocation opened a fresh run")
    else:
        say.warn(f"expected two distinct run ids, got {seen}")
    say.field("run id after", after, raw=True)
    if after == outer:
        say.ok("restored to the enclosing context — nested run() rebinds, then restores")
    else:
        say.warn(f"expected restore to {outer!r}, got {after!r}")

    print()
    say.code(
        """
        @donkey.tool
        def lookup_sku(sku: str) -> str:
            \"\"\"Return stock for a product SKU.\"\"\"
            ...
        """
    )

    @donkey.tool
    def lookup_sku(sku: str) -> str:
        """Return stock for a product SKU."""
        return "42"

    spec = next(s for s in registered_tools() if s.func is lookup_sku)
    say.field("registered", spec.name, raw=True)
    say.field("signature", str(spec.signature), raw=True)
    say.field("docstring", spec.docstring)
    if lookup_sku is spec.func and lookup_sku("AF-1001") == "42":
        say.ok("same function object — the decorator records it, it does not wrap it")

    try:

        @donkey.tool
        def undescribed(sku: str) -> str:
            return sku

        say.fail("expected ValueError for an undescribed tool")
    except ValueError:
        say.ok("ValueError — an undescribed tool is rejected at decoration time")
    say.note(
        "The same marker is what a Phase 2 scanner and an A2A agent-card "
        "generator will both read. Neither consumer is built yet; this is the "
        "annotation they will look for, not a wrapper around the tool."
    )


def _is_mock() -> bool:
    from _harness import env

    return env.target_is_mock()


async def _main() -> None:
    async with Donkey.from_env() as donkey:
        await act_1_the_governed_client(donkey)
        say.pause()
        await act_2_a_governed_call(donkey)
        say.pause()
        await act_3_raw_vs_governed(donkey)
        say.pause()
        await act_4_the_one_line_onramps(donkey)

        print()
        say.section("The point")
        say.note(
            "The wrapper is not sold as a way to reach the gateway. It is the one "
            "place every request enters and every response leaves — which is why "
            "budget, last_call, typed refusals, correlation ids, spans and "
            "simulation can all attach without the developer wiring each one. "
            "@donkey.governed is that attachment as a function decorator; "
            "@donkey.tool is the marker a scanner can find without executing it."
        )


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 01 — the governed client",
        subtitle="Reaching the gateway is easy. Everything that hangs off the client is the product.",
        target="either",
        extras=("openai",),
    )
