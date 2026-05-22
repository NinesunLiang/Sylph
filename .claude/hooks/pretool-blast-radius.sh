#!/usr/bin/env bash
# pretool-blast-radius.sh — PreToolUse:Bash — 全局破坏性命令拦截 (DG-101)
# Role: 检测 git checkout . / rm -rf 等全量操作，提醒改用选择性路径
# 哲学 #3 (先守护): 全局操作前先评估 blast radius
# 哲学 #1 (less is more): 只提醒不阻断 (exit 0)，紧急修复不受阻
# DG-100 事故: git checkout HEAD -- . 恢复所有文件 → 丢失未提交改进
# DG-101: 本机制物化——拦截全量操作，提示选择性替代方案

source "$(dirname "$0")/harness_config.sh"
hc_enabled "blast_radius" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat 2>/dev/null || echo "")
COMMAND=""
if command -v jq &>/dev/null && [ -n "$INPUT" ]; then
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
fi
[ -z "$COMMAND" ] && { echo '{"continue": true}'; exit 0; }

# ═══ 硬阻断：git checkout . (DG-100 事故根因) ═══
# 1a: git checkout . (全量回退 — DG-100 根因)
if echo "$COMMAND" | grep -qE 'git checkout (HEAD )?(-- )?\.(\s|;|$|\||&)'; then
    echo "[blast-radius] 🔴 硬阻断: 'git checkout .' 会全量恢复所有文件。" >&2
    echo "[blast-radius]    DG-100: 本操作曾在 2026-05-22 导致 71 文件静默退化。" >&2
    echo "[blast-radius]    正确做法: git checkout HEAD -- path/to/specific/file" >&2
    flywheel_event "blast_radius" "blocked_checkout_dot" "P0" "cmd=$(echo "$COMMAND" | cut -c1-80)" || true
    echo '{"continue": false, "reason": "git checkout . 全量回退已被 blast-radius 硬阻断 (DG-100)。请改用选择性路径恢复。"}'
    exit 0
fi

# 1b: git reset --hard (全量回退变体 — Oracle 发现)
if echo "$COMMAND" | grep -qE 'git reset --hard(\s|;|$|\||&)'; then
    echo "[blast-radius] 🔴 硬阻断: 'git reset --hard' 会丢弃所有未提交修改。" >&2
    echo "[blast-radius]    DG-100: 此操作等同于 'git checkout .' 的全量回退效果。" >&2
    flywheel_event "blast_radius" "blocked_reset_hard" "P0" "cmd=$(echo "$COMMAND" | cut -c1-80)" || true
    echo '{"continue": false, "reason": "git reset --hard 全量回退已被 blast-radius 硬阻断 (DG-100)。"}'
    exit 0
fi

WARN=""

# 2. git checkout -- 无具体文件路径
if echo "$COMMAND" | grep -qE 'git checkout --($| )' && ! echo "$COMMAND" | grep -q '/'; then
    WARN="[blast-radius] ⚠️  'git checkout --' 未指定具体文件路径，可能误恢复。"
fi

# 3. git add -A / git add . (全量暂存)
if [ -z "$WARN" ] && echo "$COMMAND" | grep -qE 'git add (-A|--all|\.)'; then
    WARN="[blast-radius] ⚠️  'git add -A' 会暂存所有文件。确认无敏感文件混入 (检查 .gitignore)。"
fi

# 4. package-release.sh 运行前提醒三源检查
if [ -z "$WARN" ] && echo "$COMMAND" | grep -qE 'package-release\.sh'; then
    WARN="[blast-radius] 📦 打包前建议先跑: bash .claude/scripts/audit-hooks.sh --check-source-mirror"
fi

if [ -n "$WARN" ]; then
    echo "$WARN" >&2
    flywheel_event "blast_radius" "warned" "P3" "cmd=$(echo "$COMMAND" | cut -c1-80)" || true
fi

echo '{"continue": true}'
exit 0
