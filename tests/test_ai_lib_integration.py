# Tests for ai-lib ecosystem infrastructure integration
"""
Verify spiderswitch reuses ai-lib-python infrastructure:
- error classification (retry/fallback signals) surfaced to agents
- runtime profile reflects real ai-lib feature flags / protocol versions
测试 spiderswitch 对 ai-lib 生态基础设施的复用。
"""

from __future__ import annotations

import json

import pytest
from ai_lib_python.errors import RemoteError, TransportError
from ai_lib_python.errors.classification import ErrorClass

from spiderswitch.errors import ModelSwitcherError, describe_ai_lib_error
from spiderswitch.runtime.base import ModelCapabilities, ModelInfo, RuntimeProfile
from spiderswitch.runtime.python_runtime import PythonRuntime
from spiderswitch.state import ModelStateManager
from spiderswitch.tools import switch


def test_describe_ai_lib_error_extracts_remote_error_signals() -> None:
    remote = RemoteError(
        "rate limited",
        status_code=429,
        error_class=ErrorClass.RATE_LIMITED,
        retryable=True,
        fallbackable=True,
        retry_after=2.0,
        request_id="req-1",
    )
    wrapped = ModelSwitcherError("Failed to create client")
    wrapped.__cause__ = remote

    info = describe_ai_lib_error(wrapped)
    assert info is not None
    assert info["family"] == "RemoteError"
    assert info["source"] == "ai-lib-python"
    assert info["status_code"] == 429
    assert info["retryable"] is True
    assert info["fallbackable"] is True
    assert info["retry_after"] == 2.0
    assert info["request_id"] == "req-1"
    assert info["error_class"] == "rate_limited"


def test_describe_ai_lib_error_classifies_transport_error() -> None:
    transport = TransportError("connection reset", status_code=503)
    info = describe_ai_lib_error(transport)
    assert info is not None
    assert info["family"] == "TransportError"
    assert info["status_code"] == 503
    assert info["retryable"] is True


def test_describe_ai_lib_error_returns_none_for_non_ai_lib() -> None:
    assert describe_ai_lib_error(ValueError("nope")) is None


class _FailingRuntime(PythonRuntime):
    """Runtime that fails switch_model with an ai-lib RemoteError cause."""

    async def list_models(
        self,
        filter_provider: str | None = None,
        filter_capability: str | None = None,
    ) -> list[ModelInfo]:
        _ = filter_provider, filter_capability
        return [
            ModelInfo(
                id="openai/gpt-4o",
                provider="openai",
                capabilities=ModelCapabilities(streaming=True),
            )
        ]

    async def switch_model(
        self,
        model_id: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> ModelInfo:
        _ = api_key, base_url
        remote = RemoteError(
            "quota exhausted",
            status_code=429,
            error_class=ErrorClass.QUOTA_EXHAUSTED,
            retryable=False,
            fallbackable=True,
        )
        raise ModelSwitcherError(
            f"Failed to create client for model '{model_id}'",
            details={"provider": "openai"},
        ) from remote


@pytest.mark.asyncio
async def test_switch_error_surfaces_ai_lib_diagnostics() -> None:
    runtime = _FailingRuntime()
    state = ModelStateManager()
    result = await switch.handle(runtime, state, {"model": "openai/gpt-4o"})
    payload = json.loads(result[0].text)

    assert payload["status"] == "error"
    diagnostics = payload["error"]["details"]["ai_lib_error"]
    assert diagnostics["error_class"] == "quota_exhausted"
    assert diagnostics["fallbackable"] is True
    assert diagnostics["status_code"] == 429
    # Original spiderswitch details remain intact.
    assert payload["error"]["details"]["provider"] == "openai"


def test_runtime_profile_reports_ai_lib_infrastructure() -> None:
    profile = PythonRuntime().describe_runtime_profile()
    assert isinstance(profile, RuntimeProfile)
    ai_lib = profile.operational_metrics["ai_lib"]
    assert "ai_lib_version" in ai_lib
    assert "optional_features" in ai_lib
    assert set(ai_lib["optional_features"]).issuperset(
        {"vision", "audio", "telemetry", "tokenizer"}
    )
