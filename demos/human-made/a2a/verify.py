"""Verify the real localhost Donkey.serve launcher in an isolated subprocess."""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    """Check card/tasks over TCP, then require graceful shutdown within a timeout."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port", type=int, default=0, help="0 selects a free loopback port"
    )
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    for module in ("httpx", "a2a", "starlette", "uvicorn"):
        if importlib.util.find_spec(module) is None:
            print('Missing prerequisites: pip install "donkey-kit[a2a]"')
            raise SystemExit(1)

    import httpx

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", args.port))
        port = probe.getsockname()[1]
    # The child binds after this socket closes: a competing process can still
    # claim the port. Startup failure is bounded and reported, never ignored.
    base_url = f"http://127.0.0.1:{port}"
    script = Path(__file__).with_name("01 - serve.py")
    # Allowlist instead of passing shell proxy/OTEL/DDK credentials to the child.
    env = {
        key: os.environ[key]
        for key in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT")
        if key in os.environ
    }
    env.update(PYTHONUNBUFFERED="1", NO_PROXY="127.0.0.1,localhost")
    assert not any(
        key.startswith(("OTEL_", "DONKEY_", "ANYPOINT_"))
        or key.upper().endswith("_PROXY")
        and key != "NO_PROXY"
        for key in env
    )
    process = subprocess.Popen(
        [sys.executable, str(script), "--port", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = ""
    try:
        with httpx.Client(base_url=base_url, timeout=1.0, trust_env=False) as client:
            deadline = time.monotonic() + 10
            while True:
                assert process.poll() is None, "launcher exited before readiness"
                try:
                    response = client.get("/.well-known/agent-card.json")
                    response.raise_for_status()
                    break
                except httpx.HTTPError:
                    if time.monotonic() >= deadline:
                        raise AssertionError(
                            "localhost launcher readiness exceeded 10 seconds"
                        ) from None
                    time.sleep(0.05)
            card = response.json()
            assert card["name"] == "localhost-helper"
            assert card["version"] == "1.0.0"
            assert [skill["id"] for skill in card["skills"]] == ["local-result"]
            (interface,) = card["supportedInterfaces"]
            assert interface["url"] == f"{base_url}/"
            assert interface["protocolVersion"] == "1.0"
            print(
                "PASS: real blocking Donkey.serve subprocess ready; generated A2A card fetched over TCP"
            )

            tasks = []
            for i, (text, headers) in enumerate(
                (
                    ("success", {"X-Correlation-Id": "launcher-adopted"}),
                    ("refuse", {"X-Correlation-Id": "launcher-refused"}),
                    ("success", {}),
                )
            ):
                response = client.post(
                    "/",
                    headers={"A2A-Version": "1.0", **headers},
                    json={
                        "jsonrpc": "2.0",
                        "id": i + 1,
                        "method": "SendMessage",
                        "params": {
                            "message": {
                                "messageId": f"launcher-{i}",
                                "role": "ROLE_USER",
                                "parts": [{"text": text}],
                            }
                        },
                    },
                )
                response.raise_for_status()
                payload = response.json()
                assert "error" not in payload
                tasks.append(payload["result"]["task"])
            first, failed, recovered = tasks
            assert (
                first["status"]["state"]
                == recovered["status"]["state"]
                == "TASK_STATE_COMPLETED"
            )
            assert first["artifacts"][0]["parts"] == [{"text": "completed locally"}]
            assert (
                first["artifacts"][1]["parts"][0]["data"]["correlation_id"]
                == "launcher-adopted"
            )
            minted = recovered["artifacts"][1]["parts"][0]["data"]["correlation_id"]
            assert re.fullmatch(r"[0-9a-f]{32}", minted)
            assert failed["status"]["state"] == "TASK_STATE_FAILED"
            assert failed["status"]["message"]["parts"][1]["data"]["error"] == {
                "type": "PIIDetected",
                "refusal": True,
                "correlation_id": "launcher-refused",
            }
            assert "synthetic-handler-detail-not-for-the-caller" not in str(failed)
            assert "Traceback" not in str(failed)
            assert len({task["id"] for task in tasks}) == 3
            assert process.poll() is None, (
                "launcher did not remain blocking after task completion"
            )
            print(
                "PASS: success -> synthetic PIIDetected failed task -> continued success over loopback"
            )
            print(
                "PASS: incoming ID adopted; absent ID minted; refusal message/traceback not returned"
            )

        process.send_signal(signal.SIGINT)
        output, _ = process.communicate(timeout=5)
        assert process.returncode == 0, f"launcher shutdown exit={process.returncode}"
        assert "Application shutdown complete." in output
        assert "PASS: blocking donkey.serve returned; Donkey transports closed" in output
        with socket.socket() as probe:
            assert probe.connect_ex(("127.0.0.1", port)) != 0, (
                "listener remained reachable after shutdown"
            )
        print(
            "PASS: SIGINT drained uvicorn lifespan; blocking launcher returned; child exit=0 within 5s"
        )
        print(
            "PASS: listener closed; no child left running; child environment excludes proxies/OTEL/credentials"
        )
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                output, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                output, _ = process.communicate(timeout=2)
        # Do not print raw server logs (they intentionally include operator-only
        # exception detail). All asserted response output above is synthetic.
        if process.stdout is not None:
            process.stdout.close()


if __name__ == "__main__":
    main()
