"""Centralized refusal reactions: a retry is another governed decision, not permission."""

from __future__ import annotations

import asyncio
import os
from contextlib import contextmanager

import httpx
from donkey_kit import (
    ContentSafetyBlocked,
    Donkey,
    DonkeyConfig,
    PIIDetected,
    PolicyViolation,
    TokenBudgetExceeded,
    classify,
)
from donkey_kit.conformance.gateway import start_gateway
from donkey_kit.core import RefusalContext
from donkey_kit.core.transport import CALL_ID_HEADER, CORRELATION_HEADER
from donkey_kit.simulator.scenarios import ScenarioHit

from _harness import narrate as say
from _harness import preflight


@contextmanager
def isolated_proxies():
    """Construct every shared SDK client without ambient proxy mounts."""
    keys = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    )
    previous = {key: os.environ.get(key) for key in keys}
    try:
        for key in keys:
            os.environ.pop(key, None)
        os.environ["NO_PROXY"] = os.environ["no_proxy"] = "*"
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class DemoExportBlocked(PolicyViolation):
    """Synthetic demo policy, not a captured platform policy."""

    policy = "demo_export_block"
    remediation = "Keep the synthetic export local and ask its owner to review it."


class ShortReset:
    """Refuse once with a captured budget body and a synthetic 10ms reset."""

    name = "demo_short_reset"

    def __init__(self, *, always: bool = False) -> None:
        self.calls = 0
        self.always = always

    def on_call(self, text: str) -> ScenarioHit | None:
        self.calls += 1
        if self.always or self.calls == 1:
            return ScenarioHit(
                "token-rate-limit", {"retry-after": "0.01", "x-token-reset": "10"}
            )
        return None


