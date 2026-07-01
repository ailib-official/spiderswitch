# spiderswitch query_index tool
"""
MCP tool: query the startup-built capability index by structured requirements.
MCP 工具：按结构化能力查询启动时编制的能力索引。
"""

from __future__ import annotations

import logging

from mcp.types import TextContent, Tool

from ..index.service import ModelIndexService
from ..response import MCPResponse

logger = logging.getLogger(__name__)


def tool_schema() -> Tool:
    return Tool(
        name="query_index",
        description=(
            "Query the capability index built at spiderswitch startup. "
            "Filter by core capabilities, derived facets, tags, provider, tier, "
            "task_hint, and minimum subjective score. "
            "查询启动时编制的能力索引，按结构化能力/主观评分筛选模型。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "required_capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Core capabilities (streaming, tools, vision, …).",
                },
                "required_facets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Derived facets: multimodal, agentic, long_context, "
                        "ultra_context, cost_effective, reasoning_capable."
                    ),
                },
                "required_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "filter_provider": {"type": "string"},
                "tier": {
                    "type": "string",
                    "enum": ["economy", "balanced", "premium"],
                },
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
                },
                "ready_only": {"type": "boolean", "default": True},
                "min_subjective_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Minimum accumulated subjective score (0–1).",
                },
                "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
            },
        },
    )


def _parse_string_list(raw: object) -> set[str] | None:
    if not isinstance(raw, list):
        return None
    return {str(x).lower() for x in raw}


async def handle(
    index_service: ModelIndexService | None,
    arguments: dict[str, object],
) -> list[TextContent]:
    if index_service is None:
        response = MCPResponse.error(
            message="Capability index not available (ai-protocol missing at startup).",
            error_type="IndexUnavailableError",
            error_code="SPIDER-INDEX-MISSING",
            details={
                "hint": "Run spiderswitch protocol setup and restart the MCP server.",
                "fix_commands": ["spiderswitch protocol setup", "spiderswitch doctor --json"],
            },
        )
        return [response.to_text_content()]

    req_caps = _parse_string_list(arguments.get("required_capabilities"))
    req_facets = _parse_string_list(arguments.get("required_facets"))
    req_tags = _parse_string_list(arguments.get("required_tags"))
    provider_raw = arguments.get("filter_provider")
    provider = provider_raw if isinstance(provider_raw, str) else None
    tier_raw = arguments.get("tier")
    tier = tier_raw if isinstance(tier_raw, str) else None
    task_raw = arguments.get("task_hint")
    task_hint = task_raw if isinstance(task_raw, str) else None
    ready_only = arguments.get("ready_only", True)
    ready = ready_only if isinstance(ready_only, bool) else True
    min_score_raw = arguments.get("min_subjective_score")
    min_score = float(min_score_raw) if isinstance(min_score_raw, (int, float)) else None
    limit_raw = arguments.get("limit", 20)
    limit = int(limit_raw) if isinstance(limit_raw, int) else 20

    results = index_service.index.query(
        required_capabilities=req_caps,
        required_facets=req_facets,
        required_tags=req_tags,
        provider=provider,
        tier=tier,
        task_hint=task_hint,
        ready_only=ready,
        min_subjective_score=min_score,
        limit=limit,
    )

    payload = {
        "count": len(results),
        "index_summary": index_service.index.summary(),
        "models": [entry.to_dict() for entry in results],
        "filters": {
            "required_capabilities": sorted(req_caps) if req_caps else None,
            "required_facets": sorted(req_facets) if req_facets else None,
            "required_tags": sorted(req_tags) if req_tags else None,
            "filter_provider": provider,
            "tier": tier,
            "task_hint": task_hint,
            "ready_only": ready,
            "min_subjective_score": min_score,
        },
    }
    response = MCPResponse.success(data=payload)
    return [response.to_text_content()]


__all__ = ["tool_schema", "handle"]
