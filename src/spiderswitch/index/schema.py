# spiderswitch capability schema
"""
Structured capability taxonomy for model indexing.

Capabilities from ai-protocol are flat strings; this module normalizes them into
layers so indexes and queries stay consistent:

  raw      — verbatim protocol strings (streaming, tools, vision, …)
  core     — canonical capability vocabulary (subset of raw + normalized aliases)
  derived  — computed facets (multimodal, agentic, long_context, …)
  readiness — operational signals (ready = BYOK provider has API key)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Canonical core capabilities used for primary inverted indexes.
CORE_CAPABILITIES: frozenset[str] = frozenset(
    {
        "streaming",
        "tools",
        "vision",
        "embeddings",
        "audio",
        "chat",
        "reasoning",
    }
)

# Aliases from protocol variants → core capability.
CAPABILITY_ALIASES: dict[str, str] = {
    "tool_calling": "tools",
    "function_calling": "tools",
    "image_input": "vision",
    "multimodal": "vision",
    "text_generation": "chat",
    "text": "chat",
}


class DerivedFacet(str, Enum):
    """Computed facets derived from capabilities, tags, and metadata."""

    MULTIMODAL = "multimodal"
    AGENTIC = "agentic"
    LONG_CONTEXT = "long_context"
    ULTRA_CONTEXT = "ultra_context"
    COST_EFFECTIVE = "cost_effective"
    REASONING_CAPABLE = "reasoning_capable"


def normalize_core_capabilities(raw: set[str]) -> set[str]:
    """Map raw protocol capability strings to canonical core set."""
    core: set[str] = set()
    for item in raw:
        lowered = item.lower().strip()
        if lowered in CORE_CAPABILITIES:
            core.add(lowered)
        elif lowered in CAPABILITY_ALIASES:
            core.add(CAPABILITY_ALIASES[lowered])
    return core


def compute_derived_facets(
    *,
    raw: set[str],
    core: set[str],
    tags: set[str],
    context_window: int | None,
) -> set[str]:
    """Derive structured facets from capabilities and metadata."""
    facets: set[str] = set()
    tag_lower = {t.lower() for t in tags}

    if core & {"vision", "audio"}:
        facets.add(DerivedFacet.MULTIMODAL.value)
    if "tools" in core or "agentic" in tag_lower or "agentic" in core:
        facets.add(DerivedFacet.AGENTIC.value)
    if "reasoning" in core or "reasoning" in tag_lower:
        facets.add(DerivedFacet.REASONING_CAPABLE.value)
    if "cost-effective" in tag_lower or "cost_effective" in tag_lower:
        facets.add(DerivedFacet.COST_EFFECTIVE.value)
    if context_window is not None:
        if context_window >= 200_000:
            facets.add(DerivedFacet.ULTRA_CONTEXT.value)
        if context_window >= 100_000:
            facets.add(DerivedFacet.LONG_CONTEXT.value)
    return facets


@dataclass
class StructuredCapabilities:
    """Layered capability representation for one model."""

    raw: set[str] = field(default_factory=set)
    core: set[str] = field(default_factory=set)
    derived: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)

    @classmethod
    def from_protocol(
        cls,
        capabilities: list[str],
        tags: list[str],
        context_window: int | None,
    ) -> StructuredCapabilities:
        raw = {c.lower().strip() for c in capabilities if c}
        core = normalize_core_capabilities(raw)
        # Promote reasoning tag into core when present.
        tag_set = {t.lower().strip() for t in tags if t}
        if "reasoning" in tag_set:
            core.add("reasoning")
        derived = compute_derived_facets(
            raw=raw,
            core=core,
            tags=tag_set,
            context_window=context_window,
        )
        return cls(raw=raw, core=core, derived=derived, tags=tag_set)

    def satisfies(self, required_core: set[str], required_derived: set[str]) -> bool:
        if required_core and not required_core.issubset(self.core):
            return False
        if required_derived and not required_derived.issubset(self.derived):
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": sorted(self.raw),
            "core": sorted(self.core),
            "derived": sorted(self.derived),
            "tags": sorted(self.tags),
        }


__all__ = [
    "CORE_CAPABILITIES",
    "CAPABILITY_ALIASES",
    "DerivedFacet",
    "StructuredCapabilities",
    "compute_derived_facets",
    "normalize_core_capabilities",
]
