# MCP server request-layer regression tests
"""
Test MCP request handlers through mcp.types request objects.
测试通过 mcp.types 请求对象覆盖 MCP 请求层回归路径。
"""

from __future__ import annotations

import json

import pytest
from mcp import types

from spiderswitch.runtime.base import ModelCapabilities, ModelInfo, Runtime, RuntimeProfile
from spiderswitch.server import create_app
from spiderswitch.state import ModelStateManager


class _McpDummyRuntime(Runtime):
    """Minimal runtime used for MCP request-layer tests."""

    async def list_models(
        self,
        filter_provider: str | None = None,
        filter_capability: str | None = None,
    ) -> list[ModelInfo]:
        _ = filter_provider, filter_capability
        return [
            ModelInfo(
                id="openai/gpt-4o",
                provider="openai",
                capabilities=ModelCapabilities(streaming=True, tools=True),
            )
        ]

    async def switch_model(
        self,
        model_id: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> ModelInfo:
        _ = api_key, base_url
        return ModelInfo(
            id=model_id,
            provider=model_id.split("/")[0],
            capabilities=ModelCapabilities(streaming=True),
        )

    async def close(self) -> None:
        return None

    async def get_current_model(self) -> ModelInfo | None:
        return None

    def describe_runtime_profile(self) -> RuntimeProfile:
        return RuntimeProfile(
            runtime_id="python-runtime",
            language="python",
            supports=["model_switching", "provider_manifest_loading"],
        )


def _extract_first_text_payload(result: types.ServerResult) -> dict[str, object]:
    """Decode first text content from CallToolResult."""
    root = result.root
    assert isinstance(root, types.CallToolResult)
    assert root.content
    first = root.content[0]
    assert isinstance(first, types.TextContent)
    return json.loads(first.text)


@pytest.mark.asyncio
async def test_mcp_request_handlers_register_and_list_tools() -> None:
    """Server should expose expected tools through ListToolsRequest handler."""
    app = create_app(runtime=_McpDummyRuntime(), state_manager=ModelStateManager())
    handler = app.request_handlers[types.ListToolsRequest]
    result = await handler(types.ListToolsRequest())
    root = result.root
    assert isinstance(root, types.ListToolsResult)
    tool_names = {tool.name for tool in root.tools}
    assert {"switch_model", "list_models", "get_status", "exit_switcher", "recommend_model", "auto_switch"} <= tool_names


@pytest.mark.asyncio
async def test_mcp_call_tool_unknown_name_returns_structured_error_payload() -> None:
    """Unknown tool through CallToolRequest should return structured error JSON."""
    app = create_app(runtime=_McpDummyRuntime(), state_manager=ModelStateManager())
    list_handler = app.request_handlers[types.ListToolsRequest]
    await list_handler(types.ListToolsRequest())

    call_handler = app.request_handlers[types.CallToolRequest]
    result = await call_handler(
        types.CallToolRequest(
            params=types.CallToolRequestParams(name="unknown_tool", arguments={})
        )
    )
    payload = _extract_first_text_payload(result)
    assert payload["status"] == "error"
    assert payload["error"]["type"] == "UnknownToolError"
    assert payload["error"]["code"] == "SPIDER-UNKNOWN-TOOL"


@pytest.mark.asyncio
async def test_mcp_call_tool_switch_model_updates_status_flow() -> None:
    """switch_model via MCP request handler should update get_status output."""
    state = ModelStateManager()
    app = create_app(runtime=_McpDummyRuntime(), state_manager=state)
    list_handler = app.request_handlers[types.ListToolsRequest]
    await list_handler(types.ListToolsRequest())
    call_handler = app.request_handlers[types.CallToolRequest]

    switch_result = await call_handler(
        types.CallToolRequest(
            params=types.CallToolRequestParams(
                name="switch_model",
                arguments={"model": "openai/gpt-4o"},
            )
        )
    )
    switch_payload = _extract_first_text_payload(switch_result)
    assert switch_payload["status"] == "success"
    assert switch_payload["data"]["id"] == "openai/gpt-4o"

    status_result = await call_handler(
        types.CallToolRequest(
            params=types.CallToolRequestParams(name="get_status", arguments={})
        )
    )
    status_payload = _extract_first_text_payload(status_result)
    assert status_payload["status"] == "success"
    assert status_payload["data"]["is_configured"] is True
    assert status_payload["data"]["provider"] == "openai"
