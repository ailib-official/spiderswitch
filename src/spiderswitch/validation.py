# spiderswitch validation utilities
"""
Input validation utilities for model parameters.
模型参数输入验证工具类。
"""

from __future__ import annotations

import os
import re
from typing import Any

from .errors import ApiKeyMissingError, InvalidModelError, ValidationError

# Model ID format: provider/model
# 模型 ID 格式：provider/model
MODEL_PATTERN = re.compile(r"^[a-z0-9-]+/[a-z0-9-.]+$")

# API key environment variable mapping by provider.
# Provider-specific env var names are intentionally centralized for diagnostics only.
# Provider 的密钥环境变量映射，仅用于错误提示与引导。
PROVIDER_API_KEY_ENV: dict[str, tuple[str, ...]] = {
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "google": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    "deepseek": ("DEEPSEEK_API_KEY",),
    "cohere": ("COHERE_API_KEY",),
    "mistral": ("MISTRAL_API_KEY",),
    "meta": ("META_API_KEY",),
}

# Common proxy environment variables honored by Python networking stacks.
PROXY_ENV_VARS: tuple[str, ...] = (
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "ALL_PROXY",
    "https_proxy",
    "http_proxy",
    "all_proxy",
)

# Heuristic-only list for providers that often require proxy routing in some regions.
PROVIDERS_MAY_REQUIRE_PROXY: set[str] = {"openai", "anthropic", "google", "cohere", "mistral"}


class Validator:
    """Input validator for model parameters.
    模型参数输入验证器。
    """

    def __init__(
        self,
        valid_providers: set[str] | None = None,
        strict: bool = True,
    ) -> None:
        """Initialize validator.

        Args:
            valid_providers: Set of valid provider IDs. If None, uses default
            strict: If True, raises exception on validation failure; if False,
                   returns False
        """
        self.valid_providers = valid_providers or set()
        self.strict = strict

    def validate_model_id(self, model_id: str) -> None:
        """Validate model ID format.

        Args:
            model_id: Model ID to validate

        Raises:
            InvalidModelError: If validation fails and strict=True
        """
        if not isinstance(model_id, str):
            self._raise_error(
                InvalidModelError,
                f"Model ID must be a string, got {type(model_id).__name__}",
            )

        if not model_id:
            self._raise_error(
                InvalidModelError,
                "Model ID cannot be empty",
            )

        if not MODEL_PATTERN.match(model_id):
            self._raise_error(
                InvalidModelError,
                f"Invalid model format: '{model_id}'. "
                f"Expected format: 'provider/model' (e.g., 'openai/gpt-4o')",
            )

        # Do not hardcode provider list here.
        # Provider existence must be determined from protocol-loaded model inventory.
        # 不在此处硬编码 provider 列表；由协议加载结果判定 provider 是否存在。

    def validate_api_key(self, api_key: Any) -> None:
        """Validate API key.

        Args:
            api_key: API key to validate

        Raises:
            ValidationError: If validation fails and strict=True
        """
        if api_key is None:
            # API key is optional
            return

        if not isinstance(api_key, str):
            self._raise_error(
                ValidationError,
                f"API key must be a string, got {type(api_key).__name__}",
            )

        # Some basic sanity checks
        if not api_key:
            self._raise_error(
                ValidationError,
                "API key cannot be empty string",
            )

        # Check for common placeholder strings
        placeholder_patterns = [
            "your-api-key",
            "your_api_key",
            "sk-...",
            "sk-ant-...",
        ]
        for pattern in placeholder_patterns:
            if api_key == pattern or api_key.startswith(pattern):
                self._raise_error(
                    ValidationError,
                    f"API key appears to be a placeholder: '{pattern}'",
                )

    def validate_base_url(self, base_url: Any) -> None:
        """Validate base URL.

        Args:
            base_url: Base URL to validate

        Raises:
            ValidationError: If validation fails and strict=True
        """
        if base_url is None:
            # Base URL is optional
            return

        if not isinstance(base_url, str):
            self._raise_error(
                ValidationError,
                f"Base URL must be a string, got {type(base_url).__name__}",
            )

        if not base_url:
            self._raise_error(
                ValidationError,
                "Base URL cannot be empty string",
            )

        # Check URL format
        if not base_url.startswith(("http://", "https://")):
            self._raise_error(
                ValidationError,
                f"Invalid base URL format: '{base_url}'. Must start with http:// or https://",
            )

    def validate_switch_arguments(
        self,
        model: Any,
        api_key: Any = None,
        base_url: Any = None,
    ) -> tuple[str, str | None, str | None]:
        """Validate all switch_model arguments.

        Args:
            model: Model ID argument
            api_key: Optional API key argument
            base_url: Optional base URL argument

        Returns:
            Tuple of (model, api_key, base_url) with proper types

        Raises:
            ValidationError: If any validation fails
        """
        # Validate model
        if not model or not isinstance(model, str):
            raise InvalidModelError(
                "Missing required parameter: 'model'",
            )

        self.validate_model_id(model)
        self.validate_api_key(api_key)
        self.validate_base_url(base_url)

        return (model, api_key, base_url)

    def validate_api_key_configuration(
        self,
        model_id: str,
        api_key: str | None,
    ) -> None:
        """Validate API key availability for a target model.

        Args:
            model_id: Target model ID
            api_key: Optional explicit API key

        Raises:
            ApiKeyMissingError: If explicit and environment keys are both missing
        """
        if api_key:
            return

        provider = self._extract_provider(model_id)
        expected_env = PROVIDER_API_KEY_ENV.get(provider, ())
        if not expected_env:
            # Unknown mapping: skip strict env validation and let runtime/provider decide.
            return

        if any(os.getenv(key) for key in expected_env):
            return

        raise ApiKeyMissingError(
            f"Missing API key for provider '{provider}'.",
            details={
                "provider": provider,
                "expected_env_vars": list(expected_env),
                "hint": (
                    "Set one of the expected environment variables in your MCP server "
                    "process before calling switch_model."
                ),
            },
        )

    def _extract_provider(self, model_id: str) -> str:
        """Extract provider ID from model ID.

        Args:
            model_id: Model ID string

        Returns:
            Provider ID
        """
        return model_id.split("/", 1)[0]

    def _raise_error(
        self,
        error_class: type[Exception],
        message: str,
    ) -> None:
        """Raise an exception if in strict mode.

        Args:
            error_class: Exception class to raise
            message: Error message

        Raises:
            The specified exception if strict=True
        """
        if self.strict:
            raise error_class(message)


