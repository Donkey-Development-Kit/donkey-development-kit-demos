"""Demo 24 — delegate to a governed A2A agent, and type what the gateway refuses.

Demo 21 serves an agent. This one calls one: `donkey.a2a.send()` and
`stream()` resolve an Exchange reference, check governance, and send an
official `a2a-sdk` request through the Omni Gateway. When a gateway policy
refuses the call, the caller gets the same typed exceptions as a model call.

Fully offline: `donkey.simulate_a2a()` declares the agent instead of reading
Exchange and replays the packaged Omni Gateway captures. No gateway, no
Exchange, no credentials.

    python demos/claude-made/24_a2a_outbound/demo.py
"""

from __future__ import annotations

import asyncio
import importlib
import os
import subprocess
import sys
import warnings

from _harness import narrate as say
from _harness import preflight

REF = "acme/claims-triage-agent/1.0.0"
# A synthetic address the PII capture echoes back; the demo asserts it never
# reaches the exception text or a span.
ECHOED = "capture@example.com"

GATE_PROBE = f"""
import asyncio, os
os.environ.pop("OTEL_INSTRUMENTATION_A2A_SDK_ENABLED", None)
from a2a.types import Message, Part, Role, SendMessageRequest
from donkey_kit import ConfigError, Donkey, DonkeyConfig
cfg = DonkeyConfig(llm_proxy_url="https://demo-gateway.example.invalid/a2a-demo/",
    llm_proxy_client_id="demo-client-id-not-real", llm_proxy_client_secret="demo-secret-not-real")
req = SendMessageRequest(message=Message(message_id="m", role=Role.ROLE_USER, parts=[Part(text="hi")]))
async def main():
    async with Donkey(cfg) as d:
        with d.simulate_a2a("pii-send", agents=["{REF}"]):
            try:
                await d.a2a.send("{REF}", req)
            except ConfigError:
                print("ConfigError")
asyncio.run(main())
"""


def _config():
    from donkey_kit import DonkeyConfig

    return DonkeyConfig(
        llm_proxy_url="https://demo-gateway.example.invalid/a2a-demo/",
        llm_proxy_client_id="demo-client-id-not-a-real-credential",
        llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
    )


def _request(message_id: str, text: str):
    from a2a.types import Message, Part, Role, SendMessageRequest

    return SendMessageRequest(
        message=Message(message_id=message_id, role=Role.ROLE_USER, parts=[Part(text=text)])
    )


def _text(message) -> str:
    return " ".join(p.text for p in message.parts if p.text)


def act_1_gate() -> None:
    say.step(1, "The official SDK's own tracing is off, or the call refuses")
    say.code(
        """
        os.environ["OTEL_INSTRUMENTATION_A2A_SDK_ENABLED"] = "false"   # before importing a2a
        # or: Donkey.from_env(allow_a2a_sdk_telemetry=True) to accept both recorders
        """
    )
    out = subprocess.run(
        [sys.executable, "-c", GATE_PROBE],
        capture_output=True,
        text=True,
        timeout=60,
        env={k: v for k, v in os.environ.items() if not k.startswith("OTEL_")},
    )
    if out.stdout.strip() != "ConfigError":
        raise AssertionError(
            f"tracing gate did not refuse: {out.stdout!r} {out.stderr[-300:]!r}"
        )
    say.ok("a fresh process with the variable unset: ConfigError before any request")
    say.note(
        "The a2a-sdk tracer can export private error diagnostics. DDK refuses "
        "rather than switch it off for you. This demo sets the variable before "
        "importing a2a."
    )


async def act_2_delegate(donkey) -> None:
    say.step(2, "send() and stream() return official SDK types")
    say.code(
        """
        with donkey.simulate_a2a("pii-send", agents=[REF], reply=triage):
            response = await donkey.a2a.send(REF, request)        # SendMessageResponse
            async with donkey.a2a.stream(REF, request) as events:  # StreamResponse items
                async for event in events: ...
        """
    )

    def triage(text: str) -> str:
        return f"triaged: {text}"

    # A "-stream" capture answers stream() only, so send() gets the reply, and
    # the other way round. Act 3 shows what the injected calls raise.
    with donkey.simulate_a2a("pii-stream", agents=[REF], reply=triage):
        response = await donkey.a2a.send(REF, _request("claim-41", "Summarize claim 41."))
        say.ok(
            f"send() → {type(response).__name__}.{response.WhichOneof('payload')}: "
            f"{_text(response.message)!r}"
        )
    with donkey.simulate_a2a("pii-send", agents=[REF], reply=triage):
        kinds = []
        async with donkey.a2a.stream(
            REF, _request("claim-42", "Summarize claim 42.")
        ) as events:
            async for event in events:
                kinds.append(event.WhichOneof("payload"))
                last = event
        say.ok(f"stream() → StreamResponse {kinds}: {_text(last.message)!r}")
        from donkey_kit import RegistryError

        try:
            await donkey.a2a.send("acme/unknown-agent/1.0.0", _request("x", "x"))
        except RegistryError:
            say.ok("an undeclared ref is a RegistryError; no request was sent")
        else:
            raise AssertionError("undeclared ref was sent")
    say.note(
        "Inspect the returned message or task status: HTTP success does not mean "
        "the remote task completed. Leaving `async with` closes the stream; it "
        "does not cancel the remote task."
    )


