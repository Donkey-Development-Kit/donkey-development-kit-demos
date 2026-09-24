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

No network calls are made — objects are only constructed.

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
        "LangGraph is the only adapter held to the conformance bar, and it sets "
        "use_responses_api=True so ChatOpenAI calls the live-verified /responses "
        "route rather than the unverified /chat/completions default."
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


async def act_4_policy_middleware() -> None:
    say.step(4, "Agent Framework: policy_middleware() does not retry a refusal")
    say.code(
        """
        mw = donkey.agent_framework.policy_middleware()
        # a PolicyViolation from next_ is re-raised — the loop does not retry
        """
    )
    from donkey_kit import PIIDetected
    from donkey_kit.core.transport import build_http_client
    from donkey_kit.integrations.agent_framework import AgentFrameworkAdapter

    # Constructed directly so this act runs without the [agent-framework] extra.
    # donkey.agent_framework would ImportError until that extra is installed;
    # policy_middleware() itself imports no framework classes.
    http = build_http_client(DEMO_CONFIG, None)
    adapter = AgentFrameworkAdapter(DEMO_CONFIG, http)
    middleware = adapter.policy_middleware()

    async def boom(_context: object) -> None:
        raise PIIDetected("blocked")

    try:
        await middleware(None, boom)
        say.fail("expected PIIDetected to be re-raised")
    except PIIDetected:
        say.ok("PIIDetected re-raised — terminal, not swallowed, not retried")
    finally:
        await http.aclose()
    print()
    say.note(
        "The middleware signature Agent Framework actually expects is still "
        "unverified — this is a plain async wrapper that re-raises. Once the "
        "protocol is confirmed, the same function will set the framework's "
        "explicit terminate-run signal instead of raising. The behaviour that "
        "is shipped: a policy refusal is not a retryable error."
    )


def act_5_honesty() -> None:
    say.section("What is and is not verified here")
    say.note(
        "The proxy contract these objects are configured against is live-verified: "
        "the base URL shape, the credential header pair, the rejection shapes. "
        "Agent Framework's OpenAIChatClient(model=…, base_url, api_key, "
        "default_headers) is verified against 1.19.0 — the kwarg is model=, not "
        "model_id. The other framework class names and constructor kwargs are "
        "checked against installed packages by a nightly matrix rather than "
        "asserted from documentation."
    )
    say.note(
        "Where a class name cannot be confirmed, the adapter raises 'blocked on "
        "verification' rather than guessing. A guessed class name that fails on a "
        "developer's first import costs more than the missing adapter."
    )


def main() -> None:
    donkey = Donkey(DEMO_CONFIG)
    act_1_the_roster(donkey)
    say.pause()
    act_2_connection_kwargs(donkey)
    say.pause()
    act_3_openai_agents_kwargs(donkey)
    say.pause()
    asyncio.run(act_4_policy_middleware())
    act_5_honesty()
    donkey.close()


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 08 — native framework objects",
        subtitle="One deep adapter, seven at connection_kwargs(), and no wrappers anywhere.",
        target="offline",
    )
