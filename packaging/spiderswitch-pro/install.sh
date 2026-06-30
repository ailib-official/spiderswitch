#!/usr/bin/env bash
# SpiderSwitch Pro — install for Cursor (BYOK)
set -euo pipefail

PACK_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-$HOME/.cursor/mcp.spiderswitch.json}"
SOURCE="${SPIDERSWITCH_INSTALL_SOURCE:-}"

echo "[spiderswitch-pro] pack=$PACK_DIR"

if [[ -n "$SOURCE" && -d "$SOURCE" ]]; then
  pip install -q -e "$SOURCE"
elif [[ -d "$PACK_DIR/../../.." && -f "$PACK_DIR/../../../pyproject.toml" ]]; then
  pip install -q -e "$PACK_DIR/../../.."
else
  pip install -q "spiderswitch>=0.5.0" 2>/dev/null || \
    pip install -q "git+https://github.com/ailib-official/spiderswitch.git"
fi

spiderswitch init --client cursor --output "$TARGET" --force

mkdir -p "$HOME/.spiderswitch/routing"
cp "$PACK_DIR/routing/"*.yaml "$HOME/.spiderswitch/routing/"

if [[ ! -d "$HOME/.spiderswitch/ai-protocol" ]]; then
  echo "[spiderswitch-pro] cloning ai-protocol..."
  git clone --depth 1 https://github.com/ailib-official/ai-protocol "$HOME/.spiderswitch/ai-protocol" || true
fi

echo ""
echo "✓ MCP config: $TARGET"
echo "✓ Routing policies: ~/.spiderswitch/routing/"
echo "✓ Next: export OPENAI_API_KEY / DEEPSEEK_API_KEY, restart Cursor"
echo "✓ Test: spiderswitch doctor --json"
