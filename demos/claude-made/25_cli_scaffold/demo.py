"""Demo 25 - from code to a publish-ready `.donkey-kit.toml`, offline.

`donkey scan` reads the decorators and names what the code cannot say.
`donkey scaffold` turns that into the declaration tables, `--set` fills the
values you know, and the readiness report says what each workflow still lacks.
Every step runs the real CLI on a temporary copy of `app/`, with no
credentials, no network and your own config out of reach.

    python demos/claude-made/25_cli_scaffold/demo.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from _harness import narrate as say
from _harness import preflight, redact

APP = Path(__file__).resolve().parent / "app"

# Obviously fake. The CLI must refuse these and must never echo them back.
_FAKE_PASSWORD = "demo-password-not-a-real-credential"
_FAKE_SECRET = "demo-secret-not-a-real-credential"


class Project:
    """A temporary project the CLI runs in, isolated from this machine's config."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.home = root / "home"
        self.home.mkdir()
        shutil.copytree(APP, root / "app")
        self.toml = root / ".donkey-kit.toml"

    def donkey(self, *args: str) -> tuple[int, str]:
        env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT") if key in os.environ}
        env.update(HOME=str(self.home), XDG_CONFIG_HOME=str(self.home), NO_COLOR="1")
        result = subprocess.run(
            [sys.executable, "-c", "from donkey_kit.cli import main; main()", *args],
            cwd=self.root,
            env=env,
            text=True,
            capture_output=True,
        )
        return result.returncode, result.stdout + result.stderr


def show(output: str, *, only: tuple[str, ...] = ()) -> None:
    """Print the CLI's own output, indented and masked, optionally just some lines."""
    print()
    for line in output.splitlines():
        if line.strip() and (not only or any(token in line for token in only)):
            print(f"    {redact.text(line)}")
    print()


def act_1_scan(project: Project) -> None:
    say.step(1, "Scan names what the code cannot say")
    say.code("donkey scan")
    code, out = project.donkey("scan")
    show(out)
    assert code == 0, out
    assert "transport undeclared (set transport in [donkey.mcp_servers.sku-manager]" in out
    say.ok("the line names the key to set and the table it lives in")
    say.note(
        "A server without a declaration is not an issue, so the exit code stays 0. "
        "Where it is reached is a deployment fact, not something scan guesses."
    )


def act_2_preview(project: Project) -> None:
    say.step(2, "Scaffold previews the tables and the readiness; it writes nothing")
    say.code("donkey scaffold --dry-run")
    code, out = project.donkey("scaffold", "--dry-run")
    show(out, only=("[donkey.", "readiness", "scan:", "publish:", "expose ", "missing"))
    assert code == 0, out
    assert not project.toml.exists(), "--dry-run must not write the file"
    assert "[donkey.mcp_servers.sku-manager]" in out and "publish: incomplete" in out
    assert "not checked" in out, "readiness must say live state is not checked"
    say.ok("a preview: .donkey-kit.toml does not exist yet")
    say.note(
        "Readiness is read from the committed file only. It never says a service "
        "is verified: doctor, preflight and expose --dry-run check the live side."
    )


def act_3_set_and_refusals(project: Project) -> None:
    say.step(3, "--set fills values you know; credentials and secrets are refused")
    say.code(
        """
        donkey scaffold --set mcp_servers.sku-manager.endpoint=https://demo:<password>@...
        donkey scaffold --set publication.client_secret=<secret>
        """
    )
    code, out = project.donkey(
        "scaffold",
        "--set",
        f"mcp_servers.sku-manager.endpoint=https://demo:{_FAKE_PASSWORD}@sku.example.invalid/mcp",
    )
    show(out)
    assert code == 2 and _FAKE_PASSWORD not in out, out
    code, out = project.donkey(
        "scaffold", "--set", f"publication.client_secret={_FAKE_SECRET}"
    )
    show(out)
    assert code == 2 and _FAKE_SECRET not in out, out
    assert not project.toml.exists(), "a refused --set writes nothing"
    say.ok("both refused with exit 2, nothing written, neither value echoed")

    say.code(
        """
        donkey scaffold --set publication.version=1.0.0 --set publication.group_id=demo-group \\
          --set mcp_servers.sku-manager.transport=streamable-http \\
          --set mcp_servers.sku-manager.endpoint=https://sku.example.invalid/mcp \\
          --set agents.support-triage.protocol=other
        """
    )
    code, out = project.donkey(
        "scaffold",
        "--set",
        "publication.version=1.0.0",
        "--set",
        "publication.group_id=demo-group",
        "--set",
        "mcp_servers.sku-manager.transport=streamable-http",
        "--set",
        "mcp_servers.sku-manager.endpoint=https://sku.example.invalid/mcp",
        "--set",
        "agents.support-triage.protocol=other",
    )
    show(out, only=("created", "scan:", "publish:", "expose ", "missing", "not-exposable"))
    assert code == 0 and project.toml.is_file(), out
    assert "publish: ready" in out
    text = project.toml.read_text(encoding="utf-8")
    assert 'transport = "streamable-http"' in text and "client_secret" not in text
    say.ok("publish is ready; the file holds real values and no secret")
    say.note(
        "Expose is a separate workflow and says what it still lacks: a gateway "
        "target, and an agent with protocol other is not exposable at all."
    )

    before = project.toml.read_bytes()
    code, out = project.donkey("scaffold")
    assert code == 0 and "nothing to add" in out, out
    assert project.toml.read_bytes() == before
    say.ok("a second scaffold adds nothing and leaves the file byte-for-byte alone")


def act_4_invalid(project: Project) -> None:
    say.step(4, "A value that is set but wrong is invalid, not undeclared")
    project.toml.write_text(
        '[donkey.mcp_servers.sku-manager]\ntransport = "websocket"\n', encoding="utf-8"
    )
    say.code("""# .donkey-kit.toml: transport = "websocket"\ndonkey scan""")
    code, out = project.donkey("scan")
    show(out, only=("mcp ", "invalid-", "issue"))
    assert code == 1, out
    assert "transport invalid (see the invalid-transport issue)" in out
    assert "undeclared" not in out, "a set key must not be called undeclared"
    say.ok("exit 1, and the line points at the issue instead of saying to set the key")

    project.toml.write_text(
        '[donkey.mcp_servers.sku-manager]\ntransport = "streamable-http"\n'
        f'endpoint = "https://sku.example.invalid/mcp?api_key={_FAKE_SECRET}"\n',
        encoding="utf-8",
    )
    code, out = project.donkey("scan")
    show(out, only=("mcp ", "invalid-", "issue"))
    assert code == 1 and "endpoint invalid (see the invalid-endpoint issue)" in out, out
    assert _FAKE_SECRET not in out, "a rejected value is never printed"
    say.ok("a credential in the URL is rejected, and the value is not echoed")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ddk-cli-scaffold-") as directory:
        project = Project(Path(directory))
        act_1_scan(project)
        say.pause()
        act_2_preview(project)
        say.pause()
        act_3_set_and_refusals(project)
        say.pause()
        act_4_invalid(project)

    print()
    say.section("The point")
    say.note(
        "The first publish usually fails one missing key at a time. Scan names "
        "the gap, scaffold writes the tables, --set takes the values you know, "
        "and readiness reports what each workflow still needs. All of it is "
        "offline and static: nothing was imported, and nothing here proves the "
        "live gateway, which is what doctor and expose --dry-run are for."
    )


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 25 - donkey scaffold",
        subtitle="From code to a publish-ready .donkey-kit.toml, offline.",
        target="offline",
        extras=("typer",),
    )
