"""Offline Agents Runner observations and executable customer conformance (#52).

Needs donkey-kit[openai-agents,test]. No credential reads or live calls.
First-turn last_call belongs to Runner's task: read it inside on_llm_end.
Later non-streamed turns can reach the caller; streamed runs use their own task.
This is task-local observation, not typed-refusal bridging (donkey.run()).
"""

import asyncio
import json
import logging
from typing import Any
from unittest.mock import patch

import httpx
from agents import Agent, RunConfig, RunHooks, Runner, function_tool
from donkey_kit import Donkey, DonkeyConfig
from donkey_kit._testing import http_clients, swap_transport
from donkey_kit.conformance import render_report, run_conformance
from donkey_kit.core.lastcall import LastCallStatus
from donkey_kit.core.telemetry import current_correlation_id

CONFIG = DonkeyConfig(
    llm_proxy_url="https://example.invalid/",
    llm_proxy_client_id="demo-client-not-a-real-credential",
    llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
    max_retries=0,
    telemetry=False,
)
RUN = RunConfig(tracing_disabled=True)


class GovernedAgent:
    """Small run() seam required by the customer conformance harness."""

    def __init__(self, donkey: Donkey) -> None:
        self.donkey = donkey
        self.agent = Agent(name="probe", model=donkey.openai_agents.model("gpt-4o"))

    async def run(self, prompt: str) -> Any:
        async with self.donkey.run(id=current_correlation_id()):
            logging.getLogger(__name__).info(
                "probe correlation_id=%s", current_correlation_id()
            )
            return await Runner.run(self.agent, prompt, run_config=RUN)


async def main() -> None:
    # The harness otherwise calls DonkeyConfig.from_env(). Replace its config
    # loader for this offline demo, not its scenarios, checks or wire transport.
    with patch("donkey_kit.conformance.harness.offline_config", return_value=CONFIG):
        results = await run_conformance(GovernedAgent)
    print(render_report(results))
    assert results and all(result.status == "pass" for result in results)

    for with_tool in (False, True):
        async with Donkey(CONFIG) as donkey:
            observed: list[str] = []

            class Hooks(RunHooks[Any]):
                async def on_llm_end(self, context: Any, agent: Any, response: Any) -> None:
                    record = donkey.last_call
                    assert record.status is LastCallStatus.OBSERVED
                    assert record.total_tokens == 5
                    observed.append(record.request_id)  # noqa: B023 - Runner awaited within this case
                    print("on_llm_end:", record.request_id, record.total_tokens)

            @function_tool
            def get_weather() -> str:
                """Return deterministic weather."""
                return "sunny"

            def answer(
                request: httpx.Request, with_tool: bool = with_tool
            ) -> httpx.Response:
                messages = json.loads(request.content)["messages"]
                first = with_tool and not any(
                    message["role"] == "tool" for message in messages
                )
                message: dict[str, Any] = {"role": "assistant", "content": "PONG"}
                if first:
                    message = {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {"name": "get_weather", "arguments": "{}"},
                            }
                        ],
                    }
                return httpx.Response(
                    200,
                    headers={"x-request-id": "rid-tool" if first else "rid-answer"},
                    json={
                        "id": "completion",
                        "object": "chat.completion",
                        "created": 0,
                        "model": "gpt-4o",
                        "choices": [
                            {
                                "index": 0,
                                "message": message,
                                "finish_reason": "tool_calls" if first else "stop",
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 3,
                            "completion_tokens": 2,
                            "total_tokens": 5,
                        },
                    },
                )

            for client in http_clients(donkey):
                swap_transport(client, httpx.MockTransport(answer))
            agent = Agent(
                name="weather",
                model=donkey.openai_agents.model("gpt-4o"),
                tools=[get_weather] if with_tool else [],
            )
            result = await Runner.run(agent, "hello", hooks=Hooks(), run_config=RUN)
            assert result.final_output == "PONG"
            assert observed == (["rid-tool", "rid-answer"] if with_tool else ["rid-answer"])
            if with_tool:
                assert donkey.last_call.request_id == "rid-answer"
            else:
                assert donkey.last_call.status is LastCallStatus.UNOBSERVED
            print("after run:", donkey.last_call.status.value, "tool turn:", with_tool)
    print(
        "Post-run visibility varies by execution path; observe first turns in on_llm_end."
    )


if __name__ == "__main__":
    asyncio.run(main())
