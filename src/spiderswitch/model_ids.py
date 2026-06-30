# spiderswitch model id resolution
"""
Single source of truth for resolving public/runtime model identifiers.
模型标识符解析的唯一权威实现。

Both the runtime inventory (``python_runtime``) and the policy catalog
(``policy.loader``) must derive identical public model ids from an ai-protocol
manifest entry; otherwise ``recommend_model`` could return an id that
``switch_model`` cannot find. Centralizing the logic here removes that
contradiction.
"""

from __future__ import annotations


def resolve_runtime_model_id(provider: str, raw_model_id: str) -> str:
    """Resolve the runtime-facing model id passed to ``AiClient.create()``."""
    if raw_model_id.startswith(f"{provider}/"):
        return raw_model_id
    return f"{provider}/{raw_model_id}"


def resolve_public_model_name(provider: str, model_name: str, raw_model_id: str) -> str:
    """Resolve the switchable public model name (one-level provider prefix)."""
    if model_name and "/" not in model_name:
        return model_name

    provider_prefix = f"{provider}/"
    if raw_model_id.startswith(provider_prefix):
        suffix = raw_model_id[len(provider_prefix) :]
        if suffix and "/" not in suffix:
            return suffix

    # Fallback: use the tail segment so the exposed id stays switchable under the
    # tool schema and validator pattern.
    return raw_model_id.rsplit("/", 1)[-1]


def resolve_public_model_id(provider: str, model_name: str, raw_model_id: str) -> str:
    """Resolve the fully-qualified public model id (``provider/model``)."""
    return f"{provider}/{resolve_public_model_name(provider, model_name, raw_model_id)}"


__all__ = [
    "resolve_runtime_model_id",
    "resolve_public_model_name",
    "resolve_public_model_id",
]
