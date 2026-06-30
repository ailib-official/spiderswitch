# Tests for smart routing MCP tool schemas

from __future__ import annotations

from spiderswitch.tools import auto_switch, recommend


class TestRecommendTool:
    def test_tool_schema(self) -> None:
        schema = recommend.tool_schema()
        assert schema.name == "recommend_model"
        props = schema.inputSchema["properties"]
        assert "task_hint" in props
        assert "tier" in props
        assert "prefer_provider" in props


class TestAutoSwitchTool:
    def test_tool_schema(self) -> None:
        schema = auto_switch.tool_schema()
        assert schema.name == "auto_switch"
        assert "task_hint" in schema.inputSchema["properties"]