# Default validator instance
DEFAULT_VALIDATOR = Validator()


def get_provider_api_key_status(provider: str) -> dict[str, object]:
    """Get local API key status for a provider without exposing values."""
    expected_env_vars = list(PROVIDER_API_KEY_ENV.get(provider, ()))
    configured_env_vars = [key for key in expected_env_vars if os.getenv(key)]
    return {
        "provider": provider,
        "has_api_key": bool(configured_env_vars),
        "expected_env_vars": expected_env_vars,
        "configured_env_vars": configured_env_vars,
    }


def get_provider_proxy_status(provider: str) -> dict[str, object]:
    """Get local proxy readiness status for a provider."""
    configured_proxy_env_vars = [key for key in PROXY_ENV_VARS if os.getenv(key)]
    proxy_required_guess = provider in PROVIDERS_MAY_REQUIRE_PROXY
    proxy_configured = bool(configured_proxy_env_vars)
    hint: str | None = None
    if proxy_required_guess and not proxy_configured:
        hint = (
            "This provider may require proxy access in your network region. "
            "Set HTTPS_PROXY/HTTP_PROXY in the MCP server process environment if needed."
        )
    return {
        "provider": provider,
        "proxy_required_guess": proxy_required_guess,
        "proxy_configured": proxy_configured,
        "configured_proxy_env_vars": configured_proxy_env_vars,
        "hint": hint,
    }


__all__ = [
    "Validator",
    "DEFAULT_VALIDATOR",
    "MODEL_PATTERN",
    "PROVIDER_API_KEY_ENV",
    "PROXY_ENV_VARS",
    "PROVIDERS_MAY_REQUIRE_PROXY",
    "get_provider_api_key_status",
    "get_provider_proxy_status",
]
