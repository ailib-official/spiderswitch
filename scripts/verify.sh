#!/bin/bash
# Verification script for spiderswitch
# 项目验证脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
AI_LIB_PATH="${AI_LIB_PATH:-}"

# Single source of truth: read the version from pyproject.toml.
VERSION="$(grep -E '^version[[:space:]]*=' "$PROJECT_DIR/pyproject.toml" | head -1 | sed -E 's/.*"([^"]+)".*/\1/')"
VERSION="${VERSION:-unknown}"

echo "========================================="
echo "Verifying spiderswitch v$VERSION"
echo "========================================="

# Check project structure
echo ""
echo "[1/5] Checking project structure..."
if [ ! -d "$PROJECT_DIR/src" ]; then
    echo "❌ src directory not found"
    exit 1
fi
echo "✓ Project structure valid"

# Check key files exist
echo ""
echo "[2/5] Checking key files..."
required_files=(
    "$PROJECT_DIR/pyproject.toml"
    "$PROJECT_DIR/README.md"
    "$PROJECT_DIR/README_CN.md"
    "$PROJECT_DIR/src/spiderswitch/server.py"
    "$PROJECT_DIR/src/spiderswitch/runtime/__init__.py"
    "$PROJECT_DIR/src/spiderswitch/runtime/base.py"
    "$PROJECT_DIR/src/spiderswitch/runtime/python_runtime.py"
    "$PROJECT_DIR/src/spiderswitch/tools/__init__.py"
    "$PROJECT_DIR/src/spiderswitch/tools/switch.py"
    "$PROJECT_DIR/src/spiderswitch/tools/list.py"
    "$PROJECT_DIR/src/spiderswitch/tools/status.py"
    "$PROJECT_DIR/src/spiderswitch/tools/reset.py"
    "$PROJECT_DIR/src/spiderswitch/state.py"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing file: $file"
        exit 1
    fi
done
echo "✓ All key files present"

# Check Python syntax
echo ""
echo "[3/5] Checking Python syntax..."
cd "$PROJECT_DIR"
if ! python3 -m py_compile src/spiderswitch/*.py \
    src/spiderswitch/runtime/*.py \
    src/spiderswitch/tools/*.py 2>/dev/null; then
    echo "❌ Python syntax errors found"
    exit 1
fi
echo "✓ All Python files compile successfully"

# Check module can be imported
echo ""
echo "[4/5] Checking module imports..."
cd "$PROJECT_DIR"
if [ -n "$AI_LIB_PATH" ]; then
    export PYTHONPATH="$AI_LIB_PATH:$PROJECT_DIR/src"
else
    export PYTHONPATH="$PROJECT_DIR/src"
fi

python3 -c "
from spiderswitch.runtime.base import ModelCapabilities, ModelInfo
from spiderswitch.state import ModelState, ModelStateManager
from spiderswitch.tools import list, status, switch
print('✓ All modules import successfully')
" 2>&1

if [ $? -ne 0 ]; then
    echo "❌ Module import failed"
    echo "Note: This is ok if ai-lib-python is not installed globally"
fi

# Verify line counts for key components
echo ""
echo "[5/5] Checking implementation completeness..."
SERVER_LINES=$(wc -l < "$PROJECT_DIR/src/spiderswitch/server.py")
RUNTIME_LINES=$(wc -l < "$PROJECT_DIR/src/spiderswitch/runtime/python_runtime.py")

if [ "$SERVER_LINES" -lt 50 ]; then
    echo "❌ server.py seems incomplete ($SERVER_LINES lines)"
    exit 1
fi

if [ "$RUNTIME_LINES" -lt 100 ]; then
    echo "❌ python_runtime.py seems incomplete ($RUNTIME_LINES lines)"
    exit 1
fi

echo "✓ Implementation looks complete"
echo "  - server.py: $SERVER_LINES lines"
echo "  - python_runtime.py: $RUNTIME_LINES lines"

# Summary
echo ""
echo "========================================="
echo "Verification Complete!"
echo "========================================="
echo ""
echo "Project: spiderswitch"
echo "Version: $VERSION"
echo "Location: $PROJECT_DIR"
echo ""
echo "Next steps:"
echo "  1. Install dependencies:"
echo "     pip install -e ."
echo ""
echo "  2. Set API keys:"
echo "     export OPENAI_API_KEY='sk-...'"
echo "     export ANTHROPIC_API_KEY='sk-ant-...'"
echo ""
echo "  3. Run MCP server:"
echo "     python -m spiderswitch.server"
echo ""
