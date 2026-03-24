# spiderswitch for ai-lib Ecosystem

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-green.svg)](LICENSE)

MCP (Model Context Protocol) server that enables agents to dynamically switch AI models from the [ai-lib ecosystem](https://github.com/ailib-official/ai-lib-python).

## Features

- **Protocol-Driven**: All model configurations loaded from ai-protocol manifests (ARCH-001)
- **Multi-Provider Support**: Switch between OpenAI, Anthropic, Google, DeepSeek, and more
- **Runtime-Agnostic**: Uses ai-lib-python SDK for unified model interaction
- **MCP-Compliant**: Implements standard MCP tools over stdio transport
- **Capability Discovery**: Query available models and their capabilities
- **Runtime Profile Signal**: Exposes runtime capability profile for upper-layer routing policy engines
- **Local Readiness Hints**: `list_models` includes API key presence and proxy readiness per provider
- **Explicit Exit Path**: `exit_switcher` resets switcher runtime/state for clean fallback
- **Auto Protocol Setup**: Auto-detects local `ai-protocol` path and sets `AI_PROTOCOL_PATH` for current process
- **Official Dist Sync**: Best-effort sync of official `dist/v1/*.json` snapshot into local `ai-protocol/dist/v1`

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/ailib-official/spiderswitch.git
cd spiderswitch

# Install dependencies
pip install -e .
```

### Environment Setup

Set up your API keys:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
```

Recommended provider key mapping:

| Provider | Environment Variable |
|----------|----------------------|
| openai | `OPENAI_API_KEY` |
| anthropic | `ANTHROPIC_API_KEY` |
| google | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| deepseek | `DEEPSEEK_API_KEY` |
| cohere | `COHERE_API_KEY` |
| mistral | `MISTRAL_API_KEY` |

Security note:
- Prefer environment variables over passing `api_key` in tool arguments.
- The server redacts sensitive fields in logs, but passing secrets in arguments still increases exposure risk in client traces.

Optional runtime env controls:
- `SPIDERSWITCH_SYNC_ON_INIT=1` to enable dist sync during runtime initialization (default: disabled).
- `SPIDERSWITCH_SYNC_DIST=0` to disable dist sync when it is explicitly invoked.
- `AI_PROTOCOL_DIST_BASE_URL` to override raw dist source (default official GitHub raw URL).
- `AI_PROTOCOL_DIST_API_BASE_URL` to override GitHub API listing source for models/providers dist json.
- `SPIDERSWITCH_LIST_CACHE_TTL_SEC` for `list_models` cache TTL (default: `5`).
- `SPIDERSWITCH_STATUS_CACHE_TTL_SEC` for `get_status` cache TTL (default: `2`).

### One-Click Install (Plugin-Market Style)

```bash
bash scripts/install_one_click.sh
```

Then generate MCP client config template:

```bash
spiderswitch init --client cursor --output ~/.cursor/mcp.spiderswitch.json --force
spiderswitch doctor --json
```

### Offline Install (air-gapped/intranet)

Install from local wheel or local source directory:

```bash
bash scripts/install_offline.sh /path/to/spiderswitch-0.4.0-py3-none-any.whl
# or
bash scripts/install_offline.sh /path/to/spiderswitch-source
```

### Configuration

Add to your MCP client configuration:

#### For OpenCode

Configuration file: `~/.config/opencode/opencode.json`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "spiderswitch": {
      "type": "local",
      "command": ["python3", "-m", "spiderswitch.server"],
      "enabled": true,
      "environment": {
        "AI_PROTOCOL_PATH": "/path/to/ai-protocol",
        "OPENAI_API_KEY": "sk-your-key",
        "ANTHROPIC_API_KEY": "sk-ant-your-key",
        "DEEPSEEK_API_KEY": "sk-your-key"
      }
    }
  }
}
```

#### For Claude Desktop / Cursor

Configuration file: `~/.config/claude-desktop/config.json` or `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "spiderswitch": {
      "command": "python3",
      "args": ["-m", "spiderswitch.server"],
      "env": {
        "AI_PROTOCOL_PATH": "/path/to/ai-protocol"
      }
    }
  }
}
```

### Verification (OpenCode)

```bash
# List loaded MCP servers
opencode mcp list

