# spiderswitch model index service
"""
Lifecycle service: build capability index at startup, refresh on demand.
启动时构建能力索引，支持按需刷新与主观体验累积。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ..policy.loader import ModelCatalog
from ..runtime.python_runtime import PythonRuntime
from .builder import ModelCapabilityIndex, build_index
from .experience import ExperienceStore

logger = logging.getLogger(__name__)


class ModelIndexService:
    """Owns the startup-built capability index and experience store."""

    def __init__(
        self,
        index: ModelCapabilityIndex,
        experience: ExperienceStore,
        catalog: ModelCatalog,
    ) -> None:
        self._index = index
        self._experience = experience
        self._catalog = catalog

    @property
    def index(self) -> ModelCapabilityIndex:
        return self._index

    @property
    def experience(self) -> ExperienceStore:
        return self._experience

    @property
    def catalog(self) -> ModelCatalog:
        return self._catalog

    @classmethod
    def build_from_runtime(cls, runtime: PythonRuntime) -> ModelIndexService | None:
        """Build index from a PythonRuntime (returns None if protocol missing)."""
        base = runtime.resolve_protocol_base()
        if base is None:
            logger.warning("Skipping capability index: ai-protocol not found")
            return None
        return cls.build_from_protocol_path(Path(base))

    @classmethod
    def build_from_protocol_path(cls, protocol_path: Path) -> ModelIndexService:
        catalog = ModelCatalog.from_protocol_path(protocol_path)
        experience = ExperienceStore()
        index = build_index(catalog, protocol_path=protocol_path, experience=experience)
        logger.info(
            "Capability index built: %d models (%d ready), %d core buckets",
            index.total_models,
            index.ready_models,
            len(index.by_core_capability),
        )
        return cls(index=index, experience=experience, catalog=catalog)

    def refresh(self) -> ModelCapabilityIndex:
        """Rebuild index (e.g. after experience update or protocol sync)."""
        protocol_path = Path(self._index.protocol_path)
        self._index = build_index(
            self._catalog,
            protocol_path=protocol_path,
            experience=self._experience,
        )
        return self._index

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
        # Recompute rank for the affected entry only (lightweight refresh).
        entry = self._index.entries.get(model_id)
        if entry is not None:
            rec = self._experience.get(model_id)
            entry.subjective = rec
            from .builder import compute_rank_score

            record = self._catalog.models.get(model_id)
            if record:
                entry.rank_score = compute_rank_score(
                    record,
                    ready=entry.ready,
                    subjective=rec,
                )

    def info_payload(self) -> dict[str, Any]:
        return {
            "index": self._index.summary(),
            "experience": self._experience.summary(),
        }


__all__ = ["ModelIndexService"]
