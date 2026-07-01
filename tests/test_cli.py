# Tests for CLI onboarding commands and agent-friendly tooling
"""
Test spiderswitch CLI: init, doctor, info, setup, protocol, hints.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from spiderswitch.cli import (
    build_info_payload,
    run_doctor_checks,
    run_protocol_setup,
    run_protocol_verify,
    write_init_config,
)
from spiderswitch.hints import enrich_check, hint_for_check, hint_for_error


def test_write_init_config_generates_cursor_template(tmp_path: Path) -> None:
    """init config writer should produce cursor-compatible schema."""
    target = tmp_path / "mcp.json"
    write_init_config(
        output=target,
        client="cursor",
        ai_protocol_path="/tmp/ai-protocol",
        force=False,
    )
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert "mcpServers" in payload
    assert "spiderswitch" in payload["mcpServers"]
    server = payload["mcpServers"]["spiderswitch"]
    assert server["command"].endswith("spiderswitch")
    assert server["args"] == ["serve"]
    assert server["env"]["AI_PROTOCOL_PATH"] == "/tmp/ai-protocol"


def test_write_init_config_respects_force_flag(tmp_path: Path) -> None:
    """init config writer should block overwrite unless force=true."""
    target = tmp_path / "mcp.json"
    target.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_init_config(
            output=target,
            client="cursor",
            ai_protocol_path=None,
            force=False,
        )


def test_doctor_reports_unsupported_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    """doctor should mark unsupported proxy scheme as unhealthy."""
    monkeypatch.setenv("ALL_PROXY", "socks4://127.0.0.1:9999")
    result = run_doctor_checks(include_runtime_probe=False)
    check_map = {item["name"]: item for item in result["checks"]}
    assert check_map["proxy_scheme"]["ok"] is False
    assert "fix_commands" in check_map["proxy_scheme"]
    assert result["healthy"] is False
    assert isinstance(result.get("next_steps"), list)


def test_doctor_skips_runtime_probe_when_disabled() -> None:
    """doctor should not include runtime probe when explicitly disabled."""
    result = run_doctor_checks(include_runtime_probe=False)
    names = [item["name"] for item in result["checks"]]
    assert "runtime_probe" not in names


def test_build_info_payload_lists_cli_and_mcp_capabilities() -> None:
    payload = build_info_payload()
    assert payload["name"] == "spiderswitch"
    assert "auto_switch" in payload["mcp_tools"]
    assert "spiderswitch_guide" in payload["mcp_prompts"]
    assert "setup" in payload["cli_commands"]
    assert payload["agent_guide"] == "docs/AGENT_DEPLOY_GUIDE.md"


def test_hint_for_check_includes_fix_commands() -> None:
    entry = hint_for_check("ai_protocol_path")
    assert entry is not None
    enriched = enrich_check({"name": "ai_protocol_path", "ok": False, "detail": "not found"})
    assert enriched.get("fix_commands")
    assert "spiderswitch protocol setup" in enriched["fix_commands"][0]


def test_hint_for_error_matches_missing_api_key() -> None:
    entry = hint_for_error("Missing API key for provider 'openai'.")
    assert entry is not None
    assert "fix_commands" in entry


def test_protocol_setup_no_clone_reports_missing(tmp_path: Path) -> None:
    target = tmp_path / "ai-protocol"
    result = run_protocol_setup(target=target, clone=False)
    assert result["ok"] is False
    assert result["action"] == "missing"
    assert "fix_commands" in result


def test_protocol_verify_fails_without_manifests() -> None:
    result = run_protocol_verify(None)
    assert result["ok"] is False
    assert "hint" in result or "fix_commands" in result
