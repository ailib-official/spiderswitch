# spiderswitch User Guide

> End-user guide for local installation and daily operations.

---

## What is spiderswitch?

`spiderswitch` is an MCP server that lets your agent switch models dynamically across providers in the ai-lib ecosystem.

It is designed for MCP-capable clients such as Cursor, Claude Desktop, and OpenCode.

---

## Prerequisites

| Item | Requirement |
|------|-------------|
| Python | 3.10+ |
| API key | At least one provider key |
| MCP client | Cursor / Claude Desktop / OpenCode |
| ai-protocol | Local repo path recommended (`AI_PROTOCOL_PATH`) |

---

## Install

### Option A: One-click installer (recommended)

```bash
bash scripts/install_one_click.sh
```

After installation:

```bash
spiderswitch setup --client cursor    # recommended: protocol + config + index build + doctor
spiderswitch doctor --json
spiderswitch init --client cursor --output ~/.cursor/mcp.spiderswitch.json --force
```

### Option B: Developer install

```bash
git clone https://github.com/ailib-official/spiderswitch.git
cd spiderswitch
pip install -e .
```

### Option C: Offline install (air-gapped / intranet)

Install from local wheel or local source directory:

```bash
bash scripts/install_offline.sh /path/to/spiderswitch-<version>-py3-none-any.whl
# or
bash scripts/install_offline.sh /path/to/spiderswitch-source
```

---

## Configure API keys

Set at least one provider key before starting your MCP client.

| Provider | Environment variable |
|----------|----------------------|
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Google | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| Cohere | `COHERE_API_KEY` |
| Mistral | `MISTRAL_API_KEY` |

Example:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

Security recommendations:

- Use environment variables instead of passing `api_key` in tool arguments.
- Do not hardcode or commit secrets.
- Rotate keys regularly.

---

## MCP client setup

### Fast path with `spiderswitch init`

Generate a template config:

```bash
spiderswitch init --client cursor --output ~/.cursor/mcp.spiderswitch.json --force
```

Supported `--client` values:

- `cursor`
- `claude`
- `opencode`

### Manual config examples

#### Cursor / Claude Desktop format

```json
{
  "mcpServers": {
    "spiderswitch": {
      "command": "spiderswitch",
      "args": ["serve"],
      "env": {
        "AI_PROTOCOL_PATH": "/path/to/ai-protocol",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

#### OpenCode format

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "spiderswitch": {
      "type": "local",
      "command": ["spiderswitch", "serve"],
      "enabled": true,
      "environment": {
        "AI_PROTOCOL_PATH": "/path/to/ai-protocol",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

---

## Capability index (0.7.0+)

The capability index is **pre-built offline** and **loaded at MCP startup** — no YAML re-parse on every server start.

```bash
# After ai-protocol is available:
spiderswitch index build              # writes ~/.spiderswitch/index/capability-index.json
spiderswitch index                    # load-only summary (JSON)

