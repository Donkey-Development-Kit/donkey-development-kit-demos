"""Demo 14 — `donkey doctor` tells three look-alike failures apart.

Wrong URL, wrong credentials, and credentials-fine-but-model-rejected all look
like "it doesn't work" from the outside. Doctor makes one governed call and
reads the result through the same taxonomy demo 02 walks, so the CLI and the
exceptions never disagree about the next step.

This run is against the local simulator, not a live sandbox. Incomplete
config needs no network at all.

    python demos/claude-made/14_cli_doctor/demo.py
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from _harness import narrate as say
from _harness import preflight, redact

_FAKE_ID = "demo-client-id-not-a-real-credential"
_FAKE_SECRET = "demo-client-secret-not-a-real-credential"


def _base_env() -> dict[str, str | None]:
    env: dict[str, str | None] = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("DONKEY_", "ANYPOINT_")) and k != "XDG_CONFIG_HOME"
    }
    env["NO_COLOR"] = "1"
    # CliRunner merges into os.environ; None pops a leftover parent value.
    for key in (
        "DONKEY_LLM_PROXY_URL",
        "DONKEY_LLM_PROXY_CLIENT_ID",
        "DONKEY_LLM_PROXY_CLIENT_SECRET",
        "DONKEY_LLM_PROXY_AUTH",
        "DONKEY_LLM_PROXY_WALLET_CLIENT_ID",
        "XDG_CONFIG_HOME",
    ):
        env[key] = None
    return env


def _invoke_doctor(env: dict[str, str | None], *args: str) -> tuple[int, str]:
    from donkey_kit.provisioning.cli import app
    from typer.testing import CliRunner

    tmp = Path(tempfile.mkdtemp(prefix="donkey-doctor-"))
    previous = Path.cwd()
    try:
        os.chdir(tmp)
        result = CliRunner().invoke(app, ["--json", "doctor", *args], env=env)
    finally:
        os.chdir(previous)
        tmp.rmdir()
    return result.exit_code, result.stdout or ""


def _rows(output: str) -> list[dict[str, object]]:
    text = output.strip()
    start = text.find("[")
    if start < 0:
        say.warn(redact.text(output) or "no json")
        return []
    try:
        payload = json.loads(text[start:])
    except json.JSONDecodeError:
        say.warn(redact.text(output) or "no json")
        return []
    return payload if isinstance(payload, list) else []


def _show(rows: list[dict[str, object]]) -> None:
    for row in rows:
        name = str(row.get("name", ""))
        level = str(row.get("level", ""))
        detail = redact.text(str(row.get("detail") or ""))
        say.field(f"{level} {name}", detail)


def act_1_incomplete_config() -> None:
    say.step(1, "Incomplete config exits 1 and names every missing field")
    say.code("donkey --json doctor")
    code, output = _invoke_doctor(_base_env())
    say.field("exit", code, raw=True)
    rows = _rows(output)
    _show(rows)
    config = next((r for r in rows if r.get("name") == "config"), None)
    if code == 1 and config is not None and config.get("level") == "fail":
        say.ok("config failed before any probe — no network")
    print()
    say.note(
        "This is the same all-at-once report DonkeyConfig.validated uses. "
        "gateway / credentials / model stay [--] not-checked rather than guessed."
    )


def act_2_against_the_simulator() -> None:
    say.step(2, "Pointed at start_gateway(), doctor sees a reachable proxy")
    say.code(
        """
        gw = start_gateway()
        # point DONKEY_LLM_PROXY_URL at gw.url, then:
        donkey doctor
        """
    )
    from donkey_kit.conformance.gateway import start_gateway

    gw = start_gateway()
    try:
        env = _base_env()
        env.update(
            {
                "DONKEY_LLM_PROXY_URL": gw.url.rstrip("/") + "/",
                "DONKEY_LLM_PROXY_CLIENT_ID": _FAKE_ID,
                "DONKEY_LLM_PROXY_CLIENT_SECRET": _FAKE_SECRET,
                "DONKEY_TIMEOUT_S": "5",
                "DONKEY_MAX_RETRIES": "0",
            }
        )
        code, output = _invoke_doctor(env, "--model", "gpt-4o")
    finally:
        gw.close()

    say.field("exit", code, raw=True)
    rows = _rows(output)
    _show(rows)
    names = {str(r.get("name")): str(r.get("level")) for r in rows}
    if names.get("gateway") == "ok" and names.get("credentials") == "ok":
        say.ok("gateway reachable, credentials accepted — the simulator enforces no auth")
    budget = next((r for r in rows if r.get("name") == "budget"), None)
    if budget is not None:
        say.note(
            "The budget line always says how stale the reading is. Doctor never "
            "implies a live query — there is no budget endpoint."
        )


def act_3_dead_origin() -> None:
    say.step(3, "Nothing listening → gateway fail, credentials not checked")
    env = _base_env()
    env.update(
        {
            "DONKEY_LLM_PROXY_URL": "http://127.0.0.1:9/",
            "DONKEY_LLM_PROXY_CLIENT_ID": _FAKE_ID,
            "DONKEY_LLM_PROXY_CLIENT_SECRET": _FAKE_SECRET,
            "DONKEY_TIMEOUT_S": "2",
            "DONKEY_MAX_RETRIES": "0",
        }
    )
    code, output = _invoke_doctor(env)
    say.field("exit", code, raw=True)
    rows = _rows(output)
    _show(rows)
    names = {str(r.get("name")): str(r.get("level")) for r in rows}
    if names.get("gateway") == "fail" and names.get("credentials") == "skip":
        say.ok("GatewayUnavailable — credentials skipped, not guessed as AuthError")
    print()
    say.note(
        "Wrong credentials would be [!!] credentials with the data-plane "
        "AuthError remediation (DONKEY_LLM_PROXY_*), and a model_not_found "
        "passthrough would be [!!] model after credentials passed. Live doctor "
        "against a real proxy is the same CLI; this demo does not need one."
    )


def main() -> None:
    act_1_incomplete_config()
    say.pause()
    act_2_against_the_simulator()
    say.pause()
    act_3_dead_origin()

    print()
    say.section("The point")
    say.note(
        "Three look-alike failures, one probe, the same remediation strings the "
        "typed errors carry. Do not confuse this with `make doctor` in this "
        "repo — that one reports which extras are installed."
    )


if __name__ == "__main__":
    preflight.cli(
        main,
        title="Demo 14 — donkey doctor",
        subtitle="Wrong URL, wrong credentials, or model-not-allowed — one probe tells them apart.",
        target="offline",
        extras=("typer", "openai", "uvicorn"),
    )