async def story() -> None:
    gateway = start_gateway(startup_timeout=3)
    config = DonkeyConfig(
        llm_proxy_url=f"{gateway.url}/",
        llm_proxy_client_id="demo-client-id-not-a-real-credential",
        llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
        max_retries=0,
        timeout_s=2,
        telemetry=False,
    )
    try:
        async with Donkey(config) as donkey:
            client = donkey.openai()
            say.step(1, "Wait briefly, but never indefinitely")
            donkey.on(TokenBudgetExceeded).wait_for_reset(max_wait="50ms", max_times=1)
            gateway.set_scenarios(ShortReset())
            with donkey.run(id="reaction-wait"):
                reply = await client.responses.create(model="gpt-4o", input="hello")
            assert reply.output_text
            assert gateway.requests_received == 2
            say.ok("10ms reset, one resend, then a simulator-approved response")

            gateway.reset()
            gateway.set_scenarios(ShortReset(always=True))
            try:
                with donkey.run(id="reaction-bounded"):
                    await client.responses.create(model="gpt-4o", input="hello")
            except TokenBudgetExceeded:
                assert gateway.requests_received == 2
            else:
                raise AssertionError("max_times must stop an always-refused request")
            say.ok("Repeated refusal stops after one resend; no retry loop")
            gateway.reset()
            gateway.set_scenarios(ShortReset())
            donkey.on(TokenBudgetExceeded).wait_for_reset(max_wait="1ms", max_times=1)
            try:
                with donkey.run(id="reaction-too-long"):
                    await client.responses.create(model="gpt-4o", input="hello")
            except TokenBudgetExceeded:
                assert gateway.requests_received == 1
            else:
                raise AssertionError("a reset beyond max_wait must propagate")
            say.ok("10ms reset exceeds the 1ms cap: no resend")
            gateway.set_scenarios()

            say.step(2, "Revise the request, not the gateway's decision")
            refused_ids: list[tuple[str | None, str | None]] = []

            def revise(ctx: RefusalContext) -> None:
                refused_ids.append((ctx.violation.correlation_id, ctx.violation.call_id))
                body = ctx.body
                assert body is not None
                body["input"] = "synthetic identifier removed by the application"
                ctx.resend(json=body)

            donkey.on(PIIDetected).call(revise, max_times=1)
            gateway.reset()
            with donkey.simulate(PIIDetected), donkey.run(id="reaction-resend"):
                reply = await client.responses.create(
                    model="gpt-4o", input="synthetic identifier"
                )
            assert reply.output_text
            assert gateway.requests_received == 1  # The injected refusal never hit TCP.
            first_correlation, first_call = refused_ids[-1]
            sent = gateway.requests[0]
            assert first_correlation == sent.headers[CORRELATION_HEADER.lower()]
            assert first_correlation == "reaction-resend"
            assert first_call and first_call != sent.headers[CALL_ID_HEADER.lower()]
            say.ok("Resend preserved the correlation ID and received a fresh call ID")
            try:
                with (
                    donkey.simulate(PIIDetected, times=2),
                    donkey.run(id="reaction-still-refused"),
                ):
                    await client.responses.create(
                        model="gpt-4o", input="synthetic identifier"
                    )
            except PIIDetected:
                pass
            else:
                raise AssertionError("a revised request can still be refused")
            say.ok("If the second governed request is refused too, the refusal propagates")

            say.step(3, "Fallback changes the model on a new governed request")
            donkey.on(TokenBudgetExceeded).fallback(model="demo-fallback", max_times=1)
            gateway.reset()
            with donkey.simulate(TokenBudgetExceeded), donkey.run(id="reaction-fallback"):
                reply = await client.responses.create(model="gpt-4o", input="hello")
            assert reply.output_text
            assert donkey.last_call.requested_model == "demo-fallback"
            assert gateway.requests_received == 1
            say.ok("The simulator evaluated a new request naming demo-fallback")

            say.step(4, "Escalation records locally and still raises")
            sink: list[PolicyViolation] = []
            donkey.on(ContentSafetyBlocked).escalate(to=sink.append)
            gateway.reset()
            try:
                with (
                    donkey.simulate(ContentSafetyBlocked),
                    donkey.run(id="reaction-escalation"),
                ):
                    await client.responses.create(model="gpt-4o", input="hello")
            except ContentSafetyBlocked as exc:
                assert sink == [exc] or (len(sink) == 1 and sink[0].call_id == exc.call_id)
            else:
                raise AssertionError("escalation must not swallow a refusal")
            assert gateway.requests_received == 0
            say.ok("Local sink received one refusal; no external notification or resend")

            say.step(5, "Returning a made-up 200 cannot manufacture success")
            manufactured: list[httpx.Response] = []

            def pretend_success(ctx: RefusalContext) -> httpx.Response:
                response = httpx.Response(200, json={"made_up": True})
                manufactured.append(response)
                return response

            donkey.on(PIIDetected).call(pretend_success)
            try:
                with donkey.simulate(PIIDetected), donkey.run(id="reaction-no-bypass"):
                    await client.responses.create(model="gpt-4o", input="hello")
            except PIIDetected:
                assert len(manufactured) == 1
            else:
                raise AssertionError("handler return values must not override the gateway")
            assert gateway.requests_received == 0
            say.ok(
                "Handler returned a fabricated 200; the caller still received PIIDetected"
            )

            say.step(6, "Custom classification is global; reactions belong to one Donkey")
            before = classify.registered()
            registration = classify.register(
                match={"status": 403, "error_type": "demo_export_block"},
                raises=DemoExportBlocked,
            )
            try:
                donkey.on(DemoExportBlocked).escalate(to=sink.append)
                async with Donkey(config) as other:
                    assert other.classify is donkey.classify is classify
                    for handle in (donkey, other):
                        size = len(sink)
                        try:
                            with (
                                handle.simulate(DemoExportBlocked),
                                handle.run(id="custom-policy"),
                            ):
                                await handle.openai().responses.create(
                                    model="gpt-4o", input="hello"
                                )
                        except DemoExportBlocked as exc:
                            assert exc.remediation == DemoExportBlocked.remediation
                        else:
                            raise AssertionError("synthetic custom policy must classify")
                        assert len(sink) == size + (handle is donkey)
                say.ok(
                    "Both clients classified the synthetic policy; only one escalated it"
                )
            finally:
                assert classify.unregister(DemoExportBlocked) == (registration,)
            assert classify.registered() == before
            say.ok("Custom registration removed; pre-existing registrations preserved")
            say.note(
                "Offline means no live service: this story starts its own loopback simulator. "
                "Short resets and the custom policy are synthetic, not live verification. "
                "classify registrations are process-wide; on() reactions are per Donkey."
            )
    finally:
        gateway.close()


def main() -> None:
    # Donkey has no public trust_env configuration; isolate before it builds
    # either shared client. This standalone demo owns its process environment.
    with isolated_proxies():
        asyncio.run(asyncio.wait_for(story(), timeout=15))


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 17 - refusal reactions",
        subtitle="Offline fixtures and loopback only. Reactions never grant permission.",
        target="offline",
        extras=("openai", "starlette", "uvicorn"),
    )
