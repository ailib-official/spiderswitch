# spiderswitch MCP server
"""
MCP server entry point for model switching.
MCP服务器主入口，提供模型切换功能。

Provides dependency injection for better testability and multiple instance support.
提供依赖注入以便于更好的测试和多实例支持。
"""

from __future__ import annotations

import asyncio
import logging
import sys
from uuid import uuid4

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import GetPromptResult, Prompt, TextContent, Tool

from . import prompts as prompt_catalog
from .index.service import ModelIndexService
from .response import MCPResponse
from .runtime import PythonRuntime
from .runtime.base import Runtime
from .runtime.registry import RuntimeRegistry, RuntimeResolver
from .state import ModelStateManager
from .tools import auto_switch, query_index, recommend, record_experience, reset, status, switch
from .tools import list as list_tool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def _redact_sensitive_arguments(arguments: dict[str, object]) -> dict[str, object]:
    """Redact potentially sensitive tool arguments for logging.

    屏蔽日志中的敏感参数，避免 API key 等泄露。
    """
    redacted: dict[str, object] = {}
    sensitive_markers = ("key", "token", "secret", "password", "authorization")
    for key, value in arguments.items():
        lowered = key.lower()
        if any(marker in lowered for marker in sensitive_markers):
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted


def _runtime_id_from_args(arguments: dict[str, object]) -> str | None:
    """Extract runtime_id argument with strict type check."""
    runtime_id_raw = arguments.get("runtime_id")
    return runtime_id_raw if isinstance(runtime_id_raw, str) else None


