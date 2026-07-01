# spiderswitch switch_model tool
"""
MCP tool for switching AI models.
MCP工具：切换AI模型。

Provides structured error responses and proper logging.
提供结构化的错误响应和适当的日志记录。
"""

from __future__ import annotations

import logging

from mcp.types import TextContent, Tool

from ..errors import InvalidModelError, ModelSwitcherError, describe_ai_lib_error
from ..hints import hint_for_error
from ..index.service import ModelIndexService
from ..response import MCPResponse
from ..runtime.base import Runtime
from ..runtime.python_runtime import (
    extract_model_from_args,
    format_model_info,
)
from ..state import ModelStateManager
from ..validation import get_provider_proxy_status
from . import status as status_tool

logger = logging.getLogger(__name__)


def tool_schema() -> Tool:
    """Get the switch_model tool schema.

    Returns:
        Tool schema definition
    """
    return Tool(
        name="switch_model",
        description=(
            "Switch to a different AI model/provider. "
            "Requires provider API key configured in environment or passed explicitly. "
            "切换到不同的AI模型/provider。需要在环境变量中配置provider API密钥或显式传递。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": (
                        "Model identifier (e.g., 'openai/gpt-4o', 'anthropic/claude-3-5-sonnet'). "
                        "模型标识符（如 'openai/gpt-4o', 'anthropic/claude-3-5-sonnet'）"
                    ),
                    "pattern": "^[a-z0-9-]+/[a-z0-9-.]+$",
                },
                "api_key": {
                    "type": "string",
                    "description": (
                        "Optional explicit API key (overrides environment variable). "
                        "可选的显式API密钥（覆盖环境变量）"
                    ),
                },
                "base_url": {
                    "type": "string",
                    "description": (
                        "Optional custom base URL for testing/mock. "
                        "可选的自定义基础URL，用于测试/mock"
                    ),
                },
                "runtime_id": {
                    "type": "string",
                    "description": (
                        "Optional runtime id selected by upper-layer strategy. "
                        "可选，上层策略选择的运行时 ID。"
                    ),
                },
            },
            "required": ["model"],
        },
    )


async def handle(
    runtime: Runtime,
    state_manager: ModelStateManager,
    arguments: dict[str, object],
    index_service: ModelIndexService | None = None,
) -> list[TextContent]:
    """Handle switch_model tool call.

    Args:
        runtime: Runtime implementation (e.g., PythonRuntime)
        state_manager: State manager instance
        arguments: Tool arguments from MCP request

    Returns:
        List of TextContent with result
    """
    try:
        model_id, api_key, base_url = extract_model_from_args(arguments)
        task_hint_raw = arguments.get("task_hint")
        task_hint = task_hint_raw if isinstance(task_hint_raw, str) else None
        logger.info(f"Switching to model: {model_id}")

        # Switch model via runtime
        model_info = await runtime.switch_model(
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
        )

        # Update state
        runtime_profile = runtime.describe_runtime_profile()
        state_manager.update_from_model_info_with_runtime(model_info, runtime_id=runtime_profile.runtime_id)
        status_tool.invalidate_cache(state_manager)

        if index_service is not None:
            index_service.record_switch_outcome(
                model_info.id,
                success=True,
                task_hint=task_hint,
            )

        proxy_status = get_provider_proxy_status(model_info.provider)
        warnings: list[str] = []
        if proxy_status.get("proxy_required_guess") and not proxy_status.get("proxy_configured"):
            hint = proxy_status.get("hint")
            if isinstance(hint, str):
                warnings.append(hint)

        # Format response with success status
        response = MCPResponse.success(
            data={
                **format_model_info(model_info),
                "runtime_profile": runtime_profile.to_dict(),
                "proxy_status": proxy_status,
                "warnings": warnings,
            },
            message=f"Successfully switched to {model_info.provider}/{model_info.id.split('/')[1] if '/' in model_info.id else model_info.id}",
        )

        return [response.to_text_content()]

    except InvalidModelError as e:
        # Client error - invalid input
        logger.warning(f"Invalid argument: {e}")
        response = MCPResponse.error(
            message=str(e),
            error_type="InvalidModelError",
            details=e.details if hasattr(e, "details") else None,
            error_code="SPIDER-INVALID-MODEL",
        )
        return [response.to_text_content()]

    except ModelSwitcherError as e:
        # Server error - switch failed
        logger.error(f"Failed to switch model: {e}")
        model_raw = arguments.get("model")
        if index_service is not None and isinstance(model_raw, str):
            task_hint_raw = arguments.get("task_hint")
            index_service.record_switch_outcome(
                model_raw,
                success=False,
                task_hint=task_hint_raw if isinstance(task_hint_raw, str) else None,
            )
        details = dict(e.details) if getattr(e, "details", None) else {}
        # Reuse ai-lib error classification so agents get retry/fallback signals.
        ai_lib_diagnostics = describe_ai_lib_error(e)
        if ai_lib_diagnostics:
            details["ai_lib_error"] = ai_lib_diagnostics
        else:
            heuristic = hint_for_error(str(e))
            if heuristic:
                details["hint"] = heuristic.get("message")
                if heuristic.get("fix_commands"):
                    details["fix_commands"] = list(heuristic["fix_commands"])
        response = MCPResponse.error(
            message=str(e),
            error_type=e.__class__.__name__,
            details=details or None,
            error_code="SPIDER-SWITCH-FAILED",
        )
        return [response.to_text_content()]

    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error in switch_model: {e}")
        response = MCPResponse.error(
            message="Internal tool error",
            error_type="RuntimeError",
            error_code="SPIDER-SWITCH-INTERNAL",
        )
        return [response.to_text_content()]


__all__ = ["tool_schema", "handle"]
