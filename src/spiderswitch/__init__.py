# spiderswitch
"""
Model Context Protocol server for dynamic AI model switching in ai-lib ecosystem.
MCP服务器，用于ai-lib生态系统中的动态AI模型切换。

This package provides:
- MCP server with model switching capabilities
- Runtime abstraction layer for multiple ai-lib implementations
- Thread-safe state management
- Comprehensive error handling and validation

该包提供：
- 具有模型切换功能的 MCP 服务器
- 多个 ai-lib 实现的运行时抽象层
- 线程安全的状态管理
- 全面的错误处理和验证
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

# Lazy import to avoid loading mcp dependency on package import
# This allows the package to be imported in tests without mcp installed


def main() -> None:
    """Main entry point for the MCP server."""
    from spiderswitch.cli import main as cli_main

    _ = cli_main()


try:
    # Single source of truth: read from installed package metadata (pyproject).
    __version__ = version("spiderswitch")
except PackageNotFoundError:  # pragma: no cover - editable/source fallback
    __version__ = "0.6.0"


__all__ = ["main", "__version__"]
