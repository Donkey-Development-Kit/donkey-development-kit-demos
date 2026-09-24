"""Demo 12 — ToolSet.filter returns independent views.

Enterprise MCP servers expose dozens of tools. Handing all of them to a model
degrades it and inflates token cost. `ToolSet.filter(allow=..., deny=...,
predicate=...)` returns a *new* ToolSet: the parent is unchanged, and two
filtered views do not clobber each other.

This is the part that is shipped and pure. Binding those tools into LangGraph /
ADK / … still raises `blocked on verification` — Exchange and the MCP Bridge
have not been confirmed against a sandbox, so the demo does not pretend they
work.

    python demos/claude-made/12_toolset_filter/demo.py
"""

from __future__ import annotations

from donkey_kit.registry.models import AssetRef, McpServerHandle
from donkey_kit.tools.session import ToolSet

from _harness import narrate as say
from _harness import preflight


def _server(asset_id: str, tools: tuple[str, ...]) -> McpServerHandle:
    return McpServerHandle(
        ref=AssetRef("com.acme", asset_id, "1.0.0"),
        endpoint_url=f"https://mcp.example.invalid/{asset_id}",
        tool_descriptors=tuple({"name": name} for name in tools),
    )


def act_1_independent_views() -> ToolSet:
    say.step(1, "filter() returns a new ToolSet — the parent keeps every tool")
    say.code(
        """
        tools = ToolSet([hr, crm])
        read_only = tools.filter(allow=["get_employee"])
        write_only = tools.filter(deny=["get_employee"])
        """
    )
    hr = _server("hr", ("get_employee", "update_salary"))
    crm = _server("crm", ("get_employee", "create_lead"))
    tools = ToolSet([hr, crm])
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


def act_2_binding_is_blocked(tools: ToolSet) -> None:
    say.step(2, "Binding into a framework is still blocked on verification")
    say.code(
        """
        tools.langgraph()   # → NotImplementedError("blocked on verification")
        """
    )
    try:
        tools.langgraph()
        say.fail("expected blocked on verification")
    except NotImplementedError as exc:
        say.ok("blocked on verification — Exchange / MCP Bridge are unconfirmed")
        say.field("message", str(exc).splitlines()[0])
    print()
    say.note(
        "Filter and collision resolution are pure, so they shipped. The per-"
        "framework binders open a real MCP session, and those class names are "
        "not confirmed, so they raise rather than guess. @donkey.tool (demo 01) "
        "is a different marker — it records a Python callable, it does not "
        "discover MCP tools."
    )


def main() -> None:
    tools = act_1_independent_views()
    say.pause()
    act_2_binding_is_blocked(tools)

    print()
    say.section("The point")
    say.note(
        "Two filtered views of the same servers, neither mutating the parent. "
        "That is the whole shipped surface. Discover and bind come later."
    )


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 12 — ToolSet.filter",
        subtitle="Independent filtered views of MCP tools. Binding is still blocked on verification.",
        target="offline",
    )