async def act_3_refusals(donkey) -> None:
    from donkey_kit import (
        ContentSafetyBlocked,
        PolicyViolation,
        TokenBudgetExceeded,
        ToolInvocationError,
    )

    say.step(3, "Captured gateway refusals become typed exceptions")
    say.code(
        """
        except ContentSafetyBlocked as exc:   exc.categories, exc.provider
        except TokenBudgetExceeded as exc:    exc.retry_after
        """
    )
    cases = [
        ("azure-block-send", "1.0", ContentSafetyBlocked),
        ("azure-block-stream", "1.0", ContentSafetyBlocked),
        ("rate-send", "1.0", TokenBudgetExceeded),
        ("rate-stream", "1.0", TokenBudgetExceeded),
        ("rate-send", "0.3", TokenBudgetExceeded),
        ("pii-send", "1.0", ToolInvocationError),
        ("pii-stream", "1.0", ToolInvocationError),
        ("pii-send", "0.3", ToolInvocationError),
    ]
    for capture, version, expected in cases:
        with donkey.simulate_a2a(capture, agents=[REF], version=version):
            try:
                request = _request("claim-43", f"Email the summary to {ECHOED}.")
                if capture.endswith("-stream"):
                    async with donkey.a2a.stream(REF, request) as events:
                        async for _ in events:
                            pass
                else:
                    await donkey.a2a.send(REF, request)
            except expected as exc:
                status = exc.response.status_code if exc.response is not None else "-"
                detail = ""
                if isinstance(exc, ContentSafetyBlocked):
                    detail = f" categories={exc.categories} provider={exc.provider}"
                elif isinstance(exc, TokenBudgetExceeded):
                    detail = f" retry_after={exc.retry_after}s"
                elif isinstance(exc, PolicyViolation):
                    raise AssertionError(f"{capture}: PII is not typed by policy") from exc
                if ECHOED in f"{exc}{exc!r}":
                    raise AssertionError(
                        f"{capture}: echoed PII reached the exception text"
                    ) from exc
                say.ok(
                    f"v{version} {capture:<19} HTTP {status} → {type(exc).__name__}{detail}"
                )
            else:
                raise AssertionError(f"{capture}: no refusal raised")
    print()
    say.note(
        "PII stays a generic ToolInvocationError on purpose: the A2A PII and schema "
        "refusals use generic JSON-RPC codes that do not name the policy. The "
        "capture echoes the detected value; it is not in the exception text, but "
        "exc.response still holds the raw body, so never log it."
    )


async def act_4_spans(donkey, exporter) -> None:
    say.step(4, "Each delegation is one donkey.a2a.call span, without diagnostics")
    exporter.clear()
    with donkey.simulate_a2a("pii-send", agents=[REF]):
        try:
            await donkey.a2a.send(REF, _request("claim-44", f"Forward to {ECHOED}."))
        except Exception:
            pass
        await donkey.a2a.send(REF, _request("claim-45", "Summarize claim 45."))
    spans = [s for s in exporter.get_finished_spans() if s.name == "donkey.a2a.call"]
    if len(spans) != 2:
        raise AssertionError(f"expected two donkey.a2a.call spans, got {len(spans)}")
    for span in spans:
        attrs = dict(span.attributes or {})
        if ECHOED in repr(attrs) or span.events:
            raise AssertionError("a refusal diagnostic reached the span")
        outcome = attrs.get("error.type", "none")
        say.ok(
            f"{span.kind.name} span, status {span.status.status_code.name}, "
            f"error.type={outcome}, correlation source={attrs['donkey.correlation_id.source']}"
        )
    say.note(
        "Failures record only error.type: no message, no exception event. On a "
        "successful gateway reply, Quality Evaluation headers become "
        "donkey.a2a.quality.* attributes (the explanation only with "
        "telemetry_capture_content=True). The captures here carry none."
    )


async def story(exporter) -> None:
    from donkey_kit import Donkey

    async with Donkey(_config()) as donkey:
        await act_2_delegate(donkey)
        say.pause()
        await act_3_refusals(donkey)
        say.pause()
        await act_4_spans(donkey, exporter)

    print()
    say.section("The point")
    say.note(
        "Delegating to another agent gets the same typed refusals, correlation and "
        "spans as a model call. These are replayed captures: successful gateway "
        "send and SSE are not live-verified, and donkey.a2a is Provisional. "
        "GatewayAuthRequired (v0.3 In-Task Authorization) is typed too, but has "
        "no packaged capture to replay here."
    )


def main() -> None:
    act_1_gate()
    say.pause()

    os.environ["OTEL_INSTRUMENTATION_A2A_SDK_ENABLED"] = "false"
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    if not isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider):
        raise RuntimeError(
            "Demo 24 needs a fresh process: a host OTel provider is installed."
        )
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    importlib.import_module("a2a")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            asyncio.run(asyncio.wait_for(story(exporter), timeout=30))
    finally:
        provider.shutdown()


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 24 — outbound A2A",
        subtitle="donkey.a2a send/stream to a governed agent; refusals typed, offline.",
        target="offline",
        extras=("a2a", "opentelemetry.sdk"),
    )
