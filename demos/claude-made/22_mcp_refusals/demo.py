"""Demo 22 — typed MCP tool refusals, offline, with donkey.simulate_mcp().

When the Omni Gateway refuses an MCP tool call, DDK raises the same typed
error it raises on a model call: a PII block is `PIIDetected`, an access-profile
denial is `ToolNotInProfile`. `donkey.simulate_mcp(capture, servers=...)` replays
the gateway's real captured refusal into your own bindings, with no gateway, no
Exchange and no credentials, so the agent's discovery and binding code runs
unchanged.

Not every MCP policy has a type. Schema Validation and Tool Poisoning replies
are generic on the wire, and the demo shows them staying generic.

    python demos/claude-made/22_mcp_refusals/demo.py
"""

from __future__ import annotations

import asyncio
import warnings

from donkey_kit import Donkey, DonkeyConfig, PIIDetected, PolicyViolation, ToolNotInProfile

from _harness import narrate as say
from _harness import preflight

DEMO_CONFIG = DonkeyConfig(
    llm_proxy_url="https://demo-gateway.example.invalid/mcp-demo/",
    llm_proxy_client_id="demo-client-id-not-a-real-credential",
    llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
)

CRM = "acme/crm-tools/1.0.0"
SERVERS = {
    CRM: [
        {
            "name": "lookup_customer",
            "description": "Look up a customer record by id.",
            "inputSchema": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        }
    ]
}
ARGS = {"customer_id": "C-1042"}


async def _call(donkey: Donkey) -> object:
    """What an agent does: discover, bind natively, call the tool."""
    tools = await donkey.tools.discover()
    (lookup,) = await tools.langgraph()
    return await lookup.ainvoke(ARGS)


async def act_1_pii(donkey: Donkey) -> None:
    say.step(
        1, "A PII block on a tool call is PIIDetected, then the next call goes through"
    )
    say.code(
        """
        servers = {"acme/crm-tools/1.0.0": [{"name": "lookup_customer", ...}]}
        with donkey.simulate_mcp("pii-request", servers=servers):
            tools = await donkey.tools.discover()      # declared servers, no Exchange
            (lookup,) = await tools.langgraph()        # a native LangChain tool
            await lookup.ainvoke({"customer_id": "C-1042"})
        """
    )
    for capture in ("pii-request", "pii-response-sse"):
        with donkey.simulate_mcp(capture, servers=SERVERS):
            try:
                await _call(donkey)
            except PIIDetected as exc:
                say.ok(f"{capture}: PIIDetected (phase={exc.phase}, policy={exc.policy})")
                say.field("message", str(exc))
            else:
                raise AssertionError(f"{capture} was not refused")
            result = await _call(donkey)
            say.ok("times=1: the next call is answered by the offline baseline")
            say.field("result", result)
        print()
    say.note(
        "The response-phase capture arrives on an SSE tool call but is an HTTP 403 "
        "JSON body, not an SSE error event. Either way the message withholds the "
        "flagged values."
    )


async def act_2_access(donkey: Donkey) -> None:
    say.step(2, "An access-profile denial is ToolNotInProfile, naming the tool")
    for capture in ("abac-denied", "global-access"):
        with donkey.simulate_mcp(capture, servers=SERVERS):
            try:
                await _call(donkey)
            except ToolNotInProfile as exc:
                say.ok(f"{capture}: ToolNotInProfile (policy={exc.policy})")
                say.field("tool named by the gateway", exc.tool_name)
            else:
                raise AssertionError(f"{capture} was not refused")
    print()
    say.note(
        "The tool name comes from the captured gateway reply, so it is not "
        "lookup_customer: the injection matches the tools/call method, not the "
        "tool. ToolNotInProfile does not say which of the two access policies "
        "denied the call."
    )


async def act_3_untyped(donkey: Donkey) -> None:
    say.step(3, "Schema Validation and Tool Poisoning stay generic, on purpose")
    for capture in ("schema-invalid-args", "poisoning-block-list"):
        with donkey.simulate_mcp(capture, servers=SERVERS):
            try:
                await _call(donkey)
            except PolicyViolation as exc:
                raise AssertionError(
                    f"{capture} was guessed as {type(exc).__name__}"
                ) from exc
            except Exception as exc:  # noqa: BLE001 - the point is "not a typed refusal"
                say.ok(f"{capture}: {type(exc).__name__}, not a PolicyViolation subclass")
            else:
                raise AssertionError(f"{capture} was not refused")
    print()
    say.note(
        "On the wire these are HTTP 200 JSON-RPC errors: -32602 for invalid "
        "arguments, and -32603 over SSE for the poisoning block, which fails "
        "tools/list rather than a call. They carry no reliable policy marker, so "
        "DDK will not guess a schema or poisoning type. The raw error data can "
        "echo rejected values, so this demo does not print it, and neither "
        "should your logs."
    )


async def story() -> None:
    async with Donkey(DEMO_CONFIG) as donkey:
        await act_1_pii(donkey)
        say.pause()
        await act_2_access(donkey)
        say.pause()
        await act_3_untyped(donkey)

    print()
    say.section("The point")
    say.note(
        "A gateway refusal on an MCP tool is the same typed exception as on a model "
        "call, and you can test it offline through your real binding. These are "
        "replayed Omni Gateway captures, injected with x-donkey-simulator: true. "
        "They are not live gateway evidence."
    )


def main() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.run(asyncio.wait_for(story(), timeout=30))


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 22 — typed MCP tool refusals",
        subtitle="donkey.simulate_mcp() replays captured gateway refusals into a LangGraph binding.",
        target="offline",
        extras=("langchain_mcp_adapters", "mcp"),
    )
