"""Demo 08 — your framework's own object, already pointed at the governed proxy.

No adapter returns a wrapper. `donkey.langgraph.chat_model(...)` hands back a
real `langchain_openai.ChatOpenAI`, so everything LangChain can do with a chat
model still works, and nothing new appears in your stack traces.

The roster is deliberately uneven, and it is worth saying why rather than
implying eight equal integrations. One framework — LangGraph — is the deep,
conformance-gated adapter. The other seven are supported at the
`connection_kwargs()` level. Most get base URL, headers and client configuration
to spread onto the framework's own constructor. The Agents SDK is the exception
that proves the rule: it takes a pre-built `AsyncOpenAI`, so
`connection_kwargs()` is one key — `openai_client` — carrying header *and*
transport injection as a single object.

No network calls are made. Objects are constructed, and act 4 runs one
Agent Framework turn against a simulated refusal that never leaves the process.

    python demos/claude-made/08_framework_objects/demo.py
"""

from __future__ import annotations

import asyncio

from donkey_kit import ConfigError, Donkey, DonkeyConfig

from _harness import narrate as say
from _harness import preflight, redact

# Constructing an adapter needs proxy configuration, but calling one does not
# happen here — so the demo supplies obviously-fake config rather than reading
# real credentials or booting a simulator it would never send a request to.
DEMO_CONFIG = DonkeyConfig(
    llm_proxy_url="https://demo-gateway.example.invalid/openai-sdk/",
    llm_proxy_client_id="demo-client-id-not-a-real-credential",
    llm_proxy_client_secret="demo-client-secret-not-a-real-credential",
)

# (attribute on Donkey, factory method, whether it takes a model id, depth)
#
# `openai_agents` is the OpenAI Agents SDK adapter. It is NOT `donkey.openai` —
# that name belongs to the raw client factory (demo 01), and the Agents SDK
# adapter was renamed out of the way so the headline two-line ergonomic could
# have it. Its connection_kwargs() is one key, `openai_client`, holding a
# pre-built governed AsyncOpenAI — the Agents SDK takes a ready-made client,
# not loose URL/header kwargs.
ROSTER = [
    ("langgraph", "chat_model", True, "deep — the conformance-gated adapter"),
    ("adk", "model", True, "connection_kwargs()"),
    ("strands", "model", True, "connection_kwargs()"),
    ("agent_framework", "chat_client", True, "connection_kwargs() + policy_middleware(); model="),
    ("openai_agents", "model", True, "connection_kwargs() → {openai_client}"),
    ("anthropic", "client", False, "connection_kwargs(); native route needs Format=Anthropic"),
    ("crewai", "llm", True, "connection_kwargs()"),
    ("llamaindex", "llm", True, "connection_kwargs()"),
]

MODEL = "gpt-4o"


def _probe(donkey: Donkey, attr: str, method: str, takes_model: bool) -> tuple[str, str]:
    """Return (status, detail) for one adapter, never raising."""
    try:
        adapter = getattr(donkey, attr)
    except ImportError as exc:
        # The curated ImportError carries the exact pip command; show that line.
        install = next(
            (line.strip() for line in str(exc).splitlines() if "pip install" in line), ""
        )
        return "not installed", install
    except NotImplementedError as exc:
        return "blocked on verification", redact.text(exc)

    try:
        factory = getattr(adapter, method)
        obj = factory(MODEL) if takes_model else factory()
    except NotImplementedError as exc:
        return "blocked on verification", redact.text(exc)
    except ConfigError as exc:
        return "config error", redact.text(exc)
    except Exception as exc:  # noqa: BLE001 — a demo reports, it does not crash
        return type(exc).__name__, redact.text(exc)

    return "ok", f"{type(obj).__module__}.{type(obj).__name__}"


