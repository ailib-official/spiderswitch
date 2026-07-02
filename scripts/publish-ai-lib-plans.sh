#!/usr/bin/env bash
# Publish scripts/publish-bundle/ai-lib-plans/ to github.com/ailib-official/ai-lib-plans
#
# Usage:
#   gh repo create ailib-official/ai-lib-plans --private   # first time only
#   bash scripts/publish-ai-lib-plans.sh --from-bundle
#
# Or from an existing clone of ai-lib-plans:
#   bash scripts/publish-ai-lib-plans.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE="$ROOT/scripts/publish-bundle/ai-lib-plans"
ORG_REPO="git@github.com:ailib-official/ai-lib-plans.git"
HTTPS_REPO="https://github.com/ailib-official/ai-lib-plans.git"
WORKDIR="${AI_LIB_PLANS_WORKDIR:-/tmp/ai-lib-plans-publish}"

FROM_BUNDLE=0
if [[ "${1:-}" == "--from-bundle" ]]; then
  FROM_BUNDLE=1
fi

if [[ ! -d "$BUNDLE" ]]; then
  echo "ERROR: bundle not found at $BUNDLE"
  exit 1
fi

echo "==> Preparing publish workdir: $WORKDIR"
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"

if git ls-remote "$HTTPS_REPO" HEAD &>/dev/null; then
  echo "==> Cloning existing ai-lib-plans"
  git clone "$HTTPS_REPO" "$WORKDIR"
else
  echo "==> Initializing new ai-lib-plans repo (remote must be created first)"
  echo "    Run: gh repo create ailib-official/ai-lib-plans --private"
  git init "$WORKDIR"
  git -C "$WORKDIR" branch -M main
  git -C "$WORKDIR" remote add origin "$HTTPS_REPO" 2>/dev/null || true
fi

echo "==> Copying bundle (excludes templates/ from root; templates stay in templates/)"
rsync -a --delete \
  --exclude 'templates/' \
  "$BUNDLE/" "$WORKDIR/"
mkdir -p "$WORKDIR/templates"
rsync -a "$BUNDLE/templates/" "$WORKDIR/templates/"

cd "$WORKDIR"
git add -A
if git diff --cached --quiet; then
  echo "==> No changes to publish"
  exit 0
fi

git commit -m "chore: publish product line charter from spiderswitch bundle

Canonical org repo for portfolio planning. Product repos use PORTFOLIO.md pointer only."

git push -u origin main
echo "==> Published to $HTTPS_REPO"
echo "==> Next: copy templates/PORTFOLIO.md to each product repo; set org .github PR template"
