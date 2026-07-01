# spiderswitch CLI
"""
Command-line interface for server operations and agent-friendly self-deployment.
命令行入口：MCP 服务、初始化配置、健康检查与 Agent 自部署辅助。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from . import __version__
from .hints import (
    CLIENT_CONFIG_PATHS,
    MCP_PROMPTS,
    MCP_TOOLS,
    build_next_steps,
    enrich_check,
    hint_for_error,
)
from .index.service import ModelIndexService
from .index.store import default_index_path, load_index
from .runtime.python_runtime import PythonRuntime
from .validation import PROVIDER_API_KEY_ENV, PROXY_ENV_VARS

ClientType = Literal["cursor", "claude", "opencode"]

DEFAULT_PROTOCOL_DIR = Path.home() / ".spiderswitch" / "ai-protocol"


def _resolve_spiderswitch_command() -> str:
    """Return the spiderswitch executable path for MCP configs."""
    found = shutil.which("spiderswitch")
    return found or "spiderswitch"


def _build_mcp_config(client: ClientType, ai_protocol_path: str | None) -> dict[str, Any]:
    """Build a default MCP config template for target clients."""
    command = _resolve_spiderswitch_command()
    env: dict[str, str] = {
        "AI_PROTOCOL_PATH": ai_protocol_path or str(DEFAULT_PROTOCOL_DIR),
    }
    for env_names in PROVIDER_API_KEY_ENV.values():
        for key in env_names:
            value = os.getenv(key)
            if value:
                env[key] = value
    if not any(k.endswith("_API_KEY") for k in env):
        env["OPENAI_API_KEY"] = "sk-..."

    if client in {"cursor", "claude"}:
        return {
            "mcpServers": {
                "spiderswitch": {
                    "command": command,
                    "args": ["serve"],
                    "env": env,
                }
            }
        }
    return {
        "$schema": "https://opencode.ai/config.json",
        "mcp": {
            "spiderswitch": {
                "type": "local",
                "command": [command, "serve"],
                "enabled": True,
                "environment": env,
            }
        },
    }


def write_init_config(
    *,
    output: Path,
    client: ClientType,
    ai_protocol_path: str | None,
    force: bool,
) -> Path:
    """Write MCP config template to output file."""
    if output.exists() and not force:
        raise FileExistsError(f"Config file already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    config = _build_mcp_config(client=client, ai_protocol_path=ai_protocol_path)
    output.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def build_info_payload() -> dict[str, Any]:
    """Return agent-readable capability and deployment metadata."""
    runtime = PythonRuntime()
    profile = runtime.describe_runtime_profile()
    protocol_path = runtime._resolve_protocol_base()  # noqa: SLF001
    return {
        "name": "spiderswitch",
        "version": __version__,
        "cli_commands": [
            "serve",
            "version",
            "info",
            "index",
            "index build",
            "setup",
            "init",
            "doctor",
            "protocol setup",
            "protocol verify",
        ],
        "mcp_tools": MCP_TOOLS,
        "mcp_prompts": MCP_PROMPTS,
        "client_config_paths": CLIENT_CONFIG_PATHS,
        "default_protocol_path": str(DEFAULT_PROTOCOL_DIR),
        "spiderswitch_command": _resolve_spiderswitch_command(),
        "ai_protocol_path": str(protocol_path) if protocol_path else None,
        "runtime_profile": profile.to_dict(),
        "agent_guide": "docs/AGENT_DEPLOY_GUIDE.md",
    }


async def _runtime_probe(ai_protocol_path: str | None) -> dict[str, Any]:
    """Run a lightweight runtime list_models probe."""
    old_sync = os.getenv("SPIDERSWITCH_SYNC_ON_INIT")
    os.environ["SPIDERSWITCH_SYNC_ON_INIT"] = "0"
    runtime = PythonRuntime(ai_protocol_path=ai_protocol_path)
    try:
        models = await asyncio.wait_for(runtime.list_models(), timeout=5.0)
        return {
            "ok": True,
            "detail": f"runtime probe succeeded, discovered {len(models)} models",
        }
    except Exception as exc:
        entry = hint_for_error(str(exc))
        result: dict[str, Any] = {
            "ok": False,
            "detail": f"runtime probe failed: {exc}",
        }
        if entry:
            result["hint"] = entry.get("message")
            if entry.get("fix_commands"):
                result["fix_commands"] = list(entry["fix_commands"])
        else:
            result["hint"] = "Check AI_PROTOCOL_PATH and local ai-protocol manifests."
        return result
    finally:
        await runtime.close()
        if old_sync is None:
            os.environ.pop("SPIDERSWITCH_SYNC_ON_INIT", None)
        else:
            os.environ["SPIDERSWITCH_SYNC_ON_INIT"] = old_sync


def run_doctor_checks(*, include_runtime_probe: bool) -> dict[str, Any]:
    """Run structured health checks for installation readiness."""
    checks: list[dict[str, Any]] = []

    py_ok = sys.version_info >= (3, 10)
    checks.append(
        enrich_check(
            {
                "name": "python_version",
                "ok": py_ok,
                "detail": f"detected {sys.version.split()[0]} (require >= 3.10)",
            }
        )
    )

    cmd_ok = shutil.which("spiderswitch") is not None
    checks.append(
        enrich_check(
            {
                "name": "spiderswitch_command",
                "ok": cmd_ok,
                "detail": _resolve_spiderswitch_command(),
            }
        )
    )

    runtime = PythonRuntime()
    protocol_path = runtime._resolve_protocol_base()  # noqa: SLF001
    protocol_ok = protocol_path is not None
    checks.append(
        enrich_check(
            {
                "name": "ai_protocol_path",
                "ok": protocol_ok,
                "detail": str(protocol_path) if protocol_path else "not found",
            }
        )
    )

    configured_keys: list[str] = []
    for env_names in PROVIDER_API_KEY_ENV.values():
        for env_name in env_names:
            if os.getenv(env_name):
                configured_keys.append(env_name)
    checks.append(
        enrich_check(
            {
                "name": "api_keys",
                "ok": bool(configured_keys),
                "detail": f"{len(configured_keys)} env var(s) configured",
                "configured_env_vars": sorted(set(configured_keys)),
            }
        )
    )

    unsupported_proxy_env = runtime._detect_unsupported_proxy_env()  # noqa: SLF001
    checks.append(
        enrich_check(
            {
                "name": "proxy_scheme",
                "ok": not bool(unsupported_proxy_env),
                "detail": (
                    "unsupported proxy env vars: "
                    f"{sorted(unsupported_proxy_env.keys())}"
                    if unsupported_proxy_env
                    else "proxy scheme looks compatible"
                ),
                "observed_proxy_env_vars": [key for key in PROXY_ENV_VARS if os.getenv(key)],
            }
        )
    )

    if include_runtime_probe:
        probe = asyncio.run(_runtime_probe(str(protocol_path) if protocol_path else None))
        checks.append(enrich_check({"name": "runtime_probe", **probe}))

    index_path = default_index_path()
    index_loaded = load_index(index_path, protocol_path=protocol_path) if protocol_path else None
    checks.append(
        enrich_check(
            {
                "name": "capability_index",
                "ok": index_loaded is not None,
                "detail": (
                    f"loaded from {index_path}"
                    if index_loaded is not None
                    else f"not found at {index_path}"
                ),
                "index_path": str(index_path),
                **(
                    {
                        "stale": index_loaded[1].fingerprint_stale or index_loaded[1].age_stale,
                    }
                    if index_loaded is not None
                    else {}
                ),
            }
        )
    )

    healthy = all(bool(item.get("ok", False)) for item in checks)
    return {
        "healthy": healthy,
        "checks": checks,
        "next_steps": build_next_steps(checks),
        "agent_guide": "docs/AGENT_DEPLOY_GUIDE.md",
    }


def run_protocol_setup(*, target: Path, clone: bool) -> dict[str, Any]:
    """Ensure ai-protocol exists at target path."""
    if target.exists() and (target / "v1" / "models").is_dir():
        return {
            "ok": True,
            "path": str(target),
            "action": "existing",
            "hint": f"ai-protocol already present at {target}",
            "fix_commands": [f"export AI_PROTOCOL_PATH='{target}'"],
        }

    if not clone:
        return {
            "ok": False,
            "path": str(target),
            "action": "missing",
            "hint": "ai-protocol directory not found.",
            "fix_commands": [
                f"spiderswitch protocol setup --path '{target}'",
                f"git clone https://github.com/ailib-official/ai-protocol.git '{target}'",
                f"export AI_PROTOCOL_PATH='{target}'",
            ],
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("git") is None:
        return {
            "ok": False,
            "path": str(target),
            "action": "git_missing",
            "hint": "git is required to clone ai-protocol automatically.",
            "fix_commands": [
                "sudo apt install git  # or your OS equivalent",
                f"git clone https://github.com/ailib-official/ai-protocol.git '{target}'",
            ],
        }

    try:
        subprocess.run(
            [
                "git",
                "clone",
                "https://github.com/ailib-official/ai-protocol.git",
                str(target),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        return {
            "ok": False,
            "path": str(target),
            "action": "clone_failed",
            "hint": f"git clone failed: {exc.stderr or exc.stdout or exc}",
            "fix_commands": [
                f"git clone https://github.com/ailib-official/ai-protocol.git '{target}'",
            ],
        }

    os.environ["AI_PROTOCOL_PATH"] = str(target)
    return {
        "ok": True,
        "path": str(target),
        "action": "cloned",
        "hint": f"Cloned ai-protocol to {target}. Set AI_PROTOCOL_PATH in MCP client env.",
        "fix_commands": [f"export AI_PROTOCOL_PATH='{target}'"],
    }


def run_protocol_verify(path: Path | None) -> dict[str, Any]:
    """Verify ai-protocol layout at path."""
    runtime = PythonRuntime(ai_protocol_path=str(path) if path else None)
    resolved = runtime._resolve_protocol_base()  # noqa: SLF001
    if resolved is None:
        entry = hint_for_error("Unable to locate ai-protocol")
        return {
            "ok": False,
            "path": str(path) if path else None,
            "hint": entry.get("message") if entry else "ai-protocol not found",
            "fix_commands": list(entry.get("fix_commands") or []) if entry else [],
        }
    models_dir = resolved / "v1" / "models"
    ok = models_dir.is_dir() and any(models_dir.glob("*.yaml"))
    result: dict[str, Any] = {
        "ok": ok,
        "path": str(resolved),
        "models_dir": str(models_dir),
        "model_files": len(list(models_dir.glob("*.yaml"))) if ok else 0,
    }
    if not ok:
        result["hint"] = f"Expected YAML manifests under {models_dir}"
        result["fix_commands"] = [
            "spiderswitch protocol setup",
            f"ls '{models_dir}'",
        ]
    return result


def run_setup(*, client: ClientType, protocol_path: Path, skip_protocol: bool) -> dict[str, Any]:
    """Orchestrate agent-friendly self-deployment."""
    steps: list[dict[str, Any]] = []

    if not skip_protocol:
        proto = run_protocol_setup(target=protocol_path, clone=True)
        steps.append({"step": "protocol", **proto})
        if proto.get("ok"):
            os.environ["AI_PROTOCOL_PATH"] = str(proto["path"])

    config_path = Path(CLIENT_CONFIG_PATHS[client]).expanduser()
    try:
        write_init_config(
            output=config_path,
            client=client,
            ai_protocol_path=str(protocol_path),
            force=True,
        )
        steps.append(
            {
                "step": "init",
                "ok": True,
                "path": str(config_path),
                "client": client,
                "hint": f"Wrote MCP config for {client} to {config_path}",
            }
        )
    except Exception as exc:
        steps.append({"step": "init", "ok": False, "detail": str(exc)})

    if protocol_path.exists() and (protocol_path / "v1" / "models").is_dir():
        try:
            index_service = ModelIndexService.build_from_protocol_path(protocol_path, persist=True)
            steps.append(
                {
                    "step": "index_build",
                    "ok": True,
                    "index_path": str(index_service.index_path),
                    "total_models": index_service.index.total_models,
                    "hint": "Capability index pre-built for fast MCP startup",
                }
            )
        except Exception as exc:
            steps.append({"step": "index_build", "ok": False, "detail": str(exc)})

    doctor = run_doctor_checks(include_runtime_probe=True)
    steps.append({"step": "doctor", **doctor})

    setup_ok = all(
        s.get("ok", False) for s in steps if s.get("step") in {"protocol", "init", "index_build"}
    )
    setup_ok = setup_ok and doctor.get("healthy", False)
    return {
        "ok": setup_ok,
        "client": client,
        "protocol_path": str(protocol_path),
        "config_path": str(config_path),
        "steps": steps,
        "next_steps": doctor.get("next_steps", []),
        "agent_guide": "docs/AGENT_DEPLOY_GUIDE.md",
    }


def _print_human_doctor_result(result: dict[str, Any]) -> None:
    """Print doctor output in human-readable format."""
    print("spiderswitch doctor")
    print("==================")
    for item in result.get("checks", []):
        status = "OK" if item.get("ok") else "FAIL"
        detail = item.get("detail", "")
        print(f"- [{status}] {item.get('name')}: {detail}")
        hint = item.get("hint")
        if hint and not item.get("ok"):
            print(f"  hint: {hint}")
        for cmd in item.get("fix_commands") or []:
            print(f"  fix: {cmd}")
    print("")
    print(f"overall: {'healthy' if result.get('healthy') else 'unhealthy'}")
    next_steps = result.get("next_steps") or []
    if next_steps:
        print("\nnext steps:")
        for step in next_steps:
            print(f"  {step}")


def _print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for spiderswitch."""
    parser = argparse.ArgumentParser(
        prog="spiderswitch",
        description="MCP server for dynamic AI model switching (agent-friendly CLI).",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="Run MCP stdio server")

    version_parser = subparsers.add_parser("version", help="Print package version")
    version_parser.add_argument("--json", action="store_true", help="Print JSON")

    subparsers.add_parser(
        "info",
        help="Show MCP capabilities and deployment metadata (JSON, for agents)",
    )

    index_parser = subparsers.add_parser(
        "index",
        help="Capability index: load summary or pre-build from ai-protocol",
    )
    index_sub = index_parser.add_subparsers(dest="index_command")
    index_sub.add_parser(
        "build",
        help="Pre-build and persist index from ai-protocol (cron-friendly)",
    )
    index_build = index_sub.choices["build"]
    index_build.add_argument(
        "--protocol-path",
        default=None,
        help="Optional ai-protocol root (default: auto-detect)",
    )

    setup_parser = subparsers.add_parser(
        "setup",
        help="One-shot self-deploy: protocol + MCP config + doctor",
    )
    setup_parser.add_argument(
        "--client",
        choices=["cursor", "claude", "opencode"],
        default="cursor",
        help="Target MCP client",
    )
    setup_parser.add_argument(
        "--protocol-path",
        default=str(DEFAULT_PROTOCOL_DIR),
        help="Where to clone/find ai-protocol",
    )
    setup_parser.add_argument(
        "--skip-protocol",
        action="store_true",
        help="Skip ai-protocol clone/setup step",
    )

    init_parser = subparsers.add_parser("init", help="Generate MCP config template")
    init_parser.add_argument(
        "--client",
        choices=["cursor", "claude", "opencode"],
        default="cursor",
        help="Target MCP client template",
    )
    init_parser.add_argument(
        "--output",
        default=".spiderswitch.mcp.json",
        help="Output config path",
    )
    init_parser.add_argument(
        "--ai-protocol-path",
        default=os.getenv("AI_PROTOCOL_PATH")
        or os.getenv("AI_PROTOCOL_DIR")
        or str(DEFAULT_PROTOCOL_DIR),
        help="ai-protocol root path",
    )
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing output file")

    doctor_parser = subparsers.add_parser("doctor", help="Run installation health checks")
    doctor_parser.add_argument("--json", action="store_true", help="Print JSON output")
    doctor_parser.add_argument(
        "--no-runtime-probe",
        action="store_true",
        help="Skip runtime list_models probe",
    )

    protocol_parser = subparsers.add_parser(
        "protocol",
        help="Manage ai-protocol manifests",
    )
    protocol_sub = protocol_parser.add_subparsers(dest="protocol_command")
    proto_setup = protocol_sub.add_parser("setup", help="Clone or verify ai-protocol")
    proto_setup.add_argument(
        "--path",
        default=str(DEFAULT_PROTOCOL_DIR),
        help="Target ai-protocol directory",
    )
    proto_setup.add_argument(
        "--no-clone",
        action="store_true",
        help="Do not git-clone; only report status",
    )
    proto_verify = protocol_sub.add_parser("verify", help="Verify ai-protocol layout")
    proto_verify.add_argument("--path", default=None, help="Optional ai-protocol path")

    args = parser.parse_args(argv)
    command = args.command or "serve"

    if command == "serve":
        from .server import cli as server_cli

        server_cli()
        return 0

    if command == "version":
        if args.json:
            _print_json({"version": __version__, "name": "spiderswitch"})
        else:
            print(__version__)
        return 0

    if command == "info":
        _print_json(build_info_payload())
        return 0

    if command == "index":
        runtime = PythonRuntime()
        if args.index_command == "build":
            base: Path | None
            if args.protocol_path:
                base = Path(args.protocol_path).expanduser()
            else:
                base = runtime._resolve_protocol_base()  # noqa: SLF001
            if base is None or not base.exists():
                _print_json(
                    {
                        "ok": False,
                        "hint": "ai-protocol not found",
                        "fix_commands": ["spiderswitch protocol setup"],
                    }
                )
                return 1
            service = ModelIndexService.build_from_protocol_path(base, persist=True)
            _print_json(
                {
                    "ok": True,
                    "action": "built",
                    "index_path": str(service.index_path),
                    **service.info_payload(),
                }
            )
            return 0

        base = runtime._resolve_protocol_base()  # noqa: SLF001
        if base is None:
            _print_json(
                {
                    "ok": False,
                    "hint": "ai-protocol not found (needed for staleness check)",
                    "fix_commands": ["spiderswitch protocol setup"],
                }
            )
            return 1
        loaded_service, load_status = ModelIndexService.load_or_build_for_cli(Path(base))
        if loaded_service is None:
            _print_json({"ok": False, **load_status})
            return 1
        _print_json({"ok": True, **load_status, **loaded_service.info_payload()})
        return 0

    if command == "setup":
        result = run_setup(
            client=args.client,
            protocol_path=Path(args.protocol_path).expanduser(),
            skip_protocol=bool(args.skip_protocol),
        )
        _print_json(result)
        return 0 if result.get("ok") else 1

    if command == "init":
        output = Path(args.output).expanduser()
        try:
            write_init_config(
                output=output,
                client=args.client,
                ai_protocol_path=args.ai_protocol_path,
                force=bool(args.force),
            )
        except FileExistsError as exc:
            print(str(exc))
            print("Use --force to overwrite.")
            return 1
        print(f"Generated config template: {output}")
        print(f"hint: merge into {CLIENT_CONFIG_PATHS.get(args.client, 'your MCP config')}")
        return 0

    if command == "doctor":
        result = run_doctor_checks(include_runtime_probe=not bool(args.no_runtime_probe))
        if bool(args.json):
            _print_json(result)
        else:
            _print_human_doctor_result(result)
        return 0 if result["healthy"] else 1

    if command == "protocol":
        if args.protocol_command == "setup":
            result = run_protocol_setup(
                target=Path(args.path).expanduser(),
                clone=not bool(args.no_clone),
            )
            _print_json(result)
            return 0 if result.get("ok") else 1
        if args.protocol_command == "verify":
            path = Path(args.path).expanduser() if args.path else None
            result = run_protocol_verify(path)
            _print_json(result)
            return 0 if result.get("ok") else 1
        protocol_parser.print_help()
        return 1

    parser.print_help()
    return 1


__all__ = [
    "main",
    "run_doctor_checks",
    "write_init_config",
    "build_info_payload",
    "run_setup",
    "run_protocol_setup",
    "run_protocol_verify",
]