# Expected output:
# ✓ spiderswitch connected
#   python3 -m spiderswitch.server
```
### Usage

In your agent, call MCP tools:

```python
# List available models
models = await mcp_client.call_tool("list_models", {})

# Switch to Claude 3.5 Sonnet
await mcp_client.call_tool(
    "switch_model",
    {"model": "anthropic/claude-3-5-sonnet"}
)

# Check current status
status = await mcp_client.call_tool("get_status", {})
```

## Available MCP Tools

### 1. switch_model

Switches to a different AI model/provider.

**Parameters:**
- `model` (string, required): Model identifier (e.g., `openai/gpt-4o`, `anthropic/claude-3-5-sonnet`)
- `api_key` (string, optional): Explicit API key (overrides environment variable; not recommended for production)
- `base_url` (string, optional): Custom base URL for testing/mock
- `runtime_id` (string, optional): Runtime target selected by upper-layer policy

**Returns:**
```json
{
  "status": "success",
  "data": {
    "id": "anthropic/claude-3-5-sonnet",
    "provider": "anthropic",
    "capabilities": ["streaming", "tools", "vision"],
    "proxy_status": {
      "provider": "anthropic",
      "proxy_required_guess": false,
      "proxy_configured": false,
      "configured_proxy_env_vars": [],
      "hint": null
    },
    "warnings": []
  },
  "message": "Successfully switched to anthropic/claude-3-5-sonnet"
}
```

### 2. list_models

Lists all available models from registered providers.

**Parameters:**
- `filter_provider` (string, optional): Filter by provider ID
- `filter_capability` (string, optional): Filter by capability (`streaming`, `tools`, `vision`, `embeddings`, `audio`)
- `runtime_id` (string, optional): Runtime target selected by upper-layer policy

**Returns:**
```json
{
  "status": "success",
  "data": {
    "count": 2,
    "runtime_profile": {
      "runtime_id": "python-runtime",
      "language": "python",
      "supports": ["model_switching", "capability_filtering", "provider_manifest_loading"]
    },
    "models": [
      {
        "id": "openai/gpt-4o",
        "provider": "openai",
        "capabilities": ["streaming", "tools", "vision"],
        "api_key_status": {
          "provider": "openai",
          "has_api_key": true,
          "expected_env_vars": ["OPENAI_API_KEY"],
          "configured_env_vars": ["OPENAI_API_KEY"]
        },
        "proxy_status": {
          "provider": "openai",
          "proxy_required_guess": true,
          "proxy_configured": false,
          "configured_proxy_env_vars": [],
          "hint": "This provider may require proxy access in your network region. Set HTTPS_PROXY/HTTP_PROXY in the MCP server process environment if needed."
        }
      },
      {
        "id": "anthropic/claude-3-5-sonnet",
        "provider": "anthropic",
        "capabilities": ["streaming", "tools", "vision"]
      }
    ],
    "filtered": {
      "require_api_key": false,
      "provider": null,
      "capability": null
    }
  }
}
```

### 3. get_status

Gets current model status and configuration.

**Parameters:**
- `runtime_id` (string, optional): Query status in a specific runtime scope

**Returns:**
```json
{
  "status": "success",
  "data": {
    "provider": "anthropic",
    "model": "claude-3-5-sonnet",
    "capabilities": ["streaming", "tools", "vision"],
    "runtime_profile": {
      "runtime_id": "python-runtime",
      "language": "python",
      "supports": ["model_switching", "capability_filtering", "provider_manifest_loading"]
    },
    "is_configured": true,
    "connection_epoch": 3,
    "last_switched_at": "2026-03-02T09:00:00+00:00"
  }
}
```

### 4. exit_switcher

Explicitly reset spiderswitch state and runtime client.

**Parameters:**
- `runtime_id` (string, optional): Runtime id for scoped reset
- `scope` (string, optional): `all` (default) or `runtime`

**Returns:**
```json
{
  "status": "success",
  "data": {
    "exited": true,
    "status": {
      "provider": null,
      "model": null,
      "is_configured": false
    }
  }
}
```

## API Key Guidance and Troubleshooting

When `switch_model` fails due to missing credentials, the response includes:
- `provider`: which provider is missing credentials
- `expected_env_vars`: accepted environment variable names
- `hint`: actionable setup instruction

Typical setup flow:
1. Configure provider key in your MCP server process environment.
2. Restart the MCP server process if your client does not support hot env reload.
3. Call `switch_model`.
4. Verify with `get_status`.

## Connection Coordination with Agent Runtime

This MCP server manages model client lifecycle internally. To avoid conflicts with an agent's own connection manager:
- Treat MCP switcher as the control plane for model selection.
- Let the agent side observe `get_status.connection_epoch`.
- Rebuild agent-side cached sessions only when `connection_epoch` increases.

This pattern prevents stale session reuse after model switches and supports deterministic synchronization.

## Runtime Routing Boundary

spiderswitch only executes routing actions with explicit runtime signals:

- Runtime capability model is exposed via `runtime_profile` (runtime-neutral schema).
- Runtime selection policy remains in upper-layer applications.
- Built-in registry/resolver only resolves `runtime_id` and does not implement cost/quality/business strategy.

## Architecture

```
spiderswitch/
├── src/
│   ├── server.py           # MCP server main entry point
│   ├── tools/              # MCP tool implementations
│   │   ├── switch.py       # switch_model tool
│   │   ├── list.py         # list_models tool
│   │   ├── status.py       # get_status tool
│   │   └── reset.py        # exit_switcher tool
│   ├── runtime/            # Runtime abstraction layer
│   │   ├── base.py         # Base runtime interface
│   │   ├── python_runtime.py  # ai-lib-python implementation
│   │   └── loader.py       # ProtocolLoader wrapper
│   └── state.py            # State management
├── tests/                  # Test suite
└── pyproject.toml          # Project configuration
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src/spiderswitch
```

### Testing with Mock Server

Use [ai-protocol-mock](https://github.com/ailib-official/ai-protocol-mock):

```bash
# Start mock server
docker-compose up -d ai-protocol-mock

