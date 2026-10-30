"""Shared plumbing for the demos. Not part of the Donkey Development Kit (DDK).

Non-offline preflight loads `.env.local` / `.env` into the environment before
invoking a demo. Importing the harness and running offline never reads dotenv.

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

from . import env as env
from . import mock as mock
from . import narrate as narrate
from . import preflight as preflight
from . import redact as redact

__all__ = ["env", "mock", "narrate", "preflight", "redact"]
