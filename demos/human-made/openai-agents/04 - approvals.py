"""Offline native approvals: pause, serialize RunState, decide, resume.

Needs donkey-kit[openai-agents]. No config files, credentials or live calls.
Approvals are advisory client-side gates, not gateway authorization or an approval
service. Agents rejection becomes a function-call output shown to the model;
Strands uses an error tool result, and ADK uses a confirmation error response.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from agents import Agent, Model, ModelResponse, RunConfig, Runner, RunState, Usage
from donkey_kit import Donkey
from donkey_kit.integrations.openai_agents import (
    approve,
    function_tool,
    pending_approvals,
    reject,
)
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)


class ScriptedModel(Model):
    """Ask for one refund, then acknowledge the actual tool result."""

    def __init__(self) -> None:
        self.inputs: list[Any] = []

    async def get_response(self, *args: Any, **kwargs: Any) -> ModelResponse:
        self.inputs.append(kwargs.get("input", args[1] if len(args) > 1 else None))
        if len(self.inputs) == 1:
            output = [
                ResponseFunctionToolCall(
                    type="function_call",
                    name="issue_refund",
                    call_id="refund-1",
                    arguments='{"ticket_id":"T-1"}',
                )
            ]
        else:
            output = [
                ResponseOutputMessage(
                    id="answer",
                    type="message",
                    role="assistant",
                    status="completed",
                    content=[
                        ResponseOutputText(type="output_text", text="done", annotations=[])
                    ],
                )
            ]
        return ModelResponse(output=output, usage=Usage(), response_id=None)

    async def stream_response(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        raise NotImplementedError("This approval demo is non-streaming.")
        yield


async def main() -> None:
    for allowed in (True, False):
        effects: list[str] = []

        @Donkey.tool(approval="required", risk="financial")
        def issue_refund(ticket_id: str) -> str:
            """Refund a ticket after approval."""
            effects.append(ticket_id)  # noqa: B023 - this run finishes before the next case
            return "refunded"

        model = ScriptedModel()
        agent = Agent(name="refunds", model=model, tools=[function_tool(issue_refund)])
        config = RunConfig(tracing_disabled=True)
        paused = await Runner.run(agent, "Refund T-1", run_config=config)
        (approval,) = pending_approvals(paused)
        assert effects == [] and approval.risk == "financial"
        stored = paused.to_state().to_string()
        state = await RunState.from_string(agent, stored)
        assert pending_approvals(state)[0].id == approval.id
        if allowed:
            approve(state, approval.id, by="demo-reviewer")
        else:
            reject(state, approval.id, by="demo-reviewer", message="Refund denied.")
        done = await Runner.run(agent, state, run_config=config)
        assert done.final_output == "done"
        assert effects == (["T-1"] if allowed else [])
        results = [
            item for item in model.inputs[-1] if item.get("type") == "function_call_output"
        ]
        assert results[0]["output"] == ("refunded" if allowed else "Refund denied.")
        print(
            "approved" if allowed else "rejected", "serialized resume", "effects:", effects
        )
    print(
        "Advisory client-side approval; rejection is a tool result, not a policy refusal."
    )


if __name__ == "__main__":
    asyncio.run(main())
