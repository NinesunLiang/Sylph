#!/usr/bin/env bash
# oracle-gate.sh — SessionStart — 检测 Agent 独立进程能力是否可用
# 哲学 #6 (0信任): Oracle 审核依赖独立 agent 进程，无此能力则 Oracle 形同虚设
# 检查: claude --version | gh CLI | delegate_task 能力

source "$(dirname "$0")/harness_config.sh"
hc_enabled "oracle_gate" || { echo '{"continue": true}'; exit 0; }

# 检测是否有 Agent 独立进程能力
CAN_AGENT=false

# Claude Code CLI (OMC 的物理载体)
if command -v claude &>/dev/null; then
    CAN_AGENT=true
fi

# OpenCode CLI (OMO 的物理载体)
if command -v opencode &>/dev/null; then
    CAN_AGENT=true
fi

# GH CLI (至少能做 Code Review)
if command -v gh &>/dev/null; then
    CAN_AGENT=true
fi

if ! $CAN_AGENT; then
    printf '{"continue":true,"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[oracle-gate] ⚠️ 未检测到 Agent 独立进程能力 (claude/opencode/gh CLI)。Oracle 双法官审核将降级为本地 prompt 审核，物理隔离打折扣。"}}\n'
else
    echo '{"continue": true}'
fi
exit 0
