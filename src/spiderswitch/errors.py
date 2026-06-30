# spiderswitch custom exceptions
"""
Custom exceptions for better error handling in the model switcher.
自定义异常类，用于改进模型切换器的错误处理。
"""

from __future__ import annotations


def describe_ai_lib_error(exc: BaseException) -> dict[str, object] | None:
    """Extract standardized diagnostics from an ai-lib-python error.

    Walks the exception chain (``__cause__`` / ``__context__``) looking for an
    ``ai_lib_python.errors.AiLibError``. When found, it returns agent-actionable
    routing signals sourced from the ai-lib ecosystem error contract:
    ``error_class``, ``retryable``, ``fallbackable``, ``retry_after``,
    ``status_code``, ``request_id`` and any diagnostic ``hint``.

    Returns ``None`` when the failure did not originate from ai-lib, so callers
    can keep their existing behavior unchanged.

    复用 ai-lib 生态的错误分类基础设施：从异常链中提取标准化的可重试/可回退信号，
    供上层 Agent 做路由决策。
    """
    try:
        from ai_lib_python.errors import (
            AiLibError,
            RemoteError,
            TransportError,
            classify_http_error,
            is_fallbackable,
            is_retryable,
        )
    except ImportError:  # pragma: no cover - ai-lib is a hard dependency
        return None

    seen: set[int] = set()
    current: BaseException | None = exc
    ai_error: AiLibError | None = None
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, AiLibError):
            ai_error = current
            break
        current = current.__cause__ or current.__context__

    if ai_error is None:
        return None

    info: dict[str, object] = {
        "source": "ai-lib-python",
        "family": ai_error.__class__.__name__,
    }

    error_class = None
    if isinstance(ai_error, RemoteError):
        error_class = ai_error.error_class
        info["status_code"] = ai_error.status_code
        info["retryable"] = bool(ai_error.retryable)
        info["fallbackable"] = bool(ai_error.fallbackable)
        if ai_error.retry_after is not None:
            info["retry_after"] = ai_error.retry_after
        if ai_error.request_id:
            info["request_id"] = ai_error.request_id
    elif isinstance(ai_error, TransportError):
        status_code = getattr(ai_error, "status_code", None)
        if status_code is not None:
            info["status_code"] = status_code
            try:
                error_class = classify_http_error(status_code)
            except Exception:  # pragma: no cover - defensive
                error_class = None
        # Transport-level failures (timeouts, connection resets) are transient.
        info.setdefault("retryable", True)

    context = getattr(ai_error, "context", None)
    if context is not None:
        hint = getattr(context, "hint", None)
        if hint:
            info["hint"] = hint
        origin = getattr(context, "source", None)
        if origin:
            info["origin"] = origin

    if error_class is not None:
        info["error_class"] = getattr(error_class, "value", str(error_class))
        info.setdefault("retryable", bool(is_retryable(error_class)))
        info.setdefault("fallbackable", bool(is_fallbackable(error_class)))

    return info


class ModelSwitcherError(Exception):
    """Base exception for all model switcher errors.
    模型切换器的基础异常类。"""

    def __init__(
        self,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        """Initialize exception.

        Args:
            message: Error message
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, object]:
        """Convert exception to dictionary for MCP response."""
        result: dict[str, object] = {
            "error_type": self.__class__.__name__,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class ModelNotFoundError(ModelSwitcherError):
    """Model not found in available models.
    在可用模型中找不到指定的模型。"""

    pass


class InvalidModelError(ModelSwitcherError):
    """Invalid model format or parameters.
    无效的模型格式或参数。"""

    pass


class ProviderNotAvailableError(ModelSwitcherError):
    """Provider is not available or not configured.
    Provider 不可用或未配置。"""

    pass


class ApiKeyMissingError(ModelSwitcherError):
    """API key is missing for the provider.
    缺少 Provider 的 API 密钥。"""

    pass


class ConnectionError(ModelSwitcherError):
    """Failed to connect to provider API.
    无法连接到 Provider API。"""

    pass


class ValidationError(ModelSwitcherError):
    """Input validation failed.
    输入验证失败。"""

    pass


__all__ = [
    "describe_ai_lib_error",
    "ModelSwitcherError",
    "ModelNotFoundError",
    "InvalidModelError",
    "ProviderNotAvailableError",
    "ApiKeyMissingError",
    "ConnectionError",
    "ValidationError",
]
