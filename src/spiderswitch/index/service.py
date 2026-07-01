# spiderswitch model index service
"""
Lifecycle service: load pre-built capability index at startup, build on demand.

Startup loads a persisted index (JSON) and only refreshes dynamic fields
(BYOK readiness, subjective scores). Full YAML rebuild is reserved for
`spiderswitch index build` or explicit refresh.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from ..policy.loader import ModelCatalog
from ..runtime.python_runtime import PythonRuntime
from .builder import ModelCapabilityIndex, build_index, compute_rank_score, refresh_dynamic_fields
from .experience import ExperienceStore, SubjectiveRecord
from .store import (
    compute_protocol_fingerprint,
    default_index_path,
    load_index,
    save_index,
)

logger = logging.getLogger(__name__)


def _max_age_sec() -> float | None:
    raw = os.getenv("SPIDERSWITCH_INDEX_MAX_AGE_SEC")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _rebuild_on_start() -> bool:
    return os.getenv("SPIDERSWITCH_INDEX_REBUILD_ON_START", "").strip() in {"1", "true", "yes"}


class ModelIndexService:
    """Owns the capability index and experience store."""

    def __init__(
        self,
        index: ModelCapabilityIndex,
        experience: ExperienceStore,
        catalog: ModelCatalog | None = None,
        *,
        loaded_from_disk: bool = False,
        index_path: Path | None = None,
        fingerprint_stale: bool = False,
        age_stale: bool = False,
    ) -> None:
        self._index = index
        self._experience = experience
        self._catalog = catalog
        self._loaded_from_disk = loaded_from_disk
        self._index_path = index_path or default_index_path()
        self._fingerprint_stale = fingerprint_stale
        self._age_stale = age_stale

    @property
    def index(self) -> ModelCapabilityIndex:
        return self._index

    @property
    def experience(self) -> ExperienceStore:
        return self._experience

    @property
    def catalog(self) -> ModelCatalog | None:
        return self._catalog

    @property
    def index_path(self) -> Path:
        return self._index_path

    @classmethod
    def load_from_runtime(cls, runtime: PythonRuntime) -> ModelIndexService | None:
        """Load persisted index at startup (fast path)."""
        base = runtime.resolve_protocol_base()
        if base is None:
            logger.warning("Skipping capability index: ai-protocol not found")
            return None

        protocol_path = Path(base)
        index_path = default_index_path()
        experience = ExperienceStore()

        loaded = load_index(
            index_path,
            protocol_path=protocol_path,
            max_age_sec=_max_age_sec(),
        )
        if loaded is None:
            if _rebuild_on_start():
                logger.info(
                    "Index not found at %s; rebuilding (SPIDERSWITCH_INDEX_REBUILD_ON_START=1)",
                    index_path,
                )
                return cls.build_from_protocol_path(protocol_path, persist=True)
            logger.warning(
                "Capability index not found at %s — run: spiderswitch index build",
                index_path,
            )
            return None

        index, meta = loaded
        if meta.fingerprint_stale:
            logger.warning(
                "Capability index fingerprint stale (ai-protocol changed) — run: spiderswitch index build"
            )
        if meta.age_stale:
            logger.warning(
                "Capability index exceeded SPIDERSWITCH_INDEX_MAX_AGE_SEC — run: spiderswitch index build"
            )

        refresh_dynamic_fields(index, experience)
        logger.info(
            "Capability index loaded: %d models (%d ready) from %s",
            index.total_models,
            index.ready_models,
            index_path,
        )
        return cls(
            index=index,
            experience=experience,
            catalog=None,
            loaded_from_disk=True,
            index_path=index_path,
            fingerprint_stale=meta.fingerprint_stale,
            age_stale=meta.age_stale,
        )

    @classmethod
    def build_from_runtime(cls, runtime: PythonRuntime, *, persist: bool = False) -> ModelIndexService | None:
        """Full rebuild from ai-protocol YAML (used by index build)."""
        base = runtime.resolve_protocol_base()
        if base is None:
            logger.warning("Skipping capability index: ai-protocol not found")
            return None
        return cls.build_from_protocol_path(Path(base), persist=persist)

    @classmethod
    def build_from_protocol_path(cls, protocol_path: Path, *, persist: bool = False) -> ModelIndexService:
        catalog = ModelCatalog.from_protocol_path(protocol_path)
        experience = ExperienceStore()
        index = build_index(catalog, protocol_path=protocol_path, experience=experience)
        index_path = default_index_path()
        fingerprint = compute_protocol_fingerprint(protocol_path)
        if persist:
            save_index(index, path=index_path, protocol_fingerprint=fingerprint)
            logger.info("Capability index persisted to %s", index_path)
        logger.info(
            "Capability index built: %d models (%d ready), %d core buckets",
            index.total_models,
            index.ready_models,
            len(index.by_core_capability),
        )
        return cls(
            index=index,
            experience=experience,
            catalog=catalog,
            loaded_from_disk=False,
            index_path=index_path,
        )

    @classmethod
    def load_or_build_for_cli(cls, protocol_path: Path) -> tuple[ModelIndexService | None, dict[str, Any]]:
        """Load persisted index for CLI display; metadata describes load vs missing."""
        index_path = default_index_path()
        experience = ExperienceStore()
        loaded = load_index(
            index_path,
            protocol_path=protocol_path,
            max_age_sec=_max_age_sec(),
        )
        if loaded is None:
            return None, {
                "loaded": False,
                "index_path": str(index_path),
                "hint": "Index not built yet. Run: spiderswitch index build",
                "fix_commands": ["spiderswitch index build"],
            }

        index, meta = loaded
        refresh_dynamic_fields(index, experience)
        service = cls(
            index=index,
            experience=experience,
            catalog=None,
            loaded_from_disk=True,
            index_path=index_path,
            fingerprint_stale=meta.fingerprint_stale,
            age_stale=meta.age_stale,
        )
        status: dict[str, Any] = {
            "loaded": True,
            "index_path": str(index_path),
            "loaded_from_disk": True,
            "protocol_fingerprint": meta.protocol_fingerprint,
        }
        if meta.fingerprint_stale:
            status["stale"] = True
            status["stale_reason"] = "protocol_fingerprint_mismatch"
            status["fix_commands"] = ["spiderswitch index build"]
        if meta.age_stale:
            status["stale"] = True
            status["stale_reason"] = "max_age_exceeded"
            status.setdefault("fix_commands", []).append("spiderswitch index build")
        return service, status

    def refresh(self) -> ModelCapabilityIndex:
        """Full rebuild from ai-protocol YAML."""
        protocol_path = Path(self._index.protocol_path)
        if self._catalog is None:
            self._catalog = ModelCatalog.from_protocol_path(protocol_path)
        self._index = build_index(
            self._catalog,
            protocol_path=protocol_path,
            experience=self._experience,
        )
        return self._index

    def persist(self) -> Path:
        """Save current index to disk."""
        protocol_path = Path(self._index.protocol_path)
        fingerprint = compute_protocol_fingerprint(protocol_path)
        return save_index(self._index, path=self._index_path, protocol_fingerprint=fingerprint)

    def refresh_dynamic(self) -> ModelCapabilityIndex:
        """Refresh readiness and subjective ranking without YAML parse."""
        refresh_dynamic_fields(self._index, self._experience)
        return self._index

    def _recompute_entry_rank(self, model_id: str) -> None:
        entry = self._index.entries.get(model_id)
        if entry is None:
            return
        rec = self._experience.get(model_id)
        entry.subjective = rec
        entry.rank_score = compute_rank_score(
            ready=entry.ready,
            subjective=rec,
            input_per_token=entry.input_per_token,
            blended_cost_per_1m=entry.blended_cost_per_1m,
        )
        self.refresh_dynamic()

    def record_switch_outcome(
        self,
        model_id: str,
        *,
        success: bool,
        latency_ms: float | None = None,
        task_hint: str | None = None,
    ) -> None:
        self._experience.record_switch(
            model_id,
            success=success,
            latency_ms=latency_ms,
            task_hint=task_hint,
        )
        self._recompute_entry_rank(model_id)

    def record_rating_outcome(
        self,
        model_id: str,
        *,
        quality: float | None = None,
        speed: float | None = None,
        value: float | None = None,
        task_hint: str | None = None,
    ) -> SubjectiveRecord:
        self._experience.record_ratings(
            model_id,
            quality=quality,
            speed=speed,
            value=value,
            task_hint=task_hint,
        )
        self._recompute_entry_rank(model_id)
        return self._experience.get(model_id)

    def info_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "index": self._index.summary(),
            "experience": self._experience.summary(),
            "index_path": str(self._index_path),
            "loaded_from_disk": self._loaded_from_disk,
        }
        if self._fingerprint_stale:
            payload["stale"] = True
            payload["stale_reason"] = "protocol_fingerprint_mismatch"
        if self._age_stale:
            payload["stale"] = True
            payload["stale_reason"] = payload.get("stale_reason") or "max_age_exceeded"
        return payload


__all__ = ["ModelIndexService"]
