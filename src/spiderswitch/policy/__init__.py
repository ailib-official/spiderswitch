# spiderswitch policy module — intelligent model selection (BYOK, local only).
"""Policy-driven model recommendation for agent runtime."""

from .engine import ModelCandidate, PolicyEngine, Recommendation
from .loader import ModelCatalog, ModelRecord

__all__ = [
    "ModelCandidate",
    "ModelCatalog",
    "ModelRecord",
    "PolicyEngine",
    "Recommendation",
]
