#!/usr/bin/env bash
# Build plugin-market release bundle for spiderswitch.
# 打包 spiderswitch 插件市场发布资产。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$PROJECT_DIR/dist/plugin-market"

PYTHON_BIN="python3"
if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
fi

mkdir -p "$OUT_DIR"
rm -f "$OUT_DIR"/manifest.json "$OUT_DIR"/README.md "$OUT_DIR"/install_one_click.sh "$OUT_DIR"/*.whl

VERSION="$(grep -E '^version[[:space:]]*=' "$PROJECT_DIR/pyproject.toml" | head -1 | sed -E 's/.*"([^"]+)".*/\1/')"

cp "$PROJECT_DIR/packaging/plugin-market/manifest.json" "$OUT_DIR/manifest.json"
cp "$PROJECT_DIR/packaging/plugin-market/README.md" "$OUT_DIR/README.md"
cp "$PROJECT_DIR/scripts/install_one_click.sh" "$OUT_DIR/install_one_click.sh"
cp "$PROJECT_DIR/scripts/install_offline.sh" "$OUT_DIR/install_offline.sh"

if "$PYTHON_BIN" -m build --version >/dev/null 2>&1; then
  "$PYTHON_BIN" -m build --wheel
  cp "$PROJECT_DIR/dist/spiderswitch-${VERSION}-py3-none-any.whl" "$OUT_DIR/" 2>/dev/null || \
    cp "$PROJECT_DIR"/dist/spiderswitch-*.whl "$OUT_DIR/" 2>/dev/null || true
else
  echo "[warn] python build module not found; skipping wheel build."
  echo "       Install it via: $PYTHON_BIN -m pip install build"
fi

echo "[spiderswitch] plugin-market bundle created: $OUT_DIR"
