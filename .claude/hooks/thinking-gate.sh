#!/usr/bin/env bash
# thinking-gate.sh — Thinking Content 上下文门禁
# 职责: 检查已经发生的上下文污染，记录 thinking 泄露事件
# 用法: 作为 .* matcher 的 UserPromptSubmit hook
#
# Carror OS 哲学: #1(less) > #6(0信任) > #4(验证)
#
# 注意:
# - 此 hook 不阻断，只记录和提醒
# - 真正的 thinking 过滤在平台层实现:
#   - Claude Code: Anthropic API 原生已隔离
#   - OpenCode: transform.ts outbound 剥离
# - 此 hook 是从治理层兜底检测

set -uo pipefail

# ── 配置 ──
readonly THINKING_FLYWELL_TAG="thinking-gate"
readonly EVIDENCE_LOG="$HOME/.hermes/cron/output/thinking-leak-events.json"

# ── 读取用户消息 ──
PROMPT=""
if [ -t 0 ]; then
    PROMPT="${1:-}"
else
    PROMPT=$(cat)
fi

# ── 检测 thinking 泄漏信号 ──
LEAK_TYPE=""
LEAK_EVIDENCE=""

# H1: 用户消息中包含 reasoning_content 或 thinking 残留（用户手动复制）
if echo "$PROMPT" | grep -qP '(reasoning_content|"thinking"\s*:\s*\{|type.*?thinking)'; then
    LEAK_TYPE="H1-user-copy"
    LEAK_EVIDENCE="用户消息中包含 thinking 字段结构"
fi

# H2: 检测上下文 token 增长率异常（通过 token_writer 数据）
# 此检测由 context-guard 负责，不再重复

# ── 如果有泄漏，记录并提醒 ──
if [ -n "$LEAK_TYPE" ]; then
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    LEAK_EVENT="{\"ts\":\"$TIMESTAMP\",\"type\":\"$LEAK_TYPE\",\"evidence\":\"$LEAK_EVIDENCE\"}"

    # 记录 to flywheel
    echo "[$THINKING_FLYWELL_TAG] $LEAK_EVENT" >&2
    flywheel_event "$THINKING_FLYWELL_TAG" "leak_detected" "P1"

    # 追加到证据日志
    mkdir -p "$(dirname "$EVIDENCE_LOG")"
    echo "$LEAK_EVENT" >> "$EVIDENCE_LOG" 2>/dev/null || true

    # 2>&1 输出提醒到 AI 上下文
    echo "[thinking-gate] ⚠️ 检测到 thinking 内容残留 ($LEAK_TYPE)" >&2
    echo "[thinking-gate] 提示: 如果使用 OpenCode，请确保 transform.ts 已剥离 reasoning_content 字段" >&2
fi

# ── 始终通过（永不阻断） ──
printf '%s' "$PROMPT"
exit 0
