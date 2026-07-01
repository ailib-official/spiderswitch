# Agent Self-Deploy Guide — spiderswitch MCP Server

> **Audience:** Any autonomous agent (Cursor, OpenCode, Claude Desktop, custom runners).
> **Goal:** Install spiderswitch, wire it as an MCP server, verify health, and use model-switching tools.
> **Principle:** Every step is a copy-paste shell command. Every failure has a heuristic fix.

---

## 0. Quick decision tree

```
Need model switching in an MCP client?
  ├─ Yes → follow Steps 1–5 below
  └─ Already installed? → run: spiderswitch doctor --json
         ├─ healthy: true  → use MCP tools (Section 6)
         └─ healthy: false → read next_steps in JSON output
```

**Fastest path (one command):**

```bash
pip install spiderswitch && spiderswitch setup --client cursor
```

Then set API keys in the MCP client config and restart the client.

---

## 1. Prerequisites {#prerequisites}

| Requirement | Check command | Minimum |
|-------------|---------------|---------|
| Python | `python3 --version` | 3.10+ |
| pip | `pip --version` | any recent |
| git (for auto clone) | `git --version` | optional but recommended |
| MCP client | Cursor / OpenCode / Claude Desktop | one of |

Discover capabilities at any time:

```bash
spiderswitch info
spiderswitch version
```

---

## 2. Step 1 — Install {#step-1-install}

### Option A: PyPI / wheel

```bash
pip install spiderswitch
# or from a release wheel:
pip install /path/to/spiderswitch-<version>-py3-none-any.whl
```

### Option B: From source

```bash
git clone https://github.com/ailib-official/spiderswitch.git
cd spiderswitch
pip install -e .
```

### Option C: One-click script (isolated venv)

```bash
bash scripts/install_one_click.sh
export PATH="$HOME/.local/bin:$PATH"
```

**Verify:**

```bash
which spiderswitch
spiderswitch version
```

**If `spiderswitch` not found:**

```bash
export PATH="$HOME/.local/bin:$PATH"
pip install -e .
which spiderswitch
```

---

## 3. Step 2 — ai-protocol {#step-2-ai-protocol}

