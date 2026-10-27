"""File-free regression checks for narrative settings loaded by preflight."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from _harness import env, mock, preflight  # noqa: E402

DEMOS = (
    ("01_governed_client", "either", ("gpt-4o",)),
    ("09_langgraph_agent", "live", ("gpt-4o-mini", "chat")),
    ("10_last_call", "mock", ("gpt-4o",)),
)


def load_demo(name: str):
    spec = importlib.util.spec_from_file_location(
        name, REPO / "demos" / "claude-made" / name / "demo.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NarrativeEnvTests(unittest.TestCase):
    def test_settings_are_selected_after_preflight_load(self) -> None:
        for name, target, defaults in DEMOS:
            for use_defaults in (False, True):
                with (
                    self.subTest(demo=name, defaults=use_defaults),
                    patch.dict(os.environ, {}, clear=True),
                    patch.object(env, "load") as load,
                    patch.object(preflight, "_installed", return_value=True),
                    patch.object(mock, "running") as running,
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    # Import with stale settings; only preflight supplies the new ones.
                    os.environ.update(DEMO_MODEL="before-load", DEMO_LANGGRAPH_API="chat")
                    module = load_demo(name)
                    load.assert_not_called()

                    def loaded(use_defaults=use_defaults, target=target):
                        if use_defaults:
                            os.environ.pop("DEMO_MODEL")
                            os.environ.pop("DEMO_LANGGRAPH_API")
                        else:
                            os.environ.update(
                                DEMO_MODEL="after-load", DEMO_LANGGRAPH_API="responses"
                            )
                        if target == "live":
                            os.environ.update(dict.fromkeys(env.PROXY_VARS, "fake"))
                        return []

                    load.side_effect = loaded
                    running.return_value.__enter__.return_value = "http://127.0.0.1:8080/"
                    with patch.object(module, "_main", new_callable=AsyncMock) as execution:
                        self.assertEqual(
                            preflight.run(module.main, title=name, target=target, argv=[]), 0
                        )
                        expected = defaults if use_defaults else (
                            ("after-load", "responses") if target == "live" else ("after-load",)
                        )
                        execution.assert_awaited_once_with(*expected)
                    load.assert_called_once_with()

    def test_langgraph_nonlive_guard_does_not_execute(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(env, "load", return_value=[]) as load,
            patch.object(preflight, "_installed", return_value=True),
            patch.object(mock, "running") as running,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            module = load_demo("09_langgraph_agent")
            with patch.object(module, "_main", new_callable=AsyncMock) as execution:
                self.assertEqual(
                    preflight.run(
                        module.main, title="09", target="live", argv=["--target", "mock"]
                    ), 0
                )
                execution.assert_not_called()
            load.assert_called_once_with()
            running.assert_not_called()
            self.assertIn("no simulator equivalent", output.getvalue())
            self.assertIn("This demo needs a real governed proxy", output.getvalue())


if __name__ == "__main__":
    unittest.main()
