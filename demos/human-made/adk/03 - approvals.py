"""Offline ADK confirmation lifecycle and replay protection; needs donkey-kit[adk].

Scripted BaseLlm, real App/Runner/plugin, no credential reads or live requests.
These are advisory client-side approvals, not gateway authorization. ADK sends
a rejected confirmation back to the model as an error function response (Agents
uses a function-call output; Strands uses an error tool result).
"""

import asyncio
from typing import Any

from donkey_kit import Donkey
from donkey_kit.integrations.adk import approval_plugin, approve, pending_approvals, reject
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.models import BaseLlm, LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


class ScriptedModel(BaseLlm):
    """Request a refund once, then answer after receiving its tool response."""

    seen: list[Any] = []

    async def generate_content_async(self, llm_request: Any, stream: bool = False) -> Any:
        answers = [
            part.function_response.response
            for content in llm_request.contents
            for part in content.parts or ()
            if part.function_response is not None
        ]
        if answers:
            self.seen.extend(answers)
            part = types.Part(text="done")
        else:
            part = types.Part(
                function_call=types.FunctionCall(
                    id="refund-1",
                    name="issue_refund",
                    args={"ticket_id": "T-1"},
                )
            )
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


async def main() -> None:
    for allowed in (True, False):
        effects: list[str] = []

        @Donkey.tool(approval="required", risk="financial")
        def issue_refund(ticket_id: str) -> dict[str, str]:
            """Refund an approved ticket."""
            effects.append(ticket_id)  # noqa: B023 - this run finishes before the next case
            return {"status": "refunded"}

        model = ScriptedModel(model="scripted")
        agent = LlmAgent(name="refunds", model=model, tools=[issue_refund])
        app = App(name="refunds", root_agent=agent, plugins=[approval_plugin()])
        sessions = InMemorySessionService()
        runner = Runner(app=app, session_service=sessions)
        session = await sessions.create_session(app_name="refunds", user_id="demo")

        async def send(
            part: types.Part, runner: Runner = runner, session_id: str = session.id
        ) -> list[Any]:
            return [
                event
                async for event in runner.run_async(
                    user_id="demo",
                    session_id=session_id,
                    new_message=types.Content(role="user", parts=[part]),
                )
            ]

        (request,) = pending_approvals(await send(types.Part(text="Refund T-1")))
        assert effects == [] and request.name == "adk_request_confirmation"
        decision = (approve if allowed else reject)(request, by="demo-reviewer")
        resumed = await send(decision)
        assert resumed[-1].content.parts[0].text == "done"
        assert effects == (["T-1"] if allowed else [])
        if not allowed:
            assert "issue_refund" in model.seen[-1]["error"]
        # Some ADK releases retry the tool on replay; the plugin refuses that.
        # Newer ADK releases suppress it themselves. Either path must run it once.
        await send(decision)
        assert effects == (["T-1"] if allowed else [])
        print(
            "approved" if allowed else "rejected",
            "confirmation + replay",
            "effects:",
            effects,
        )
    print("Advisory client-side confirmation; rejection is an error tool response.")


if __name__ == "__main__":
    asyncio.run(main())
