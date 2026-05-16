#!/usr/bin/env bash
# meta-oracle-trigger.sh — PostToolUse:.* — Meta-Oracle 最后守门员自动触发（G1-G4）
# Role: 检测 G1-G4 触发条件，提醒 AI 执行 Meta-Oracle 最高级独立验证
# 哲学 #4(没验证=没做) + #6(0信任): Oracle 的结论 + 架构决策 + PRD方案 + Release 都需最后守门
#
# 4 个触发点:
#   G1 - 架构决策终审: 检测架构讨论输出中的关键决策
#   G2 - PRD/方案最后一步: 检测 PRD 生命周期完成信号
#   G3 - Oracle ACCEPT + 高分 (≥8.5): 原有逻辑，保留
#   G4 - Release 门禁: 由 package-release.sh 显式调用，hook 层检测 Bash 中的 release 命令
#
# 优先级: G1 > G2 > G4 > G3。同一任务最多触发 1 次。
# 软门禁: 给出裁决和建议，AI 可在明确理由下覆写。

source "$(dirname "$0")/harness_config.sh"
hc_enabled "meta_oracle_trigger" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat)

# 提取工具名和输出内容
if command -v jq &>/dev/null; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
    TOOL_OUTPUT=$(echo "$INPUT" | jq -r '.tool_response // .tool_response.stdout // .tool_response.content // empty' 2>/dev/null)
    AGENT_TEXT=$(echo "$INPUT" | jq -r '.tool_response.message // .tool_response.text // empty' 2>/dev/null)
    COMBINED="${TOOL_OUTPUT} ${AGENT_TEXT}"
else
    TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null)
    COMBINED=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); tr=d.get('tool_response',{}); print(tr.get('stdout',tr.get('content',tr.get('message',''))))" 2>/dev/null)
fi

[ -z "$COMBINED" ] && { echo '{"continue": true}'; exit 0; }

# ── 触发检测（按优先级 G1 > G2 > G4 > G3）──
TRIGGERED=false
TRIGGER_REASON=""
TRIGGER_PRIORITY=""

# G1: 架构决策终审 — 检测架构讨论中的关键决策信号
# 触发信号: 架构文档生成 + Oracle ACCEPT + 涉及多子系统 + 不可逆标记
# 权威定义见 AGENTS.md: ≥2 子系统 + 不可逆的架构变更
if [ "$TRIGGERED" = false ]; then
    # 第一步: 检测架构决策语境
    ARCH_CTX=$(echo "$COMBINED" | grep -iE '(架构|architecture|子系统|subsystem|domain.*split|功能域).*(决策|decision|终审|final|不可逆|irreversible)' 2>/dev/null)
    if [ -n "$ARCH_CTX" ]; then
        # 第二步: 必须有 Oracle ACCEPT（确保是通过了 Oracle 审核的架构决策）
        if echo "$COMBINED" | grep -qE '(Oracle|oracle).*(ACCEPT|APPROVED|通过)' 2>/dev/null; then
            # 第三步: 检测不可逆标记或多子系统信号（减少误触发）
            if echo "$COMBINED" | grep -qiE '不可逆|irreversible|[3-9]\s*(个|子系|功能域|domain|subsystem)' 2>/dev/null; then
                TRIGGERED=true
                TRIGGER_PRIORITY="G1"
                TRIGGER_REASON="G1 架构决策终审 — ≥2 子系统 + 不可逆变更 + Oracle 已 ACCEPT"
            fi
        fi
    fi
fi

# G2: PRD/方案最后一步 — 检测 PRD 生命周期完成信号
# 触发信号: lx-oma-orch advance → dev 阶段 / PRD pipeline 完成 + Oracle ACCEPT
if [ "$TRIGGERED" = false ]; then
    if echo "$COMBINED" | grep -qE '(pipeline|管线|PRD|prd).*(完成|complete|done|final|最后|终审)' 2>/dev/null; then
        if echo "$COMBINED" | grep -qE '(Oracle|oracle).*(ACCEPT|APPROVED|通过)' 2>/dev/null; then
            TRIGGERED=true
            TRIGGER_PRIORITY="G2"
            TRIGGER_REASON="G2 PRD/方案最后一步 — PRD 生命周期完成 + Oracle 已 ACCEPT"
        fi
    fi
