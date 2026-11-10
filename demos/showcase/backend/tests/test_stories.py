"""Protocol stories execute SDK paths offline, not model-chat stand-ins."""

import importlib.util
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.main import app
from app.routes import story
from starlette.testclient import TestClient


@pytest.mark.parametrize(
    ("feature", "outcomes"),
    [
        ("mcp-refusals", ["PIIDetected", "PIIDetected", "ToolNotInProfile", "generic"]),
        (
            "tool-lockfile",
            [
                "locked",
                "bound",
                "ToolLockDrift",
                "ToolLockDrift",
                "ToolLockDrift",
                "excluded",
            ],
        ),
        (
            "a2a-outbound",
            [
                "SendMessageResponse",
                "StreamResponse",
                "ContentSafetyBlocked",
                "TokenBudgetExceeded",
                "ToolInvocationError",
            ],
        ),
    ],
)
def test_protocol_story(feature, outcomes):
    # No lifespan: these stories own their offline transports, not donkey mock.
    client = TestClient(app)
    response = client.post("/api/story", json={"feature": feature})
    assert response.status_code == 200
    result = response.json()
    assert result["feature"] == feature
    assert [step["outcome"] for step in result["steps"]] == outcomes
    assert "offline" in result["boundary"].lower()
    assert "capture@example.com" not in json.dumps(result)
    if feature == "a2a-outbound":
        assert len(result["spans"]) == 5
        assert all(s["name"] == "donkey.a2a.call" for s in result["spans"])
        assert all("exception.message" not in s["attributes"] for s in result["spans"])


def test_story_rejects_unknown_feature():
    client = TestClient(app)
    assert client.post("/api/story", json={"feature": "llm-client"}).status_code == 400
    assert client.post("/api/story", content="not json").status_code == 400
    assert client.post("/api/story", json={"feature": []}).status_code == 400


def test_story_does_not_accept_unrelated_discovery_failure(monkeypatch):
    from donkey_kit.tools import ToolSet

    original = ToolSet.langgraph
    calls = 0

    async def broken(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 4:
            raise RuntimeError("unrelated binding failure")
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(ToolSet, "langgraph", broken)
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/story", json={"feature": "mcp-refusals"}
    )
    assert response.status_code == 500
    assert "unrelated binding failure" not in response.text


def test_story_checks_exception_privacy(monkeypatch):
    monkeypatch.setattr(
        story.ToolInvocationError, "__str__", lambda _: "capture@example.com"
    )
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/story", json={"feature": "a2a-outbound"}
    )
    assert response.status_code == 500
    assert "capture@example.com" not in response.text


def test_story_rejects_unrelated_a2a_failure(monkeypatch):
    from donkey_kit.a2a.client import A2AFacade

    original = A2AFacade.send
    calls = 0

    async def broken(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise story.ToolInvocationError("Unrelated protocol failure")
        return await original(self, *args, **kwargs)

    monkeypatch.setattr(A2AFacade, "send", broken)
    response = TestClient(app).post("/api/story", json={"feature": "a2a-outbound"})
    assert response.status_code == 500
    assert response.json() == {"error": "Protocol story verification failed"}


def test_story_checks_unprojected_span_privacy(monkeypatch):
    original = story.telemetry.finished_spans

    def contaminated():
        spans = original()
        last = spans[-1]
        return [
            *spans,
            SimpleNamespace(
                attributes=last.attributes,
                name="donkey.a2a.call",
                to_json=lambda: '{"events":[{"exception.message":"capture@example.com"}]}',
            ),
        ]

    monkeypatch.setattr(story.telemetry, "finished_spans", contaminated)
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/story", json={"feature": "a2a-outbound"}
    )
    assert response.status_code == 500
    assert "capture@example.com" not in response.text


@pytest.mark.parametrize(
    "field,value", [("steps", ["not a step"]), ("spans", None), ("spans", [{}])]
)
def test_replay_gate_rejects_malformed_stories(tmp_path, field, value):
    root = Path(__file__).resolve().parents[4]
    spec = importlib.util.spec_from_file_location(
        "catalog_check", root / "scripts/check_showcase_catalog.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    replay = tmp_path / "replay"
    shutil.copytree(root / "demos/showcase/frontend/public/replay", replay)
    stories = json.loads((replay / "stories.json").read_text())
    stories["mcp-refusals"][field] = value
    (replay / "stories.json").write_text(json.dumps(stories))
    assert any("invalid story recording" in error for error in module.check(replay))
