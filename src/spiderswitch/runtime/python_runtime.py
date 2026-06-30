# spiderswitch Python runtime implementation
"""
ai-lib-python runtime implementation using ProtocolLoader and AiClient.
使用ai-lib-python SDK的实现，通过ProtocolLoader和AiClient进行模型交互。

Follows ARCH-001: All provider configurations loaded from ai-protocol manifests.
遵循 ARCH-001：所有 provider 配置从 ai-protocol manifests 加载。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import yaml
from ai_lib_python import AiClient

from .. import __version__
from ..errors import (
    InvalidModelError,
    ModelNotFoundError,
    ModelSwitcherError,
)
from ..validation import DEFAULT_VALIDATOR, PROXY_ENV_VARS, get_provider_proxy_status
from .base import ModelCapabilities, ModelInfo, Runtime, RuntimeProfile

logger = logging.getLogger(__name__)

OFFICIAL_DIST_RAW_BASE_URL = (
    "https://raw.githubusercontent.com/ailib-official/ai-protocol/main/dist/v1"
)
OFFICIAL_DIST_API_BASE_URL = (
    "https://api.github.com/repos/ailib-official/ai-protocol/contents/dist/v1"
)
UNSUPPORTED_PROXY_SCHEMES = ("socks4://", "socks4a://")
USER_AGENT = f"spiderswitch/{__version__}"


class PythonRuntime(Runtime):
    """ai-lib-python runtime implementation.

    This implementation uses the ai-lib-python SDK to interact with AI models.
    It follows the protocol-driven design principle (ARCH-001): all provider
    behavior is loaded from ai-protocol manifests, with no hardcoded provider logic.

    Runtime state is managed internally and cleaned up on close().
    使用 ai-lib-python SDK 的实现。遵循协议驱动设计原则 (ARCH-001)：
    所有 provider 行为从 ai-protocol manifests 加载，没有硬编码的 provider 逻辑。
    运行时状态在内部管理，并在 close() 时清理。
    """

    def __init__(
        self,
        fallback_to_github: bool = True,
        cache_enabled: bool = True,
        ai_protocol_path: str | None = None,
    ) -> None:
        """Initialize the Python runtime.

        Args:
            fallback_to_github: Kept for compatibility (reserved for future use)
            cache_enabled: Kept for compatibility (reserved for future use)
            ai_protocol_path: Optional custom path to ai-protocol directory
        """
        self._fallback_to_github = fallback_to_github
        self._cache_enabled = cache_enabled
        self._ai_protocol_path = Path(ai_protocol_path) if ai_protocol_path else None
        self._available_models: dict[str, ModelInfo] = {}
        self._current_client: AiClient | None = None
        self._current_model_info: ModelInfo | None = None
        self._switch_lock = asyncio.Lock()
        self._is_initialized = False

    def resolve_protocol_base(self) -> Path | None:
        """Return ai-protocol root directory if discoverable."""
        return self._resolve_protocol_base()

    def _resolve_protocol_base(self) -> Path | None:
        """Resolve ai-protocol base directory."""
        if self._ai_protocol_path and self._ai_protocol_path.exists():
            return self._ai_protocol_path

        env_path = os.getenv("AI_PROTOCOL_DIR") or os.getenv("AI_PROTOCOL_PATH")
        if env_path:
            env_candidate = Path(env_path)
            if env_candidate.exists():
                return env_candidate

        for candidate in (
            Path.cwd() / "ai-protocol",
            Path.cwd() / "../ai-protocol",
            Path.cwd() / "../../ai-protocol",
            Path("d:/ai-protocol"),
        ):
            if candidate.exists():
                return candidate

        return None

    def _sync_official_dist_json(self, base_path: Path) -> None:
        """Best-effort sync for official ai-protocol dist json snapshot."""
        sync_flag = os.getenv("SPIDERSWITCH_SYNC_DIST", "1").lower()
        if sync_flag in {"0", "false", "no"}:
            return

        dist_base = base_path / "dist" / "v1"
        dist_base.mkdir(parents=True, exist_ok=True)

        raw_base = os.getenv("AI_PROTOCOL_DIST_BASE_URL", OFFICIAL_DIST_RAW_BASE_URL).rstrip("/")
        api_base = os.getenv("AI_PROTOCOL_DIST_API_BASE_URL", OFFICIAL_DIST_API_BASE_URL).rstrip("/")

        try:
            self._download_file(
                f"{raw_base}/spec.json",
                dist_base / "spec.json",
            )
            self._download_dir_from_github_api(
                f"{api_base}/models",
                dist_base / "models",
            )
            self._download_dir_from_github_api(
                f"{api_base}/providers",
                dist_base / "providers",
            )
            logger.info("Synced official ai-protocol dist json snapshot.")
        except Exception as e:
            logger.warning("Failed to sync official dist json snapshot: %s", e)

    @staticmethod
    def _download_file(url: str, target: Path) -> None:
        """Download a file to target path."""
        target.parent.mkdir(parents=True, exist_ok=True)
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=10) as resp:
            content = resp.read()
        target.write_bytes(content)

    def _download_dir_from_github_api(self, api_url: str, target_dir: Path) -> None:
        """Download all json files from a GitHub API directory listing."""
        req = Request(api_url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        if not isinstance(payload, list):
            return

        target_dir.mkdir(parents=True, exist_ok=True)
        for item in payload:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "file":
                continue
            name = item.get("name")
            download_url = item.get("download_url")
            if not isinstance(name, str) or not isinstance(download_url, str):
                continue
            if not name.endswith(".json"):
                continue
            try:
                self._download_file(download_url, target_dir / name)
            except URLError as e:
                logger.warning("Failed downloading %s: %s", name, e)

    @staticmethod
    def _capabilities_from_list(capabilities: list[str]) -> ModelCapabilities:
        """Convert protocol capabilities to ModelCapabilities."""
        capability_set = set(capabilities)
        return ModelCapabilities(
            streaming="streaming" in capability_set,
            tools="tools" in capability_set,
            vision="vision" in capability_set,
            embeddings="embeddings" in capability_set,
            audio="audio" in capability_set,
        )

    @staticmethod
    def _resolve_runtime_model_id(provider: str, raw_model_id: str) -> str:
        """Resolve runtime-facing model id for AiClient.create()."""
        if raw_model_id.startswith(f"{provider}/"):
            return raw_model_id
        return f"{provider}/{raw_model_id}"

    @staticmethod
    def _resolve_public_model_name(
        provider: str,
        model_name: str,
        raw_model_id: str,
    ) -> str:
        """Resolve switchable public model name with one-level provider prefix."""
        if model_name and "/" not in model_name:
            return model_name

        provider_prefix = f"{provider}/"
        if raw_model_id.startswith(provider_prefix):
            suffix = raw_model_id[len(provider_prefix) :]
            if suffix and "/" not in suffix:
                return suffix

        # Fallback: use tail segment so the exposed ID remains switchable
        # under the tool schema and validator pattern.
        return raw_model_id.rsplit("/", 1)[-1]

    @staticmethod
    def _detect_unsupported_proxy_env() -> dict[str, str]:
        """Detect unsupported proxy env vars without mutating process env."""
        unsupported: dict[str, str] = {}
        for env_key in PROXY_ENV_VARS:
            value = os.getenv(env_key)
            if not value:
                continue
            if value.lower().startswith(UNSUPPORTED_PROXY_SCHEMES):
                unsupported[env_key] = value
        return unsupported

    def _load_models_from_protocol(self, base_path: Path) -> dict[str, ModelInfo]:
        """Load model inventory from ai-protocol `v1/models/*.yaml` files."""
        model_dir = base_path / "v1" / "models"
        if not model_dir.exists():
            raise ModelSwitcherError(
                "ai-protocol model directory not found",
                details={"expected_path": str(model_dir)},
            )

        loaded: dict[str, ModelInfo] = {}
        model_sources: dict[str, str] = {}
        for model_file in sorted(model_dir.glob("*.yaml")):
            content = yaml.safe_load(model_file.read_text(encoding="utf-8"))
            if not isinstance(content, dict):
                continue
            models = content.get("models")
            if not isinstance(models, dict):
                continue

            for model_name, model_data in models.items():
                if not isinstance(model_name, str):
                    continue
                if not isinstance(model_data, dict):
                    continue

                provider = model_data.get("provider")
                if not isinstance(provider, str) or not provider:
                    continue

                raw_model_id = model_data.get("model_id", model_name)
                if not isinstance(raw_model_id, str) or not raw_model_id:
                    continue

                runtime_model_id = self._resolve_runtime_model_id(provider, raw_model_id)
                public_model_name = self._resolve_public_model_name(
                    provider=provider,
                    model_name=model_name,
                    raw_model_id=raw_model_id,
                )
                full_id = f"{provider}/{public_model_name}"
                source_path = str(model_file)
                if full_id in loaded:
                    raise ModelSwitcherError(
                        f"Duplicate model id detected: '{full_id}'",
                        details={
                            "model_id": full_id,
                            "first_source": model_sources.get(full_id),
                            "duplicate_source": source_path,
                        },
                    )
                capabilities_raw = model_data.get("capabilities", [])
                capabilities = (
                    [c for c in capabilities_raw if isinstance(c, str)]
                    if isinstance(capabilities_raw, list)
                    else []
                )

                loaded[full_id] = ModelInfo(
                    id=full_id,
                    provider=provider,
                    capabilities=self._capabilities_from_list(capabilities),
                    runtime_model_id=runtime_model_id,
                )
                model_sources[full_id] = source_path

        return loaded

    def _ensure_initialized(self) -> None:
        """Lazy initialization of the model manager.

        Loads models from ai-protocol manifests on first use.
        延迟初始化模型管理器，首次使用时从 ai-protocol manifests 加载。
        """
        if self._is_initialized:
            return

        try:
            base_path = self._resolve_protocol_base()
            if base_path is None:
                raise ModelSwitcherError(
                    "Unable to locate ai-protocol directory",
                    details={
                        "checked": [
                            "AI_PROTOCOL_DIR / AI_PROTOCOL_PATH",
                            "./ai-protocol",
                            "../ai-protocol",
                            "../../ai-protocol",
                            "d:/ai-protocol",
                        ]
                    },
                )

            if not (os.getenv("AI_PROTOCOL_PATH") or os.getenv("AI_PROTOCOL_DIR")):
                os.environ["AI_PROTOCOL_PATH"] = str(base_path)

            sync_on_init = os.getenv("SPIDERSWITCH_SYNC_ON_INIT", "0").lower()
            if sync_on_init in {"1", "true", "yes"}:
                logger.info("SPIDERSWITCH_SYNC_ON_INIT enabled, syncing dist snapshot on init.")
                self._sync_official_dist_json(base_path)

            self._available_models = self._load_models_from_protocol(base_path)
            self._is_initialized = True
            logger.info(f"Runtime initialized: loaded {len(self._available_models)} models")
        except Exception as e:
            logger.error(f"Failed to initialize runtime: {e}")
            raise ModelSwitcherError(
                "Failed to load model manifests from ai-protocol",
                details={"error": str(e)},
            ) from e

    async def list_models(
        self,
        filter_provider: str | None = None,
        filter_capability: str | None = None,
    ) -> list[ModelInfo]:
        """List available models from ai-protocol manifests.

        Args:
            filter_provider: Optional provider ID to filter by
            filter_capability: Optional capability to filter by

        Returns:
            List of ModelInfo objects matching filters

        Raises:
            ModelSwitcherError: If runtime initialization fails
        """
        # Ensure initialization
        self._ensure_initialized()

        models = list(self._available_models.values())

        result = []
        for model in models:
            provider_id = model.provider

            if filter_provider and provider_id != filter_provider:
                continue

            if filter_capability and not getattr(model.capabilities, filter_capability, False):
                continue

            result.append(
                ModelInfo(
                    id=model.id,
                    provider=provider_id,
                    capabilities=model.capabilities,
                    runtime_model_id=model.runtime_model_id,
                )
            )

        return result

    async def switch_model(
        self,
        model_id: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> ModelInfo:
        """Switch to a specific model using ai-lib-python SDK.

        Args:
            model_id: Model identifier (e.g., "openai/gpt-4o")
            api_key: Optional explicit API key
            base_url: Optional custom base URL

        Returns:
            ModelInfo for the switched model

        Raises:
            InvalidModelError: If model_id format is invalid
            ModelNotFoundError: If model_id is not in available models
            ModelSwitcherError: If client creation fails
        """
        # Validate parameters
        try:
            DEFAULT_VALIDATOR.validate_model_id(model_id)
            DEFAULT_VALIDATOR.validate_api_key(api_key)
            DEFAULT_VALIDATOR.validate_base_url(base_url)
        except InvalidModelError as e:
            logger.error(f"Invalid model parameters: {e}")
            raise

        # Ensure initialization and get available models
        self._ensure_initialized()
        available_models = await self.list_models()
        model_map = {m.id: m for m in available_models}

        if model_id not in model_map:
            available = list(model_map.keys())
            logger.error(f"Model '{model_id}' not found. Available: {available}")
            raise ModelNotFoundError(
                f"Model '{model_id}' not found.",
                details={"available_models": available},
            )

        model_info = model_map[model_id]
        provider = model_info.provider

        # Validate key source before creating a new client.
        DEFAULT_VALIDATOR.validate_api_key_configuration(model_id=model_id, api_key=api_key)
        proxy_status = get_provider_proxy_status(provider)
        unsupported_proxy_env = self._detect_unsupported_proxy_env()
        if (
            proxy_status.get("proxy_required_guess")
            and not proxy_status.get("proxy_configured")
        ):
            logger.warning(
                "Provider '%s' may require proxy, but no proxy env var is configured.",
                provider,
            )
        if unsupported_proxy_env:
            unsupported_keys = sorted(unsupported_proxy_env.keys())
            raise ModelSwitcherError(
                "Unsupported proxy scheme detected in environment.",
                details={
                    "unsupported_proxy_env_vars": unsupported_keys,
                    "supported_proxy_schemes": ["http://", "https://", "socks5://"],
                    "hint": (
                        "Please update proxy env vars to supported schemes, or unset them "
                        "before calling switch_model."
                    ),
                },
            )

        async with self._switch_lock:
            # Close existing client
            if self._current_client:
                try:
                    await self._current_client.close()
                except Exception as e:
                    logger.warning(f"Error closing previous client: {e}")

            # Create new client
            try:
                self._current_client = await AiClient.create(
                    model=model_info.runtime_model_id or model_id,
                    api_key=api_key,
                    base_url=base_url,
                )
                self._current_model_info = model_info
                logger.info(f"Successfully switched to model: {model_id}")
            except Exception as e:
                self._current_client = None
                self._current_model_info = None
                logger.exception("Failed to create client for model '%s'", model_id)
                details: dict[str, object] = {"provider": provider}
                if (
                    proxy_status.get("proxy_required_guess")
                    and not proxy_status.get("proxy_configured")
                ):
                    details["proxy_hint"] = proxy_status.get("hint")
                    details["proxy_status"] = proxy_status
                raise ModelSwitcherError(
                    f"Failed to create client for model '{model_id}'",
                    details=details,
                ) from e

        return model_info

    async def get_current_model(self) -> ModelInfo | None:
        """Get information about the currently active model.

        Returns:
            ModelInfo if a model is configured, None otherwise
        """
        return self._current_model_info

    async def close(self) -> None:
        """Cleanup resources.

        Closes the current client and clears internal state.
        Any errors during cleanup are logged but not raised.
        关闭当前客户端并清理内部状态。清理过程中的错误会被记录但不会抛出。
        """
        cleanup_errors: list[str] = []

        # Close current client
        if self._current_client:
            try:
                await self._current_client.close()
                logger.info("Client closed successfully")
            except Exception as e:
                error_msg = f"Failed to close client: {e}"
                cleanup_errors.append(error_msg)
                logger.error(error_msg)
            finally:
                self._current_client = None

        # Clear internal state
        self._current_model_info = None
        self._is_initialized = False

        # Report any cleanup errors
        if cleanup_errors:
            logger.warning(f"Resource cleanup completed with {len(cleanup_errors)} error(s)")

    def describe_runtime_profile(self) -> RuntimeProfile:
        """Expose runtime-level capabilities for routing-aware callers."""
        return RuntimeProfile(
            runtime_id="python-runtime",
            language="python",
            supports=[
                "model_switching",
                "capability_filtering",
                "provider_manifest_loading",
                "streaming",
                "tool_calling",
                "stt",
                "tts",
                "vision_input",
                "audio_input",
                "video_input",
            ],
            model_capabilities=[
                "text_generation",
                "streaming_chat",
                "tool_calling",
                "vision_input",
                "audio_input",
                "video_input",
            ],
            runtime_capabilities=[
                "runtime_switch_execution",
                "capability_filtering",
                "manifest_driven_loading",
                "connection_epoch_signaling",
            ],
            operational_metrics={
                "switch_lock": "asyncio_lock",
                "supports_hot_switch": True,
                "supports_multi_runtime_registry": True,
            },
            notes=(
                "Spiderswitch only exposes routing capability signals. "
                "Policy selection should be implemented by upper-layer applications."
            ),
        )


# Helper functions for MCP tool handlers


def extract_model_from_args(args: dict[str, object]) -> tuple[str, str | None, str | None]:
    """Extract and validate model parameters from MCP tool arguments.

    Args:
        args: Arguments dictionary from MCP tool call

    Returns:
        Tuple of (model_id, api_key, base_url)

    Raises:
        InvalidModelError: If validation fails
    """
    model = args.get("model")
    if not model or not isinstance(model, str):
        raise InvalidModelError(
            "Missing required parameter: 'model'",
        )

    api_key = args.get("api_key")
    base_url = args.get("base_url")

    # Use the validator
    return DEFAULT_VALIDATOR.validate_switch_arguments(
        model=model,
        api_key=api_key,
        base_url=base_url,
    )


def format_model_info(info: ModelInfo) -> dict[str, object]:
    """Convert ModelInfo to MCP response format.

    Args:
        info: ModelInfo object to format

    Returns:
        Dictionary with model information
    """
    return {
        "id": info.id,
        "provider": info.provider,
        "capabilities": info.capabilities.to_list(),
    }


__all__ = ["PythonRuntime", "extract_model_from_args", "format_model_info"]
