"""Demo 05: the same conformance verdicts in-process and over loopback HTTP."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent


def run_suite(factory: str, mode: str, *, known: str | None = None) -> tuple[int, str]:
    """Run the public plugin with empty home/config and no ambient credentials."""
    args = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--no-header",
        "--show-capture=no",
        "--tb=no",
        "-p",
        "no:cacheprovider",
        "--donkey-conformance",
        f"--donkey-agent=shipping_agent:{factory}",
        f"--donkey-mode={mode}",
    ]
    if known:
        args.append(f"--donkey-known-limitations=exemptions:{known}")
    with TemporaryDirectory(prefix="ddk-conformance-home-") as home:
        env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT") if key in os.environ}
        env.update(HOME=home, XDG_CONFIG_HOME=home, PYTHONPATH=str(HERE), NO_COLOR="1")
        result = subprocess.run(args, cwd=home, env=env, text=True, capture_output=True)
    return result.returncode, result.stdout + result.stderr


def main() -> None:
    """Fail if either mode diverges from the four expected scenario verdicts."""
    print("Demo 05: no external network; server mode uses a local simulator")
    # Use the report rows, not timing-dependent pytest summaries, to match modes.
    verdicts = {}
    for mode in ("in-process", "server"):
        for factory, status, summary in (
            ("build_naive", 1, "1 passed, 3 failed"),
            ("build_governed", 0, "4 passed, 0 failed"),
        ):
            code, output = run_suite(factory, mode)
            assert code == status and summary in output, output
            rows = [
                line.strip()
                for line in output.splitlines()
                if line.strip().startswith(("PASS  ", "FAIL  "))
            ]
            assert len(rows) == 4, output
            verdicts[mode, factory] = rows
            print(f"{mode} / {factory}: exit {code}; {summary}")
            for row in rows:
                print(f"  {row}")
        code, output = run_suite("build_naive", mode, known="FRAMEWORK_LIMITS")
        assert code == 1 and "1 passed, 2 failed, 1 exempt" in output, output
        for known in ("TYPO", "NO_REASON"):
            code, output = run_suite("build_governed", mode, known=known)
            assert code == 4 and "KNOWN_LIMITATIONS" in output, output
        print(f"PASS: {mode} validates asserted exemptions and rejects malformed ones")
    for factory in ("build_naive", "build_governed"):
        assert verdicts["in-process", factory] == verdicts["server", factory]
    print("PASS: identical scenario verdicts and details in both modes")
    print(
        "In-process swaps a counting transport. Server mode leaves the SDK transport "
        "untouched and sends HTTP to an ephemeral loopback port; retries are counted "
        "from the server request log. The harness closes the server in finally, "
        "including on failure. These simulator responses are not live gateway evidence."
    )
    print(
        "Custom classify.register refusal shapes without simulator captures require "
        "in-process mode. For a copyable pytest agent and explicit request-log/cleanup "
        "assertions, see demos/human-made/conformance."
    )


if __name__ == "__main__":
    main()
