# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

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

