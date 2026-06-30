# spiderswitch policy catalog loader
"""
Load model metadata (pricing, tags, capabilities) from ai-protocol YAML.
从 ai-protocol YAML 加载模型元数据（定价、标签、能力）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..errors import ModelSwitcherError


@dataclass
class ModelRecord:
    """Enriched model record for policy scoring."""

    id: str
    provider: str
    display_name: str
    capabilities: list[str]
    tags: list[str]
    input_per_token: float | None = None
    output_per_token: float | None = None
    context_window: int | None = None
    status: str = "active"

    @property
    def input_per_1m(self) -> float | None:
        if self.input_per_token is None:
            return None
        return self.input_per_token * 1_000_000

    @property
    def output_per_1m(self) -> float | None:
        if self.output_per_token is None:
            return None
        return self.output_per_token * 1_000_000

    @property
    def blended_cost_per_1m(self) -> float:
        """Rough blended cost (70% input / 30% output assumption)."""
        inp = self.input_per_1m or 9999.0
        out = self.output_per_1m or inp * 2
        return inp * 0.7 + out * 0.3


@dataclass
class ModelCatalog:
    """In-memory catalog indexed by public model id."""

    models: dict[str, ModelRecord] = field(default_factory=dict)

    @classmethod
    def from_protocol_path(cls, base_path: Path) -> ModelCatalog:
        model_dir = base_path / "v1" / "models"
        if not model_dir.exists():
            raise ModelSwitcherError(
                "ai-protocol model directory not found",
                details={"expected_path": str(model_dir)},
            )

        loaded: dict[str, ModelRecord] = {}
        for model_file in sorted(model_dir.glob("*.yaml")):
            content = yaml.safe_load(model_file.read_text(encoding="utf-8"))
            if not isinstance(content, dict):
                continue
            models = content.get("models")
            if not isinstance(models, dict):
                continue

            for model_name, model_data in models.items():
                if not isinstance(model_data, dict):
                    continue
                provider = model_data.get("provider")
                if not isinstance(provider, str) or not provider:
                    continue

                raw_model_id = model_data.get("model_id", model_name)
                if not isinstance(raw_model_id, str):
                    continue

                public_name = raw_model_id
                if provider in raw_model_id and "/" in raw_model_id:
                    public_name = raw_model_id.rsplit("/", 1)[-1]
                elif raw_model_id.startswith(f"{provider}-"):
                    public_name = raw_model_id

                full_id = f"{provider}/{public_name}"
                status = model_data.get("status", "active")
                if status not in (None, "active"):
                    continue

                caps_raw = model_data.get("capabilities", [])
                capabilities = [c for c in caps_raw if isinstance(c, str)] if isinstance(caps_raw, list) else []
                tags_raw = model_data.get("tags", [])
                tags = [t for t in tags_raw if isinstance(t, str)] if isinstance(tags_raw, list) else []

                pricing = model_data.get("pricing") or {}
                inp = pricing.get("input_per_token")
                out = pricing.get("output_per_token")

                loaded[full_id] = ModelRecord(
                    id=full_id,
                    provider=provider,
                    display_name=str(model_data.get("display_name", model_name)),
                    capabilities=capabilities,
                    tags=tags,
                    input_per_token=float(inp) if inp is not None else None,
                    output_per_token=float(out) if out is not None else None,
                    context_window=model_data.get("context_window"),
                    status=str(status),
                )

        return cls(models=loaded)

    def get(self, model_id: str) -> ModelRecord | None:
        return self.models.get(model_id)
