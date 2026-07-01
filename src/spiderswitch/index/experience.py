# spiderswitch subjective experience store
"""
Persistent accumulation of user/agent subjective experience per model.

Stored locally at ~/.spiderswitch/experience/models.json (override via
SPIDERSWITCH_EXPERIENCE_PATH). Used to rank models within capability buckets.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_MAX_RATING_SAMPLES = 50


def default_experience_path() -> Path:
    override = os.getenv("SPIDERSWITCH_EXPERIENCE_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".spiderswitch" / "experience" / "models.json"


@dataclass
class SubjectiveRecord:
    """Rolling subjective metrics for one model."""

    model_id: str
    sample_count: int = 0
    switch_success: int = 0
    switch_failure: int = 0
    latency_ms_sum: float = 0.0
    quality_ratings: list[float] = field(default_factory=list)
    speed_ratings: list[float] = field(default_factory=list)
    value_ratings: list[float] = field(default_factory=list)
    task_wins: dict[str, int] = field(default_factory=dict)
    task_losses: dict[str, int] = field(default_factory=dict)
    last_updated: str | None = None

    @property
    def success_rate(self) -> float | None:
        total = self.switch_success + self.switch_failure
        if total == 0:
            return None
        return self.switch_success / total

    @property
    def avg_latency_ms(self) -> float | None:
        if self.sample_count == 0:
            return None
        return self.latency_ms_sum / self.sample_count

    def _avg_rating(self, ratings: list[float]) -> float | None:
        if not ratings:
            return None
        return sum(ratings) / len(ratings)

    @property
    def subjective_score(self) -> float:
        """Composite 0–1 score blending ratings and reliability."""
        parts: list[float] = []
        for ratings in (self.quality_ratings, self.speed_ratings, self.value_ratings):
            avg = self._avg_rating(ratings)
            if avg is not None:
                parts.append(max(0.0, min(1.0, avg / 5.0)))
        rate = self.success_rate
        if rate is not None:
            parts.append(rate)
        if not parts:
            return 0.5  # neutral prior for unseen models
        return sum(parts) / len(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "sample_count": self.sample_count,
            "switch_success": self.switch_success,
            "switch_failure": self.switch_failure,
            "success_rate": self.success_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "avg_quality": self._avg_rating(self.quality_ratings),
            "avg_speed": self._avg_rating(self.speed_ratings),
            "avg_value": self._avg_rating(self.value_ratings),
            "subjective_score": round(self.subjective_score, 4),
            "task_wins": dict(self.task_wins),
            "task_losses": dict(self.task_losses),
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, model_id: str, data: dict[str, Any]) -> SubjectiveRecord:
        return cls(
            model_id=model_id,
            sample_count=int(data.get("sample_count", 0)),
            switch_success=int(data.get("switch_success", 0)),
            switch_failure=int(data.get("switch_failure", 0)),
            latency_ms_sum=float(data.get("latency_ms_sum", 0.0)),
            quality_ratings=list(data.get("quality_ratings") or []),
            speed_ratings=list(data.get("speed_ratings") or []),
            value_ratings=list(data.get("value_ratings") or []),
            task_wins=dict(data.get("task_wins") or {}),
            task_losses=dict(data.get("task_losses") or {}),
            last_updated=data.get("last_updated"),
        )


class ExperienceStore:
    """Thread-safe local store for subjective model experience."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or default_experience_path()
        self._lock = threading.Lock()
        self._records: dict[str, SubjectiveRecord] = {}
        self._load()

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        models = payload.get("models")
        if not isinstance(models, dict):
            return
        for model_id, data in models.items():
            if not isinstance(data, dict):
                continue
            self._records[model_id] = SubjectiveRecord(
                model_id=model_id,
                sample_count=int(data.get("sample_count", 0)),
                switch_success=int(data.get("switch_success", 0)),
                switch_failure=int(data.get("switch_failure", 0)),
                latency_ms_sum=float(data.get("latency_ms_sum", 0.0)),
                quality_ratings=list(data.get("quality_ratings") or []),
                speed_ratings=list(data.get("speed_ratings") or []),
                value_ratings=list(data.get("value_ratings") or []),
                task_wins=dict(data.get("task_wins") or {}),
                task_losses=dict(data.get("task_losses") or {}),
                last_updated=data.get("last_updated"),
            )

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "models": {mid: self._serialize_record(rec) for mid, rec in self._records.items()},
        }
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _serialize_record(rec: SubjectiveRecord) -> dict[str, Any]:
        return {
            "sample_count": rec.sample_count,
            "switch_success": rec.switch_success,
            "switch_failure": rec.switch_failure,
            "latency_ms_sum": rec.latency_ms_sum,
            "quality_ratings": rec.quality_ratings[-_MAX_RATING_SAMPLES:],
            "speed_ratings": rec.speed_ratings[-_MAX_RATING_SAMPLES:],
            "value_ratings": rec.value_ratings[-_MAX_RATING_SAMPLES:],
            "task_wins": rec.task_wins,
            "task_losses": rec.task_losses,
            "last_updated": rec.last_updated,
        }

    def _get_or_create_unlocked(self, model_id: str) -> SubjectiveRecord:
        if model_id not in self._records:
            self._records[model_id] = SubjectiveRecord(model_id=model_id)
        return self._records[model_id]

    def get(self, model_id: str) -> SubjectiveRecord:
        with self._lock:
            return self._get_or_create_unlocked(model_id)

    def record_switch(
        self,
        model_id: str,
        *,
        success: bool,
        latency_ms: float | None = None,
        task_hint: str | None = None,
    ) -> SubjectiveRecord:
        with self._lock:
            rec = self._get_or_create_unlocked(model_id)
            if success:
                rec.switch_success += 1
                if task_hint:
                    rec.task_wins[task_hint] = rec.task_wins.get(task_hint, 0) + 1
            else:
                rec.switch_failure += 1
                if task_hint:
                    rec.task_losses[task_hint] = rec.task_losses.get(task_hint, 0) + 1
            if latency_ms is not None:
                rec.sample_count += 1
                rec.latency_ms_sum += latency_ms
            rec.last_updated = datetime.now(timezone.utc).isoformat()
            self._persist()
            return rec

    def record_ratings(
        self,
        model_id: str,
        *,
        quality: float | None = None,
        speed: float | None = None,
        value: float | None = None,
        task_hint: str | None = None,
    ) -> SubjectiveRecord:
        with self._lock:
            rec = self._get_or_create_unlocked(model_id)
            for rating, bucket in (
                (quality, rec.quality_ratings),
                (speed, rec.speed_ratings),
                (value, rec.value_ratings),
            ):
                if rating is not None:
                    bucket.append(max(1.0, min(5.0, float(rating))))
                    if len(bucket) > _MAX_RATING_SAMPLES:
                        del bucket[: len(bucket) - _MAX_RATING_SAMPLES]
            if task_hint and quality is not None and quality >= 4.0:
                rec.task_wins[task_hint] = rec.task_wins.get(task_hint, 0) + 1
            rec.last_updated = datetime.now(timezone.utc).isoformat()
            self._persist()
            return rec

    def all_records(self) -> dict[str, SubjectiveRecord]:
        with self._lock:
            return dict(self._records)

    def summary(self) -> dict[str, Any]:
        records = self.all_records()
        return {
            "path": str(self._path),
            "models_with_data": len(records),
            "total_switch_events": sum(r.switch_success + r.switch_failure for r in records.values()),
        }


__all__ = [
    "ExperienceStore",
    "SubjectiveRecord",
    "default_experience_path",
]
