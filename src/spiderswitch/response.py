# spiderswitch response utilities
"""
Unified MCP response format and utilities.
统一的 MCP 响应格式和工具类。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from mcp.types import TextContent


@dataclass
class MCPResponse:
    """Unified MCP response format.
    统一的 MCP 响应格式。

    Attributes:
        status: Response status - 'success' or 'error'
        data: Optional response data for successful responses
        error: Optional error information for error responses
        message: Optional human-readable message
    """

    status: str
    data: dict[str, Any] | None = None
    error_info: dict[str, Any] | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary representation.
        将响应转换为字典表示。

        Returns:
            Dictionary with response data
        """
        result: dict[str, Any] = {"status": self.status}

        if self.data is not None:
            result["data"] = self.data

        if self.error_info is not None:
            result["error"] = self.error_info

        if self.message is not None:
            result["message"] = self.message

        return result

    def to_text_content(self) -> TextContent:
        """Convert response to MCP TextContent.
        将响应转换为 MCP TextContent。

        Returns:
            TextContent object with serialized response
        """
        return TextContent(
            type="text",
            text=json.dumps(self.to_dict(), ensure_ascii=False),
        )

    @classmethod
    def success(
        cls,
        data: dict[str, Any],
        message: str | None = None,
    ) -> MCPResponse:
        """Create a successful response.
        创建成功响应。

        Args:
            data: Response data
            message: Optional success message

        Returns:
            MCPResponse with success status
        """
        return cls(status="success", data=data, message=message)

    @classmethod
    def error(
        cls,
        message: str,
        error_type: str = "RuntimeError",
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
        request_id: str | None = None,
    ) -> MCPResponse:
        """Create an error response.
        创建错误响应。

        Args:
            message: Error message
            error_type: Type of error
            details: Optional error details

        Returns:
            MCPResponse with error status
        """
        error_info: dict[str, Any] = {"type": error_type, "message": message}
        if error_code:
            error_info["code"] = error_code
        if request_id:
            error_info["request_id"] = request_id
        if details:
            error_info["details"] = details

        return cls(status="error", error_info=error_info, message=message)


__all__ = [
    "MCPResponse",
]
