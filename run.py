#!/usr/bin/env python3
"""Run one demo, or all the offline ones, without worrying about `PYTHONPATH`.

    python run.py                 # list the demos and what each one needs
    python run.py 03              # run demo 03 against the local simulator
    python run.py 03 --target live
    python run.py --offline       # every demo that needs no credentials

Each demo is also a plain script (`python demos/03_*/demo.py`) once the repo is
installed with `pip install -e .`; this runner exists so it works before that
too, and so `--offline` has one obvious meaning.
"""

from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

DEMOS = REPO / "demos"


def _discover() -> list[tuple[str, Path]]:
    out = []
    for directory in sorted(DEMOS.iterdir()):
        script = directory / "demo.py"
        if directory.is_dir() and script.is_file():
            out.append((directory.name.split("_", 1)[0], script))
    return out


def _needs_live(script: Path) -> bool:
    return 'target="live"' in script.read_text(encoding="utf-8")


def _list() -> int:
    print("\nDonkey Development Kit (DDK) demos\n")
    print(f"  {'#':<4} {'needs':<12} demo")
    print(f"  {'-' * 4} {'-' * 12} {'-' * 48}")
    for number, script in _discover():
        needs = "credentials" if _needs_live(script) else "nothing"
        print(f"  {number:<4} {needs:<12} {script.parent.name}")
    print("\n  python run.py <#>          run one")
    print("  python run.py --offline    run every demo that needs nothing\n")
    return 0


def _run(script: Path, argv: list[str]) -> int:
    sys.argv = [str(script), *argv]
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        return _list()

    if args[0] in ("--offline", "-o"):
        failed = []
        for number, script in _discover():
            if _needs_live(script):
                continue
            # A subprocess per demo: each one owns a simulator and an event loop,
            # and one demo's cleanup should never affect the next one's run.
            result = subprocess.run([sys.executable, str(script)], cwd=REPO)
            if result.returncode != 0:
                failed.append(number)
        print()
        if failed:
            print(f"Demos that did not exit cleanly: {', '.join(failed)}")
            return 1
        print("All offline demos completed.")
        return 0

    wanted = args[0].lstrip("0") or "0"
    for number, script in _discover():
        if number.lstrip("0") == wanted or number == args[0]:
            return _run(script, args[1:])

    print(f"No demo {args[0]!r}.")
    return _list() or 1


if __name__ == "__main__":
    sys.exit(main())
