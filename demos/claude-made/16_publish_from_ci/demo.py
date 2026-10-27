"""Demo 16 — publish an MCP server to Exchange from CI.

`server/` is a one-tool MCP server: the tool is declared in code with
`@donkey.tool(server=...)`, and `.donkey-kit.toml` says which version to
publish and where the server is reached. `donkey publish` turns that into an
Exchange asset. The scan-and-publish GitHub Action runs it on every PR (a dry
run) and on every push to `develop` (a real publish):
`.github/workflows/publish-from-ci.yml`.

This demo is the offline half: the plan the PR job prints, how its digest
moves, and the workflow. Nothing is sent.

    python demos/claude-made/16_publish_from_ci/demo.py
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from _harness import narrate as say
from _harness import preflight, redact

HERE = Path(__file__).resolve().parent
SERVER = HERE / "server"
WORKFLOW = HERE.parents[2] / ".github" / "workflows" / "publish-from-ci.yml"

# Obviously fake: the dry run needs a group ID, and the real one (the org ID)
# is a repository secret, never a value in this repo.
_FAKE_ORG = "demo-org-id-not-real"


def _isolated_env() -> dict[str, str]:
    # No real Anypoint credential reaches the CLI, whatever this shell has set.
    env = {
        k: v for k, v in os.environ.items() if not k.startswith(("DONKEY_", "ANYPOINT_"))
    }
    env.update({"ANYPOINT_ORG_ID": _FAKE_ORG, "NO_COLOR": "1"})
    return env


def _plan(path: Path) -> tuple[int, dict[str, object]]:
    """`donkey --json publish <path> --dry-run`, in-process."""
    from donkey_kit.cli import app
    from typer.testing import CliRunner

    result = CliRunner().invoke(
        app, ["--json", "publish", str(path), "--dry-run"], env=_isolated_env()
    )
    try:
        return result.exit_code, json.loads(result.stdout)
    except json.JSONDecodeError:
        say.warn(redact.text(result.stdout + (result.stderr or "")) or "no output")
        return result.exit_code, {}


def act_1_the_plan() -> str:
    say.step(1, "The PR job: a dry run prints what would be published")
    say.code(
        """
        donkey publish demos/claude-made/16_publish_from_ci/server --dry-run
        """
    )
    code, plan = _plan(SERVER)
    say.field("exit", code, raw=True)
    assets = plan.get("assets") or []
    for asset in assets:  # type: ignore[union-attr]
        say.field("type", asset["type"], raw=True)
        say.field(
            "asset", f"{asset['group_id']}:{asset['asset_id']}:{asset['version']}", raw=True
        )
        say.field("tools", asset["tools"], raw=True)
        say.field("endpoint", asset["endpoint"], raw=True)
        say.field("digest", asset["digest"], raw=True)
    print()
    if code == 0 and len(assets) == 1:  # type: ignore[arg-type]
        say.ok("one MCP server, from one decorator and one toml table; nothing was sent")
    else:
        say.fail("expected one asset and exit 0")
    say.note(
        "The group is the org ID (a fake one here). In CI it comes from the "
        "ANYPOINT_ORG_ID secret, so no org identifier is committed."
    )
    return str(assets[0]["digest"]) if assets else ""  # type: ignore[index]


def act_2_the_digest(digest: str) -> None:
    say.step(2, "The digest is the code: same code, same digest; edit a tool, new digest")
    _, again = _plan(SERVER)
    same = (again.get("assets") or [{}])[0].get("digest")  # type: ignore[union-attr]
    say.field("run again", same, raw=True)
    if same == digest:
        say.ok("deterministic: a merge that changes nothing publishes nothing")

    edited = Path(tempfile.mkdtemp(prefix="donkey-publish-")) / "server"
    try:
        shutil.copytree(SERVER, edited)
        app_py = edited / "app.py"
        app_py.write_text(
            app_py.read_text().replace("name, price and stock level", "name and price only")
        )
        _, changed = _plan(edited)
    finally:
        shutil.rmtree(edited.parent, ignore_errors=True)
    moved = (changed.get("assets") or [{}])[0].get("digest")  # type: ignore[union-attr]
    say.field("docstring edited", moved, raw=True)
    if moved and moved != digest:
        say.ok("a tool's description is part of the contract, so the digest moved")
    print()
    say.note(
        "On develop the action publishes with --if-changed: an unchanged digest "
        "is left alone. A changed digest at a version Exchange already has stops "
        "before sending and asks you to bump `version` in .donkey-kit.toml."
    )


def act_3_the_workflow() -> None:
    say.step(3, "The workflow: dry run on PRs, real publish on develop")
    if not WORKFLOW.is_file():
        say.fail(f"missing {WORKFLOW.name}")
        return
    text = WORKFLOW.read_text()
    start = text.index("      - uses: Donkey-Development-Kit/")
    print()
    for line in text[start:].splitlines()[:9]:
        print(f"    {line[6:].split(' # zizmor')[0]}")
    print()
    say.ok(
        "the credentials are secrets, passed as inputs; the action masks the client secret"
    )
    say.note(
        "The job summary shows the plan on a PR and each asset's status after a "
        "publish. A failed publish fails the job, with donkey's error lines as "
        "annotations. Fork PRs get no secrets, so the job skips them."
    )


def main() -> None:
    digest = act_1_the_plan()
    say.pause()
    act_2_the_digest(digest)
    say.pause()
    act_3_the_workflow()

    print()
    say.section("The point")
    say.note(
        "The registry entry is a consequence of the code. Decorate the tool, "
        "set a version, merge: CI publishes it, and a merge that changes "
        "nothing publishes nothing."
    )


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 16 — publish from CI",
        subtitle="An MCP server declared in code, published to Exchange by the GitHub Action.",
        target="offline",
        extras=("typer",),
    )
