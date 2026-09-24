"""Demo 11 — `donkey init` writes a config file that never holds a secret.

The four-command CLI is `init`, `doctor`, `mock`, `test`. Doctor needs a live
proxy; mock and test have their own demos (04, 05). Init is the one that pays
for itself in the first five minutes: it writes a commented `.donkey-kit.toml`
from whatever is already resolved, names every missing required field at once
(the same report `DonkeyConfig.validated` uses), and refuses to put a secret
in the file.

    python demos/claude-made/11_cli_init/demo.py
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from _harness import narrate as say
from _harness import preflight, redact

# Obviously fake. Init must list them as missing or write the non-secret ones
# as values — and must NEVER copy the secret into the toml.
_FAKE_URL = "https://demo-gateway.example.invalid/openai-sdk/"
_FAKE_ID = "demo-client-id-not-a-real-credential"
_FAKE_SECRET = "demo-client-secret-not-a-real-credential"


def _isolated_env() -> dict[str, str]:
    # Strip every Donkey/Anypoint var and XDG_CONFIG_HOME so from_env() cannot
    # pick up a real .donkey-kit.toml or a real secret from this machine.
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("DONKEY_", "ANYPOINT_")) and k != "XDG_CONFIG_HOME"
    }
    env.update(
        {
            "DONKEY_LLM_PROXY_URL": _FAKE_URL,
            "DONKEY_LLM_PROXY_CLIENT_ID": _FAKE_ID,
            "DONKEY_LLM_PROXY_CLIENT_SECRET": _FAKE_SECRET,
            "NO_COLOR": "1",
        }
    )
    return env


def _invoke_init(target: Path, *, force: bool = False) -> tuple[int, str]:
    from donkey_kit.provisioning.cli import app
    from typer.testing import CliRunner

    args = ["--json", "--config", str(target), "init"]
    if force:
        args.append("--force")
    previous = Path.cwd()
    try:
        os.chdir(target.parent)
        result = CliRunner().invoke(app, args, env=_isolated_env())
    finally:
        os.chdir(previous)
    return result.exit_code, (result.stdout or "") + (result.stderr or "")


def act_1_writes_and_names_gaps() -> Path:
    say.step(1, "donkey init writes a commented toml and lists every gap at once")
    say.code(
        """
        donkey --json --config .donkey-kit.toml init
        """
    )
    tmp = Path(tempfile.mkdtemp(prefix="donkey-init-")) / ".donkey-kit.toml"
    code, output = _invoke_init(tmp)
    say.field("exit", code, raw=True)
    try:
        payload = json.loads(output.strip().splitlines()[-1])
    except json.JSONDecodeError:
        say.warn(redact.text(output) or "no json")
        payload = {}
    say.field("written", payload.get("written"), raw=True)
    missing = payload.get("missing") or []
    if missing:
        say.table({item: "missing" for item in missing}, title_="still missing")
    if tmp.is_file():
        say.ok(f"wrote {tmp.name} in a temp directory — not your repo")
    return tmp


def act_2_secrets_stay_out(target: Path) -> None:
    say.step(2, "Secrets are env pointers, never values in the file")
    text = target.read_text() if target.is_file() else ""
    if _FAKE_SECRET in text:
        say.fail("the proxy client_secret was written into the toml")
    else:
        say.ok("client_secret is not in the file")
    if "llm_proxy_client_secret" in text.lower() or "client_secret" in text:
        say.note(
            "The key may appear as a commented env pointer. That is the point — "
            "the file names what to set, it does not hold the value."
        )
    # Show a few non-secret lines, redacted in case a hostname slipped in.
    print()
    for line in text.splitlines()[:12]:
        if line.strip():
            print(f"    {redact.text(line)}")
    print()
    say.note(
        "Idempotent: a second init leaves the file untouched unless --force. "
        "doctor / mock / test are the other three shipped commands — doctor "
        "against the local simulator is demo 14; mock and test are 04 and 05."
    )


def act_3_idempotent(target: Path) -> None:
    say.step(3, "A second init does not clobber")
    before = target.read_text() if target.is_file() else ""
    code, output = _invoke_init(target)
    try:
        payload = json.loads(output.strip().splitlines()[-1])
    except json.JSONDecodeError:
        payload = {}
    say.field("exit", code, raw=True)
    say.field("written", payload.get("written"), raw=True)
    after = target.read_text() if target.is_file() else ""
    if after == before and payload.get("written") is False:
        say.ok("left the existing file untouched")
    target.unlink(missing_ok=True)
    target.parent.rmdir()


def main() -> None:
    target = act_1_writes_and_names_gaps()
    say.pause()
    act_2_secrets_stay_out(target)
    say.pause()
    act_3_idempotent(target)

    print()
    say.section("The point")
    say.note(
        "The first five minutes of an SDK are usually one-missing-variable-per-run. "
        "init reports everything at once, writes nothing secret, and will not "
        "overwrite a file you already edited."
    )


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 11 — donkey init",
        subtitle="A commented config file, every gap named at once, no secrets on disk.",
        target="offline",
        extras=("typer",),
    )