fi

# G4: Release 门禁 — 检测 package-release.sh 调用
# 注意: G4 主要由 package-release.sh 显式调用 meta-oracle-review.sh，hook 层做补充检测
if [ "$TRIGGERED" = false ]; then
    if echo "$COMBINED" | grep -qE 'package-release\.sh|release.*(打包|package|发布)' 2>/dev/null; then
        TRIGGERED=true
        TRIGGER_PRIORITY="G4"
        TRIGGER_REASON="G4 Release 门禁 — package-release.sh 执行前安全检查"
    fi
fi

# G3: Oracle ACCEPT / 高分 (≥8.5) — 原有逻辑，最低优先级
if [ "$TRIGGERED" = false ]; then
    # 检测 Oracle ACCEPT/APPROVED
    if echo "$COMBINED" | grep -qE '(Oracle|oracle).*(ACCEPT|APPROVED|approve|accept)' 2>/dev/null; then
        TRIGGERED=true
        TRIGGER_PRIORITY="G3"
        TRIGGER_REASON="G3 Oracle ACCEPT/APPROVED 裁决检测"
    fi
fi

if [ "$TRIGGERED" = false ]; then
    HIGH_SCORE=$(echo "$COMBINED" | grep -oE '(score|Score|评分|得分)[:： ]*[0-9]+\.[0-9]+' 2>/dev/null | head -3)
    if [ -n "$HIGH_SCORE" ]; then
        MAX_SCORE=$(echo "$HIGH_SCORE" | grep -oE '[0-9]+\.[0-9]+' | sort -rn | head -1)
        if [ -n "$MAX_SCORE" ] && python3 -c "exit(0 if float('$MAX_SCORE') >= 8.5 else 1)" 2>/dev/null; then
            TRIGGERED=true
            TRIGGER_PRIORITY="G3"
            TRIGGER_REASON="G3 Oracle 高分评分 (${MAX_SCORE} ≥ 8.5)"
        fi
    fi
fi

if [ "$TRIGGERED" = false ]; then
    OVERALL_SCORE=$(echo "$COMBINED" | grep -oE '(综合|总分|平均|overall)[:： ]*[0-9]+\.[0-9]+' 2>/dev/null | head -3)
    if [ -n "$OVERALL_SCORE" ]; then
        MAX_OS=$(echo "$OVERALL_SCORE" | grep -oE '[0-9]+\.[0-9]+' | sort -rn | head -1)
        if [ -n "$MAX_OS" ] && python3 -c "exit(0 if float('$MAX_OS') >= 8.5 else 1)" 2>/dev/null; then
            TRIGGERED=true
            TRIGGER_PRIORITY="G3"
            TRIGGER_REASON="G3 综合评分 ≥ 8.5 (${MAX_OS})"
        fi
    fi
fi

# 输出 Meta-Oracle 触发 — 软门禁: 提醒 AI 执行最高级独立审查
if [ "$TRIGGERED" = true ]; then
    printf '{"continue":true,"hookSpecificOutput":{"additionalContext":"🔍 [Meta-Oracle %s 触发] %s\n→ Meta-Oracle = 最后守门员（核武器级终审），权威高于 Oracle\n→ 软门禁: 给出 ACCEPT/ADVISORY/REJECT 裁决，AI 可在明确理由下覆写\n→ 执行方式: Agent(critic, opus, 独立上下文) — 运行时验证 > 静态检查\n→ 审查脚本: bash .claude/scripts/meta-oracle-review.sh\n→ 裁决留痕: .omc/state/meta-oracle-verdicts.md\n→ 注意: 同一任务最多触发 1 次 Meta-Oracle，请珍惜使用"}}\n' "$TRIGGER_PRIORITY" "$TRIGGER_REASON"
    echo "[meta-oracle] ${TRIGGER_PRIORITY}: ${TRIGGER_REASON} — Meta-Oracle 最后守门提醒已注入" >&2
    exit 0
fi

echo '{"continue": true}'
exit 0
