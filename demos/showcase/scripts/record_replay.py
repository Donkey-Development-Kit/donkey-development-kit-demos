"""Record the backend's responses into frontend/public/replay/ for the static build.

The GitHub Pages build has no backend, so it replays what the real backend
returned for every card: run the backend (it boots `donkey mock` itself), then

    python3 scripts/record_replay.py http://127.0.0.1:8000

Only `donkey mock` traffic is recorded — the backend points DDK at the local
simulator with placeholder credentials, never at a real gateway.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "replay"
SIM_PORT = re.compile(r"127\.0\.0\.1:\d+")


def call(path: str, body: dict | None = None) -> bytes:
    data = None if body is None else json.dumps(body).encode()
    method = "GET" if body is None and path in ("/api/features", "/api/simulator", "/api/budget") else "POST"
    req = Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=300) as res:
        return res.read()


def sse(raw: bytes) -> list[dict]:
    events = []
    for frame in raw.decode().split("\n\n"):
        event, data = "message", []
        for line in frame.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].strip())
        if data:
            events.append({"event": event, "data": json.loads("\n".join(data))})
    return events


def save(name: str, payload: object) -> None:
    text = SIM_PORT.sub("127.0.0.1:8080", json.dumps(payload, indent=1))
    (OUT / name).write_text(text + "\n")


OUT.mkdir(parents=True, exist_ok=True)
features = json.loads(call("/api/features"))
features = features.get("features", features)
save("features.json", features)
save("simulator.json", json.loads(call("/api/simulator")))
save("budget.json", json.loads(call("/api/budget")))

chats, compares = {}, {}
for f in features:
    if f["action"] != "chat":
        continue
    key = f"{f['model']}::{f['prompt']}"
    chats[key] = sse(call("/api/chat", {"prompt": f["prompt"], "model": f["model"]}))
    compares[key] = json.loads(call("/api/compare", {"prompt": f["prompt"], "model": f["model"]}))
    print("recorded", f["id"])
save("chat.json", chats)
save("compare.json", compares)
save("pace.json", sse(call("/api/pace", {"calls": 6, "reserve": 0.05})))
save("conformance.json", json.loads(call("/api/conformance", {})))
save("doctor.json", json.loads(call("/api/doctor", {})))
print("wrote", OUT)
