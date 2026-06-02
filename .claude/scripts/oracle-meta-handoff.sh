#!/usr/bin/env bash
# oracle-meta-handoff.sh — Oracle → Meta-Oracle 交接文档生成器
# Role: Oracle ACCEPT 后生成交接文档，中断执行，让人参与选择
#
# 非无人模式流程:
#   1. Oracle ACCEPT → 生成交接文档 .omc/state/oracle-handoff-*.md
#   2. 中断执行，展示交接文档给用户
#   3. 用户选择: 本终端继续 / 其他终端不同模型 / 跳过
#
# 无人模式(goal/ghost): 不中断，自动记录后继续

source "$(dirname "$0")/../hooks/harness_config.sh"
set -f

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
PLANS_DIR="$PROJECT_ROOT/.omc/plans"
MODE=$(is_mode_active "$STATE_DIR" 2>/dev/null || echo "normal")

TODAY=$(date +%Y-%m-%d)
NOW=$(date +%Y%m%d-%H%M%S)
# 固定路径: .omc/plans/{date}/{topic}.md
HANDOFF_DIR="$PLANS_DIR/$TODAY"

# ─────────────────────────────────────────────
# 生成交接文档
# ─────────────────────────────────────────────
generate_handoff() {
    local oracle_verdict="$1"
    local review_target="$2"
    local review_type="$3"

    # 从审核类型生成 topic 目录名（保留中文，去掉特殊字符）
    local topic
    topic=$(echo "$review_type" | sed 's/[\/:.*"<>|]//g' | head -c 40)
    [ -z "$topic" ] && topic="oracle-meta-handoff"

    # 固定路径: .omc/plans/{date}/{topic}/v{version}.md
    local topic_dir="$HANDOFF_DIR/$topic"
    mkdir -p "$topic_dir"

    # 自动检测版本号：用 Python 查找 topic_dir 中已有的 v{N}.md 文件，取最大版本+1
    local version
    version=$(${PYTHON_BIN:-python3} -c "
import os, glob, re
topic_dir = '$topic_dir'
existing = glob.glob(os.path.join(topic_dir, 'v*.md'))
max_v = 0
for f in existing:
    m = re.search(r'v(\d+)\.md$', os.path.basename(f))
    if m:
        v = int(m.group(1))
        if v > max_v:
            max_v = v
print(max_v + 1)
" 2>/dev/null || echo "1")

    HANDOFF_FILE="$topic_dir/v${version}.md"

    # 读取最新 Oracle 裁决详情
    local oracle_detail=""
    if [ -f "$STATE_DIR/oracle-verdicts.md" ]; then
        oracle_detail=$(tail -20 "$STATE_DIR/oracle-verdicts.md" 2>/dev/null)
    fi

    # 读取审核目标文件内容摘要
    local target_summary=""
    if [ -f "$review_target" ]; then
        target_summary=$(head -30 "$review_target" 2>/dev/null)
    fi

    cat > "$HANDOFF_FILE" << HANDOFFEOF
# Oracle → Meta-Oracle 交接文档

> 生成时间: $(date -u +%Y-%m-%dT%H:%M:%SZ)
> 审核类型: ${review_type}
> 审核目标: ${review_target}

---

## 一、Oracle 裁决结果

\`\`\`
${oracle_verdict}
\`\`\`

### Oracle 审核详情

${oracle_detail}

---

## 二、审核目标摘要

\`\`\`
${target_summary}
\`\`\`

---

## 三、Meta-Oracle 审查要求

Meta-Oracle 是 Carror OS 的最高审查权威，独立于 Oracle。
使用完全不同的审查方法（运行时验证 > 静态检查，对抗性审查 > 合规检查）。

**审查重点**:
1. 运行时验证 > 静态检查 — 检查 smoke test 实际通过率、error-dna 真实频率
2. 设计级盲区检查 — fail-open/fail-closed 设计缺陷、门禁降级、正则覆盖率
3. 对抗性审查 — 刻意假设 Oracle 错误，尝试证伪

---

## 四、请选择执行路径

> 请在下方选择 Meta-Oracle 审查的执行方式：

### [选项 A] 本终端继续
在当前终端使用当前模型（deepseek-v4-pro）执行 Meta-Oracle 审查。
命令:
\`\`\`bash
bash ${SCRIPT_DIR}/meta-oracle-agent-spawn.sh prepare
# 然后 AI 使用 Agent(subagent_type="critic") 拉起独立审查
\`\`\`

### [选项 B] 其他终端 — 不同模型
将本交接文档复制到其他终端，用不同模型执行 Meta-Oracle 审查。
在其他终端中:
\`\`\`bash
# 1. 读取本交接文档了解上下文
cat ${HANDOFF_FILE}

# 2. 运行 Meta-Oracle 审查脚本
bash ${SCRIPT_DIR}/meta-oracle-agent-spawn.sh prepare

# 3. 审查完成后记录裁决
bash ${SCRIPT_DIR}/meta-oracle-agent-spawn.sh record --verdict "<审查结果>"
\`\`\`

### [选项 C] 跳过 Meta-Oracle
信任 Oracle 裁决，跳过 Meta-Oracle 二审。直接继续执行。

---

> 选择后请告知 AI，AI 将根据您的选择执行对应操作。
HANDOFFEOF

    echo "$HANDOFF_FILE"
}

# ─────────────────────────────────────────────
# 展示交接文档（非无人模式）
# ─────────────────────────────────────────────
show_handoff() {
    local handoff_file="$1"

    if [ ! -f "$handoff_file" ]; then
        echo "[oracle-meta-handoff] ERROR: handoff file not found: $handoff_file"
        exit 1
    fi

    # 无人模式：不中断，记录后继续
    if [ "$MODE" != "normal" ]; then
        echo "[oracle-meta-handoff] 自主模式: 跳过人为交接，记录到退出报告" >&2
        flywheel_event "oracle_meta_handoff" "autonomous_skip" "P2" "mode=$MODE" || true
        echo '{"continue": true}'
        exit 0
    fi

    # 非无人模式：展示交接文档，中断执行
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  🔄 Oracle → Meta-Oracle 交接                              ║"
    echo "║  Oracle 已给出 ACCEPT 裁决，需要 Meta-Oracle 独立二审     ║"
    echo "║                                                           ║"
    echo "║  交接文档已生成: ${handoff_file}  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "请选择 Meta-Oracle 审查的执行路径:"
    echo ""
    echo "  [A] 本终端继续 — 当前模型执行 Meta-Oracle 审查"
    echo "  [B] 其他终端 — 用不同模型执行 Meta-Oracle 审查"
    echo "  [C] 跳过 — 信任 Oracle 裁决，跳过 Meta-Oracle"
    echo ""
    echo "输入 A/B/C 后告知 AI:"
    echo ""

    flywheel_event "oracle_meta_handoff" "handoff_created" "P2" "file=$handoff_file" || true
}

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

case "${1:-}" in
    generate)
        shift
        generate_handoff "$@"
        ;;
    show)
        shift
        show_handoff "$@"
        ;;
    help|--help|-h)
        echo "Usage: oracle-meta-handoff.sh <generate|show>"
        echo "  generate <verdict> <target> <type>   生成交接文档"
        echo "  show <handoff_file>                  展示交接文档并中断"
        exit 0
        ;;
    *)
        echo "[oracle-meta-handoff] Usage: $0 <generate|show>"
        exit 1
        ;;
esac
