"""Demo 16: static registration and the existing CI workflow, entirely offline."""

import sys
from pathlib import Path

from _harness import narrate as say
from _harness import preflight

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    """Assert the offline contract, then explain the separate CI publication path."""
    from offline import SERVER, cli, verify

    say.step(1, "Static inventory and the PR dry-run plan")
    say.code(
        "donkey scan demos/claude-made/16_publish_from_ci/server --json\n"
        "donkey publish demos/claude-made/16_publish_from_ci/server --dry-run --json"
    )
    verify(report=lambda message: say.ok(message.removeprefix("PASS: ")))
    code, plan, _ = cli("publish", SERVER)
    assert code == 0
    asset = plan["assets"][0]
    for key in ("type", "asset_id", "name", "version", "tools", "endpoint", "digest"):
        say.field(key, asset[key])
    say.field("protocol_version", asset["protocol_version"])
    say.field("provider", asset["provider"]["organization"])
    say.field("documentation", asset["documentation"])
    say.pause()
    say.step(2, "The existing CI workflow, inspected but not executed")
    workflow = Path(__file__).resolve().parents[3] / ".github/workflows/publish-from-ci.yml"
    text = workflow.read_text(encoding="utf-8")
    assert "Donkey-Development-Kit/donkey-development-kit/action@develop" in text
    say.ok("existing scan-and-publish CI workflow inspected, not executed")
    say.note(
        "The workflow dry-runs on PRs and publishes on develop. Fork PRs get no "
        "secrets and are skipped. Credentials remain CI secret inputs, not demo values."
    )
    say.pause()
    say.section("Registration, not deployment")
    say.note(
        "The CLI's default --if-changed skips matching published content digests. "
        "Changed content at an existing immutable Exchange version requires a version bump. "
        "These are publication semantics, not a claim that this offline run contacted Exchange."
    )
    say.note(
        "Registration is not deployment or provisioning. Agent publication is skipped. "
        "Connected-app publication authentication remains unconfirmed live: "
        "user-session captures do not establish it. Live CI publication stays separate."
    )


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 16 - publish from CI",
        subtitle="Static inventory, deterministic digests and invalid declarations.",
        target="offline",
        extras=("typer",),
    )
