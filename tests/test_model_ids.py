# Tests for shared model-id resolution
"""
Ensure runtime inventory and policy catalog derive identical public ids.
确保运行时与策略目录解析出一致的公开模型 id，避免 recommend/switch 矛盾。
"""

from __future__ import annotations

import pytest

from spiderswitch.model_ids import (
    resolve_public_model_id,
    resolve_public_model_name,
    resolve_runtime_model_id,
)


@pytest.mark.parametrize(
    ("provider", "model_name", "raw_model_id", "expected_public"),
    [
        ("openai", "gpt-4o", "gpt-4o", "openai/gpt-4o"),
        ("openai", "gpt-4o", "openai/gpt-4o", "openai/gpt-4o"),
        ("anthropic", "claude-3-5-sonnet", "anthropic/claude-3-5-sonnet", "anthropic/claude-3-5-sonnet"),
        ("google", "gemini-1.5-pro", "gemini-1.5-pro", "google/gemini-1.5-pro"),
        ("meta", "llama-3", "meta-llama/llama-3", "meta/llama-3"),
    ],
)
def test_public_model_id_resolution(
    provider: str, model_name: str, raw_model_id: str, expected_public: str
) -> None:
    assert resolve_public_model_id(provider, model_name, raw_model_id) == expected_public
    # Public name is the part after the provider prefix.
    assert resolve_public_model_name(provider, model_name, raw_model_id) == (
        expected_public.split("/", 1)[1]
    )


def test_runtime_model_id_is_provider_prefixed() -> None:
    assert resolve_runtime_model_id("openai", "gpt-4o") == "openai/gpt-4o"
    assert resolve_runtime_model_id("openai", "openai/gpt-4o") == "openai/gpt-4o"
