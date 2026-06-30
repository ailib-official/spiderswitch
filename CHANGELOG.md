# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

### Added
- **Prompt-injection layer**: the MCP server now advertises `instructions` (auto-injected
  operating policy that tells agents when/how to switch models) and two MCP **prompts** —
  `spiderswitch_guide` (system-level guidance) and `route_task` (route a concrete task to
  the best model via `auto_switch`). Exposed through standard `prompts/list` and
  `prompts/get`.
- **ai-lib ecosystem error classification**: `switch_model` failures now surface
  standardized routing signals (`error_class`, `retryable`, `fallbackable`,
  `retry_after`, `status_code`, `request_id`) extracted from `ai_lib_python.errors`
  under `error.details.ai_lib_error`, so agents can programmatically retry or fall back.
- **Infrastructure-aware runtime profile**: `runtime_profile.operational_metrics.ai_lib`
  now reports the live ai-lib version, optional feature flags (vision/audio/telemetry/
  tokenizer/keyring/watchdog) via ai-lib's own feature detection, and the supported
  ai-protocol versions, instead of a static guess.

### Fixed
- Corrected official ai-protocol dist sync URLs from the legacy `hiddenpath` org to
  `ailib-official`, matching the rest of the project after the org migration.
- Single-sourced the package version from installed metadata (`importlib.metadata`)
  so `spiderswitch.__version__` and the HTTP `User-Agent` always track `pyproject.toml`
  (previously hardcoded `0.4.0`).

### Removed
- Deleted dead/duplicate code: `response.format_error_response` /
  `format_success_response` (superseded by `MCPResponse`), `validation.validate_or_raise`,
  and the unused `ProviderNotAvailableError` / `ConnectionError` exceptions (the latter
  also shadowed the builtin `ConnectionError`).
- Removed redundant one-off release docs (`MODIFICATION_SUMMARY.md`,
  `DEPLOYMENT_VERIFICATION.md`); `CHANGELOG.md` is the single source of release history.

### Changed
- Refactored the MCP `call_tool` dispatcher to share a single runtime-resolution
  helper, removing repeated boilerplate across all six tool branches.
- Unified public/runtime model-id resolution in a single `model_ids` module shared by
  the runtime inventory and the policy catalog, so `recommend_model` can no longer
  surface an id that `switch_model` cannot resolve.
- Removed version contradictions: the plugin manifest now tracks `0.5.0` with the
  `ailib-official` id, `scripts/verify.sh` reads the version from `pyproject.toml`, and
  offline-install examples use a version-agnostic wheel placeholder. Added a test that
  guards manifest/package version drift.
- Documentation now matches the implementation: README documents all six tools and a
  corrected architecture tree.
- Smart routing policy engine is now deterministic (stable score/cost/id tie-breaking)
  and rewards large context windows for `code`/`reasoning`/`quality` tasks; removed a
  dead no-op branch in tier handling.

## [0.5.0] - 2026-06-30

### Added
- **Smart routing MCP tools**: `recommend_model` (local policy, BYOK) and `auto_switch` (recommend + switch).
- Policy engine (`spiderswitch.policy`) scoring models from ai-protocol pricing, tags, and capabilities.
- Pro pack under `packaging/spiderswitch-pro/` (Cursor MCP templates, routing YAML, install script).
- E2E tests (`tests/test_e2e_smart_routing.py`) and guide (`docs/E2E_SMART_ROUTING.md`).

### Changed
- Version bump to 0.5.0; MCP server exposes 6 tools (was 4).
- `PythonRuntime.resolve_protocol_base()` public API for policy catalog loading.

## [0.4.2] - prior

### Added
- Added runtime-level profile API in runtime abstraction (`describe_runtime_profile`) and Python runtime implementation.
- Added runtime registry/resolver execution layer for runtime-aware routing (`RuntimeRegistry`, `RuntimeResolver`).
- Added runtime-scoped state signals (`runtime_id`, `runtime_epoch`, `runtime_epochs`) and scoped reset semantics (`scope=runtime|all`).
- Added contract test baseline for runtime selection order (`request -> state -> default`) and runtime-aware tool behavior.

### Changed
- Clarified routing boundary in docs: spiderswitch provides routing capability signals only; strategy policy remains in upper-layer applications.
- Extended MCP tool schemas (`switch_model`, `list_models`, `get_status`, `exit_switcher`) with `runtime_id` and reset scope semantics.

## [0.4.0] - 2026-03-06

### Added
- Added runtime model-id normalization to keep MCP-visible IDs switchable while passing provider-qualified IDs to `AiClient.create`.
- Added regression coverage for provider-prefixed model normalization and unsupported `socks4://` proxy handling.

### Fixed
- Ensured MCP text payloads are serialized as valid JSON (not Python dict repr), improving compatibility with strict MCP clients.
- Temporarily sanitize unsupported SOCKS4 proxy env vars during runtime client creation to reduce avoidable switch failures.

### Changed
- Updated Cursor Windows configuration guidance in `USER_GUIDE.md` and `USER_GUIDE_CN.md` to prefer `%USERPROFILE%\\.cursor\\mcp.json` with `%APPDATA%\\Cursor\\mcp.json` fallback.
- Aligned public documentation examples to the unified MCP response envelope: `{\"status\":\"success\",\"data\":...}`.

## [0.3.0] - 2026-03-02

### Added
- Added provider readiness metadata in `list_models` output, including local API key presence and proxy status hints.
- Added `exit_switcher` MCP tool for explicit switcher session exit/reset.
- Added automatic local protocol setup (`AI_PROTOCOL_PATH`) and best-effort sync of official `ai-protocol/dist/v1` JSON snapshots.

### Changed
- Enhanced switch flow diagnostics with proxy pre-check warnings and actionable hints when connectivity fails.
- Updated README/README_CN to document readiness checks, exit flow, and auto protocol/dist behavior.
- Expanded regression and runtime tests to cover new readiness and exit capabilities.

## [0.2.0] - 2026-03-02

### Added
- Added API key configuration diagnostics with provider-specific environment variable hints.
- Added connection coordination metadata in status responses: `connection_epoch` and `last_switched_at`.
- Added concurrency protection for model switching in runtime implementation.
- Added validation tests for API key configuration behavior.
- Published package under new distribution name `spiderswitch` on PyPI.

### Changed
- Improved API key setup and troubleshooting guidance in `README.md` and `README_CN.md`.
- Updated package version to `0.2.0` in runtime and packaging metadata.
- Updated console entrypoint to invoke package CLI correctly.
- Improved model inventory loading to use ai-protocol model manifests dynamically.
- Renamed project/package identity from `ai-mcp-model-switcher` to `spiderswitch`.

### Fixed
- Fixed unknown-tool error path that previously referenced invalid response helpers.
- Fixed duplicate class/function definitions causing runtime instability.
- Fixed sensitive argument logging by applying redaction for secret-like keys.
- Fixed state manager thread-safety issues and state copy behavior.
- Fixed strict typing and lint issues across runtime, tools, and server modules.

