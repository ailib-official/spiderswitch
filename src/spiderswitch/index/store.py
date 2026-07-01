# spiderswitch capability index persistence
"""
Persist pre-built capability indexes for fast startup load.

The index is built offline via `spiderswitch index build` (cron-friendly) and
loaded at MCP server startup without re-parsing ai-protocol YAML.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .builder import INDEX_VERSION, ModelCapabilityIndex, ModelIndexEntry
from .experience import SubjectiveRecord
from .schema import StructuredCapabilities

STORE_VERSION = 1


def default_index_path() -> Path:
    override = os.getenv("SPIDERSWITCH_INDEX_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".spiderswitch" / "index" / "capability-index.json"


def compute_protocol_fingerprint(protocol_path: Path) -> str:
    """Hash ai-protocol model YAML contents for staleness detection."""
    model_dir = protocol_path / "v1" / "models"
    if not model_dir.is_dir():
        return ""
    hasher = hashlib.sha256()
    for model_file in sorted(model_dir.glob("*.yaml")):
        hasher.update(model_file.name.encode("utf-8"))
        hasher.update(model_file.read_bytes())
    return hasher.hexdigest()[:16]


@dataclass
class PersistedIndexMeta:
    """Metadata loaded alongside the capability index."""

    protocol_fingerprint: str
    store_version: int
    fingerprint_stale: bool = False
    age_stale: bool = False


def _serialize_subjective(rec: SubjectiveRecord) -> dict[str, Any]:
    return {
        "sample_count": rec.sample_count,
        "switch_success": rec.switch_success,
        "switch_failure": rec.switch_failure,
        "latency_ms_sum": rec.latency_ms_sum,
        "quality_ratings": rec.quality_ratings,
        "speed_ratings": rec.speed_ratings,
        "value_ratings": rec.value_ratings,
        "task_wins": rec.task_wins,
        "task_losses": rec.task_losses,
        "last_updated": rec.last_updated,
    }


def _deserialize_subjective(model_id: str, data: dict[str, Any]) -> SubjectiveRecord:
    return SubjectiveRecord.from_dict(model_id, data)


def _serialize_entry(entry: ModelIndexEntry) -> dict[str, Any]:
    return {
        "model_id": entry.model_id,
        "provider": entry.provider,
        "display_name": entry.display_name,
        "capabilities": entry.structured.to_dict(),
        "tier": entry.tier,
        "ready": entry.ready,
        "context_window": entry.context_window,
        "subjective": _serialize_subjective(entry.subjective),
        "rank_score": entry.rank_score,
        "input_per_token": entry.input_per_token,
        "blended_cost_per_1m": entry.blended_cost_per_1m,
    }


def _deserialize_entry(data: dict[str, Any]) -> ModelIndexEntry:
    model_id = str(data["model_id"])
    caps = data.get("capabilities") or {}
    return ModelIndexEntry(
        model_id=model_id,
        provider=str(data["provider"]),
        display_name=str(data.get("display_name") or model_id),
        structured=StructuredCapabilities.from_dict(caps),
        tier=str(data.get("tier") or "balanced"),
        ready=bool(data.get("ready")),
        context_window=data.get("context_window"),
        subjective=_deserialize_subjective(model_id, data.get("subjective") or {}),
        rank_score=float(data.get("rank_score") or 0.0),
        input_per_token=data.get("input_per_token"),
        blended_cost_per_1m=float(data.get("blended_cost_per_1m") or 9999.0),
    )


def save_index(
    index: ModelCapabilityIndex,
    *,
    path: Path | None = None,
    protocol_fingerprint: str,
) -> Path:
    """Persist a built capability index to disk."""
    target = path or default_index_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "store_version": STORE_VERSION,
        "index_version": index.version,
        "built_at": index.built_at,
        "protocol_path": index.protocol_path,
        "protocol_fingerprint": protocol_fingerprint,
        "total_models": index.total_models,
        "ready_models": index.ready_models,
        "by_core_capability": index.by_core_capability,
        "by_derived_facet": index.by_derived_facet,
        "by_tag": index.by_tag,
        "by_provider": index.by_provider,
        "by_tier": index.by_tier,
        "by_task_hint": index.by_task_hint,
        "entries": {
            model_id: _serialize_entry(entry) for model_id, entry in index.entries.items()
        },
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def _index_age_seconds(built_at: str) -> float | None:
    try:
        built = datetime.fromisoformat(built_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - built).total_seconds()


def load_index(
    path: Path | None = None,
    *,
    protocol_path: Path | None = None,
    max_age_sec: float | None = None,
) -> tuple[ModelCapabilityIndex, PersistedIndexMeta] | None:
    """Load a persisted capability index. Returns None if file missing or invalid."""
    target = path or default_index_path()
    if not target.is_file():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("store_version") != STORE_VERSION:
        return None
    if payload.get("index_version") != INDEX_VERSION:
        return None

    entries_raw = payload.get("entries")
    if not isinstance(entries_raw, dict):
        return None

    entries: dict[str, ModelIndexEntry] = {}
    for model_id, entry_data in entries_raw.items():
        if isinstance(entry_data, dict):
            entries[model_id] = _deserialize_entry(entry_data)

    index = ModelCapabilityIndex(
        version=str(payload.get("index_version") or INDEX_VERSION),
        built_at=str(payload.get("built_at") or ""),
        protocol_path=str(payload.get("protocol_path") or ""),
        total_models=int(payload.get("total_models") or len(entries)),
        ready_models=int(payload.get("ready_models") or 0),
        by_core_capability=dict(payload.get("by_core_capability") or {}),
        by_derived_facet=dict(payload.get("by_derived_facet") or {}),
        by_tag=dict(payload.get("by_tag") or {}),
        by_provider=dict(payload.get("by_provider") or {}),
        by_tier=dict(payload.get("by_tier") or {}),
        by_task_hint=dict(payload.get("by_task_hint") or {}),
        entries=entries,
    )

    stored_fingerprint = str(payload.get("protocol_fingerprint") or "")
    fingerprint_stale = False
    if protocol_path is not None:
        current = compute_protocol_fingerprint(protocol_path)
        fingerprint_stale = bool(current) and current != stored_fingerprint

    age_stale = False
    if max_age_sec is not None and index.built_at:
        age = _index_age_seconds(index.built_at)
        if age is not None and age > max_age_sec:
            age_stale = True

    meta = PersistedIndexMeta(
        protocol_fingerprint=stored_fingerprint,
        store_version=int(payload.get("store_version") or STORE_VERSION),
        fingerprint_stale=fingerprint_stale,
        age_stale=age_stale,
    )
    return index, meta


__all__ = [
    "PersistedIndexMeta",
    "STORE_VERSION",
    "compute_protocol_fingerprint",
    "default_index_path",
    "load_index",
    "save_index",
]