def act_1_the_roster(donkey: Donkey) -> None:
    say.step(1, "One call per framework, and what came back")
    width = max(len(a) for a, _, _, _ in ROSTER)
    for attr, method, takes_model, depth in ROSTER:
        status, detail = _probe(donkey, attr, method, takes_model)
        marker = {"ok": say.ok, "not installed": say.note}.get(status, say.warn)
        call = f"donkey.{attr}.{method}({'…' if takes_model else ''})"
        print()
        print(f"  {attr:<{width}}  {depth}")
        print(f"    {call}")
        if status == "ok":
            marker(f"returned {detail}")
        else:
            print(f"    {status}: {detail}")


def act_2_connection_kwargs(donkey: Donkey) -> None:
    say.step(2, "connection_kwargs() — the surface that actually carries the roster")
    say.code(
        """
        kwargs = donkey.strands.connection_kwargs()
        SomeFrameworkModel(model="gpt-4o", **kwargs)
        """
    )

    shown = 0
    for attr, _, _, _ in ROSTER:
        if attr == "openai_agents":
            continue
        try:
            adapter = getattr(donkey, attr)
        except (ImportError, NotImplementedError):
            continue
        accessor = getattr(adapter, "connection_kwargs", None)
        if accessor is None:
            continue
        try:
            kwargs = accessor()
        except Exception as exc:  # noqa: BLE001
            say.warn(f"{attr}: {redact.text(exc)}")
            continue
        print()
        say.field(f"{attr}.connection_kwargs()", "")
        say.table(redact.headers(_flatten(kwargs)))
        shown += 1
        if shown == 2:
            break

    print()
    say.note(
        "Same base URL, same default client_id / client_secret pair "
        "(llm_proxy_auth='client-id'), handed to the framework's own constructor. "
        "The model-wallet JWT ingress is a different mode — demo 13. Bringing a "
        "framework up to the deep bar is demand-driven and happens one at a time, "
        "so this is not a stepping stone that everything is queued behind — it is "
        "the supported surface."
    )
    say.note(
        "LangGraph is the only adapter held to the conformance bar. It sets "
        "use_responses_api=True so ChatOpenAI calls /responses rather than its "
        "/chat/completions default: /responses is the raw client's route and the "
        "only one the local simulator serves."
    )


def _flatten(kwargs: dict[str, object]) -> dict[str, str]:
    """One level of flattening, so nested header dicts are visible and maskable."""
    out: dict[str, str] = {}
    for key, value in kwargs.items():
        if isinstance(value, dict):
            for inner, inner_value in value.items():
                out[f"{key}.{inner}"] = str(inner_value)
        else:
            out[key] = str(value)
    return out


def act_3_openai_agents_kwargs(donkey: Donkey) -> None:
    say.step(3, "Agents SDK: connection_kwargs() is one governed client object")
    say.code(
        """
        kwargs = donkey.openai_agents.connection_kwargs()
        OpenAIChatCompletionsModel(model="gpt-4o", **kwargs)
        """
    )
    try:
        kwargs = donkey.openai_agents.connection_kwargs()
    except ImportError as exc:
        install = next(
            (line.strip() for line in str(exc).splitlines() if "pip install" in line),
            str(exc),
        )
        say.note(f"openai-agents is not installed — {install}")
        say.note(
            "The shape is still the point: one key, openai_client, a real "
            "AsyncOpenAI bound to the proxy. Not 'no connection_kwargs()'."
        )
        return

    client = kwargs.get("openai_client")
    say.field("keys", sorted(kwargs), raw=True)
    if client is not None:
        say.field("openai_client", f"{type(client).__module__}.{type(client).__name__}")
        say.field("base_url", redact.url(str(getattr(client, "base_url", ""))))
        if set(kwargs) == {"openai_client"}:
            say.ok("one key — header and transport injection travel as one object")
    print()
    say.note(
        "The Agents SDK does not take loose URL/header kwargs. It takes a client. "
        "So connection_kwargs() returns that client, and model() is "
        "OpenAIChatCompletionsModel(model=..., **those kwargs). donkey.openai() "
        "is still the raw factory; donkey.openai_agents is this adapter."
    )


