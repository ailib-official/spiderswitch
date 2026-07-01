# Tests for capability index and subjective experience
"""Test structured capability indexing and experience accumulation."""

from __future__ import annotations

from pathlib import Path

import pytest

from spiderswitch.index.builder import build_index
from spiderswitch.index.experience import ExperienceStore
from spiderswitch.index.schema import StructuredCapabilities
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
            "openai/gpt-4o": ModelRecord(
                id="openai/gpt-4o",
                provider="openai",
                display_name="GPT-4o",
                capabilities=["chat", "tools", "vision", "streaming"],
                tags=["reasoning"],
                input_per_token=0.000005,
                output_per_token=0.000015,
                context_window=128_000,
            ),
        }
    )


def test_structured_capabilities_derives_facets() -> None:
    structured = StructuredCapabilities.from_protocol(
        ["tools", "vision", "streaming"],
        ["agentic"],
        context_window=200_000,
    )
    assert "tools" in structured.core
    assert "multimodal" in structured.derived
    assert "ultra_context" in structured.derived
    assert "agentic" in structured.derived


def test_build_index_creates_inverted_postings(
    sample_catalog: ModelCatalog, tmp_path: Path
) -> None:
    experience = ExperienceStore(path=tmp_path / "experience.json")
    index = build_index(sample_catalog, protocol_path=tmp_path, experience=experience)

    assert index.total_models == 2
    assert "tools" in index.by_core_capability
    assert "openai/gpt-4o" in index.by_core_capability["tools"]
    assert "vision" in index.by_core_capability
    assert "multimodal" in index.by_derived_facet
    assert "code" in index.by_task_hint


def test_index_query_by_capabilities(sample_catalog: ModelCatalog, tmp_path: Path) -> None:
    experience = ExperienceStore(path=tmp_path / "experience.json")
    index = build_index(sample_catalog, protocol_path=tmp_path, experience=experience)

    results = index.query(
        required_capabilities={"vision", "tools"},
        ready_only=False,
        limit=10,
    )
    assert len(results) == 1
    assert results[0].model_id == "openai/gpt-4o"


def test_experience_store_accumulates_and_affects_rank(
    sample_catalog: ModelCatalog, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    experience = ExperienceStore(path=tmp_path / "experience.json")
    experience.record_ratings("openai/gpt-4o", quality=5.0, speed=5.0, value=5.0)
    experience.record_switch("openai/gpt-4o", success=True, task_hint="code")

    index = build_index(sample_catalog, protocol_path=tmp_path, experience=experience)
    entry = index.entries["openai/gpt-4o"]
    assert entry.subjective.sample_count >= 0
    assert entry.subjective.switch_success == 1
    assert entry.subjective.subjective_score > 0.5


def test_index_query_min_subjective_score(sample_catalog: ModelCatalog, tmp_path: Path) -> None:
    experience = ExperienceStore(path=tmp_path / "experience.json")
    experience.record_ratings("openai/gpt-4o", quality=5.0)
    index = build_index(sample_catalog, protocol_path=tmp_path, experience=experience)

    high = index.query(min_subjective_score=0.8, ready_only=False)
    assert any(r.model_id == "openai/gpt-4o" for r in high)

    # deepseek has neutral prior 0.5 — excluded by high threshold
    low_only = index.query(min_subjective_score=0.55, ready_only=False)
    assert all(r.model_id == "openai/gpt-4o" for r in low_only)
