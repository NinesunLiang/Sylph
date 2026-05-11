#!/usr/bin/env bash
# completion-gate.sh — PostToolUse:TaskUpdate — 强制 TaskUpdate 前提供结构化证据文件
# Role: 强制 TaskUpdate 前提供结构化证据文件

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
hc_enabled "completion_gate" || exit 0
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
    exit 0
fi

# 检查证据文件是否存在（AI 必须先运行验证并写入证据文件才能标记完成）
EVIDENCE_DIR=$(hc_get "completion_gate.evidence_dir" ".omc/state")
EVIDENCE_FILE="$PROJECT_ROOT/$EVIDENCE_DIR/.completion-evidence-$(date +%Y%m%d)"
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
            exit 2
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
            exit 2
        fi

        if ! echo "$CONTENT" | grep -q "$REQ_KEYWORD"; then
            echo "⛔ COMPLETION BLOCKED: 证据文件中未找到 '${REQ_KEYWORD}' 关键字。" >&2
            rm -f "$CONSUMED"
            exit 2
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
            exit 2
        fi

        # E3 增强: 软完成语检测 — 拒绝违禁词（AGENTS.md §软完成语禁令）
        SOFT_WORDS=$(hc_get "completion_gate.soft_completion_words" "应该没问题了|基本完成|大部分完成|差不多了.*完成|理论上可行|看起来正常|之前验证过")
        if echo "$CONTENT" | grep -qiE "$SOFT_WORDS"; then
            echo "⛔ COMPLETION BLOCKED: 证据含软完成语（违禁词），请用具体验证结果替换。" >&2
            echo "违禁词: 应该没问题了、基本完成、大部分完成、差不多了、理论上可行、看起来正常" >&2
            echo "正确格式示例: 'VERIFIED: go build ./... → exit 0, all tests PASS'" >&2
            rm -f "$CONSUMED"
            exit 2
        fi

        # E3 增强: 证据质量评分 — 量化证据完整性，低于阈值则阻断
        QUALITY_SCORE=$(python3 -c "
import sys, re
content = '''$CONTENT'''
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

        QUALITY_THRESHOLD=$(hc_get "completion_gate.quality_threshold" "50")

        if [ -n "$QUALITY_SCORE" ] && [ "$QUALITY_SCORE" -lt "$QUALITY_THRESHOLD" ] 2>/dev/null; then
            echo "⛔ COMPLETION BLOCKED: 证据质量评分 ${QUALITY_SCORE}% < ${QUALITY_THRESHOLD}% 最低要求。" >&2
            echo "质量分解:" >&2
            python3 -c "
content = '''$(cat "$CONSUMED" 2>/dev/null)'''
import re; score=0; fl=len(re.findall(r'[\w./-]+\.[a-z]+:\d+', content))
cmd=sum(1 for p in ['exit.code',r'PASS',r'FAIL','✅','❌','test','build'] if re.search(p,content,re.I))
multi=sum(1 for p in [r'\d+%',r'\d+ms','coverage','all tests','edge.case'] if re.search(p,content,re.I))
print(f'  file:line引用: {fl}处 (需≥3)')
print(f'  测试/编译标记: {cmd}处 (需≥2)')
print(f'  多方面验证:   {multi}处 (需≥2)')
print(f'  >>> 改进: 添加 file:line 引用 + 具体命令输出 + 量化测试结果')
" 2>/dev/null
            rm -f "$CONSUMED"
            exit 2
        fi

        # 验证通过，清理消费文件
        rm -f "$CONSUMED"

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
***** 复制以下全部内容到 B 终端 *****

【当前终端：A | 方案方】

【对抗性验收提示词】
换一个不同模型（如 A 用 Claude 则 B 用 GPT/Gemini），
你是一个对抗性验收官。逐条审查以下方案中每个断言：
· 有行业标准来源吗？有 file:line 吗？
· 是自创指标/口径含糊/结论夸大吗？→ ❌
· 输出格式: 断言 → 证据 → 判定(✅/⚠️/❌) + 理由

【以下为待验收方案内容】
任务描述: ${CONTENT}

近期修改的相关文件（10分钟内）:
$(echo "${RECENT_DOCS}" | sed 's/^/  - /')

（如方案内容在以上文件中，B 终端直接读取对应文件审查）

***** 以上复制到 B 终端 *****
***** 以下为 B 返回报告 *****

【当前终端：B | 验收方】
（B 终端贴在这里）

***** 验收报告结束 *****
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
exit 2
