"""Demo 12 — ToolSet.filter returns independent views.

Enterprise MCP servers expose dozens of tools. Handing all of them to a model
degrades it and inflates token cost. `ToolSet.filter(allow=..., deny=...,
predicate=...)` returns a *new* ToolSet: the parent is unchanged, and two
filtered views do not clobber each other.

This is the part that is shipped and pure. Binding those tools into LangGraph /
ADK / … first refuses any server that is not governed (`UngovernedMcpServer`,
before a connection opens), then still raises `blocked on verification`: the
binders' class names have not been confirmed, so the demo does not pretend
they work.

    python demos/claude-made/12_toolset_filter/demo.py
"""

from __future__ import annotations

from donkey_kit import ConfigError
from donkey_kit.registry import AssetRef, GovernanceReport, McpServerHandle
from donkey_kit.tools import ToolSet
from donkey_kit.tools.session import UngovernedMcpServer

from _harness import narrate as say
from _harness import preflight


def _server(
    asset_id: str, tools: tuple[str, ...], governance: GovernanceReport | None = None
) -> McpServerHandle:
    return McpServerHandle(
        ref=AssetRef("com.acme", asset_id, "1.0.0"),
        endpoint_url=f"https://mcp.example.invalid/{asset_id}",
        tool_descriptors=tuple(
            {
                "name": name,
                "description": f"{name} accesses the {asset_id} employee and customer records.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"record_id": {"type": "string"}},
                    "required": ["record_id"],
                },
            }
            for name in tools
        ),
        governance=governance,
    )


def _servers(governance: GovernanceReport | None = None) -> list[McpServerHandle]:
    return [
        _server("hr", ("get_employee", "update_salary"), governance),
        _server("crm", ("get_employee", "create_lead"), governance),
    ]


def act_1_independent_views() -> ToolSet:
    say.step(1, "filter() returns a new ToolSet — the parent keeps every tool")
    say.code(
        """
        tools = ToolSet([hr, crm])
        read_only = tools.filter(allow=["get_employee"])
        write_only = tools.filter(deny=["get_employee"])
        """
    )
    tools = ToolSet(_servers())
    read_only = tools.filter(allow=["get_employee"])
    write_only = tools.filter(deny=["get_employee"])

    say.field("parent name_map", dict(tools.name_map), raw=True)
    say.field("read_only", dict(read_only.name_map), raw=True)
    say.field("write_only", dict(write_only.name_map), raw=True)
    print()
    if read_only is not tools and write_only is not tools:
        say.ok("each filter() returned a different object")
    parent_after = dict(tools.name_map)
    say.field("parent after filters", parent_after, raw=True)
    if "update_salary" in parent_after and "update_salary" not in read_only.name_map:
        say.ok("the parent was not mutated")
    print()
    say.note(
        "get_employee lives on both servers, so the exposed name is prefixed: "
        "hr__get_employee / crm__get_employee. name_map is exposed_name → "
        "original_name, which is how you debug why the model called a prefixed id."
    )
    return tools


def act_2_narrowing_and_cost(tools: ToolSet) -> None:
    say.step(2, "Globs and chained filters narrow; descriptor estimates show the cost")
    gated = tools.require_approval(tools=["get_employee"], risk="personal-data", timeout=30)
    final = (
        gated.filter(allow=["get_*"])
        .filter(deny=["crm__*"])
        .filter(predicate=lambda tool: bool(tool.description))
    )
    assert final.name_map == {"get_employee": "get_employee"}
    assert final is not gated and len(tools.name_map) == 4
    assert final.descriptor_tokens() < tools.descriptor_tokens()
    say.field("parent estimate", tools.descriptor_tokens(), raw=True)
    say.field("filtered estimate", final.descriptor_tokens(), raw=True)
    say.ok("Each filter narrowed without mutating the parent")
    try:
        tools.filter(deny=["misspelled_tool"])
    except ConfigError:
        say.ok("Unknown patterns fail instead of silently leaving a tool exposed")
    else:
        raise AssertionError("unknown filter pattern was accepted")
    say.note(
        "require_approval() declares an advisory gate that filters preserve. "
        "The public binders remain blocked, so this does not execute an MCP tool. "
        "Descriptor tokens are roughly four JSON characters per token, not a bill."
    )
    try:
        tools.filter(allow=[]).langgraph()
    except UngovernedMcpServer:
        say.ok("Even an empty filtered view cannot bypass server governance")
    else:
        raise AssertionError("filter bypassed server governance")


def act_2_binding_is_refused_then_blocked(tools: ToolSet) -> None:
    say.step(3, "Binding refuses ungoverned servers, then is blocked on verification")
    say.code(
        """
        tools.langgraph()           # → UngovernedMcpServer (no governance verdict)
        governed.langgraph()        # → NotImplementedError("blocked on verification")
        """
    )
    try:
        tools.langgraph()
        raise AssertionError("expected UngovernedMcpServer")
    except UngovernedMcpServer as exc:
        say.ok("refused before any connection — no gateway credentials were sent")
        say.field("servers", list(exc.servers), raw=True)
        say.field("reasons", list(exc.reasons), raw=True)
    print()

    # The verdict discover(governed=True) would attach; built by hand here.
    governed = ToolSet(_servers(GovernanceReport(governed=True, checks=[])))
    try:
        governed.langgraph()
        raise AssertionError("expected blocked on verification")
    except NotImplementedError as exc:
        say.ok("a governed set passes the check, and binding is still blocked")
        say.field("message", str(exc).splitlines()[0])
    print()
    say.note(
        "The governed transport attaches your gateway credentials to every MCP "
        "request, so binding a server the gateway does not front would hand them "
        "to it. donkey.tools.discover(governed=True) attaches the verdict; a "
        "handle built by hand has none, so it is refused. Past that check the "
        "per-framework binders still raise, because their class names are not "
        "confirmed. @donkey.tool (demo 01) is a different marker: it records a "
        "Python callable, it does not discover MCP tools."
    )


def main() -> None:
    tools = act_1_independent_views()
    say.pause()
    act_2_narrowing_and_cost(tools)
    say.pause()
    act_2_binding_is_refused_then_blocked(tools)

    print()
    say.section("The point")
    say.note(
        "Two filtered views of the same servers, neither mutating the parent, and "
        "a binder that refuses any server the gateway does not govern before it "
        "opens a connection. Binding itself comes later."
    )


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 12 — ToolSet.filter",
        subtitle="Independent filtered views of MCP tools. Binding refuses ungoverned servers.",
        target="offline",
    )
