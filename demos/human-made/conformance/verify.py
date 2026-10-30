"""Run ordinary tests and both public plugin modes with no ambient config."""

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent


def main() -> None:
    """Assert pytest exit codes as well as all four plugin scenario verdicts."""
    for mode in (None, "in-process", "server"):
        args = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "--show-capture=no",
        ]
        if mode:
            args += [
                "--donkey-conformance",
                "--donkey-agent=agent:build",
                f"--donkey-mode={mode}",
            ]
        else:
            args.append(str(HERE / "test_agent.py"))
        with TemporaryDirectory(prefix="ddk-pytest-home-") as home:
            env = {
                key: os.environ[key] for key in ("PATH", "SYSTEMROOT") if key in os.environ
            }
            env.update(HOME=home, XDG_CONFIG_HOME=home, PYTHONPATH=str(HERE), NO_COLOR="1")
            result = subprocess.run(args, cwd=home, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        if mode:
            assert "4 passed, 0 failed" in result.stdout, result.stdout
        else:
            assert "3 passed" in result.stdout, result.stdout
        print(f"PASS: {mode or 'ordinary pytest'}; exit {result.returncode}")
        print(result.stdout)


if __name__ == "__main__":
    main()
