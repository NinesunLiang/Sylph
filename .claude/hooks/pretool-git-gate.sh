#!/usr/bin/env bash
# pretool-git-gate.sh — PreToolUse:Bash — Git 提交前 pre-commit 检查门禁（铁律 #4 物化）
# Role: 检测 git commit 前是否有 pre-commit 检查。非 git commit 命令透传。
# 铁律 #4 (Git 门禁): 编译 → 功能 → 报告 → Boss 批准 → 提交，跳步=回滚
# 哲学 #3 (先守护): 确保代码进入 git 历史前经过质量门禁

source "$(dirname "$0")/harness_config.sh"
hc_enabled "pretool_git_gate" || { echo '{"continue": true}'; exit 0; }
source "$(dirname "$0")/agentic-ui.sh"
set -f
INPUT=$(cat)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"

# ── 提取命令 ──
COMMAND=""
if command -v jq &>/dev/null; then
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // .args.command // empty' 2>/dev/null)
fi
[ -z "$COMMAND" ] && { echo '{"continue": true}'; exit 0; }

# ── 模式检测: ghost/goal 降级为记录跳过 ──
MODE=$(is_mode_active "$STATE_DIR")
if [ "$MODE" != "normal" ]; then
    echo "[pretool-git-gate] ${MODE} mode — git commit pre-commit 检查已记录（模式降级，不阻断）" >&2
    flywheel_event "pretool_git_gate" "mode_skip" "P2" || true
    echo '{"continue": true}'
    exit 0
fi

# ── 非 git commit 命令透传 ──
if ! echo "$COMMAND" | grep -qE '^git\s+commit\b'; then
    echo '{"continue": true}'
    exit 0
fi

# ── git commit --dry-run / --help 透传 ──
if echo "$COMMAND" | grep -qE 'git\s+commit\s+--(dry-run|help)'; then
    echo '{"continue": true}'
    exit 0
fi

# ── 检查 .pre-commit-verified 标记文件（5分钟内有效）──
MARKER_FILE="$PROJECT_ROOT/.pre-commit-verified"
MARKER_VALID=false

if [ -f "$MARKER_FILE" ]; then
    MARKER_MTIME=$(stat -f %m "$MARKER_FILE" 2>/dev/null || stat -c %Y "$MARKER_FILE" 2>/dev/null)
    NOW_EPOCH=$(date +%s 2>/dev/null || echo 0)
    if [ -n "$MARKER_MTIME" ] && [ -n "$NOW_EPOCH" ] && [ "$NOW_EPOCH" -gt 0 ]; then
        AGE=$(( NOW_EPOCH - MARKER_MTIME ))
        if [ "$AGE" -le 300 ]; then
            MARKER_VALID=true
        fi
    fi
fi

if [ "$MARKER_VALID" = true ]; then
    echo "[pretool-git-gate] pre-commit 已验证（标记文件 5 分钟内有效）" >&2
    flywheel_event "pretool_git_gate" "pre_commit_verified" "P3" || true
    echo '{"continue": true}'
    exit 0
fi

# ── 无有效标记 → 阻断并输出铁律 #4 提示 ──
cat >&2 <<'BLOCKMSG'

⛔ [Git Gate] pre-commit 检查未通过 — 铁律 #4 门禁阻断

铁律 #4 (Git 门禁): 编译 → 功能 → 报告 → Boss 批准 → 提交，跳步=回滚

检测到 git commit 前缺少有效的 pre-commit 验证标记。
请先执行 pre-commit 检查（如 /lx-pre-commit），通过后系统将自动
生成 .pre-commit-verified 标记文件，5 分钟内 git commit 放行。

  ✓ 运行 /lx-pre-commit 完成质量门禁
  ✓ 或在终端执行 git commit（绕过 AI 门禁）

BLOCKMSG

flywheel_event "pretool_git_gate" "blocked_no_pre_commit" "P1" || true
printf '[Git Gate] 铁律#4 门禁阻断: git commit 前缺少 pre-commit 验证标记。请先运行 /lx-pre-commit 完成质量门禁。' | hc_emit_hook_json "PreToolUse" "false"
exit 2
