# spiderswitch record_experience tool
"""
MCP tool: record subjective experience ratings for a model.
MCP 工具：累积用户/Agent 对模型的主观感受指标。
"""

from __future__ import annotations

import logging

from mcp.types import TextContent, Tool

from ..index.service import ModelIndexService
from ..response import MCPResponse

logger = logging.getLogger(__name__)


def tool_schema() -> Tool:
    return Tool(
        name="record_experience",
        description=(
            "Record subjective experience ratings (1–5) for a model. "
            "Accumulated scores influence future query_index and recommend_model ranking. "
            "记录对模型的主观感受评分（1–5），影响后续能力索引排序。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "model_id": {
                    "type": "string",
                    "description": "Model id (provider/model).",
                },
                "quality": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Output quality (1=poor, 5=excellent).",
                },
                "speed": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Response speed feel (1=slow, 5=fast).",
                },
                "value": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Cost/value feel (1=poor value, 5=great value).",
                },
                "task_hint": {
                    "type": "string",
                    "description": "Optional task context for this rating.",
                },
            },
            "required": ["model_id"],
        },
    )


async def handle(
    index_service: ModelIndexService | None,
    arguments: dict[str, object],
) -> list[TextContent]:
    model_id = arguments.get("model_id")
    if not isinstance(model_id, str) or not model_id.strip():
        response = MCPResponse.error(
            message="Missing required parameter: model_id",
            error_type="ValidationError",
            error_code="SPIDER-EXPERIENCE-INVALID",
        )
        return [response.to_text_content()]

    if index_service is None:
        response = MCPResponse.error(
            message="Experience store unavailable (index not built at startup).",
            error_type="IndexUnavailableError",
            error_code="SPIDER-EXPERIENCE-MISSING",
        )
        return [response.to_text_content()]

    def _optional_rating(key: str) -> float | None:
        raw = arguments.get(key)
        if isinstance(raw, (int, float)):
            return float(raw)
        return None

    task_raw = arguments.get("task_hint")
    task_hint = task_raw if isinstance(task_raw, str) else None

    rec = index_service.record_rating_outcome(
        model_id.strip(),
        quality=_optional_rating("quality"),
        speed=_optional_rating("speed"),
        value=_optional_rating("value"),
        task_hint=task_hint,
    )

    response = MCPResponse.success(
        data={
            "model_id": model_id.strip(),
            "subjective": rec.to_dict(),
            "experience_path": str(index_service.experience.path),
        },
        message=f"Recorded experience for {model_id.strip()}",
    )
    return [response.to_text_content()]


__all__ = ["tool_schema", "handle"]
