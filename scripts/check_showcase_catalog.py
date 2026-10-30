"""Fail when the showcase catalog and its static replay drift apart.

Checks (no credentials, no SDK, no network):

1. demos/showcase/backend/app/features.py (FEATURES) equals
   demos/showcase/frontend/public/replay/features.json, same order.
2. Every `chat` card has a recording for `model::prompt` in chat.json and
   compare.json (the key frontend/src/api.ts and scripts/record_replay.py use).
3. Every pace / conformance / doctor card has its replay file (pace.json,
   conformance.json, doctor.json). `info` cards need nothing.

    python3 scripts/check_showcase_catalog.py [--replay-dir DIR]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

SHOWCASE = Path(__file__).resolve().parents[1] / "demos" / "showcase"
FEATURES_PY = SHOWCASE / "backend" / "app" / "features.py"
ACTION_FILES = {"pace": "pace.json", "conformance": "conformance.json", "doctor": "doctor.json"}


def load_features() -> list[dict]:
    spec = importlib.util.spec_from_file_location("_showcase_features", FEATURES_PY)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.FEATURES


def check(replay: Path) -> list[str]:
    errors: list[str] = []
    py = load_features()
    try:
        js = json.loads((replay / "features.json").read_text())
    except (OSError, ValueError) as exc:
        return [f"cannot read {replay / 'features.json'}: {exc}"]
    if isinstance(js, dict):
        errors.append("features.json must be a bare list, not wrapped in an object")
        js = js.get("features", [])

    py_ids, js_ids = [f["id"] for f in py], [f.get("id") for f in js]
    if py_ids != js_ids:
        errors.append(
            f"card ids/order differ: only in features.py {sorted(set(py_ids) - set(js_ids))}, "
            f"only in features.json {sorted(set(js_ids) - set(py_ids))}"
            + ("" if set(py_ids) != set(js_ids) else " (same ids, different order)")
        )
    by_id = {f.get("id"): f for f in js}
    for f in py:
        other = by_id.get(f["id"])
        if other is None:
            continue
        for key in sorted(set(f) | set(other)):
            if f.get(key) != other.get(key):
                errors.append(f"card '{f['id']}': field '{key}' differs between features.py and features.json")

    def load(name: str):
        try:
            return json.loads((replay / name).read_text())
        except (OSError, ValueError):
            return None

    chat, compare = load("chat.json") or {}, load("compare.json") or {}
    for f in py:
        action = f["action"]
        if action == "chat":
            key = f"{f['model']}::{f['prompt']}"
            for name, data in (("chat.json", chat), ("compare.json", compare)):
                if key not in data:
                    errors.append(f"card '{f['id']}': no recording for '{key}' in {name}")
        elif action in ACTION_FILES:
            if load(ACTION_FILES[action]) is None:
                errors.append(f"card '{f['id']}': missing replay file {ACTION_FILES[action]}")
        elif action != "info":
            errors.append(f"card '{f['id']}': unknown action '{action}'")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--replay-dir", type=Path, default=SHOWCASE / "frontend" / "public" / "replay")
    args = ap.parse_args()
    errors = check(args.replay_dir)
    if errors:
        print("showcase catalog check FAILED:")
        for e in errors:
            print(f"  - {e}")
        print("See demos/showcase/README.md, 'Re-record the static replay'.")
        return 1
    n = len(load_features())
    print(f"showcase catalog ok: {n} cards, features.py == features.json, every interactive card has a recording")
    return 0


if __name__ == "__main__":
    sys.exit(main())
