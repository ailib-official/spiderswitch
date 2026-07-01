# spiderswitch index package
"""Capability indexing and subjective experience for model selection."""

from .builder import ModelCapabilityIndex, ModelIndexEntry, build_index
from .experience import ExperienceStore, SubjectiveRecord
from .schema import StructuredCapabilities
from .service import ModelIndexService

__all__ = [
    "ExperienceStore",
    "ModelCapabilityIndex",
    "ModelIndexEntry",
    "ModelIndexService",
    "StructuredCapabilities",
    "SubjectiveRecord",
    "build_index",
]
