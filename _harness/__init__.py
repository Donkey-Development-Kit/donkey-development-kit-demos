"""Shared plumbing for the demos. Not part of the Donkey Development Kit (DDK).

Importing this package loads `.env.local` / `.env` into the environment, so a
demo's first statement can assume configuration is present.

A demo is expected to look like this, and nothing more:

    from _harness import narrate as say, preflight, redact

    def main() -> None:
        ...

    if __name__ == "__main__":
        preflight.cli(main, title="…", target="mock", extras=("openai",))

The split is: `preflight` decides whether and against what the demo runs,
`narrate` prints, `redact` masks, `mock` owns the simulator process, and `env`
owns configuration. The one rule that matters is that **values reach the screen
only through `narrate` or `redact`** — see `redact.py` for why.
"""

from __future__ import annotations

from . import env as env  # noqa: F401 — imported for its load-on-import side effect
from . import mock as mock
from . import narrate as narrate
from . import preflight as preflight
from . import redact as redact

__all__ = ["env", "mock", "narrate", "preflight", "redact"]
