"""Terminal output helpers, so every demo reads the same way on a projector.

Two constraints shape this. Output has to survive a low-contrast projector and a
video re-encode, so it uses spacing and rules rather than colour for structure
and never relies on colour alone to carry meaning. And it has to be readable in
a 100-column terminal at a font size an audience can actually see, so lines wrap
at 88 and labels are padded to a fixed width.

Everything that prints a *value* goes through `redact`, so a demo cannot leak
the gateway host or a credential just by calling the obvious helper.
"""

from __future__ import annotations

import os
import shutil
import sys
import textwrap
from collections.abc import Mapping

from . import redact

__all__ = [
    "bullet",
    "code",
    "fail",
    "field",
    "note",
    "ok",
    "pause",
    "rule",
    "section",
    "step",
    "table",
    "title",
    "warn",
]

WIDTH = min(88, shutil.get_terminal_size((88, 24)).columns)
_LABEL = 22

_USE_COLOUR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code_: str, s: str) -> str:
    return f"\033[{code_}m{s}\033[0m" if _USE_COLOUR else s


def title(text: str, subtitle: str | None = None) -> None:
    print()
    print(_c("1", "═" * WIDTH))
    print(_c("1", text))
    if subtitle:
        print(textwrap.fill(subtitle, WIDTH))
    print(_c("1", "═" * WIDTH))


def section(text: str) -> None:
    print()
    print(_c("1", text))
    print("─" * min(WIDTH, len(text)))


def step(n: int, text: str) -> None:
    print()
    print(_c("1", f"[{n}] {text}"))


def rule() -> None:
    print("─" * WIDTH)


def note(text: str) -> None:
    print(textwrap.fill(text, WIDTH, initial_indent="  ", subsequent_indent="  "))


def bullet(text: str) -> None:
    print(textwrap.fill(text, WIDTH, initial_indent="  • ", subsequent_indent="    "))


def ok(text: str) -> None:
    print(f"  {_c('32', 'PASS')}  {text}")


def fail(text: str) -> None:
    print(f"  {_c('31', 'FAIL')}  {text}")


def warn(text: str) -> None:
    print(f"  {_c('33', 'WARN')}  {text}")


def field(label: str, value: object, *, raw: bool = False) -> None:
    """One `label : value` line. The value is masked unless `raw=True`, which is
    reserved for values the demo itself produced (a locally generated correlation
    id, a token count) rather than anything read from config or the wire."""
    shown = str(value) if raw else redact.text(value)
    print(f"  {label:<{_LABEL}} {shown}")


def table(mapping: Mapping[str, str], *, title_: str | None = None) -> None:
    """Header dicts and similar. Values are already masked by `redact.headers`;
    pass the output of that, not a raw header mapping."""
    if title_:
        print(f"  {title_}")
    if not mapping:
        print("    (none)")
        return
    width = max(len(k) for k in mapping)
    for key, value in mapping.items():
        print(f"    {key:<{width}}  {value}")


def code(snippet: str) -> None:
    """Echo the code the next step runs, so the audience reads it before the
    output appears rather than reverse-engineering it afterwards."""
    print()
    for line in textwrap.dedent(snippet).strip("\n").splitlines():
        print(_c("36", f"    {line}"))
    print()


def pause(prompt: str = "next") -> None:
    """Wait for Enter between acts, but only when a human is watching and
    `DEMO_PAUSE=1` asked for it. Never blocks in CI or a piped run."""
    if os.environ.get("DEMO_PAUSE", "0").strip() not in ("1", "true", "yes"):
        return
    if not sys.stdin.isatty():
        return
    try:
        input(_c("2", f"    ⏎ {prompt} "))
    except (EOFError, KeyboardInterrupt):
        print()
