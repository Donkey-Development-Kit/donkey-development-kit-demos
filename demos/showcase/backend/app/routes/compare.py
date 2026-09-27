"""POST /api/compare — the same prompt, WITHOUT DDK vs WITH DDK.

Without DDK: a stock ``openai`` client pointed at the same proxy, with no
``classify()`` — it sees the raw status code and body a non-DDK app would have to
reverse-engineer (and would likely retry). With DDK: the governed path, which
turns that same response into a typed exception with a remediation.

Returns a single JSON object (not streamed); the frontend renders the two sides.
"""

from __future__ import annotations

import os
from typing import Any

import openai
from donkey_kit import DonkeyError
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..agent import build_graph, user_state
from ..donkeys import DEFAULT_MODEL, budget_snapshot, get_donkey, message_text
from .chat import governance_payload


def _raw_without_ddk(prompt: str, model_id: str) -> dict[str, Any]:
    """Exactly what a non-DDK app gets: a raw OpenAI SDK call at the proxy."""
    client = openai.OpenAI(
        base_url=os.environ["DONKEY_LLM_PROXY_URL"],
        api_key="local",
        max_retries=0,
    )
    try:
        resp = client.responses.create(model=model_id, input=prompt)
        return {"ok": True, "text": getattr(resp, "output_text", "")[:600]}
    except openai.APIStatusError as exc:
        body = ""
        try:
            body = exc.response.text[:600]
        except Exception:
            body = str(exc)[:600]
        return {
            "ok": False,
            "status_code": exc.status_code,
            "body": body,
            "note": "Opaque HTTP error. Is it auth? PII? content-safety? "
            "You can't tell without parsing — and a 429 here would often be retried, "
            "burning the window.",
        }
    except openai.APIConnectionError as exc:
        return {"ok": False, "status_code": None, "body": str(exc), "note": "Could not reach the proxy."}


async def _governed_with_ddk(prompt: str, model_id: str) -> dict[str, Any]:
    donkey = get_donkey()
    model = donkey.langgraph.chat_model(model_id)
    graph = build_graph(model)
    try:
        async with donkey.run(id="compare", team="support", project="triage-v2"):
            result = await graph.ainvoke(user_state(prompt))
        return {
            "ok": True,
            "text": message_text(result["messages"][-1])[:600],
            "budget": budget_snapshot(donkey),
        }
    except DonkeyError as exc:
        return {
            "ok": False,
            "governance": governance_payload(exc),
            "budget": budget_snapshot(donkey),
            "note": "A typed exception you branch on — never confused, never blindly retried.",
        }


async def compare(request: Request) -> JSONResponse:
    body = await request.json()
    prompt = (body.get("prompt") or "").strip()
    model_id = body.get("model") or DEFAULT_MODEL
    return JSONResponse(
        {
            "prompt": prompt,
            "model": model_id,
            "without": _raw_without_ddk(prompt, model_id),
            "with": await _governed_with_ddk(prompt, model_id),
        }
    )