# Run with mock
MOCK_HTTP_URL=http://localhost:4010 python -m spiderswitch.server
```

### Code Style

```bash
# Format code
ruff format src tests

# Lint
ruff check src tests

# Type check
mypy src
```

## Protocol-Driven Design (ARCH-001)

This server follows the ai-lib design principle:

> **一切逻辑皆算子，一切配置皆协议**

All provider configurations are loaded from ai-protocol manifests. No provider-specific logic is hardcoded. Adding a new provider requires only a manifest file in ai-protocol.

Routing boundary:
- spiderswitch exposes runtime/model capability signals only.
- Routing strategy policy (cost/latency/circuit-breaker/business rules) belongs to upper-layer applications.

Deterministic routing contract:
- runtime resolution order is fixed as `request runtime_id -> active state runtime_id -> default runtime`.
- reset supports scoped behavior (`scope=runtime`) to clear a target runtime without global teardown.
- contract tests in `tests/test_runtime.py` verify resolver order and scoped reset stability.

## Related Projects

- [ai-protocol](https://github.com/ailib-official/ai-protocol) - Protocol specification
- [ai-lib-python](https://github.com/ailib-official/ai-lib-python) - Python runtime SDK
- [ai-lib-rust](https://github.com/ailib-official/ai-lib-rust) - Rust runtime SDK
- [ai-lib-ts](https://github.com/ailib-official/ai-lib-ts) - TypeScript runtime SDK

## License

This project is licensed under either of:
- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) or http://www.apache.org/licenses/LICENSE-2.0)
- MIT License ([LICENSE-MIT](LICENSE-MIT) or http://opensource.org/licenses/MIT)

at your option.

## Contributing

Contributions are welcome! Please ensure:
1. Code follows PEP 8 and passes `ruff check`
2. Type hints pass `mypy --strict`
3. Tests are included for new features
4. Documentation is updated

---

**spiderswitch** - Where MCP meets ai-lib. 🤖🔀
