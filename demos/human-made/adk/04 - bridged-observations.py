"""Offline streamed ADK factory + hand-built model observation (#52).

Needs donkey-kit[adk,llm]. MockTransport scripts SSE bytes, no credentials/live
calls. last_call_bridged bridges observation into after_model_callback, not
typed refusals; donkey.run()/typed_refusals() is the separate refusal boundary.
Usage is available on the complete response, not partial responses. The Runner
caller remains unobserved because ADK runs the flow in its own task.
"""

import asyncio
import json
from typing import Any

import httpx
from donkey_kit import Donkey, DonkeyConfig
from donkey_kit._testing import http_clients, swap_transport
from donkey_kit.core.lastcall import LastCallStatus
from donkey_kit.integrations.adk import last_call_bridged
from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.genai import types


class Chunks(httpx.AsyncByteStream):
    """Deliver events incrementally so governed transport scans streamed usage."""

    async def __aiter__(self):
        chunk = {
            "id": "completion",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "gpt-4o",
        }
        for event in (
            {
                **chunk,
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": "PO"}}],
            },
            {
                **chunk,
                "choices": [
                    {"index": 0, "delta": {"content": "NG"}, "finish_reason": "stop"}
                ],
            },
            {
                **chunk,
                "choices": [],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            },
        ):
            yield f"data: {json.dumps(event)}\n\n".encode()
        yield b"data: [DONE]\n\n"


async def main() -> None:
    for hand_built in (False, True):
        cfg = DonkeyConfig(
            llm_proxy_url="https://example.invalid/",
            llm_proxy_client_id="demo-client-not-a-real-credential",
            llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
            max_retries=0,
            telemetry=False,
        )
        async with Donkey(cfg) as donkey:

            def answer(request: httpx.Request) -> httpx.Response:
                assert request.url.path.endswith("/chat/completions")
                assert json.loads(request.content)["stream"] is True
                return httpx.Response(
                    200,
                    headers={
                        "content-type": "text/event-stream",
                        "x-request-id": "rid-stream",
                    },
                    stream=Chunks(),
                )

            for client in http_clients(donkey):
                swap_transport(client, httpx.MockTransport(answer))
            model = (
                last_call_bridged(LiteLlm)(
                    model="openai/gpt-4o", **donkey.adk.connection_kwargs()
                )
                if hand_built
                else donkey.adk.model("gpt-4o")
            )
            observed: list[tuple[bool, int | None]] = []

            def after_model(
                callback_context: Any,
                llm_response: Any,
                observed=observed,
                hand_built=hand_built,
            ) -> None:
                record = donkey.last_call
                assert record.status is LastCallStatus.OBSERVED
                assert record.request_id == "rid-stream"
                observed.append((bool(llm_response.partial), record.total_tokens))
                print(
                    "hand-built" if hand_built else "factory",
                    "partial:",
                    bool(llm_response.partial),
                    "total_tokens:",
                    record.total_tokens,
                )

            agent = LlmAgent(name="greeter", model=model, after_model_callback=after_model)
            runner = InMemoryRunner(agent=agent, app_name="observations")
            session = await runner.session_service.create_session(
                app_name="observations", user_id="demo"
            )
            async for _ in runner.run_async(
                user_id="demo",
                session_id=session.id,
                new_message=types.Content(role="user", parts=[types.Part(text="hello")]),
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            ):
                pass
            assert observed == [(True, None), (True, None), (False, 5)]
            assert donkey.last_call.status is LastCallStatus.UNOBSERVED
            print("after Runner:", donkey.last_call.status.value)
    print("Observation bridge != typed-refusal bridge; usage appears at stream completion.")


if __name__ == "__main__":
    asyncio.run(main())
