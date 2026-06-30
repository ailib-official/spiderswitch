#!/usr/bin/env bash
# Build release artifacts: wheel + pro-pack zip
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")"
DIST="$ROOT/dist"
PRO="$ROOT/packaging/spiderswitch-pro"
OUT="$DIST/spiderswitch-pro-${VERSION}.zip"

mkdir -p "$DIST"

echo "==> Building wheel (spiderswitch ${VERSION})"
if [[ -x "$ROOT/.venv/bin/pip" ]]; then
  "$ROOT/.venv/bin/pip" install -q build 2>/dev/null && \
    "$ROOT/.venv/bin/python" -m build -o "$DIST" 2>/dev/null || \
    echo "Wheel build skipped (install build in .venv if needed)"
else
  echo "Wheel build skipped (no .venv — run: python3 -m venv .venv && .venv/bin/pip install build)"
fi

echo "==> Packaging Pro pack"
mkdir -p "$DIST"
rm -f "$OUT"
(
  cd "$PRO/.."
  zip -r "$OUT" spiderswitch-pro -x "*.git*"
)

echo ""
echo "Artifacts:"
ls -lh "$DIST"/spiderswitch-*.whl 2>/dev/null || ls -lh "$DIST"/*.whl 2>/dev/null || true
ls -lh "$OUT"
echo ""
echo "E2E: bash scripts/e2e_smart_routing.sh"
echo "Install local: pip install -e . && SPIDERSWITCH_INSTALL_SOURCE=$ROOT packaging/spiderswitch-pro/install.sh"
