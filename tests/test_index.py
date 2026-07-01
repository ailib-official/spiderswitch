# Tests for capability index and subjective experience
"""Test structured capability indexing and experience accumulation."""

from __future__ import annotations

from pathlib import Path

import pytest

from spiderswitch.index.builder import build_index, refresh_dynamic_fields
from spiderswitch.index.experience import ExperienceStore
from spiderswitch.index.schema import StructuredCapabilities
from spiderswitch.index.service import ModelIndexService
from spiderswitch.index.store import compute_protocol_fingerprint, load_index, save_index
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


def _make_protocol_dir(tmp_path: Path) -> Path:
    model_dir = tmp_path / "v1" / "models"
    model_dir.mkdir(parents=True)
    (model_dir / "fixtures.yaml").write_text("models: {}\n", encoding="utf-8")
    return tmp_path


def test_index_persist_load_roundtrip(sample_catalog: ModelCatalog, tmp_path: Path) -> None:
    protocol = _make_protocol_dir(tmp_path)
    experience = ExperienceStore(path=tmp_path / "experience.json")
    index = build_index(sample_catalog, protocol_path=protocol, experience=experience)
    fingerprint = compute_protocol_fingerprint(protocol)
    index_file = tmp_path / "capability-index.json"
    save_index(index, path=index_file, protocol_fingerprint=fingerprint)

    loaded = load_index(index_file, protocol_path=protocol)
    assert loaded is not None
    restored, meta = loaded
    assert meta.fingerprint_stale is False
    assert restored.total_models == index.total_models
    assert set(restored.entries.keys()) == set(index.entries.keys())
    assert restored.by_core_capability["tools"]


def test_load_index_skips_yaml_parse_on_dynamic_refresh(
    sample_catalog: ModelCatalog, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    protocol = _make_protocol_dir(tmp_path)
    experience = ExperienceStore(path=tmp_path / "experience.json")
    index = build_index(sample_catalog, protocol_path=protocol, experience=experience)
    index_file = tmp_path / "capability-index.json"
    save_index(
        index, path=index_file, protocol_fingerprint=compute_protocol_fingerprint(protocol)
    )

    def fail_yaml(*_args: object, **_kwargs: object) -> ModelCatalog:
        raise AssertionError("ModelCatalog.from_protocol_path should not run on load path")

    monkeypatch.setattr(ModelCatalog, "from_protocol_path", fail_yaml)
    loaded = load_index(index_file, protocol_path=protocol)
    assert loaded is not None
    restored, _ = loaded
    refresh_dynamic_fields(restored, experience)
    assert restored.ready_models >= 1


def test_fingerprint_stale_detection(sample_catalog: ModelCatalog, tmp_path: Path) -> None:
    protocol = _make_protocol_dir(tmp_path)
    experience = ExperienceStore(path=tmp_path / "experience.json")
    index = build_index(sample_catalog, protocol_path=protocol, experience=experience)
    index_file = tmp_path / "capability-index.json"
    save_index(index, path=index_file, protocol_fingerprint="stale-fingerprint")

    loaded = load_index(index_file, protocol_path=protocol)
    assert loaded is not None
    _, meta = loaded
    assert meta.fingerprint_stale is True


def test_model_index_service_load_from_disk(
    sample_catalog: ModelCatalog, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    protocol = _make_protocol_dir(tmp_path)
    monkeypatch.setenv("SPIDERSWITCH_INDEX_PATH", str(tmp_path / "capability-index.json"))
    experience = ExperienceStore(path=tmp_path / "experience.json")
    index = build_index(sample_catalog, protocol_path=protocol, experience=experience)
    save_index(
        index,
        path=tmp_path / "capability-index.json",
        protocol_fingerprint=compute_protocol_fingerprint(protocol),
    )

    service, status = ModelIndexService.load_or_build_for_cli(protocol)
    assert service is not None
    assert status["loaded"] is True
    assert service.index.total_models == 2
