# spiderswitch policy engine
"""
Local policy engine for intelligent model selection during agent runtime.
Agent 运行时的本地策略引擎，智能选择大模型。

100% BYOK — only considers providers with configured API keys.
No upstream API calls; uses ai-protocol pricing snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from ..validation import get_provider_api_key_status
from .loader import ModelCatalog, ModelRecord

if TYPE_CHECKING:
    from ..index.builder import ModelCapabilityIndex


class TaskHint(str, Enum):
    """High-level task hints agents can pass."""

    CHAT = "chat"
    CODE = "code"
    REASONING = "reasoning"
    VISION = "vision"
    SUMMARIZE = "summarize"
    CHEAP = "cheap"
    QUALITY = "quality"


class TierPreference(str, Enum):
    ECONOMY = "economy"
    BALANCED = "balanced"
    PREMIUM = "premium"


TASK_REQUIRED_CAPS: dict[TaskHint, set[str]] = {
    TaskHint.CODE: {"tools"},
    TaskHint.VISION: {"vision"},
    TaskHint.REASONING: set(),
    TaskHint.SUMMARIZE: set(),
    TaskHint.CHAT: set(),
    TaskHint.CHEAP: set(),
    TaskHint.QUALITY: set(),
}

TASK_TAG_BOOSTS: dict[TaskHint, set[str]] = {
    TaskHint.CODE: {"tools", "agentic", "cost-effective"},
    TaskHint.REASONING: {"reasoning", "agentic"},
    TaskHint.VISION: {"vision", "multimodal"},
    TaskHint.SUMMARIZE: {"cost-effective"},
    TaskHint.CHEAP: {"cost-effective"},
    TaskHint.QUALITY: {"reasoning", "agentic", "gpt"},
}


@dataclass
class ModelCandidate:
    model_id: str
    provider: str
    display_name: str
    score: float
    tier: str
    reasons: list[str]
    input_per_1m: float | None
    output_per_1m: float | None


@dataclass
class Recommendation:
    selected: ModelCandidate
    task_hint: str
    tier_preference: str
    alternatives: list[ModelCandidate] = field(default_factory=list)
    policy_version: str = "smart-v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": {
                "model_id": self.selected.model_id,
                "provider": self.selected.provider,
                "display_name": self.selected.display_name,
                "score": round(self.selected.score, 4),
                "tier": self.selected.tier,
                "reasons": self.selected.reasons,
                "pricing": {
                    "input_per_1m": self.selected.input_per_1m,
                    "output_per_1m": self.selected.output_per_1m,
                },
            },
            "alternatives": [
                {
                    "model_id": c.model_id,
                    "score": round(c.score, 4),
                    "tier": c.tier,
                    "reasons": c.reasons[:2],
                }
                for c in self.alternatives[:5]
            ],
            "task_hint": self.task_hint,
            "tier_preference": self.tier_preference,
            "policy_version": self.policy_version,
        }


class PolicyEngine:
    """Score and rank models for agent runtime selection."""

    def __init__(
        self,
        catalog: ModelCatalog,
        index: ModelCapabilityIndex | None = None,
    ) -> None:
        self._catalog = catalog
        self._index = index

    def recommend(
        self,
        *,
        task_hint: str = "chat",
        tier_preference: str = "balanced",
        required_capabilities: list[str] | None = None,
        prefer_provider: str | None = None,
        only_ready_providers: bool = True,
    ) -> Recommendation:
        hint = self._parse_task_hint(task_hint)
        tier = self._parse_tier(tier_preference)
        req_caps = set(required_capabilities or [])
        req_caps.update(TASK_REQUIRED_CAPS.get(hint, set()))

        candidates = self._filter_candidates(
            req_caps=req_caps,
            prefer_provider=prefer_provider,
            only_ready=only_ready_providers,
            task_hint=hint.value,
        )
        if not candidates:
            raise ValueError(
                "No eligible models: configure provider API keys or relax filters."
            )

        costs = sorted(m.blended_cost_per_1m for m in candidates)
        cost_p33 = costs[max(0, len(costs) // 3 - 1)] if costs else 0.0
        cost_p66 = costs[min(len(costs) - 1, (2 * len(costs)) // 3)] if costs else 9999.0

        scored: list[ModelCandidate] = []
        for record in candidates:
            model_tier = self._classify_tier(record, cost_p33, cost_p66)
            if tier == TierPreference.ECONOMY and model_tier == "premium":
                continue
            # PREMIUM preference keeps economy-tier models eligible but the scorer
            # deprioritizes them, so no explicit filtering is required here.

            score, reasons = self._score(record, hint, tier, model_tier)
            scored.append(
                ModelCandidate(
                    model_id=record.id,
                    provider=record.provider,
                    display_name=record.display_name,
                    score=score,
                    tier=model_tier,
                    reasons=reasons,
                    input_per_1m=record.input_per_1m,
                    output_per_1m=record.output_per_1m,
                )
            )

        if not scored:
            raise ValueError("No models match tier preference; try tier=balanced.")

        # Deterministic ranking: higher score first, then cheaper input cost as a
        # stable tie-breaker so identical-score candidates resolve predictably.
        scored.sort(
            key=lambda c: (
                -c.score,
                c.input_per_1m if c.input_per_1m is not None else float("inf"),
                c.model_id,
            )
        )
        selected = scored[0]
        return Recommendation(
            selected=selected,
            alternatives=scored[1:6],
            task_hint=hint.value,
            tier_preference=tier.value,
        )

    def _filter_candidates(
        self,
        *,
        req_caps: set[str],
        prefer_provider: str | None,
        only_ready: bool,
        task_hint: str = "chat",
    ) -> list[ModelRecord]:
        allowed_ids: set[str] | None = None
        if self._index is not None:
            indexed = self._index.query(
                required_capabilities=req_caps or None,
                provider=prefer_provider,
                task_hint=task_hint,
                ready_only=only_ready,
                limit=10_000,
            )
            allowed_ids = {e.model_id for e in indexed}

        out: list[ModelRecord] = []
        for record in self._catalog.models.values():
            if allowed_ids is not None and record.id not in allowed_ids:
                continue
            if prefer_provider and record.provider != prefer_provider:
                continue
            if req_caps and not req_caps.issubset(set(record.capabilities)):
                continue
            if only_ready:
                status = get_provider_api_key_status(record.provider)
                if not status.get("has_api_key", False):
                    continue
            out.append(record)
        return out

    def _score(
        self,
        record: ModelRecord,
        hint: TaskHint,
        tier_pref: TierPreference,
        model_tier: str,
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

        tag_set = set(record.tags)
        cap_set = set(record.capabilities)
        boosts = TASK_TAG_BOOSTS.get(hint, set())
        matched = boosts & (tag_set | cap_set)
        if matched:
            score += 0.25 * len(matched)
            reasons.append(f"task match: {', '.join(sorted(matched)[:3])}")

        if hint == TaskHint.CHEAP or tier_pref == TierPreference.ECONOMY:
            inv = 1.0 / max(record.blended_cost_per_1m, 0.001)
            score += inv * 0.5
            reasons.append(f"low cost (${record.blended_cost_per_1m:.3f}/1M blended)")
        elif tier_pref == TierPreference.PREMIUM or hint == TaskHint.QUALITY:
            if model_tier == "premium":
                score += 0.4
                reasons.append("premium tier")
            if "reasoning" in tag_set or "agentic" in cap_set:
                score += 0.2
                reasons.append("reasoning/agentic capable")
        else:
            if model_tier == "balanced":
                score += 0.3
                reasons.append("balanced tier")

        if record.input_per_token is not None:
            score += 0.05

        if self._index is not None:
            entry = self._index.entries.get(record.id)
            if entry is not None:
                subj = entry.subjective.subjective_score
                if subj > 0.55:
                    score += (subj - 0.5) * 0.3
                    reasons.append(f"subjective score {subj:.2f}")

        # Reward larger context windows for context-hungry tasks (guarded for None
        # so models without published context windows are unaffected).
        if hint in (TaskHint.CODE, TaskHint.REASONING, TaskHint.QUALITY) and record.context_window:
            if record.context_window >= 200_000:
                score += 0.1
                reasons.append("large context window (>=200k)")
            elif record.context_window >= 100_000:
                score += 0.05
                reasons.append("large context window (>=100k)")

        if not reasons:
            reasons.append("default ranking")

        return score, reasons

    @staticmethod
    def _classify_tier(record: ModelRecord, p33: float, p66: float) -> str:
        cost = record.blended_cost_per_1m
        if cost <= p33:
            return "economy"
        if cost >= p66:
            return "premium"
        return "balanced"

    @staticmethod
    def _parse_task_hint(raw: str) -> TaskHint:
        try:
            return TaskHint(raw.lower())
        except ValueError:
            return TaskHint.CHAT

    @staticmethod
    def _parse_tier(raw: str) -> TierPreference:
        try:
            return TierPreference(raw.lower())
        except ValueError:
            return TierPreference.BALANCED