def create_app(
    runtime: Runtime | None = None,
    runtimes: dict[str, Runtime] | None = None,
    state_manager: ModelStateManager | None = None,
    index_service: ModelIndexService | None = None,
) -> Server:
    """Create MCP server with optional dependencies.

    This factory function allows for dependency injection, making the server
    more testable and enabling multiple instances with different runtimes.

    Args:
        runtime: Optional runtime instance. If None, uses PythonRuntime
        state_manager: Optional state manager instance. If None, creates new one

    Returns:
        Configured MCP Server instance
    """
    _runtime = runtime or PythonRuntime()
    runtime_map = dict(runtimes or {})
    if not runtime_map:
        profile = _runtime.describe_runtime_profile()
        runtime_map[profile.runtime_id] = _runtime
    if runtime and _runtime.describe_runtime_profile().runtime_id not in runtime_map:
        runtime_map[_runtime.describe_runtime_profile().runtime_id] = _runtime
    default_runtime_id = _runtime.describe_runtime_profile().runtime_id
    registry = RuntimeRegistry(runtimes=runtime_map, default_runtime_id=default_runtime_id)
    resolver = RuntimeResolver(registry)
    _state = state_manager or ModelStateManager()

    _index_service = index_service
    if _index_service is None and isinstance(_runtime, PythonRuntime):
        try:
            _index_service = ModelIndexService.load_from_runtime(_runtime)
            if _index_service is not None:
                logger.info(
                    "Capability index ready: %d models indexed",
                    _index_service.index.total_models,
                )
        except Exception as index_error:
            logger.warning("Capability index build failed: %s", index_error)

    def _resolve_target_runtime(args: dict[str, object]) -> Runtime:
        """Resolve the runtime instance for a tool call.

        Resolution order is fixed: request runtime_id -> active state runtime_id
        -> default runtime. Selection policy stays in upper-layer applications.
        解析目标运行时，顺序固定：请求 -> 活动状态 -> 默认。
        """
        resolution = resolver.resolve(
            requested_runtime_id=_runtime_id_from_args(args),
            active_runtime_id=_state.get_state().runtime_id,
        )
        _, target_runtime = registry.get_runtime(resolution.runtime_id)
        return target_runtime

    app = Server("spiderswitch", instructions=prompt_catalog.SERVER_INSTRUCTIONS)

    @app.list_prompts()  # type: ignore[no-untyped-call,untyped-decorator]
    async def list_prompts() -> list[Prompt]:
        """Expose injectable prompt templates that steer model switching."""
        return prompt_catalog.list_prompts()

    @app.get_prompt()  # type: ignore[no-untyped-call,untyped-decorator]
    async def get_prompt(
        name: str,
        arguments: dict[str, str] | None,
    ) -> GetPromptResult:
        """Render a prompt template by name."""
        return prompt_catalog.get_prompt(name, arguments)

    @app.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
    async def list_tools() -> list[Tool]:
        """Expose available MCP tools.

        Returns:
            List of Tool objects
        """
        return [
            switch.tool_schema(),
            list_tool.tool_schema(),
            status.tool_schema(),
            reset.tool_schema(),
            recommend.tool_schema(),
            auto_switch.tool_schema(),
            query_index.tool_schema(),
            record_experience.tool_schema(),
        ]

    @app.call_tool()  # type: ignore[untyped-decorator]
    async def call_tool(
        name: str,
        arguments: dict[str, object] | None,
    ) -> list[TextContent]:
        """Handle tool calls with structured error logging.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            List of response content or error content
        """
        args = arguments or {}
        request_id = str(uuid4())
        try:
            if name == "switch_model":
                return await switch.handle(
                    _resolve_target_runtime(args), _state, args, index_service=_index_service
                )
            elif name == "list_models":
                return await list_tool.handle(_resolve_target_runtime(args), args)
            elif name == "get_status":
                return await status.handle(_state, _resolve_target_runtime(args))
            elif name == "exit_switcher":
                scope_raw = args.get("scope")
                scope = (
                    scope_raw
                    if isinstance(scope_raw, str) and scope_raw in {"all", "runtime"}
                    else "all"
                )
                resolution = resolver.resolve(
                    requested_runtime_id=_runtime_id_from_args(args),
                    active_runtime_id=_state.get_state().runtime_id,
                )
                _, target_runtime = registry.get_runtime(resolution.runtime_id)
                return await reset.handle(
                    target_runtime, _state, runtime_id=resolution.runtime_id, scope=scope
                )
            elif name == "recommend_model":
                return await recommend.handle(
                    _resolve_target_runtime(args), args, index_service=_index_service
                )
            elif name == "auto_switch":
                return await auto_switch.handle(
                    _resolve_target_runtime(args), _state, args, index_service=_index_service
                )
            elif name == "query_index":
                return await query_index.handle(_index_service, args)
            elif name == "record_experience":
                return await record_experience.handle(_index_service, args)
            else:
                logger.warning(f"Unknown tool requested: {name}")
                response = MCPResponse.error(
                    message=f"Unknown tool: {name}",
                    error_type="UnknownToolError",
                    error_code="SPIDER-UNKNOWN-TOOL",
                    request_id=request_id,
                )
                return [response.to_text_content()]
        except Exception as e:
            logger.exception(
                f"Error handling tool call '{name}': {e}",
                extra={
                    "tool": name,
                    "request_id": request_id,
                    "arguments": _redact_sensitive_arguments(args),
                }
            )
            response = MCPResponse.error(
                message="Internal server error",
                error_type="InternalServerError",
                error_code="SPIDER-INTERNAL-ERROR",
                request_id=request_id,
            )
            return [response.to_text_content()]

    return app


async def main(
    runtime: Runtime | None = None,
    runtimes: dict[str, Runtime] | None = None,
    state_manager: ModelStateManager | None = None,
) -> None:
    """Main entry point for the MCP server.

    Runs the stdio server and handles cleanup on shutdown.

    Args:
        runtime: Optional runtime instance for dependency injection
        state_manager: Optional state manager for dependency injection
    """
    logger.info("Starting spiderswitch MCP server")

    _runtime = runtime or PythonRuntime()
    _state = state_manager or ModelStateManager()
    app = create_app(_runtime, runtimes=runtimes, state_manager=_state)

    try:
        # Run stdio server
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.exception(f"Server error: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Cleaning up resources...")
        try:
            await _runtime.close()
            if runtimes:
                for runtime_id, extra_runtime in runtimes.items():
                    if extra_runtime is _runtime:
                        continue
                    try:
                        await extra_runtime.close()
                    except Exception as runtime_close_error:
                        logger.error("Error closing runtime '%s': %s", runtime_id, runtime_close_error)
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        logger.info("Server shutdown complete")


def cli() -> None:
    """CLI entry point for the server."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()


__all__ = ["create_app", "main", "cli"]
