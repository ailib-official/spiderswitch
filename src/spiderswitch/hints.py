# spiderswitch heuristic hints
"""
Centralized, agent-actionable hints for CLI diagnostics and error recovery.
集中管理的启发式错误提示，供 CLI 诊断与 Agent 自动修复使用。

Each hint entry includes:
- ``message``: human-readable explanation
- ``fix_commands``: shell commands an agent can run (may contain placeholders)
- ``docs``: optional doc anchor or path
"""

from __future__ import annotations

from typing import Any, TypedDict


class HintEntry(TypedDict, total=False):
    message: str
    fix_commands: list[str]
    docs: str


# Check name -> hint when the check fails.
DOCTOR_HINTS: dict[str, HintEntry] = {
    "python_version": {
        "message": "Python 3.10 or newer is required.",
        "fix_commands": [
            "python3 --version",
            "# Install Python 3.10+ via your OS package manager or pyenv",
        ],
        "docs": "docs/AGENT_DEPLOY_GUIDE.md#prerequisites",
    },
    "spiderswitch_command": {
        "message": "The spiderswitch CLI is not on PATH.",
        "fix_commands": [
            "pip install -e .",
            "export PATH=\"$HOME/.local/bin:$PATH\"",
            "which spiderswitch",
        ],
        "docs": "docs/AGENT_DEPLOY_GUIDE.md#step-1-install",
    },
    "ai_protocol_path": {
        "message": "ai-protocol manifests were not found. spiderswitch loads model inventory from this directory.",
        "fix_commands": [
            "spiderswitch protocol setup",
            "# or manually:",
            "git clone https://github.com/ailib-official/ai-protocol.git ~/.spiderswitch/ai-protocol",
            "export AI_PROTOCOL_PATH=\"$HOME/.spiderswitch/ai-protocol\"",
        ],
        "docs": "docs/AGENT_DEPLOY_GUIDE.md#step-2-ai-protocol",
    },
    "api_keys": {
        "message": "No provider API keys detected in the MCP server process environment.",
        "fix_commands": [
            "export OPENAI_API_KEY='sk-...'",
            "# Add the same env vars to your MCP client config (Cursor/OpenCode mcp env block)",
            "spiderswitch doctor --json",
        ],
        "docs": "docs/AGENT_DEPLOY_GUIDE.md#step-3-api-keys",
    },
    "proxy_scheme": {
        "message": "Unsupported proxy scheme (socks4) detected in environment.",
        "fix_commands": [
            "unset ALL_PROXY HTTP_PROXY HTTPS_PROXY",
            "export HTTPS_PROXY='http://127.0.0.1:7890'  # example: use http/https/socks5",
        ],
        "docs": "docs/AGENT_DEPLOY_GUIDE.md#troubleshooting",
    },
    "runtime_probe": {
        "message": "Runtime could not load models from ai-protocol.",
        "fix_commands": [
            "spiderswitch protocol verify",
            "export AI_PROTOCOL_PATH=\"$HOME/.spiderswitch/ai-protocol\"",
            "spiderswitch doctor --json",
        ],
        "docs": "docs/AGENT_DEPLOY_GUIDE.md#step-4-verify",
    },
    "mcp_config": {
        "message": "MCP client config for spiderswitch was not found or is incomplete.",
        "fix_commands": [
            "spiderswitch init --client cursor --output ~/.cursor/mcp.json --force",
            "spiderswitch init --client opencode --output ~/.config/opencode/opencode.json --force",
        ],
        "docs": "docs/AGENT_DEPLOY_GUIDE.md#step-3-mcp-client",
    },
}

# Common CLI / runtime error substrings -> hint.
ERROR_HEURISTICS: list[tuple[str, HintEntry]] = [
    (
        "Unable to locate ai-protocol",
        DOCTOR_HINTS["ai_protocol_path"],
    ),
    (
        "Missing API key",
        DOCTOR_HINTS["api_keys"],
    ),
    (
        "No eligible models",
        {
            "message": "No models match filters with configured API keys (BYOK).",
            "fix_commands": [
                "export OPENAI_API_KEY='sk-...'  # or another provider key",
                "spiderswitch doctor --json",
                "# Then retry: auto_switch with a relaxed tier or task_hint",
            ],
            "docs": "docs/AGENT_DEPLOY_GUIDE.md#troubleshooting",
        },
    ),
    (
        "Unknown runtime_id",
        {
            "message": "Requested runtime_id is not registered.",
            "fix_commands": [
                "spiderswitch info --json  # inspect runtime_profile.runtime_id",
                "# Omit runtime_id to use the default python-runtime",
            ],
        },
    ),
    (
        "Unsupported proxy scheme",
        DOCTOR_HINTS["proxy_scheme"],
    ),
]

CLIENT_CONFIG_PATHS: dict[str, str] = {
    "cursor": "~/.cursor/mcp.json",
    "claude": "~/.config/claude-desktop/config.json",
    "opencode": "~/.config/opencode/opencode.json",
}

MCP_TOOLS = [
    "switch_model",
    "list_models",
    "get_status",
    "exit_switcher",
    "recommend_model",
    "auto_switch",
]

MCP_PROMPTS = [
    "spiderswitch_guide",
    "route_task",
]


def hint_for_check(check_name: str) -> HintEntry | None:
    """Return the structured hint for a failed doctor check."""
    return DOCTOR_HINTS.get(check_name)


def hint_for_error(message: str) -> HintEntry | None:
    """Match a runtime/CLI error message to a heuristic hint."""
    lowered = message.lower()
    for needle, entry in ERROR_HEURISTICS:
        if needle.lower() in lowered:
            return entry
    return None


def enrich_check(check: dict[str, Any]) -> dict[str, Any]:
    """Attach heuristic hint fields to a doctor check result."""
    if check.get("ok"):
        return check
    entry = hint_for_check(str(check.get("name", "")))
    if entry is None:
        return check
    enriched = dict(check)
    enriched.setdefault("hint", entry.get("message"))
    if entry.get("fix_commands"):
        enriched["fix_commands"] = list(entry["fix_commands"])
    if entry.get("docs"):
        enriched["docs"] = entry["docs"]
    return enriched


def build_next_steps(checks: list[dict[str, Any]]) -> list[str]:
    """Flatten fix_commands from all failed checks into an ordered action list."""
    steps: list[str] = []
    seen: set[str] = set()
    for check in checks:
        if check.get("ok"):
            continue
        for cmd in check.get("fix_commands") or []:
            if cmd not in seen:
                seen.add(cmd)
                steps.append(cmd)
    return steps


__all__ = [
    "CLIENT_CONFIG_PATHS",
    "DOCTOR_HINTS",
    "ERROR_HEURISTICS",
    "MCP_PROMPTS",
    "MCP_TOOLS",
    "HintEntry",
    "build_next_steps",
    "enrich_check",
    "hint_for_check",
    "hint_for_error",
]
