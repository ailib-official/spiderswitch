# spiderswitch model capability index builder
"""
Build inverted indexes over all available models at startup.

Indexes are structured in layers (core capabilities, derived facets, tags,
provider, tier, task_hint) and ranked by readiness + subjective score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..policy.engine import TASK_REQUIRED_CAPS, TaskHint
from ..policy.loader import ModelCatalog, ModelRecord
from ..validation import get_provider_api_key_status
from .experience import ExperienceStore, SubjectiveRecord
from .schema import StructuredCapabilities

INDEX_VERSION = "cap-index-v1"


@dataclass
class ModelIndexEntry:
    """One model in the capability index."""

    model_id: str
    provider: str
    display_name: str
    structured: StructuredCapabilities
    tier: str
    ready: bool
    context_window: int | None
    subjective: SubjectiveRecord
    rank_score: float
    input_per_token: float | None = None
    blended_cost_per_1m: float = 9999.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "display_name": self.display_name,
            "capabilities": self.structured.to_dict(),
            "tier": self.tier,
            "ready": self.ready,
            "context_window": self.context_window,
            "subjective": self.subjective.to_dict(),
            "rank_score": round(self.rank_score, 4),
            "input_per_token": self.input_per_token,
            "blended_cost_per_1m": self.blended_cost_per_1m,
        }


@dataclass
class ModelCapabilityIndex:
    """Startup-built capability index with inverted posting lists."""

    version: str
    built_at: str
    protocol_path: str
    total_models: int
    ready_models: int
    by_core_capability: dict[str, list[str]] = field(default_factory=dict)
    by_derived_facet: dict[str, list[str]] = field(default_factory=dict)
    by_tag: dict[str, list[str]] = field(default_factory=dict)
    by_provider: dict[str, list[str]] = field(default_factory=dict)
    by_tier: dict[str, list[str]] = field(default_factory=dict)
    by_task_hint: dict[str, list[str]] = field(default_factory=dict)
    entries: dict[str, ModelIndexEntry] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "built_at": self.built_at,
            "protocol_path": self.protocol_path,
            "total_models": self.total_models,
            "ready_models": self.ready_models,
            "core_capability_buckets": {
                k: len(v) for k, v in sorted(self.by_core_capability.items())
            },
            "derived_facet_buckets": {
                k: len(v) for k, v in sorted(self.by_derived_facet.items())
            },
            "task_hint_buckets": {k: len(v) for k, v in sorted(self.by_task_hint.items())},
        }

    def query(
        self,
        *,
        required_capabilities: set[str] | None = None,
        required_facets: set[str] | None = None,
        required_tags: set[str] | None = None,
        provider: str | None = None,
        tier: str | None = None,
        task_hint: str | None = None,
        ready_only: bool = True,
        min_subjective_score: float | None = None,
        limit: int = 20,
    ) -> list[ModelIndexEntry]:
        """Query models by structured capability requirements."""
        candidate_ids: set[str] | None = None

        def intersect(current: set[str]) -> None:
            nonlocal candidate_ids
            candidate_ids = current if candidate_ids is None else candidate_ids & current

        if task_hint:
            hint_key = task_hint.lower()
            if hint_key in self.by_task_hint:
                intersect(set(self.by_task_hint[hint_key]))
            hint_enum = TaskHint(hint_key) if hint_key in TaskHint._value2member_map_ else None
            if hint_enum and hint_enum in TASK_REQUIRED_CAPS:
                for cap in TASK_REQUIRED_CAPS[hint_enum]:
                    if cap in self.by_core_capability:
                        intersect(set(self.by_core_capability[cap]))

        if required_capabilities:
            for cap in required_capabilities:
                bucket = self.by_core_capability.get(cap.lower())
                if bucket is None:
                    return []
                intersect(set(bucket))

        if required_facets:
            for facet in required_facets:
                bucket = self.by_derived_facet.get(facet.lower())
                if bucket is None:
                    return []
                intersect(set(bucket))

        if required_tags:
            for tag in required_tags:
                bucket = self.by_tag.get(tag.lower())
                if bucket is None:
                    return []
                intersect(set(bucket))

        if provider:
            bucket = self.by_provider.get(provider)
            if not bucket:
                return []
            intersect(set(bucket))

        if tier:
            bucket = self.by_tier.get(tier.lower())
            if not bucket:
                return []
            intersect(set(bucket))

        if candidate_ids is None:
            candidate_ids = set(self.entries.keys())

        results: list[ModelIndexEntry] = []
        for model_id in candidate_ids:
            entry = self.entries.get(model_id)
            if entry is None:
                continue
            if ready_only and not entry.ready:
                continue
            if min_subjective_score is not None and entry.subjective.subjective_score < min_subjective_score:
                continue
            if required_capabilities or required_facets:
                req_core = {c.lower() for c in (required_capabilities or set())}
                req_derived = {f.lower() for f in (required_facets or set())}
                if not entry.structured.satisfies(req_core, req_derived):
                    continue
            results.append(entry)

        results.sort(key=lambda e: (-e.rank_score, e.model_id))
        return results[:limit]


def _classify_tier(record: ModelRecord, catalog: ModelCatalog) -> str:
    costs = sorted(m.blended_cost_per_1m for m in catalog.models.values())
    if not costs:
        return "balanced"
    p33 = costs[max(0, len(costs) // 3 - 1)]
    p66 = costs[min(len(costs) - 1, (2 * len(costs)) // 3)]
    cost = record.blended_cost_per_1m
    if cost <= p33:
        return "economy"
    if cost >= p66:
        return "premium"
    return "balanced"


def compute_rank_score(
    *,
    ready: bool,
    subjective: SubjectiveRecord,
    input_per_token: float | None = None,
    blended_cost_per_1m: float = 9999.0,
) -> float:
    score = subjective.subjective_score
    if ready:
        score += 0.15
    if input_per_token is not None:
        score += 0.02
    score += 0.05 / max(blended_cost_per_1m, 0.001)
    return score


def compute_rank_score_for_record(
    record: ModelRecord, *, ready: bool, subjective: SubjectiveRecord
) -> float:
    return compute_rank_score(
        ready=ready,
        subjective=subjective,
        input_per_token=record.input_per_token,
        blended_cost_per_1m=record.blended_cost_per_1m,
    )


def _posting_add(bucket: dict[str, list[str]], key: str, model_id: str, rank: float) -> None:
    bucket.setdefault(key, []).append((rank, model_id))  # type: ignore[arg-type]


def _finalize_buckets(buckets: dict[str, list[Any]]) -> dict[str, list[str]]:
    finalized: dict[str, list[str]] = {}
    for key, items in buckets.items():
        if not items:
            continue
        if isinstance(items[0], tuple):
            sorted_items = sorted(items, key=lambda x: (-x[0], x[1]))
            finalized[key] = [mid for _, mid in sorted_items]
        else:
            finalized[key] = list(items)
    return finalized


def build_index(
    catalog: ModelCatalog,
    *,
    protocol_path: Path,
    experience: ExperienceStore,
) -> ModelCapabilityIndex:
    """Build full capability index from catalog + experience store."""
    by_core: dict[str, list[Any]] = {}
    by_derived: dict[str, list[Any]] = {}
    by_tag: dict[str, list[Any]] = {}
    by_provider: dict[str, list[Any]] = {}
    by_tier: dict[str, list[Any]] = {}
    by_task: dict[str, list[Any]] = {}
    entries: dict[str, ModelIndexEntry] = {}

    for record in catalog.models.values():
        structured = StructuredCapabilities.from_protocol(
            record.capabilities,
            record.tags,
            record.context_window,
        )
        ready = bool(get_provider_api_key_status(record.provider).get("has_api_key"))
        subjective = experience.get(record.id)
        tier = _classify_tier(record, catalog)
        rank = compute_rank_score_for_record(record, ready=ready, subjective=subjective)

        entry = ModelIndexEntry(
            model_id=record.id,
            provider=record.provider,
            display_name=record.display_name,
            structured=structured,
            tier=tier,
            ready=ready,
            context_window=record.context_window,
            subjective=subjective,
            rank_score=rank,
            input_per_token=record.input_per_token,
            blended_cost_per_1m=record.blended_cost_per_1m,
        )
        entries[record.id] = entry

        for cap in structured.core:
            _posting_add(by_core, cap, record.id, rank)
        for facet in structured.derived:
            _posting_add(by_derived, facet, record.id, rank)
        for tag in structured.tags:
            _posting_add(by_tag, tag, record.id, rank)
        _posting_add(by_provider, record.provider, record.id, rank)
        _posting_add(by_tier, tier, record.id, rank)

        for hint in TaskHint:
            req = TASK_REQUIRED_CAPS.get(hint, set())
            if req and not req.issubset(structured.core):
                continue
            _posting_add(by_task, hint.value, record.id, rank)

    ready_count = sum(1 for e in entries.values() if e.ready)
    return ModelCapabilityIndex(
        version=INDEX_VERSION,
        built_at=datetime.now(timezone.utc).isoformat(),
        protocol_path=str(protocol_path),
        total_models=len(entries),
        ready_models=ready_count,
        by_core_capability=_finalize_buckets(by_core),
        by_derived_facet=_finalize_buckets(by_derived),
        by_tag=_finalize_buckets(by_tag),
        by_provider=_finalize_buckets(by_provider),
        by_tier=_finalize_buckets(by_tier),
        by_task_hint=_finalize_buckets(by_task),
        entries=entries,
    )


def refresh_dynamic_fields(
    index: ModelCapabilityIndex,
    experience: ExperienceStore,
) -> ModelCapabilityIndex:
    """Refresh readiness, subjective scores, and posting order without YAML parse."""
    by_core: dict[str, list[Any]] = {}
    by_derived: dict[str, list[Any]] = {}
    by_tag: dict[str, list[Any]] = {}
    by_provider: dict[str, list[Any]] = {}
    by_tier: dict[str, list[Any]] = {}
    by_task: dict[str, list[Any]] = {}
    ready_count = 0

    for entry in index.entries.values():
        ready = bool(get_provider_api_key_status(entry.provider).get("has_api_key"))
        subjective = experience.get(entry.model_id)
        rank = compute_rank_score(
            ready=ready,
            subjective=subjective,
            input_per_token=entry.input_per_token,
            blended_cost_per_1m=entry.blended_cost_per_1m,
        )
        entry.ready = ready
        entry.subjective = subjective
        entry.rank_score = rank
        if ready:
            ready_count += 1

        for cap in entry.structured.core:
            _posting_add(by_core, cap, entry.model_id, rank)
        for facet in entry.structured.derived:
            _posting_add(by_derived, facet, entry.model_id, rank)
        for tag in entry.structured.tags:
            _posting_add(by_tag, tag, entry.model_id, rank)
        _posting_add(by_provider, entry.provider, entry.model_id, rank)
        _posting_add(by_tier, entry.tier, entry.model_id, rank)

        for hint in TaskHint:
            req = TASK_REQUIRED_CAPS.get(hint, set())
            if req and not req.issubset(entry.structured.core):
                continue
            _posting_add(by_task, hint.value, entry.model_id, rank)

    index.ready_models = ready_count
    index.by_core_capability = _finalize_buckets(by_core)
    index.by_derived_facet = _finalize_buckets(by_derived)
    index.by_tag = _finalize_buckets(by_tag)
    index.by_provider = _finalize_buckets(by_provider)
    index.by_tier = _finalize_buckets(by_tier)
    index.by_task_hint = _finalize_buckets(by_task)
    return index


__all__ = [
    "INDEX_VERSION",
    "ModelCapabilityIndex",
    "ModelIndexEntry",
    "build_index",
    "compute_rank_score",
    "compute_rank_score_for_record",
    "refresh_dynamic_fields",
]
