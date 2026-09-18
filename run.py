#!/usr/bin/env python3
"""Run one demo, or all the offline ones, without worrying about `PYTHONPATH`.

    python run.py                          # list the demos and what each one needs
    python run.py 03                       # run demo 03 against the local simulator
    python run.py 03 --target live
    python run.py claude-made/03           # qualified, when a number is ambiguous
    python run.py --offline                # every demo that needs no credentials

Demos live in groups under `demos/` (`claude-made/`, `human-made/`), so a demo is
identified by its number, its directory name, or its `group/directory` path. A
number that matches in more than one group is reported rather than guessed at.

Each demo is also a plain script (`python demos/claude-made/03_*/demo.py`) once the
repo is installed with `pip install -e .`; this runner exists so it works before
that too, and so `--offline` has one obvious meaning.
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
    """Every `demo.py` under `demos/`, at any depth.

    The number comes from the script's own parent directory rather than from a
    fixed path depth, so demos can be regrouped into subdirectories without
    this runner losing sight of them.
    """
    return [
        (script.parent.name.split("_", 1)[0], script)
        for script in sorted(DEMOS.rglob("demo.py"))
    ]


def _label(script: Path) -> str:
    """How a demo is named in output: `group/directory`, relative to `demos/`."""
    return script.parent.relative_to(DEMOS).as_posix()


def _matches(wanted: str, demos: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
    """The demos a command-line argument selects.

    Accepts the number (`03`, `3`), the directory name (`03_budget_and_pacing`),
    or the qualified path (`claude-made/03_budget_and_pacing`, `claude-made/03`).
    """
    wanted = wanted.strip("/")
    loose = wanted.lstrip("0") or "0"
    out = []
    for number, script in demos:
        label = _label(script)
        candidates = {
            number,
            number.lstrip("0") or "0",
            script.parent.name,
            label,
            f"{label.rsplit('/', 1)[0]}/{number}" if "/" in label else number,
        }
        if wanted in candidates or loose in candidates:
            out.append((number, script))
    return out


def _needs_live(script: Path) -> bool:
    return 'target="live"' in script.read_text(encoding="utf-8")


def _list() -> int:
    print("\nDonkey Development Kit (DDK) demos\n")
    print(f"  {'#':<4} {'needs':<12} demo")
    print(f"  {'-' * 4} {'-' * 12} {'-' * 48}")
    for number, script in _discover():
        needs = "credentials" if _needs_live(script) else "nothing"
        print(f"  {number:<4} {needs:<12} {_label(script)}")
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

    found = _matches(args[0], _discover())
    if len(found) == 1:
        return _run(found[0][1], args[1:])

    if not found:
        print(f"No demo {args[0]!r}.")
        return _list() or 1

    print(f"\n{args[0]!r} matches more than one demo:\n")
    for _, script in found:
        print(f"      {_label(script)}")
    print("\n  Name one of those, e.g. python run.py "
          f"{_label(found[0][1])}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
