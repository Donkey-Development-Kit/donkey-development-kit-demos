"""Demo 05 — a conformance suite someone can run against *your* agent.

The questions here are ones a team usually cannot answer about its own code.
Does your agent retry a budget refusal? Does a typed refusal survive your error
handling, or does it come out as a generic exception? Does your correlation id
reach your logs? Does the agent still work when the gateway sends no budget
headers at all?

It answers them without reading your code: it swaps a fixture-serving transport
underneath, calls `agent.run(...)`, and watches the wire and the logs. So it
grades any agent in any framework, including ones it has never heard of.

    pip install "donkey-kit[test]"
    pytest --donkey-conformance --agent=my_app.agent:build

This demo runs it twice — against an agent written the usual way, then against
the same agent after the findings.

    python demos/claude-made/05_conformance/demo.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from _harness import narrate as say
from _harness import preflight

HERE = Path(__file__).resolve().parent
# The repo root is the ancestor holding `_harness`, found by walking up rather than
# by counting parents: the pytest subprocess below needs it on PYTHONPATH, and
# regrouping the demos into subdirectories would silently shift a fixed depth.
REPO = next(p for p in HERE.parents if (p / "_harness").is_dir())


PLUGIN = "donkey_kit.conformance.plugin"


def _pytest(args: list[str], *, load_plugin: bool) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        "--no-header",
        "-q",
        # The agent under test emits openai/httpx DEBUG logs the harness captures
        # for the correlation scenario. They are the suite working correctly, but
        # printing them buries the four findings — and replays captured
        # correlation ids into the transcript.
        "--show-capture=no",
        "--tb=no",
    ]
    if load_plugin:
        command += ["-p", PLUGIN]
    command += args
    # The agent module is on the path the way a customer's own package would be.
    return subprocess.run(
        command,
        cwd=REPO,
        capture_output=True,
        text=True,
        env={**_clean_env(), "PYTHONPATH": f"{HERE}{os.pathsep}{REPO}"},
    )


def _run_suite(factory: str, *, known: str | None = None) -> tuple[int, str]:
    args = ["--donkey-conformance", f"--agent=shipping_agent:{factory}"]
    if known:
        args.append(f"--donkey-known-limitations={known}")

    result = _pytest(args, load_plugin=False)
    if "unrecognized arguments" in result.stderr + result.stdout:
        # The plugin normally auto-loads from donkey-kit's pytest11 entry point.
        # An editable install whose metadata predates the plugin will not have it
        # registered, so load it by module instead — same plugin, same run.
        result = _pytest(args, load_plugin=True)
    return result.returncode, result.stdout + result.stderr


def _entry_point_registered() -> bool:
    from importlib.metadata import entry_points

    return any(e.value == PLUGIN for e in entry_points().select(group="pytest11"))


def _clean_env() -> dict[str, str]:
    """Run the suite with the ambient proxy config removed.

    The harness never reaches the network — it swaps the transport for every
    scenario — but stripping the variables makes that visible rather than
    something the audience has to take on trust.
    """
    return {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("DONKEY_LLM_PROXY", "ANYPOINT_"))
    }


def _echo(output: str) -> None:
    """Print pytest's output, scrubbed. Defence in depth: the suite runs against
    fixtures that carry captured identifiers, and a subprocess's stdout is not
    something the narrate helpers have already masked."""
    from _harness import redact

    for line in redact.text(output).splitlines():
        if line.strip():
            print(f"    {line}")


def act_1_the_naive_agent() -> None:
    say.step(1, "An agent written the way people actually write them")
    say.code(
        """
        for attempt in range(3):                     # retry on failure
            try:
                return await client.responses.create(...)
            except openai.APIStatusError as exc:
                if attempt == 2:
                    raise RuntimeError(...) from exc  # friendly error
        """
    )
    say.note(
        "Nothing there is obviously wrong. Retrying is a sane default, wrapping "
        "errors keeps stack traces out of the caller's face, and it logs what it "
        "is doing. Run the suite against it."
    )
    say.code("pytest --donkey-conformance --agent=…:build_naive")

    code, output = _run_suite("build_naive")
    print()
    _echo(output)
    print()
    say.field("exit status", code, raw=True)


def act_2_the_findings() -> None:
    say.section("What each failure actually means")
    say.bullet(
        "Retried a TokenBudgetExceeded 3× — the window is already exhausted, so "
        "the retries cannot succeed and the extra calls make the rate-limit "
        "situation worse for everyone else on the same budget."
    )
    say.bullet(
        "Raised a bare RuntimeError for a PII block — the caller wanted to catch "
        "PIIDetected and redact the flagged entities. It cannot, because the type "
        "was thrown away in the name of a friendlier message."
    )
    say.bullet(
        "Never logged the correlation id — so when the platform team asks which "
        "gateway request corresponds to this run, there is no answer."
    )


def act_3_the_governed_agent() -> None:
    say.step(2, "The same agent, after the findings")
    say.code(
        """
        try:
            return await client.responses.create(...)
        except openai.APIStatusError as exc:
            error = classify(exc.response)
            log.warning("governed refusal", extra={
                "correlation_id": current_correlation_id(),
                "refusal": type(error).__name__,
            })
            raise error from exc          # typed, and not retried
        """
    )
    code, output = _run_suite("build_governed")
    print()
    _echo(output)
    print()
    say.field("exit status", code, raw=True)


def act_4_exemptions() -> None:
    say.step(3, "When an agent genuinely cannot pass, it says so out loud")
    say.note(
        "Suppose the correlation finding is not fixable: your framework owns the "
        "HTTP transport and gives you no per-request hook. That is a real "
        "limitation, so you assert it — with a reason — and it becomes an `exempt` "
        "row rather than a failure. It is never a silent skip, and the reason is "
        "meant to be published."
    )
    say.code(
        """
        # exemptions.py
        FRAMEWORK_LIMITS = {
            "correlation_id_propagated": "This agent's framework owns the HTTP …",
        }

        pytest --donkey-conformance --agent=shipping_agent:build_naive \\
               --donkey-known-limitations=exemptions:FRAMEWORK_LIMITS
        """
    )
    code, output = _run_suite("build_naive", known="exemptions:FRAMEWORK_LIMITS")
    print()
    _echo(output)
    print()
    say.field("exit status", code, raw=True)
    say.note(
        "One row moved to EXEMPT with its reason attached. The other two findings "
        "are untouched — an exemption excuses exactly what it names."
    )


def act_5_bad_exemptions() -> None:
    say.step(4, "And an exemption you get wrong fails the run, loudly")
    say.note(
        "The mapping is validated at collection time, before any scenario runs. "
        "A typo'd scenario name would otherwise exempt nothing while looking like "
        "it exempted something, and an empty reason is a skip wearing a costume."
    )

    for name, description in (
        ("TYPO", "a misspelled scenario name"),
        ("NO_REASON", "an exemption with an empty reason"),
    ):
        print()
        say.field("case", description)
        code, output = _run_suite("build_governed", known=f"exemptions:{name}")
        for line in output.splitlines():
            if "ERROR" in line or "KNOWN_LIMITATIONS" in line:
                print(f"    {line.strip()}")
        say.field("exit status", code, raw=True)


def main() -> None:
    if not _entry_point_registered():
        say.warn(
            "donkey-kit's pytest11 entry point is not registered in this "
            "environment, so the plugin is being loaded with `-p "
            f"{PLUGIN}` instead. Re-run `pip install -e python` in the SDK "
            "checkout to refresh the metadata and get the plain invocation."
        )
    act_1_the_naive_agent()
    act_2_the_findings()
    say.pause()
    act_3_the_governed_agent()
    say.pause()
    act_4_exemptions()
    act_5_bad_exemptions()

    print()
    say.section("The point")
    say.note(
        "This is the deliverable, not our internal adapter matrix. It ships as a "
        "pytest plugin so it runs in your CI, against your agent, in whatever "
        "framework you chose — and it needs no gateway to do it."
    )


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 05 — the conformance suite",
        subtitle="Four questions about your agent that you cannot currently answer.",
        target="offline",
        extras=("pytest", "openai"),
    )
