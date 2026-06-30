"""Tests for smart routing policy engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from spiderswitch.policy.engine import PolicyEngine, TaskHint, TierPreference
from spiderswitch.policy.loader import ModelCatalog, ModelRecord


@pytest.fixture
def sample_catalog() -> ModelCatalog:
    return ModelCatalog(
        models={
            "deepseek/deepseek-chat": ModelRecord(
                id="deepseek/deepseek-chat",
                provider="deepseek",
                display_name="DeepSeek Chat",
                capabilities=["chat", "tools", "streaming"],
                tags=["cost-effective"],
                input_per_token=0.00000014,
                output_per_token=0.00000028,
            ),
            "openai/gpt-4o-mini": ModelRecord(
                id="openai/gpt-4o-mini",
                provider="openai",
                display_name="GPT-4o Mini",
                capabilities=["chat", "tools", "vision", "streaming"],
                tags=["cost-effective", "tools"],
                input_per_token=0.00000015,
                output_per_token=0.0000006,
            ),
            "openai/gpt-4o": ModelRecord(
                id="openai/gpt-4o",
                provider="openai",
                display_name="GPT-4o",
                capabilities=["chat", "tools", "vision", "streaming", "reasoning"],
                tags=["reasoning", "agentic"],
                input_per_token=0.000005,
                output_per_token=0.000015,
            ),
        }
    )


def test_cheap_task_prefers_deepseek(monkeypatch: pytest.MonkeyPatch, sample_catalog: ModelCatalog) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    engine = PolicyEngine(sample_catalog)
    rec = engine.recommend(task_hint="cheap", tier_preference="economy")
    assert rec.selected.model_id == "deepseek/deepseek-chat"


def test_code_task_requires_tools(monkeypatch: pytest.MonkeyPatch, sample_catalog: ModelCatalog) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    engine = PolicyEngine(sample_catalog)
    rec = engine.recommend(task_hint="code", tier_preference="balanced")
    assert "tools" in sample_catalog.models[rec.selected.model_id].capabilities


def test_premium_quality_prefers_gpt4o(monkeypatch: pytest.MonkeyPatch, sample_catalog: ModelCatalog) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    engine = PolicyEngine(sample_catalog)
    rec = engine.recommend(task_hint="quality", tier_preference="premium")
    assert rec.selected.model_id == "openai/gpt-4o"


def test_prefer_single_provider(monkeypatch: pytest.MonkeyPatch, sample_catalog: ModelCatalog) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    engine = PolicyEngine(sample_catalog)
    rec = engine.recommend(
        task_hint="chat",
        tier_preference="economy",
        prefer_provider="openai",
    )
    assert rec.selected.provider == "openai"


@pytest.mark.skipif(
    not Path("/home/alex/ai-protocol/v1/models").exists(),
    reason="ai-protocol not available",
)
def test_catalog_loads_from_protocol() -> None:
    catalog = ModelCatalog.from_protocol_path(Path("/home/alex/ai-protocol"))
    assert len(catalog.models) > 50
