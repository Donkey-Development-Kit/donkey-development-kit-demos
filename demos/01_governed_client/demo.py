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

    python demos/01_governed_client/demo.py
    python demos/01_governed_client/demo.py --target live
"""

from __future__ import annotations

import asyncio
import os

import openai
from donkey_kit import Donkey, PIIDetected
from donkey_kit.core.errors import classify

from _harness import mock, preflight, redact
from _harness import narrate as say

MODEL = os.environ.get("DEMO_MODEL", "gpt-4o")
PROMPT = "Say hello in exactly three words."


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
        """
    )

    client = donkey.openai()
    say.field("type", f"{type(client).__module__}.{type(client).__name__}")
    say.field("base_url", redact.url(str(client.base_url)))
    print()
    say.table(redact.headers(_injected_headers(client)), title_="headers the SDK injects:")
    print()
    say.note(
        "Note the base URL has no /v1 — the ingress is https://<host>/<instance>/ "
        "and the OpenAI SDK appends /responses itself. Auth is the client_id / "
        "client_secret header pair, not a bearer token."
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
        "That call also did four things nobody asked for, because every request "
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
    say.bullet("a correlation id went out on the request")
    say.bullet("a gen_ai.* span opened and closed around it (demo 06)")


async def act_3_raw_vs_governed(donkey: Donkey) -> None:
    say.step(3, "The same refusal, through both clients")
    say.note(
        "The simulator serves a real captured PII rejection when the model id is "
        "the sentinel below. This is the byte-identical body a live gateway sent."
    )

    pii_model = mock.sentinel("pii-detected") if _is_mock() else MODEL
    if not _is_mock():
        say.warn(
            "Against a live proxy there is no sentinel: this act needs a prompt "
            "your PII policy actually blocks. Skipping it."
        )
        return

    say.code(
        f"""
        # A: stock OpenAI client, no SDK — just base_url + headers
        raw = openai.AsyncOpenAI(base_url=..., api_key=..., default_headers=...)
        await raw.responses.create(model={pii_model!r}, input="...")
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
        await raw.responses.create(model=pii_model, input="My email is a@b.com")
        say.warn("expected a refusal and did not get one")
        return
    except openai.APIStatusError as exc:
        say.field("A: raised", f"openai.{type(exc).__name__}")
        say.field("A: status", exc.status_code, raw=True)
        say.field("A: you get", "a JSON body to parse, and a status code to guess from")
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
        await client.responses.create(model=pii_model, input="My email is a@b.com")
    except openai.APIStatusError as exc:
        governed = classify(exc.response)
        say.field("B: raised", type(governed).__name__)
        say.field("B: policy", getattr(governed, "policy", "—"))
        say.field("B: entities", getattr(governed, "entities", []), raw=True)
        say.field("B: remediation", getattr(governed, "remediation", "—"))
        print()
        if isinstance(governed, PIIDetected):
            say.ok("A 403 that is a policy refusal, not an auth failure — and it says so.")
        say.note(
            "classify() is the bridge, because the raw client raises openai.* errors "
            "and the SDK does not silently re-map them. Demo 02 walks the full taxonomy."
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

        print()
        say.section("The point")
        say.note(
            "The wrapper is not sold as a way to reach the gateway. It is the one "
            "place every request enters and every response leaves — which is why "
            "budget, typed refusals, correlation ids, spans and simulation can all "
            "attach without the developer wiring each one."
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
