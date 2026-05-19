#!/usr/bin/env bash
# completion-gate.sh — PostToolUse:TaskUpdate — 强制 TaskUpdate 前提供结构化证据文件
# Role: 强制 TaskUpdate 前提供结构化证据文件

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
hc_enabled "completion_gate" || { echo '{"continue": true}'; exit 0; }
source "$SCRIPT_DIR/agentic-ui.sh"
INPUT=$(cat)

# 提取 status 字段
if command -v jq &>/dev/null; then
    STATUS=$(echo "$INPUT" | jq -r '.tool_input.status // empty' 2>/dev/null)
else
    STATUS=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('status', ''))
except:
    pass" 2>/dev/null)
fi

# 非 completed 状态 → 放行
if [ "$STATUS" != "completed" ]; then
    echo '{"continue": true}'
    exit 0
fi

# 自主/无人值守模式：证据检查仍执行（留痕），但失败降级为 warn
AUTONOMOUS=false
if [ -f "$PROJECT_ROOT/.omc/state/autonomous.active" ] || \
   [ -f "$PROJECT_ROOT/.omc/state/ghost-mode.active" ] || \
   [ -f "$PROJECT_ROOT/.omc/state/lx-ghost.json" ] || \
   [ -f "$PROJECT_ROOT/.omc/state/lx-goal.json" ]; then
    AUTONOMOUS=true
fi

# 自主模式降级：exit 2 → warn + exit 0（仍检查证据用于留痕，但不阻断操作）
# DF-02: 自主模式下 stderr 警告写入日志，不干扰用户终端
auto_soft_block() {
    # ── issue-triage 集成: 发现问题 → 分流 ──
    local triage_msg=""
    if [ -f "$SCRIPT_DIR/../scripts/issue-triage.sh" ]; then
        triage_msg=$(source "$SCRIPT_DIR/../scripts/issue-triage.sh" && triage_for_hook "completion-gate" "$1" "" "{}" 2>/dev/null || echo "")
    fi

    if [ "$AUTONOMOUS" = true ]; then
        echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [自主模式] $1" >> "$PROJECT_ROOT/.omc/state/completion-gate-autonomous.log"
        [ -n "$triage_msg" ] && echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $triage_msg" >> "$PROJECT_ROOT/.omc/state/completion-gate-autonomous.log"
        echo '{"continue": true}'
        exit 0
    fi
    [ -n "$triage_msg" ] && echo "$triage_msg" >&2
flywheel_event "completion_gate" "blocked" "P2" || true
    exit 2
}

