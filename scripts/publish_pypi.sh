#!/usr/bin/env bash
# Publish spiderswitch to PyPI (manual fallback when CI secrets are unavailable).
#
# Prerequisites:
#   pip install build twine
#   export TWINE_USERNAME=__token__
#   export TWINE_PASSWORD=pypi-...   # PyPI API token with upload scope
#
# Usage:
#   bash scripts/publish_pypi.sh           # build + upload wheel + sdist
#   bash scripts/publish_pypi.sh --check   # build + twine check only

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CHECK_ONLY=0
if [[ "${1:-}" == "--check" ]]; then
  CHECK_ONLY=1
fi

VERSION="$(grep -E '^version[[:space:]]*=' pyproject.toml | head -1 | sed -E 's/.*"([^"]+)".*/\1/')"
echo "==> Building spiderswitch ${VERSION}"
python3 -m pip install -q build twine
rm -rf dist/
python3 -m build
twine check dist/spiderswitch-"${VERSION}"*

if [[ "$CHECK_ONLY" -eq 1 ]]; then
  echo "==> Check-only mode; artifacts in dist/"
  ls -lh dist/
  exit 0
fi

if [[ -z "${TWINE_PASSWORD:-}" ]]; then
  echo "ERROR: TWINE_PASSWORD not set."
  echo "Create a PyPI API token and run:"
  echo "  export TWINE_USERNAME=__token__"
  echo "  export TWINE_PASSWORD=pypi-..."
  echo "  bash scripts/publish_pypi.sh"
  exit 1
fi

echo "==> Uploading to PyPI"
twine upload dist/spiderswitch-"${VERSION}"* dist/*.tar.gz
echo "==> Done. Verify: pip install spiderswitch==${VERSION}"