spiderswitch loads model inventory from the [ai-protocol](https://github.com/ailib-official/ai-protocol) manifests. Without it, `list_models` and `switch_model` will fail.

### Automatic (recommended for agents)

```bash
spiderswitch protocol setup
export AI_PROTOCOL_PATH="$HOME/.spiderswitch/ai-protocol"
```

### Manual

```bash
git clone https://github.com/ailib-official/ai-protocol.git ~/.spiderswitch/ai-protocol
export AI_PROTOCOL_PATH="$HOME/.spiderswitch/ai-protocol"
```

### Verify

```bash
spiderswitch protocol verify
# Expect: "ok": true, model_files > 0
```

---

## 4. Step 3 — MCP client + API keys {#step-3-mcp-client}

### 3a. Generate MCP config

**Cursor** (config: `~/.cursor/mcp.json`):

```bash
spiderswitch init --client cursor --output ~/.cursor/mcp.json --force \
  --ai-protocol-path "$HOME/.spiderswitch/ai-protocol"
```

**OpenCode** (config: `~/.config/opencode/opencode.json`):

```bash
spiderswitch init --client opencode \
  --output ~/.config/opencode/opencode.json --force \
  --ai-protocol-path "$HOME/.spiderswitch/ai-protocol"
```

**Claude Desktop** (config: `~/.config/claude-desktop/config.json`):

```bash
spiderswitch init --client claude \
  --output ~/.config/claude-desktop/config.json --force \
  --ai-protocol-path "$HOME/.spiderswitch/ai-protocol"
```

Or use the all-in-one setup:

```bash
spiderswitch setup --client cursor   # or opencode / claude
```

### 3b. API keys {#step-3-api-keys}

Add at least one provider key **inside the MCP config `env` block** (not only in your shell):

| Provider | Environment variable |
|----------|---------------------|
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Google | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |

Example snippet (Cursor):

```json
{
  "mcpServers": {
    "spiderswitch": {
      "command": "/home/you/.local/bin/spiderswitch",
      "args": ["serve"],
      "env": {
        "AI_PROTOCOL_PATH": "/home/you/.spiderswitch/ai-protocol",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

**Restart the MCP client** after editing config.

---

## 5. Step 4 — Verify {#step-4-verify}

```bash
spiderswitch doctor --json
```

**Success criteria:**

```json
{ "healthy": true, "checks": [ ... all ok: true ... ] }
```

**On failure**, read:

- `checks[].hint` — what went wrong
- `checks[].fix_commands` — commands to run
- `next_steps` — ordered recovery actions

Skip the runtime probe during install-only checks:

```bash
spiderswitch doctor --json --no-runtime-probe
```

**In the MCP client**, confirm the server is connected:

```bash
# OpenCode example
opencode mcp list
```

---

## 6. MCP capabilities (after deploy) {#capabilities}

### Tools (6)

| Tool | When to call |
|------|--------------|
| `auto_switch` | **Default.** Pick + switch model for a task (`task_hint`, `tier`) |
| `recommend_model` | Suggest a model without switching |
| `switch_model` | Switch to an explicit `provider/model` id |
| `list_models` | Discover models (`require_api_key: true` for BYOK-only list) |
| `get_status` | Confirm active model; watch `connection_epoch` after switches |
| `exit_switcher` | Reset spiderswitch state |

### Prompts (2)

| Prompt | Purpose |
|--------|---------|
| `spiderswitch_guide` | Inject operating policy once per session |
| `route_task` | Route a concrete task via `auto_switch` before answering |

### Server instructions

Injected automatically at MCP init — tells the agent when/how to call the tools above.

### Typical agent workflow

```
1. auto_switch(task_hint="code", tier="balanced")
2. get_status()  → confirm is_configured == true
3. [do work with the host LLM]
4. if switch fails → read error.details.hint / error.details.ai_lib_error
```

---

## 7. CLI reference (full) {#cli-reference}

| Command | Purpose |
|---------|---------|
| `spiderswitch serve` | Run MCP stdio server (used by MCP clients) |
| `spiderswitch version [--json]` | Print package version |
| `spiderswitch info` | JSON: tools, prompts, config paths, runtime profile |
| `spiderswitch setup [--client cursor\|opencode\|claude]` | One-shot deploy |
| `spiderswitch init --client … --output …` | Write MCP config template |
| `spiderswitch doctor [--json] [--no-runtime-probe]` | Health checks + fix hints |
| `spiderswitch protocol setup [--path …]` | Clone/verify ai-protocol |
| `spiderswitch protocol verify [--path …]` | Validate manifest layout |

All JSON outputs include `hint`, `fix_commands`, and/or `next_steps` where applicable.

---

## 8. Troubleshooting {#troubleshooting}

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `ai_protocol_path: not found` | Missing manifests | `spiderswitch protocol setup` |
| `api_keys: 0 env var(s)` | Keys not in MCP env | Add `OPENAI_API_KEY` etc. to MCP config `env` |
| `switch_model` → Missing API key | Same as above | Keys must be in **MCP server process** env |
| `No eligible models` | BYOK filter, no keys | Configure a provider key, retry `auto_switch` |
| `Model 'x/y' not found` | Id mismatch | Run `list_models` and use exact id |
| `rate_limited` in `ai_lib_error` | Upstream 429 | Wait `retry_after`, or `fallbackable: true` → switch model |
| MCP server not listed | Config path wrong | `spiderswitch info` → `client_config_paths` |
| `spiderswitch: command not found` | Not on PATH | `export PATH="$HOME/.local/bin:$PATH"` |
| Proxy errors | socks4 unsupported | Use `http://` or `socks5://` proxy schemes |

For any error message, match against:

```bash
spiderswitch doctor --json   # structured hints
spiderswitch info            # capability + path reference
```

Tool errors may include:

```json
{
  "error": {
    "details": {
      "hint": "...",
      "fix_commands": ["..."],
      "ai_lib_error": { "retryable": true, "fallbackable": true }
    }
  }
}
```

---

## 9. Agent checklist (copy before closing)

- [ ] `spiderswitch version` prints expected version
- [ ] `spiderswitch protocol verify` → `"ok": true`
- [ ] `spiderswitch doctor --json` → `"healthy": true`
- [ ] MCP client config written and contains `AI_PROTOCOL_PATH` + at least one API key
- [ ] MCP client restarted; server shows connected
- [ ] `auto_switch` or `list_models` callable from agent

---

## 10. Related docs

- [README.md](../README.md) — feature overview
- [USER_GUIDE.md](../USER_GUIDE.md) — human-oriented usage
- [CHANGELOG.md](../CHANGELOG.md) — release history
