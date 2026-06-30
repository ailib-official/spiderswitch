# Tests for MCP prompt-injection layer
"""
Verify spiderswitch exposes server instructions and injectable prompts that
steer agents to call the model-switching tools.
测试 spiderswitch 的提示注入层（instructions + prompts）。
"""

from __future__ import annotations

import pytest
from mcp import types

from spiderswitch import prompts
from spiderswitch.server import create_app
from spiderswitch.state import ModelStateManager
from tests.test_server_mcp_flow import _McpDummyRuntime


def test_server_instructions_mention_switch_tools() -> None:
    text = prompts.SERVER_INSTRUCTIONS
    assert "auto_switch" in text
    assert "recommend_model" in text
    assert "exit_switcher" in text


def test_list_prompts_catalog() -> None:
    names = {p.name for p in prompts.list_prompts()}
    assert {"spiderswitch_guide", "route_task"} <= names


def test_get_prompt_route_task_with_explicit_hint() -> None:
    result = prompts.get_prompt(
        "route_task", {"task": "Fix the failing test", "task_hint": "code", "tier": "premium"}
    )
    rendered = result.messages[0].content.text
    assert 'task_hint="code"' in rendered
    assert 'tier="premium"' in rendered
    assert "auto_switch" in rendered
    assert "Fix the failing test" in rendered


def test_get_prompt_route_task_infers_hint_when_invalid() -> None:
    result = prompts.get_prompt("route_task", {"task": "Summarize", "task_hint": "bogus"})
    rendered = result.messages[0].content.text
    assert "infer the best task_hint" in rendered


def test_get_prompt_requires_task() -> None:
    with pytest.raises(ValueError):
        prompts.get_prompt("route_task", {"task": "   "})


def test_get_prompt_unknown_name() -> None:
    with pytest.raises(ValueError):
        prompts.get_prompt("does_not_exist", {})


def test_app_advertises_prompts_capability_and_instructions() -> None:
    app = create_app(runtime=_McpDummyRuntime(), state_manager=ModelStateManager())
    options = app.create_initialization_options()
    assert options.instructions
    assert options.capabilities.prompts is not None


@pytest.mark.asyncio
async def test_mcp_prompt_handlers_list_and_render() -> None:
    app = create_app(runtime=_McpDummyRuntime(), state_manager=ModelStateManager())

    list_handler = app.request_handlers[types.ListPromptsRequest]
    list_result = await list_handler(types.ListPromptsRequest())
    prompt_names = {p.name for p in list_result.root.prompts}
    assert {"spiderswitch_guide", "route_task"} <= prompt_names

    get_handler = app.request_handlers[types.GetPromptRequest]
    get_result = await get_handler(
        types.GetPromptRequest(
            params=types.GetPromptRequestParams(
                name="spiderswitch_guide", arguments=None
            )
        )
    )
    text = get_result.root.messages[0].content.text
    assert "auto_switch" in text