# 检查证据文件是否存在（AI 必须先运行验证并写入证据文件才能标记完成）
EVIDENCE_DIR=$(hc_get "completion_gate.evidence_dir" ".omc/state")
EVIDENCE_FILE="$PROJECT_ROOT/$EVIDENCE_DIR/.completion-evidence-$(date +%Y%m%d-%H%M)"
EVIDENCE_FRESHNESS_SEC=$(hc_get "completion_gate.evidence_freshness_sec" "300")
if [ -f "$EVIDENCE_FILE" ]; then
    # 证据文件存在，检查是否在 ${EVIDENCE_FRESHNESS_SEC} 秒内写入
    if command -v python3 &>/dev/null; then
        FRESH=$(python3 -c "import os, time
try:
    age = time.time() - os.path.getmtime('$EVIDENCE_FILE')
    print('yes' if age < $EVIDENCE_FRESHNESS_SEC else 'no')
except:
    print('no')" 2>/dev/null)
    else
        FRESH="yes"
    fi
    if [ "$FRESH" = "yes" ]; then
        # 原子消费：mv 在同一文件系统是原子操作
        # 并发场景下只有一个进程能 mv 成功，其余进程到此发现源文件已不存在
        CONSUMED="${EVIDENCE_FILE}.consumed.$$"
        if ! mv "$EVIDENCE_FILE" "$CONSUMED" 2>/dev/null; then
            echo "⛔ COMPLETION BLOCKED: 证据已被其他进程消费" >&2
            auto_soft_block "证据已被其他进程消费"
        fi

        # 证据内容验证：必须包含至少 20 字符实际描述 + VERIFIED 关键字
        CONTENT=$(cat "$CONSUMED" 2>/dev/null)
        CONTENT_LEN=${#CONTENT}
        MIN_CHARS=$(hc_get "completion_gate.min_evidence_chars" "20")
        REQ_KEYWORD=$(hc_get "completion_gate.required_keyword" "VERIFIED")

        if [ "$CONTENT_LEN" -lt "$MIN_CHARS" ]; then
            echo "⛔ COMPLETION BLOCKED: 证据内容过短（${CONTENT_LEN} 字符 < ${MIN_CHARS} 字符最低要求）。" >&2
            echo "证据必须包含至少 ${MIN_CHARS} 字符的实际验证描述，不能只有 '${REQ_KEYWORD}' 等占位符。" >&2
            rm -f "$CONSUMED"
            auto_soft_block "证据内容过短（${CONTENT_LEN}字符）"
        fi

        if ! echo "$CONTENT" | grep -q "$REQ_KEYWORD"; then
            echo "⛔ COMPLETION BLOCKED: 证据文件中未找到 '${REQ_KEYWORD}' 关键字。" >&2
            rm -f "$CONSUMED"
            auto_soft_block "证据文件缺少关键字"
        fi

        # R27: 语义验证 — 形式门禁通过 ≠ 断言真实
        # 强制证据包含结构化格式（file:line 引用 或 命令输出）
        # 拒绝仅 "VERIFIED" + 描述 的模糊证据
        if ! echo "$CONTENT" | grep -qE '(\[已验证:|\[已测试:|✅|exit 0|PASS|is_danger.*false|status.*completed)'; then
            echo "⛔ COMPLETION BLOCKED: 证据格式过于模糊，缺少结构化验证标记。" >&2
            echo "证据必须包含以下结构化格式之一：" >&2
            echo "  - [已验证: file:line] 格式的代码引用" >&2
            echo "  - [已测试: 命令+输出] 格式的运行验证" >&2
            echo "  - 明确的通过标记（exit 0, PASS, ✅ 等）" >&2
            rm -f "$CONSUMED"
            auto_soft_block "证据格式模糊"
        fi

        # E3 增强: 软完成语检测 — 拒绝违禁词（AGENTS.md §软完成语禁令）
        SOFT_WORDS=$(hc_get "completion_gate.soft_completion_words" "应该没问题了|基本完成|大部分完成|差不多了.*完成|理论上可行|看起来正常|之前验证过|should be fine|basically done|mostly complete|seems to work|probably works|theoretically|should work|looks good")
        if echo "$CONTENT" | grep -qiE "$SOFT_WORDS"; then
            echo "⛔ COMPLETION BLOCKED: 证据含软完成语（违禁词），请用具体验证结果替换。" >&2
            echo "违禁词: 应该没问题了、基本完成、大部分完成、差不多了、理论上可行、看起来正常" >&2
            echo "正确格式示例: 'VERIFIED: go build ./... → exit 0, all tests PASS'" >&2
            rm -f "$CONSUMED"
            auto_soft_block "证据含软完成语"
        fi

        # E2 增强: 双源证据要求 — 证据必须来自 ≥2 个独立验证类别
        # 类别: (A) file:line 引用 / (B) 测试/编译标记 / (C) 边界/量化数据
        DUAL_SOURCE=$(echo "$CONTENT" | python3 -c "
import sys, re
c = sys.stdin.read()
sources = 0
if re.search(r'[\w./-]+\.[a-zA-Z]+:\d+', c): sources += 1  # A: file:line
if re.search(r'(exit\.code|PASS|FAIL|✅|❌|build|test|\d+ passed|\d+ failed)', c, re.I): sources += 1  # B: test
if re.search(r'(\d+/\d+|\d+\.\d+%|edge.case|coverage|regression|\d+ms)', c, re.I): sources += 1  # C: quant
print(sources)
" 2>/dev/null)
        if [ -n "$DUAL_SOURCE" ] && [ "$DUAL_SOURCE" -lt 2 ] 2>/dev/null; then
            echo "⛔ COMPLETION BLOCKED: 证据仅来自 ${DUAL_SOURCE}/3 个验证类别，需要 ≥2 类独立证据。" >&2
            echo "证据类别:" >&2
            echo "  (A) file:line 代码引用" >&2
            echo "  (B) 测试/编译通过标记" >&2
            echo "  (C) 量化/边界数据" >&2
            echo "示例: 'VERIFIED: go build → exit 0, handler.go:42 配置加载 ✅'" >&2
            rm -f "$CONSUMED"
            auto_soft_block "证据仅来自 ${DUAL_SOURCE}/3 类别"
        fi

        # E3 增强: 证据质量评分 — 量化证据完整性，低于阈值则阻断
        QUALITY_SCORE=$(echo "$CONTENT" | python3 -c "
import sys, re
content = sys.stdin.read()
score = 0.0
details = []

# 1) file:line 引用（权重 40%）
fl_count = len(re.findall(r'[\w./-]+\.[a-z]+:\d+', content))
fl_score = min(fl_count / 3.0, 1.0) * 40
score += fl_score
details.append(f'file:line refs ({fl_count}处): {fl_score:.0f}/40')

# 2) 命令/测试输出（权重 30%）
cmd_patterns = ['exit.code', r'\bPASS\b', r'\bFAIL\b', r'✅', r'❌', 'test', 'build', r'\d+ passed', r'\d+ failed', 'VERIFIED']
cmd_hits = sum(1 for p in cmd_patterns if re.search(p, content, re.IGNORECASE))
cmd_score = min(cmd_hits / 4.0, 1.0) * 30
score += cmd_score
details.append(f'test/cmd markers ({cmd_hits}处): {cmd_score:.0f}/30')

# 3) 多方面验证（权重 20%）
multi_patterns = [r'\d+%', r'\d+ms', r'\d+ req', r'coverage', 'all tests', 'zero errors', 'edge.case', 'regression']
multi_hits = sum(1 for p in multi_patterns if re.search(p, content, re.IGNORECASE))
multi_score = min(multi_hits / 3.0, 1.0) * 20
score += multi_score
details.append(f'multi-aspect ({multi_hits}处): {multi_score:.0f}/20')

# 4) 量化/边界（权重 10%）
quant_patterns = [r'\d+/\d+', r'\d+\.\d+', r'PASS.*FAIL', r'N/A']
quant_hits = sum(1 for p in quant_patterns if re.search(p, content))
quant_score = min(quant_hits / 2.0, 1.0) * 10
score += quant_score
details.append(f'quantification ({quant_hits}处): {quant_score:.0f}/10')

print(f'{score:.0f}')
for d in details:
    print(d)
" 2>/dev/null)
	# C1-fix: Python outputs multi-line (score + details). Bash [ multi-line -lt N ] silently fails.
	# Extract first line only for integer comparison. DG-29/DG-36/DG-54 class bug.
	_SCORE_NUM=$(echo "$QUALITY_SCORE" 2>/dev/null | head -1 | grep -oE '^[0-9]+' || echo "0")


        QUALITY_THRESHOLD=$(hc_get "completion_gate.quality_threshold" "65")

        if [ -n "$_SCORE_NUM" ] && [ "$_SCORE_NUM" -lt "$QUALITY_THRESHOLD" ] 2>/dev/null; then
            echo "⛔ COMPLETION BLOCKED: 证据质量评分 ${_SCORE_NUM}% < ${QUALITY_THRESHOLD}% 最低要求。" >&2
            echo "质量分解与改进方向:" >&2
            cat "$CONSUMED" 2>/dev/null | python3 -c "
import sys, re
content = sys.stdin.read()
fl = len(re.findall(r'[\w./-]+\.[a-z]+:\d+', content))
cmd = sum(1 for p in ['exit.code',r'PASS',r'FAIL','✅','❌','test','build'] if re.search(p,content,re.I))
multi = sum(1 for p in [r'\d+%',r'\d+ms','coverage','all tests','edge.case'] if re.search(p,content,re.I))
quant = sum(1 for p in [r'\d+/\d+',r'\d+\.\d+'] if re.search(p,content))
fl_s = min(fl / 3.0, 1.0) * 40
cmd_s = min(cmd / 4.0, 1.0) * 30
multi_s = min(multi / 3.0, 1.0) * 20
quant_s = min(quant / 2.0, 1.0) * 10
total = fl_s + cmd_s + multi_s + quant_s
print(f'  总分分解: {total:.0f}/100 = file:line({fl_s:.0f}/40) + test/cmd({cmd_s:.0f}/30) + multi({multi_s:.0f}/20) + quant({quant_s:.0f}/10)')
print(f'  具体统计: file:line={fl}处(需≥3)  test/cmd={cmd}处(需≥2)  multi={multi}处(需≥2)  quant={quant}处(需≥1)')
# Find weakest area
weakest = max([(40-fl_s, '添加更多 file:line 引用', fl < 3), (30-cmd_s, '补充命令输出/PASS/FAIL 等测试标记', cmd < 2), (20-multi_s, '增加多方面验证（覆盖率/百分比/边界值）', multi < 2), (10-quant_s, '添加量化数据（计数/比率/具体数值）', quant < 1)], key=lambda x: x[0])
if weakest[2]:
    print(f'  >>> 优先改进: {weakest[1]}')
print(f'  通用改进: 引用 file:line 源码 + 使用 VERIFIED: 格式 + 附原始命令输出')
" 2>/dev/null
            rm -f "$CONSUMED"
            auto_soft_block "证据质量评分过低（${QUALITY_SCORE}%）"
        fi

        # E5 根因分析门禁（US-007 + E5 硬阻断）
        # 当证据质量评分 >= 阈值但 RCA 缺失 → 硬阻断
        # AI 有能力完成高质量验证，但未诊断根因 — 症状混淆风险
        # E5 结构化检测: ≥2/5 RCA 字段（反关键词游戏化，DG-29/DG-43 同类教训）
        # B5 增强: 检测模板化 RCA（仅含占位符/泛泛而谈），要求具体引用
        RCA_CONTENT=$(cat "$CONSUMED" 2>/dev/null)
        RCA_STRUCTURED=0

        # 检测1: 结构化字段存在性
        echo "$RCA_CONTENT" | grep -qiE 'root.cause[:=].{5,}' && RCA_STRUCTURED=$((RCA_STRUCTURED + 1))
        echo "$RCA_CONTENT" | grep -qiE '(repro|复现|触发条件).{5,}' && RCA_STRUCTURED=$((RCA_STRUCTURED + 1))
        echo "$RCA_CONTENT" | grep -qiE '(underlying|底层原因|why.*fail).{5,}' && RCA_STRUCTURED=$((RCA_STRUCTURED + 1))
        echo "$RCA_CONTENT" | grep -qiE '(fix.approach|修复方式|solution).{5,}' && RCA_STRUCTURED=$((RCA_STRUCTURED + 1))
        echo "$RCA_CONTENT" | grep -qiE '(根因|原因分析|cause_analysis|根本原因)' && RCA_STRUCTURED=$((RCA_STRUCTURED + 1))

        # 检测2 (B5): 模板化 RCA 检测 — 防止 AI 填充无意义占位符/泛泛而谈
        RCA_TEMPLATED=0
        echo "$RCA_CONTENT" | grep -qiE '(占位符|placeholder|待补充|TODO|待确定|TBD|具体.*根据.*情况)' && RCA_TEMPLATED=$((RCA_TEMPLATED + 1))
        echo "$RCA_CONTENT" | grep -qiE '(需要查看|需确认|需进一步|请根据|请参考|参见.*文档)' && RCA_TEMPLATED=$((RCA_TEMPLATED + 1))
        echo "$RCA_CONTENT" | grep -qiE '(typical.common|generic|general.*error|standard.*root)' && RCA_TEMPLATED=$((RCA_TEMPLATED + 1))
        # 检测 RCA 是否包含具体 file:line 引用（真实 RCA 应有具体引用）
        RCA_HAS_REFERENCE=0
        echo "$RCA_CONTENT" | grep -qiE '[a-zA-Z0-9_./-]+\.[a-z]+:[0-9]+' && RCA_HAS_REFERENCE=$((RCA_HAS_REFERENCE + 1))
        if [ "$RCA_STRUCTURED" -ge 2 ]; then
            echo "  ✓ RCA 根因分析已包含（${RCA_STRUCTURED}/5 结构化字段匹配）" >&2
        else
            QS_VALUE=$(echo "$QUALITY_SCORE" | grep -oE '^[0-9]+' | head -1)
            QS_THRESHOLD_NUM="${QUALITY_THRESHOLD%%.*}"
            QS_THRESHOLD_NUM="${QS_THRESHOLD_NUM:-65}"
            if [ -n "$QS_VALUE" ] && [ "$QS_VALUE" -ge "$QS_THRESHOLD_NUM" ] 2>/dev/null; then
                # 检查 RCA 是否模板化
                if [ "$RCA_TEMPLATED" -ge 1 ]; then
                    echo "⛔ COMPLETION BLOCKED [E5+B5]: 检测到模板化 RCA（占位符/泛泛而谈），请提供具体根因分析。" >&2
                    echo "  RCA 中含模板化表述(${RCA_TEMPLATED}处)，缺少具体 file:line 引用。" >&2
                    [ "$RCA_HAS_REFERENCE" -eq 0 ] && echo "  建议: RCA 中引用具体代码位置 file:line" >&2
                    rm -f "$CONSUMED"
                    auto_soft_block "E5+B5 硬阻断: RCA 模板化（含占位符）"
                elif [ "$RCA_STRUCTURED" -lt 2 ]; then
                    echo "⛔ COMPLETION BLOCKED [E5]: 证据质量评分 ${QS_VALUE}% 已达阈值 ${QS_THRESHOLD_NUM}%，但缺少根因分析。" >&2
                    echo "  高质量证据表明 AI 有能力完成验证，但未诊断问题根因 — 这是症状混淆风险（E5）。" >&2
                    echo "  请补充结构化根因分析后重试（需≥2/5字段）。格式示例:" >&2
                    echo "    root_cause: <错误签名> / repro: <复现条件> / underlying: <底层原因> / fix_approach: <修复方式>" >&2
                    rm -f "$CONSUMED"
                    auto_soft_block "E5 硬阻断: 质量评分≥阈值但 RCA 缺失"
                fi
            else
                echo "  ⚠️ [E5] RCA 根因分析未检测到。建议在证据中包含根因分析（root cause analysis）以证明修复触及底层原因，而非仅表面修复。" >&2
                echo "    格式示例: 'root_cause: <错误签名> / <复现条件> / <底层原因> / <修复方式>'" >&2
            fi
        fi

        # P3.4: 质量评分透明输出（通过时也展示评分）
        # 自主模式: 跳过 agentic_status UI 渲染，仅记录到日志
        if [ "$AUTONOMOUS" = true ]; then
            echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] [自主模式] 证据通过 — 质量评分: ${QUALITY_SCORE}/100 (阈值 ${QUALITY_THRESHOLD})" >> "$PROJECT_ROOT/.omc/state/completion-gate-autonomous.log"
        else
            agentic_status success \
                "证据通过" \
                "质量评分: ${QUALITY_SCORE}/100 (阈值 ${QUALITY_THRESHOLD})"
            cat "$CONSUMED" 2>/dev/null | python3 -c "
import sys, re
content = sys.stdin.read()
fl = len(re.findall(r'[\w./-]+\.[a-z]+:\d+', content))
cmd = sum(1 for p in ['exit.code',r'PASS',r'FAIL','✅','❌','test','build'] if re.search(p,content,re.I))
multi = sum(1 for p in [r'\d+%',r'\d+ms','coverage','all tests','edge.case'] if re.search(p,content,re.I))
quant = sum(1 for p in [r'\d+/\d+',r'\d+\.\d+'] if re.search(p,content))
print(f'{AGENTIC_UI_INDENT}file:line={fl}  test/cmd={cmd}  multi-aspect={multi}  quant={quant}')
" 2>/dev/null

        fi
        # --- C3: L3 复杂度检测 — Oracle 终审记录检查 ---
        # 当证据显示 L3 级别任务（多文件变更、架构决策）但没有 Oracle 终审记录时输出 warning
        # 非阻断 — 仅 additionalContext 警告
        if echo "$CONTENT" | grep -qiE '(L[34]|三重门|architecture|arch decision|方案选型|跨模块|interface change|multi.*file|设计决策|架构变更|design decision)'; then
            if ! echo "$CONTENT" | grep -qE '^## Oracle 终审记录'; then
                echo "⚠️ [C3] L3 任务检测到：证据内容含架构决策/多文件变更等 L3 复杂度关键词，但未找到 Oracle 终审记录块。" >&2
                echo "   L3 任务应包含 Oracle 终审记录以完成 C3 流程验证。格式参考：" >&2
                echo "   ## Oracle 终审记录" >&2
                echo "   审核时间: {timestamp}" >&2
                echo "   审核者: Oracle" >&2
                echo "   结论: APPROVED | NEEDS_REVISION" >&2
                echo "   备注: {note}" >&2
            else
                echo "  ✓ C3: Oracle 终审记录已找到" >&2
            fi
        fi

        # 验证通过，清理消费文件
        rm -f "$CONSUMED"

        # --- 自动推进 Pipeline Step（C3 流程结构化） ---
        PIPELINE_SCRIPT="$PROJECT_ROOT/.claude/scripts/pipeline-step.sh"
        if [ -f "$PIPELINE_SCRIPT" ]; then
            bash "$PIPELINE_SCRIPT" advance >/dev/null 2>&1 || true
        fi

        # --- A→B→A 交叉验证触发（Oracle Q1: 关键词匹配 + 复杂度门控双通道）---
        # 通道1: 复杂度门控 — L3/L4 任务、架构决策、多文件变更等复杂度指标
        if echo "$CONTENT" | grep -qiE '(L[34]|三重门|architecture|arch decision|方案选型|跨模块|interface change|multi.*file|设计决策|架构变更|design decision)'; then
            TRIGGER="yes"
        fi
        # 通道2: 关键词匹配（原有逻辑，复杂度未命中时启用）
        if [ "$TRIGGER" != "yes" ]; then
            # 高精确率词：单命中即触发
            if echo "$CONTENT" | grep -qiE '(验收|benchmark|scorecard|通过率|口径|mapping|合规)'; then
                TRIGGER="yes"
            # 中等精确率词：需 2+ 匹配避免日常用语误报
            elif [ "$(echo "$CONTENT" | grep -ioE '(报告|方案|评估|design|proposal|review|analysis|评审|分析)' | sort -u | wc -l)" -ge 2 ]; then
                TRIGGER="yes"
            fi
        fi
        if [ "${TRIGGER:-no}" = "yes" ]; then
            # 构建手off内容（同时写文件 + 打印 stderr）
            HANDOFF_FILE="$PROJECT_ROOT/.omc/state/cross-verify-handoff.md"
            # 扫描近期修改的方案/报告文件
            RECENT_DOCS=$(find "$PROJECT_ROOT/docs" "$PROJECT_ROOT/rpe" "$PROJECT_ROOT/.omc/plans" -name "*.md" -mmin -10 2>/dev/null | head -5)
            cat > "$HANDOFF_FILE" <<HANDOFF
# 🚦 三重门交叉验证 — A→B→A

## Phase 1: A 填写可证伪预测（发给 B 前填写）
> 注意：以下预测由 A 终端填写，B 终端**不得查看** Phase 1 内容

**subject**: ${TASK_DESCRIPTION:-任务验证}

predictions:
$(echo "${CONTENT}" | head -5 | sed 's/^/  /')
- [ ] 预测1: [A 填写具体可证伪断言]
- [ ] 预测2: [A 填写具体可证伪断言]
- [ ] 预测3: [A 填写具体可证伪断言]

**evidence_requirements**:
  - build: [产物/exit_code/构建日志]
  - test: [通过数/失败数/覆盖率]
  - behavior: [路径/内容/副作用]

---

## Phase 2: B 盲执行（剥离预测后发给 B）

> 以下内容复制到 B 终端（B **不知道** A 的预测，消除确认偏差）

B 终端，你是执行方。执行以下验证任务，**只陈述事实**，不下结论：

**任务描述**:
${CONTENT}

**近期修改的相关文件（10分钟内）**:
$(echo "${RECENT_DOCS}" | sed 's/^/  - /')

**B 报告格式**（请逐项填写原始输出，不做分析）:
\`\`\`
executed_steps:
  - step_id: "S1"
    command: "[实际执行的命令]"
    exit_code: 0|1|null
    actual_output: "[原始输出]"
    observed: "[客观描述]"
anomalies: []
\`\`\`

---

## Phase 3: A 自证（收到 B 报告后填写）

comparisons:
  - prediction_id: "P1"
    expected: "[A 的预测内容]"
    observed: "[B 的观测结果]"
    match: true|false
    explanation: "[不匹配时解释原因]"
self_verdict: "PASS|FAIL|INCONCLUSIVE"
reasoning: "[综合判断]"

***** 全部内容结束 *****
HANDOFF
            # 读回文件打印到 stderr
            cat "$HANDOFF_FILE" >&2
            echo "" >&2
            echo "📁 手off文件已写入: .omc/state/cross-verify-handoff.md" >&2
            echo "   B 终端启动后直接执行: cat .omc/state/cross-verify-handoff.md" >&2
            echo "" >&2
            echo "同模型交叉验证效果有限（盲区重叠），必须不同模型才能真正发现断言造假。" >&2
            echo "比对一致 → 验收通过 | 不一致 → 返回 A 重新生成方案，重复此流程" >&2
            echo "══════════════════════════" >&2
        fi
        echo '{"continue": true}'
        exit 0
    fi
fi

# 阻断：无有效证据文件
REQ_KW=$(hc_get "completion_gate.required_keyword" "VERIFIED")
MIN_CH=$(hc_get "completion_gate.min_evidence_chars" "20")

# 从 feature-registry.yaml 读取预期证据级别（AC-5.6）
EVIDENCE_LEVEL_LABEL="L3"
REGISTRY_PATH="$(cd "$(dirname "$0")/.." && pwd)/feature-registry.yaml"
if [ -f "$REGISTRY_PATH" ]; then
    L=$(grep -A2 "^  - name: completion-gate" "$REGISTRY_PATH" | grep "evidence_level:" | sed 's/.*evidence_level: *//')
    [ -n "$L" ] && EVIDENCE_LEVEL_LABEL="$L"
fi

echo "[Completion Gate] evidence missing: expected ${EVIDENCE_LEVEL_LABEL} at ${EVIDENCE_FILE}" >&2
auto_soft_block "无证据文件"
