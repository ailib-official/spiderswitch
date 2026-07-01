# spiderswitch MCP prompts / instructions
"""
Prompt-injection layer that teaches agents to drive spiderswitch.
通过 MCP instructions 与 prompts 注入引导，规定 Agent 何时/如何调用 spiderswitch 切换模型。

Two complementary mechanisms are provided:

1. ``SERVER_INSTRUCTIONS`` — passed to the MCP ``Server`` and surfaced by most
   clients during initialization, so the guidance is injected into the agent's
   system context automatically (the "always-on" prompt injection).
2. MCP **Prompts** (``list_prompts`` / ``get_prompt``) — reusable, parameterized
   templates a client or user can attach on demand to make a specific task
   spiderswitch-aware.
"""

from __future__ import annotations

from mcp.types import GetPromptResult, Prompt, PromptArgument, PromptMessage, TextContent

# Allowed routing hints mirrored from the recommend/auto_switch tool schema.
TASK_HINTS = ("chat", "code", "reasoning", "vision", "summarize", "cheap", "quality")
TIERS = ("economy", "balanced", "premium")


SERVER_INSTRUCTIONS = (
    "spiderswitch lets you switch the active LLM per task within the ai-lib "
    "ecosystem (BYOK: only providers with configured API keys are usable).\n\n"
    "Operating policy:\n"
    "- Before starting a task whose ideal model differs from the current one "
    "(heavy reasoning, coding/tool use, vision, or cheap high-volume work), call "
    "`auto_switch` with a `task_hint` (one of: "
    f"{', '.join(TASK_HINTS)}) and optional `tier` (one of: {', '.join(TIERS)}). "
    "It selects and switches in one step using local policy only (no upstream API).\n"
    "- Use `recommend_model` first if you want a suggestion without switching.\n"
    "- Use `list_models` to discover available models, `switch_model` to switch to "
    "an explicit `provider/model`, and `get_status` to confirm the active model.\n"
    "- Use `query_index` to look up models by structured capabilities and subjective scores.\n"
    "- Use `record_experience` after using a model to accumulate quality/speed/value ratings.\n"
    "- Call `exit_switcher` to reset spiderswitch and hand control back to the "
    "client's built-in model selection.\n"
    "- After any switch, treat an increased `get_status.connection_epoch` as the "
    "signal to rebuild cached model sessions.\n"
    "- If a switch fails, inspect `error.details.ai_lib_error`: when `retryable` is "
    "true wait `retry_after` and retry; when `fallbackable` is true pick another "
    "model/provider.\n\n"
    "规定：在执行需要不同模型的任务前，先调用 `auto_switch`（传入 task_hint/tier）"
    "完成智能选模与切换；仅使用已配置 Key 的 Provider。"
)


_PROMPTS: list[Prompt] = [
    Prompt(
        name="spiderswitch_guide",
        title="spiderswitch usage guide",
        description=(
            "System-style guidance that makes an agent spiderswitch-aware: when and "
            "how to call the model-switching tools. Attach once per session. "
            "可注入的系统级引导：规定 Agent 何时/如何调用 spiderswitch。"
        ),
        arguments=[],
    ),
    Prompt(
        name="route_task",
        title="Route a task to the best model",
        description=(
            "Instruct the agent to select and switch to the best model for a concrete "
            "task before answering. 针对具体任务注入：先用 auto_switch 选模再作答。"
        ),
        arguments=[
            PromptArgument(
                name="task",
                description="The task the agent must complete.",
                required=True,
            ),
            PromptArgument(
                name="task_hint",
                description=f"Optional routing hint, one of: {', '.join(TASK_HINTS)}.",
                required=False,
            ),
            PromptArgument(
                name="tier",
                description=f"Optional cost/quality tier, one of: {', '.join(TIERS)}.",
                required=False,
            ),
        ],
    ),
]


def list_prompts() -> list[Prompt]:
    """Return the catalog of injectable prompts."""
    return list(_PROMPTS)


def _guide_message() -> GetPromptResult:
    return GetPromptResult(
        description="spiderswitch operating guidance",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=SERVER_INSTRUCTIONS),
            )
        ],
    )


def _route_task_message(arguments: dict[str, str]) -> GetPromptResult:
    task = (arguments.get("task") or "").strip()
    if not task:
        raise ValueError("Prompt 'route_task' requires a non-empty 'task' argument.")

    raw_hint = (arguments.get("task_hint") or "").strip().lower()
    task_hint = raw_hint if raw_hint in TASK_HINTS else None
    raw_tier = (arguments.get("tier") or "").strip().lower()
    tier = raw_tier if raw_tier in TIERS else None

    if task_hint:
        hint_clause = f"Use task_hint=\"{task_hint}\""
    else:
        hint_clause = (
            "First infer the best task_hint from "
            f"[{', '.join(TASK_HINTS)}] based on the task, then use it"
        )
    tier_clause = f" and tier=\"{tier}\"" if tier else ""

    text = (
        "Before answering, route this task to the most suitable model using "
        "spiderswitch.\n"
        f"1. {hint_clause}{tier_clause} to call the `auto_switch` tool "
        "(BYOK; only configured providers are eligible).\n"
        "2. Confirm the active model via `get_status` if needed.\n"
        "3. If `auto_switch` returns no eligible model, fall back to the client's "
        "current model and continue.\n"
        "4. Then complete the task.\n\n"
        f"Task:\n{task}"
    )

    return GetPromptResult(
        description=f"Route task to best model (hint={task_hint or 'infer'}, tier={tier or 'default'})",
        messages=[
            PromptMessage(role="user", content=TextContent(type="text", text=text))
        ],
    )


def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Render a prompt by name.

    Raises:
        ValueError: If the prompt name is unknown or required args are missing.
    """
    args = arguments or {}
    if name == "spiderswitch_guide":
        return _guide_message()
    if name == "route_task":
        return _route_task_message(args)
    raise ValueError(f"Unknown prompt: {name}")


__all__ = [
    "SERVER_INSTRUCTIONS",
    "TASK_HINTS",
    "TIERS",
    "list_prompts",
    "get_prompt",
]