async def act_4_policy_middleware(donkey: Donkey) -> None:
    say.step(4, "Agent Framework: policy_middleware() ends the run on a refusal")
    say.code(
        """
        agent = Agent(
            client=donkey.agent_framework.chat_client("gpt-4o"),
            middleware=[donkey.agent_framework.policy_middleware()],
        )
        with donkey.simulate(PIIDetected):
            await agent.run("my email is jane@example.com")   # → PIIDetected
        """
    )
    from donkey_kit import PIIDetected

    # policy_middleware() wraps the function in agent_framework's
    # chat_middleware decorator, so without the package it raises
    # NotImplementedError naming the missing import.
    try:
        from agent_framework import Agent

        middleware = donkey.agent_framework.policy_middleware()
    except (ImportError, NotImplementedError):
        say.note(
            'agent-framework is not installed — pip install "donkey-kit[agent_framework]"'
        )
        say.note(
            "The behaviour is still the point: with the middleware, a policy "
            "refusal ends agent.run() as the typed PIIDetected, not as the "
            "framework's generic client error, and the loop does not retry it."
        )
        return

    agent = Agent(
        client=donkey.agent_framework.chat_client(MODEL), middleware=[middleware]
    )
    # simulate() injects the proxy's PII refusal at the transport, so the agent
    # loop runs for real and no request leaves the process.
    error: BaseException | None = None
    try:
        with donkey.run(id="demo-08-run"), donkey.simulate(PIIDetected):
            await agent.run("my email is jane@example.com")
    except Exception as exc:  # noqa: BLE001 — the exception is what is shown
        error = exc

    if not isinstance(error, PIIDetected):
        got = type(error).__name__ if error else "no error"
        say.fail(f"expected PIIDetected, got {got}")
        # The other acts report what is installed; this one asserts SDK
        # behaviour, so a regression must fail the run rather than read as a pass.
        raise RuntimeError(f"demo 08 act 4: expected PIIDetected, got {got}")
    say.ok("agent.run() raised PIIDetected — terminal, typed, not retried")
    say.field("correlation_id", error.correlation_id, raw=True)
    say.field("entities", getattr(error, "entities", None), raw=True)
    framework_error = getattr(error, "framework_error", None)
    if framework_error is not None:
        say.field("framework_error", type(framework_error).__name__, raw=True)
    print()
    say.note(
        "The middleware protocol is confirmed offline against agent-framework "
        "1.19.0: policy_middleware() is a chat_middleware, streaming included. "
        "Agent Framework wraps every openai error in its own ChatClientException; "
        "the middleware raises the typed DDK refusal instead, with the run's "
        "correlation id, and keeps the framework's exception on .framework_error."
    )


def act_5_honesty() -> None:
    say.section("What is and is not verified here")
    say.note(
        "The proxy contract these objects are configured against is live-verified: "
        "the base URL shape, the credential header pair, the rejection shapes. The "
        "adapters themselves are held to three bars (docs/verified-apis.md §8):"
    )
    say.bullet("Conformance-tested against the simulator: the raw client and LangGraph.")
    say.bullet(
        "Signature-confirmed offline: every other adapter, ADK's model() included. "
        "The SDK's scripts/verify_frameworks.py builds each native object against "
        "the installed framework; Agent Framework's model= kwarg (not model_id) is "
        "confirmed that way against 1.19.0."
    )
    say.bullet("Live-verified: ADK's gemini(), through a Format=Gemini proxy.")
    print()
    say.note(
        "The adapters build the framework's native object directly. They refuse "
        "with 'blocked on verification' only when the installed framework version "
        "lacks the class or field the adapter depends on: an Agent Framework class "
        "rename, or ADK's gemini() before google-adk 2.4."
    )


def main() -> None:
    donkey = Donkey(DEMO_CONFIG)
    act_1_the_roster(donkey)
    say.pause()
    act_2_connection_kwargs(donkey)
    say.pause()
    act_3_openai_agents_kwargs(donkey)
    say.pause()
    asyncio.run(act_4_policy_middleware(donkey))
    act_5_honesty()
    donkey.close()


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 08 — native framework objects",
        subtitle="One deep adapter, seven at connection_kwargs(), and no wrappers anywhere.",
        target="offline",
    )
