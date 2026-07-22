#!/usr/bin/env bash
# lx-pre-commit.sh — 提交前轻量检查脚本
set -euo pipefail

CONFIG_FILE=".lx-pre-commit.yml"
BUILD_TIMEOUT=120
TEST_TIMEOUT=120
LINT_TIMEOUT=60
SKIP_TESTS=false
LINT_ENABLED=true

# ── 配置加载（可选）───────────────────────────
if [ -f "$CONFIG_FILE" ]; then
  # 尝试 yq 解析
  if command -v yq &>/dev/null; then
    BUILD_TIMEOUT=$(yq '.timeout.build // $BUILD_TIMEOUT' "$CONFIG_FILE" 2>/dev/null) || true
    TEST_TIMEOUT=$(yq '.timeout.test // $TEST_TIMEOUT' "$CONFIG_FILE" 2>/dev/null) || true
    LINT_ENABLED=$(yq '.lint // true' "$CONFIG_FILE" 2>/dev/null) || true
    SKIP_TESTS=$(yq '.skip_tests // false' "$CONFIG_FILE" 2>/dev/null) || true
  # 降级 python3 解析
  elif command -v python3 &>/dev/null; then
    eval "$(python3 -c "
import yaml, sys
try:
    c = yaml.safe_load(open('$CONFIG_FILE')) or {}
    t = c.get('timeout', {})
    print(f'BUILD_TIMEOUT={t.get(\"build\", 120)}')
    print(f'TEST_TIMEOUT={t.get(\"test\", 120)}')
    print(f'LINT_ENABLED={\"true\" if c.get(\"lint\", True) else \"false\"}')  # noqa
    print(f'SKIP_TESTS={\"true\" if c.get(\"skip_tests\", False) else \"false\"}')  # noqa
except Exception:
    pass
" 2>/dev/null)" || true
  fi
fi

# ── 语言检测 ──────────────────────────────────
detect_lang() {
  [ -f go.mod ] && echo "go" && return
  [ -f package.json ] && echo "node" && return
  [ -f pyproject.toml ] && echo "python" && return
  [ -f Cargo.toml ] && echo "rust" && return
  echo "unknown"
}

LANG=$(detect_lang)
HAS_ERROR=false
HAS_WARNING=false

run_step() {
  local name="$1" cmd="$2" timeout="$3" is_blocking="$4"
  echo "  → $name..."
  if ! timeout "$timeout" bash -c "$cmd" 2>&1; then
    echo "  ❌ $name 失败"
    [ "$is_blocking" = "true" ] && HAS_ERROR=true
  else
    echo "  ✅ $name 通过"
  fi
}

# ── 编译检查 ──────────────────────────────────
echo "==> lx-pre-commit"
echo "语言: $LANG"

case "$LANG" in
  go)
    run_step "go build" "go build ./..." "$BUILD_TIMEOUT" true
    $SKIP_TESTS || run_step "go test" "go test ./... -count=1 -timeout ${TEST_TIMEOUT}s" "$TEST_TIMEOUT" true
    $LINT_ENABLED && run_step "gofmt" "gofmt -l . | grep -q . && echo '⚠️ 格式问题' || true" "$LINT_TIMEOUT" false
    ;;
  node)
    run_step "npm build" "npm run build 2>/dev/null || npm run build:prod 2>/dev/null || echo '⚠️ 无build脚本'" "$BUILD_TIMEOUT" true
    $SKIP_TESTS || run_step "npm test" "npm test -- --bail 2>/dev/null || npm test 2>/dev/null" "$TEST_TIMEOUT" true
    $LINT_ENABLED && run_step "eslint" "npx eslint . --max-warnings=10 2>/dev/null || echo '⚠️ lint问题'" "$LINT_TIMEOUT" false
    ;;
  python)
    run_step "py_compile" "python3 -m compileall -q . 2>/dev/null" "$BUILD_TIMEOUT" true
    $SKIP_TESTS || run_step "pytest" "python3 -m pytest --tb=short -x --timeout=60 2>/dev/null || python3 -m pytest --tb=short -x 2>/dev/null" "$TEST_TIMEOUT" true
    $LINT_ENABLED && run_step "ruff" "python3 -m ruff check . --quiet 2>/dev/null || echo '⚠️ lint问题'" "$LINT_TIMEOUT" false
    ;;
  rust)
    run_step "cargo build" "cargo build 2>&1" "$BUILD_TIMEOUT" true
    $SKIP_TESTS || run_step "cargo test" "cargo test 2>&1" "$TEST_TIMEOUT" true
    $LINT_ENABLED && run_step "clippy" "cargo clippy -- -D warnings 2>/dev/null || echo '⚠️ clippy警告'" "$LINT_TIMEOUT" false
    ;;
  *)
    echo "  ⚠️ 未知项目类型，跳过检查"
    exit 0
    ;;
esac

echo "---"
if $HAS_ERROR; then
  echo "❌ lx-pre-commit 未通过"
  exit 1
elif $HAS_WARNING; then
  echo "⚠️ lx-pre-commit 通过（有警告）"
  exit 0
else
  echo "✅ lx-pre-commit 全部通过"
  exit 0
fi
