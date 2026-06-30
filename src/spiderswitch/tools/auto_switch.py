# spiderswitch auto_switch tool
"""
MCP tool: recommend + switch in one call for agent runtime.
MCP 工具：推荐并切换模型（Agent 运行时一键智能选模）。
"""

from __future__ import annotations

import json
import logging

from mcp.types import TextContent, Tool

from ..response import MCPResponse
from ..runtime.base import Runtime
from ..state import ModelStateManager
from . import recommend, switch

logger = logging.getLogger(__name__)


def tool_schema() -> Tool:
    return Tool(
        name="auto_switch",
        description=(
            "Intelligently select and switch to the best model for the current task. "
            "Uses local policy (BYOK only, no upstream API for selection). "
            "智能选择并切换到最适合当前任务的模型；仅使用本地策略与 BYOK。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "task_hint": {
                    "type": "string",
                    "enum": [
                        "chat",
                        "code",
                        "reasoning",
                        "vision",
                        "summarize",
                        "cheap",
                        "quality",
                    ],
                    "default": "chat",
                },
                "tier": {
                    "type": "string",
                    "enum": ["economy", "balanced", "premium"],
                    "default": "balanced",
                },
                "required_capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "prefer_provider": {"type": "string"},
                "api_key": {"type": "string"},
                "base_url": {"type": "string"},
                "runtime_id": {"type": "string"},
            },
        },
    )


async def handle(
    runtime: Runtime,
    state_manager: ModelStateManager,
    arguments: dict[str, object],
) -> list[TextContent]:
    rec_result = await recommend.handle(runtime, arguments)
    rec_content = rec_result[0]

    try:
        body = json.loads(rec_content.text)
    except json.JSONDecodeError:
        return rec_result

    if body.get("status") != "success":
        return rec_result

    selected = (body.get("data") or {}).get("selected") or {}
    model_id = selected.get("model_id")
    if not isinstance(model_id, str):
        return rec_result

    switch_args: dict[str, object] = {"model": model_id}
    for key in ("api_key", "base_url", "runtime_id"):
        if key in arguments:
            switch_args[key] = arguments[key]

    switch_result = await switch.handle(runtime, state_manager, switch_args)
    switch_content = switch_result[0]

    try:
        switch_body = json.loads(switch_content.text)
    except json.JSONDecodeError:
        return switch_result

    if switch_body.get("status") != "success":
        return switch_result

    merged = {
        **switch_body.get("data", {}),
        "recommendation": body.get("data"),
    }
    response = MCPResponse.success(
        data=merged,
        message=f"Auto-switched to {model_id} for task {arguments.get('task_hint', 'chat')}",
    )
    return [response.to_text_content()]


__all__ = ["tool_schema", "handle"]