# Periodic refresh when ai-protocol updates (cron-friendly):
0 3 * * * spiderswitch index build
```

`spiderswitch setup` runs `index build` automatically. Without a persisted index, MCP tools like `query_index` are unavailable unless `SPIDERSWITCH_INDEX_REBUILD_ON_START=1` is set.

---

## CLI commands

### `spiderswitch serve`

Run the MCP stdio server.

### `spiderswitch setup`

One-shot self-deploy: ai-protocol + MCP config + **index build** + doctor.

```bash
spiderswitch setup --client cursor   # or opencode / claude
```

### `spiderswitch index build`

Pre-build and persist the capability index from ai-protocol (run once or on a schedule).

### `spiderswitch index`

Load the persisted index and print JSON summary (fast, no rebuild).

### `spiderswitch init`

Generate MCP config template.

Common flags:

- `--client {cursor|claude|opencode}`
- `--output <path>`
- `--ai-protocol-path <path>`
- `--force`

### `spiderswitch doctor`

Run health checks (python version, protocol path, **capability index**, key presence, proxy scheme, optional runtime probe).

Useful flags:

- `--json` structured output
- `--no-runtime-probe` fast check without model inventory probe

### `spiderswitch info` / `spiderswitch version`

Print deployment metadata or package version (`--json` supported for version).

### `spiderswitch protocol setup|verify`

Manage ai-protocol manifests.

---

## MCP tools (8)

### `list_models`

List available models from ai-protocol manifests.

Parameters:

- `filter_provider` (optional)
- `filter_capability` (optional)
- `require_api_key` (optional)
- `runtime_id` (optional)

### `switch_model`

Switch active model.

Parameters:

- `model` (required, `provider/model` format)
- `api_key` (optional, not recommended for production)
- `base_url` (optional)
- `runtime_id` (optional)

### `get_status`

Get current state and runtime profile.

Parameters:

- `runtime_id` (optional)

### `exit_switcher`

Reset runtime/session state.

Parameters:

- `runtime_id` (optional)
- `scope` (`all` or `runtime`, optional)

### `recommend_model`

Suggest the best model for a task using local BYOK policy (no upstream API call).

### `auto_switch`

Recommend and switch in one call.

### `query_index`

Query the pre-built capability index by capabilities, facets, tags, tier, or subjective score.

### `record_experience`

Rate a model (quality/speed/value 1–5) to improve future ranking.

---

## Runtime environment variables

- `AI_PROTOCOL_PATH` / `AI_PROTOCOL_DIR`: local ai-protocol root path
- `SPIDERSWITCH_SYNC_ON_INIT=1`: enable dist sync during runtime init (default disabled)
- `SPIDERSWITCH_SYNC_DIST=0`: disable dist sync when sync is explicitly invoked
- `AI_PROTOCOL_DIST_BASE_URL`: override raw dist source URL
- `AI_PROTOCOL_DIST_API_BASE_URL`: override GitHub API listing URL
- `SPIDERSWITCH_LIST_CACHE_TTL_SEC`: `list_models` cache TTL (default `5`)
- `SPIDERSWITCH_STATUS_CACHE_TTL_SEC`: `get_status` cache TTL (default `2`)
- `SPIDERSWITCH_INDEX_PATH`: persisted capability index file (default `~/.spiderswitch/index/capability-index.json`)
- `SPIDERSWITCH_INDEX_MAX_AGE_SEC`: warn when loaded index exceeds TTL (seconds)
- `SPIDERSWITCH_INDEX_REBUILD_ON_START=1`: rebuild from YAML at startup if index missing (slow fallback)

---

## Troubleshooting

### Missing API key error

- Ensure provider key env vars are set in the same environment as your MCP client.
- Restart client after changing environment variables.
- Re-run `spiderswitch doctor --json`.

### Proxy-related failures

- Unsupported proxy schemes (for example `socks4://`) are rejected.
- Use supported proxy schemes: `http://`, `https://`, or `socks5://`.

### No models found

- Verify `AI_PROTOCOL_PATH` points to a valid `ai-protocol` repository.
- Check if `v1/models/*.yaml` exists under that path.

### Capability index missing

- Run `spiderswitch index build` after protocol setup.
- Or use `spiderswitch setup --client cursor` which builds the index automatically.
- Check `spiderswitch doctor --json` → `capability_index` check.

---

## Recommended verification flow

1. `spiderswitch protocol verify`
2. `spiderswitch index build`
3. `spiderswitch doctor --json`
4. Start/restart MCP client
5. Call `list_models` or `query_index`
6. Call `auto_switch` or `switch_model`
7. Call `get_status`
8. Call `exit_switcher` (optional cleanup)

---

## Related docs

- `README.md` for project overview
- `README_CN.md` for Chinese quick-start
- `docs/AGENT_DEPLOY_GUIDE.md` for autonomous agent deploy playbook
- `CHANGELOG.md` for release history
- `USAGE_EXAMPLES.md` for usage snippets

---

`spiderswitch` helps keep model routing operational, explicit, and easy to validate.
