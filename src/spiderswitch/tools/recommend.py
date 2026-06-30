# spiderswitch recommend_model tool
"""
MCP tool: recommend best model for current task (BYOK, local policy).
MCP 工具：根据任务智能推荐模型（BYOK，本地策略）。
"""

from __future__ import annotations

import logging
from pathlib import Path

from mcp.types import TextContent, Tool

from ..errors import ModelSwitcherError
from ..policy.engine import PolicyEngine
from ..policy.loader import ModelCatalog
from ..response import MCPResponse
from ..runtime.base import Runtime
from ..runtime.python_runtime import PythonRuntime

logger = logging.getLogger(__name__)


def _resolve_catalog(runtime: Runtime) -> ModelCatalog:
    if isinstance(runtime, PythonRuntime):
        base = runtime.resolve_protocol_base()
        if base is None:
            raise ModelSwitcherError("Unable to locate ai-protocol directory")
        return ModelCatalog.from_protocol_path(Path(base))
    raise ModelSwitcherError(
        "Smart routing requires PythonRuntime with ai-protocol manifests"
    )


def tool_schema() -> Tool:
    return Tool(
        name="recommend_model",
        description=(
            "Recommend the best model for the current agent task using local policy. "
            "Only considers providers with configured API keys (BYOK). "
            "Does not call any LLM API — uses ai-protocol pricing and capabilities. "
            "根据当前任务智能推荐模型；仅考虑已配置 Key 的 Provider；不调用上游 API。"
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
                    "description": (
                        "Task type hint for routing. "
                        "任务类型提示：code/reasoning/vision/cheap/quality 等。"
                    ),
                },
                "tier": {
                    "type": "string",
                    "enum": ["economy", "balanced", "premium"],
                    "default": "balanced",
                    "description": (
                        "Cost/quality tier within your configured providers. "
                        "在已配置 Provider 内选择经济/均衡/高端档位。"
                    ),
                },
                "required_capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Extra required capabilities (tools, vision, …).",
                },
                "prefer_provider": {
                    "type": "string",
                    "description": "Optional: restrict to one provider (single BYOK account).",
                },
                "runtime_id": {"type": "string"},
            },
        },
    )


async def handle(runtime: Runtime, arguments: dict[str, object]) -> list[TextContent]:
    try:
        task_hint = arguments.get("task_hint", "chat")
        tier = arguments.get("tier", "balanced")
        prefer = arguments.get("prefer_provider")
        req_caps_raw = arguments.get("required_capabilities")

        req_caps: list[str] | None = None
        if isinstance(req_caps_raw, list):
            req_caps = [str(c) for c in req_caps_raw]

        catalog = _resolve_catalog(runtime)
        engine = PolicyEngine(catalog)
        rec = engine.recommend(
            task_hint=str(task_hint),
            tier_preference=str(tier),
            required_capabilities=req_caps,
            prefer_provider=str(prefer) if isinstance(prefer, str) else None,
            only_ready_providers=True,
        )

        payload = rec.to_dict()
        payload["runtime_profile"] = runtime.describe_runtime_profile().to_dict()
        payload["next_step"] = (
            f"Call auto_switch with same task_hint/tier, or switch_model to {rec.selected.model_id}"
        )

        response = MCPResponse.success(
            data=payload,
            message=f"Recommended {rec.selected.model_id} ({rec.selected.tier})",
        )
        return [response.to_text_content()]

    except ValueError as e:
        response = MCPResponse.error(
            message=str(e),
            error_type="NoEligibleModelError",
            error_code="SPIDER-RECOMMEND-NONE",
        )
        return [response.to_text_content()]

    except ModelSwitcherError as e:
        response = MCPResponse.error(
            message=str(e),
            error_type=e.__class__.__name__,
            error_code="SPIDER-RECOMMEND-FAILED",
        )
        return [response.to_text_content()]

    except Exception as e:
        logger.exception("Unexpected error in recommend_model: %s", e)
        response = MCPResponse.error(
            message="Internal tool error",
            error_type="RuntimeError",
            error_code="SPIDER-RECOMMEND-INTERNAL",
        )
        return [response.to_text_content()]


__all__ = ["tool_schema", "handle"]
