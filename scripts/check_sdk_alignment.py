#!/usr/bin/env python3
"""Fail if this branch's `[sdk]` / `[full]` extras install the wrong SDK.

The rule: demos `main` runs against SDK `main` (the latest release, from PyPI)
and demos `develop` runs against SDK `develop`. A `donkey-kit` requirement with
no ref follows the SDK repo's *default* branch, which is `develop`, so `main`
silently ran against unreleased code until it was pinned (#25).

    python scripts/check_sdk_alignment.py                   # branch from git / CI
    python scripts/check_sdk_alignment.py --branch main
    python scripts/check_sdk_alignment.py --sdk-version 0.1.1   # skip the network

What each branch must pin, in every `donkey-kit` line of `[sdk]` and `[full]`:

* `main`: `donkey-kit[...]==X`, where X is `project.version` on SDK `main`.
  When the SDK releases, this fails until the pin is bumped, by design.
* `develop`: `donkey-kit[...] @ git+https://…/donkey-development-kit.git@develop#subdirectory=python`.

Both must also carry the `llm`, `local`, `test` and `cli` extras: without `cli`
there is no `donkey mock`, and every mock-target demo fails.

Any other branch is checked against the branch it will merge into: the PR base
in CI, `main` for `hotfix/*`, otherwise `develop`.

Exit status is 0 when aligned and 1 when not, so it works as a CI step.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    sys.exit("check_sdk_alignment.py needs Python 3.11+ (tomllib)")

REPO = Path(__file__).resolve().parents[1]
SDK_REPO = "Donkey-Development-Kit/donkey-development-kit"
SDK_GIT = f"git+https://github.com/{SDK_REPO}.git@develop#subdirectory=python"
SDK_MAIN_PYPROJECT = (
    f"https://raw.githubusercontent.com/{SDK_REPO}/main/python/pyproject.toml"
)
CHECKED_EXTRAS = ("sdk", "full")
REQUIRED_SDK_EXTRAS = {"llm", "local", "test", "cli"}

_REQ = re.compile(r"^donkey-kit\[(?P<extras>[^\]]*)\]\s*(?P<spec>.*)$")


def _current_branch() -> str:
    for var in ("GITHUB_BASE_REF", "GITHUB_REF_NAME"):
        if value := os.environ.get(var):
            return value
    out = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def _target(branch: str) -> str:
    if branch in ("main", "develop"):
        return branch
    return "main" if branch.startswith("hotfix/") else "develop"


def _sdk_main_version() -> str:
    with urllib.request.urlopen(SDK_MAIN_PYPROJECT, timeout=30) as response:
        return tomllib.loads(response.read().decode())["project"]["version"]


def _problems(target: str, sdk_version: str | None) -> list[str]:
    extras = tomllib.loads((REPO / "pyproject.toml").read_text())["project"][
        "optional-dependencies"
    ]
    problems = []
    for name in CHECKED_EXTRAS:
        lines = [r for r in extras.get(name, []) if r.startswith("donkey-kit")]
        if not lines:
            problems.append(f"[{name}] has no donkey-kit requirement")
        for line in lines:
            match = _REQ.match(line)
            if match is None:
                problems.append(f"[{name}] {line!r}: expected donkey-kit[<extras>]<pin>")
                continue
            have = {e.strip() for e in match["extras"].split(",")}
            if missing := sorted(REQUIRED_SDK_EXTRAS - have):
                problems.append(
                    f"[{name}] {line!r}: missing SDK extras {', '.join(missing)}"
                )
            spec = match["spec"].strip()
            if target == "main":
                want = f"=={sdk_version}"
                if spec != want:
                    problems.append(
                        f"[{name}] {line!r}: main must pin the SDK main release {want!r}"
                    )
            elif spec != f"@ {SDK_GIT}":
                problems.append(f"[{name}] {line!r}: develop must pin '@ {SDK_GIT}'")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--branch", help="demos branch to check as (default: from git/CI)")
    parser.add_argument(
        "--sdk-version", help="SDK main version (default: read from GitHub)"
    )
    args = parser.parse_args()

    branch = args.branch or _current_branch()
    target = _target(branch)
    sdk_version = None
    if target == "main":
        sdk_version = args.sdk_version or _sdk_main_version()

    problems = _problems(target, sdk_version)
    against = f"SDK main ({sdk_version})" if target == "main" else "SDK develop"
    if problems:
        print(
            f"demos {branch} (as {target}) is NOT aligned with {against}:", file=sys.stderr
        )
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"demos {branch} (as {target}) is aligned with {against}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
