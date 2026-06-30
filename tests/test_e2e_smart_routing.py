# E2E tests for smart routing MCP tools (recommend_model, auto_switch).
"""End-to-end smart routing tests against real ai-protocol + optional live switch."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from mcp import types

from spiderswitch.runtime.python_runtime import PythonRuntime
from spiderswitch.server import create_app
from spiderswitch.state import ModelStateManager

PROTO_PATH = Path(os.getenv("AI_PROTOCOL_PATH", "/home/alex/ai-protocol"))
LIVE_E2E = os.getenv("SPIDERSWITCH_E2E_LIVE", "0").lower() in {"1", "true", "yes"}


def _payload(result: types.ServerResult) -> dict[str, object]:
    root = result.root
    assert isinstance(root, types.CallToolResult)
    text = root.content[0]
    assert isinstance(text, types.TextContent)
    return json.loads(text.text)


@pytest.fixture
def smart_app() -> object:
    if not PROTO_PATH.is_dir():
        pytest.skip(f"ai-protocol not found: {PROTO_PATH}")
    runtime = PythonRuntime(ai_protocol_path=PROTO_PATH)
    return create_app(runtime=runtime, state_manager=ModelStateManager())


@pytest.mark.asyncio
async def test_e2e_recommend_model_cheap(smart_app: object) -> None:
    app = smart_app
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("DEEPSEEK_API_KEY"):
        pytest.skip("Set OPENAI_API_KEY or DEEPSEEK_API_KEY for recommend e2e")

    handler = app.request_handlers[types.CallToolRequest]
    result = await handler(
        types.CallToolRequest(
            params=types.CallToolRequestParams(
                name="recommend_model",
                arguments={"task_hint": "cheap", "tier": "economy"},
            )
        )
    )
    body = _payload(result)
    assert body["status"] == "success"
    data = body["data"]
    assert isinstance(data, dict)
    selected = data["selected"]
    assert isinstance(selected, dict)
    assert "model_id" in selected
    assert selected.get("tier") in {"economy", "balanced", "premium"}
    assert data.get("policy_version") == "smart-v1"


@pytest.mark.asyncio
async def test_e2e_recommend_no_keys_returns_error(smart_app: object) -> None:
    app = smart_app
    key_vars = [k for k in os.environ if k.endswith("_API_KEY") or k in {"GEMINI_API_KEY"}]
    saved = {k: os.environ.pop(k) for k in key_vars}
    try:
        handler = app.request_handlers[types.CallToolRequest]
        result = await handler(
            types.CallToolRequest(
                params=types.CallToolRequestParams(
                    name="recommend_model",
                    arguments={"task_hint": "chat"},
                )
            )
        )
        body = _payload(result)
        assert body["status"] == "error"
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


@pytest.mark.asyncio
async def test_e2e_auto_switch_code(smart_app: object) -> None:
    app = smart_app
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("DEEPSEEK_API_KEY"):
        pytest.skip("Set OPENAI_API_KEY or DEEPSEEK_API_KEY for auto_switch e2e")
    if not LIVE_E2E:
        pytest.skip("Set SPIDERSWITCH_E2E_LIVE=1 to run live model switch (calls provider init)")

    handler = app.request_handlers[types.CallToolRequest]
    result = await handler(
        types.CallToolRequest(
            params=types.CallToolRequestParams(
                name="auto_switch",
                arguments={"task_hint": "code", "tier": "balanced"},
            )
        )
    )
    body = _payload(result)
    assert body["status"] == "success"
    data = body["data"]
    assert isinstance(data, dict)
    assert "recommendation" in data
    assert data.get("id") or data.get("provider")


@pytest.mark.asyncio
async def test_e2e_prefer_provider_openai(smart_app: object) -> None:
    app = smart_app
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("Set OPENAI_API_KEY for prefer_provider e2e")

    handler = app.request_handlers[types.CallToolRequest]
    result = await handler(
        types.CallToolRequest(
            params=types.CallToolRequestParams(
                name="recommend_model",
                arguments={
                    "task_hint": "chat",
                    "tier": "economy",
                    "prefer_provider": "openai",
                },
            )
        )
    )
    body = _payload(result)
    assert body["status"] == "success"
    selected = body["data"]["selected"]
    assert selected["provider"] == "openai"
