#!/usr/bin/env bash
# Run SpiderSwitch smart routing E2E tests
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${ROOT}/.venv/bin/python"
PYTEST="${ROOT}/.venv/bin/pytest"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
  PYTEST="python3 -m pytest"
fi

export AI_PROTOCOL_PATH="${AI_PROTOCOL_PATH:-/home/alex/ai-protocol}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"

echo "==> Unit + integration tests"
$PYTEST tests/test_policy_engine.py tests/test_smart_tools.py tests/test_server_mcp_flow.py -v --tb=short

echo ""
echo "==> E2E recommend_model (needs at least one *_API_KEY)"
$PYTEST tests/test_e2e_smart_routing.py -v --tb=short -k "recommend"

if [[ "${SPIDERSWITCH_E2E_LIVE:-0}" == "1" ]]; then
  echo ""
  echo "==> LIVE auto_switch (initializes AiClient — may call provider)"
  $PYTEST tests/test_e2e_smart_routing.py -v --tb=short -k "auto_switch"
else
  echo ""
  echo "Skip live auto_switch (set SPIDERSWITCH_E2E_LIVE=1 to enable)"
fi

echo ""
echo "==> Full test suite"
$PYTEST tests/ -v --tb=line -q

echo ""
echo "E2E complete."
