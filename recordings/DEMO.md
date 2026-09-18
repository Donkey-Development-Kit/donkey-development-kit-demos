# Recording runbook

For producing a screen recording rather than presenting live. If you are
presenting to people, read [PRESENTING.md](../PRESENTING.md) instead — it has
the talk tracks and the failure playbook. This page is about capture.

Recordings go in `assets/`, which is git-ignored apart from its `.gitkeep`, so a
video cannot be committed by reflex. Publish them deliberately.

## Before you hit record

Work through the checklist in
[PRESENTING.md § screen-recording safety](../PRESENTING.md#screen-recording-safety).
The short version, because this is the part people skip:

```bash
echo $DEMO_REDACT          # must be empty or 1
clear && printf '\e[3J'    # scrollback is the most common leak, not demo output
make doctor                # prints what is configured, never what it is set to
```

Then close the editor tab holding `.env.local`, and check your shell prompt does
not interpolate a hostname, cloud profile or kubectl context you would rather
not publish.

## Setup

```bash
export DEMO_PAUSE=1        # pause between acts, so you can narrate
export DEMO_QUIET_MOCK=1   # keep uvicorn's request log out of the capture
```

Terminal: 18pt or larger, at least 100 columns, light background. Two panes —
demos on the left, `make mock` on the right so the simulator's honesty banner is
on screen throughout.

## Three acts, about eight minutes

### Act 1 — the argument (2:30)

```bash
make demo N=01
```

Open by conceding that a stock OpenAI client reaches the gateway in two lines.
Let the demo make that point itself, then let it show the same 403 arriving at
both clients. Land the sentence: *the wrapper is not a way to reach the gateway,
it is the one place every request passes through.*

When the captured unicorn reply appears, read the warning above it aloud. The
honesty is part of the pitch, and a viewer who spots the mismatch before you
mention it will discount everything after.

### Act 2 — what that buys (3:30)

```bash
make demo N=04      # the except branch that has never run
make demo N=05      # red, then green, against someone else's agent
```

Demo 04 is the fastest payoff in the set. Demo 05 is the one worth the most
screen time: read the naive agent's code out loud and ask what is wrong with it
before running the suite, because the answer is *nothing obviously*.

### Act 3 — live proof (2:00)

```bash
make demo N=09
```

The only demo with a real model and real tool calls. If the sandbox is down,
record `make demo N=08` instead and say why — it constructs real framework
objects and at least is not a simulator.

## Typing on camera

`scratchpads/` holds the minimal versions, small enough to write live. Each is
fully typed, so every `.` opens a real completion list — which is the point of
typing rather than pasting.

| File | Lines | Needs |
|---|---|---|
| [`scratchpads/offline_simulate.py`](scratchpads/offline_simulate.py) | ~10 | nothing — start here |
| [`scratchpads/live_chat.py`](scratchpads/live_chat.py) | ~8 | credentials |
| [`scratchpads/live_chat_sync.py`](scratchpads/live_chat_sync.py) | ~4 | credentials |
| [`scratchpads/live_langgraph.py`](scratchpads/live_langgraph.py) | ~3 | credentials |

Prefer `offline_simulate.py` for a recording. It needs no gateway, so it cannot
fail because a sandbox is down — and watching a typed refusal appear from a
three-line block is a better beat than watching a completion stream.

Point the simulator at your shell first:

```bash
donkey mock &
export DONKEY_LLM_PROXY_URL=http://127.0.0.1:8080
export DONKEY_LLM_PROXY_CLIENT_ID=anything
export DONKEY_LLM_PROXY_CLIENT_SECRET=anything
```

With those exported you can delete the `import _harness` line from a scratchpad
before you start typing — it only loads `.env.local`, and one less line of
plumbing on camera is worth it.

## Afterwards

```bash
make scan       # before committing anything from the session
```

Move the capture into `assets/`. If it is going somewhere public, watch it back
once at full size specifically looking at the scrollback in the first few frames
— that is where the leak is, if there is one.
