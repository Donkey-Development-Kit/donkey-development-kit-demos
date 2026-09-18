"""Demo 08 — your framework's own object, already pointed at the governed proxy.

No adapter returns a wrapper. `donkey.langgraph.chat_model(...)` hands back a
real `langchain_openai.ChatOpenAI`, so everything LangChain can do with a chat
model still works, and nothing new appears in your stack traces.

The roster is deliberately uneven, and it is worth saying why rather than
implying eight equal integrations. One framework — LangGraph — is the deep,
conformance-gated adapter. The other seven are supported at the
`connection_kwargs()` level: the SDK gives you the base URL, headers and client
configuration, and you pass them to the framework's own constructor. That makes
`connection_kwargs()` the most load-bearing method here, not the least, because
it is the entire supported surface for seven of the eight.

No network calls are made — objects are only constructed.

    python demos/claude-made/08_framework_objects/demo.py
"""

from __future__ import annotations

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
# have it. It is also the one adapter with no connection_kwargs(), because it
# builds an AsyncOpenAI internally.
ROSTER = [
    ("langgraph", "chat_model", True, "deep — the conformance-gated adapter"),
    ("adk", "model", True, "connection_kwargs()"),
    ("strands", "model", True, "connection_kwargs()"),
    ("agent_framework", "chat_client", True, "connection_kwargs()"),
    ("openai_agents", "model", True, "no connection_kwargs() — builds its own client"),
    ("anthropic", "client", False, "connection_kwargs()"),
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
        "Same base URL, same verified client_id / client_secret pair, handed to "
        "the framework's own constructor. Bringing a framework up to the deep bar "
        "is demand-driven and happens one at a time, so this is not a stepping "
        "stone that everything is queued behind — it is the supported surface."
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


def act_3_honesty() -> None:
    say.section("What is and is not verified here")
    say.note(
        "The proxy contract these objects are configured against is live-verified: "
        "the base URL shape, the credential header pair, the rejection shapes. The "
        "exact framework class names and constructor kwargs are not — they are "
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
    act_3_honesty()
    donkey.close()


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 08 — native framework objects",
        subtitle="One deep adapter, seven at connection_kwargs(), and no wrappers anywhere.",
        target="offline",
    )
