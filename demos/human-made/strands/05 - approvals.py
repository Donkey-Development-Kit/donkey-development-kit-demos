"""Offline native Strands interrupts and typed governed-tool refusal propagation.

Needs donkey-kit[strands,llm]. ApprovalHook is an advisory client-side gate, not
gateway authorization. Rejection cancels the call and gives the model an error
tool result; unlike Agents' function-call output or ADK's confirmation response.
The scripted model chooses tools deterministically; HTTP is MockTransport only.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from donkey_kit import Donkey, DonkeyConfig, PIIDetected
from donkey_kit._testing import http_clients, swap_transport
from donkey_kit.integrations.strands import ApprovalHook, approve, pending_approvals, reject
from donkey_kit.simulator.fixtures import load
from strands import Agent, tool
from strands.models.model import Model


class ScriptedModel(Model):
    """Request a tool once, then retain the native tool result."""

    def __init__(self, name: str, arguments: dict[str, Any]) -> None:
        self.name, self.arguments = name, arguments
        self.turns: list[Any] = []

    def update_config(self, **model_config: Any) -> None:
        pass

    def get_config(self) -> Any:
        return {}

    async def structured_output(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        raise NotImplementedError("This approval demo has no structured output.")
        yield

    async def stream(self, messages: Any, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        self.turns.append(list(messages))
        yield {"messageStart": {"role": "assistant"}}
        if len(self.turns) == 1:
            yield {
                "contentBlockStart": {
                    "start": {"toolUse": {"toolUseId": "call-1", "name": self.name}}
                }
            }
            yield {
                "contentBlockDelta": {
                    "delta": {"toolUse": {"input": json.dumps(self.arguments)}}
                }
            }
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockDelta": {"delta": {"text": "done"}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}


async def main() -> None:
    for allowed in (True, False):
        effects: list[str] = []

        @Donkey.tool(approval="required", risk="financial")
        def issue_refund(ticket_id: str) -> str:
            """Refund an approved ticket."""
            effects.append(ticket_id)  # noqa: B023 - this run finishes before the next case
            return "refunded"

        model = ScriptedModel("issue_refund", {"ticket_id": "T-1"})
        agent = Agent(
            model=model,
            tools=[tool(issue_refund)],
            hooks=[ApprovalHook()],
            callback_handler=None,
        )
        paused = await agent.invoke_async("Refund T-1")
        assert paused.stop_reason == "interrupt" and effects == []
        (approval,) = pending_approvals(paused)
        if allowed:
            decision = approve(approval, by="demo-reviewer")
        else:
            decision = reject(approval, by="demo-reviewer", message="Refund denied.")
        # `.native` is the Strands interruptResponse to resume with.
        done = await agent.invoke_async([decision.native])
        assert done.stop_reason == "end_turn"
        assert effects == (["T-1"] if allowed else [])
        results = [
            block["toolResult"]
            for message in model.turns[-1]
            for block in message["content"]
            if "toolResult" in block
        ]
        assert results[0]["status"] == ("success" if allowed else "error")
        if not allowed:
            assert results[0]["content"] == [{"text": "Refund denied."}]
        print(
            "approved" if allowed else "rejected", "native interrupt", "effects:", effects
        )

    cfg = DonkeyConfig(
        llm_proxy_url="https://example.invalid/",
        llm_proxy_client_id="demo-client-not-a-real-credential",
        llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
        max_retries=0,
        telemetry=False,
    )
    async with Donkey(cfg) as donkey:
        fixture = load("pii-detected")
        sends: list[str] = []

        def refuse(request: httpx.Request) -> httpx.Response:
            sends.append(request.url.path)
            return httpx.Response(
                fixture.status, headers=fixture.headers, content=fixture.body
            )

        for client in http_clients(donkey):
            swap_transport(client, httpx.MockTransport(refuse))

        @Donkey.tool(approval="required")
        async def ask() -> str:
            """Ask a governed model after approval."""
            await donkey.llm.client().chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "hello"}],
            )
            raise AssertionError("The governed call must refuse.")

        model = ScriptedModel("ask", {})
        agent = Agent(
            model=model, tools=[tool(ask)], hooks=[ApprovalHook()], callback_handler=None
        )
        (approval,) = pending_approvals(await agent.invoke_async("ask"))
        assert sends == []
        try:
            async with donkey.run(id="strands-approved-refusal"):
                await agent.invoke_async([approve(approval, by="demo-reviewer").native])
        except PIIDetected:
            assert len(sends) == 1 and len(model.turns) == 1
            print("Approved governed tool: PIIDetected propagated, no second model turn.")
        else:
            raise AssertionError("PIIDetected must not become a tool result.")


if __name__ == "__main__":
    asyncio.run(main())
