#!/usr/bin/env bash
# pretool-rules-inject.sh — UserPromptSubmit — 3级脱水分层注入
# 永不阻断 (exit 0)
# Turn 0: L1+L2+L3 全量上车
# Turn 1+: 自适应频率 (L1每轮, L2自适应, L3每10轮)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
set -f
hc_enabled "pretool_rules_inject" || { echo '{"continue": true}'; exit 0; }

TURNS_FILE="$PROJECT_ROOT/.omc/state/session-turns.json"
TURN_COUNT=0
[ -f "$TURNS_FILE" ] && TURN_COUNT=$(${PYTHON_BIN:-python3} -c "import json; print(json.load(open('$TURNS_FILE', encoding="utf-8")).get('count',0))" 2>/dev/null || echo 0)

CACHE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$CACHE_DIR"

# ═══ 分层注入 — 从 context-cache.md 单源提取，按频率注入 ═══
# L1 每轮: 铁律+哲学+软完成语 (~15行, 防漂移)
# L2 Turn0+每5轮: 操作约束+反模式+架构铁律 (~30行, AI有记忆定期刷新)
# L3 Turn0+每10轮: 教训速查+禁止项+TODO (~30行, 参考型偶尔提醒)
CACHE="$PROJECT_ROOT/.omc/state/context-cache.md"

# Fallback: 如果 context-cache.md 不存在，使用硬编码 L1
L1_FALLBACK="[L1·铁律8条] ①禁编造(file:line) ②用户裁定 ③证据门禁(VERIFIED) ④Git门禁 ⑤范围冻结 ⑥隐私防线 ⑦断言真实 ⑧哲学先行
[L1·哲学] #4验>#6信>#3守>#7文>#5人>#2益>#1简
[L1·裁判团] 哲学7条 > 铁律8条 > 现状 > Oracle > Meta-Oracle > 人
[L1·决策链] 过程问题->#4直接执行 | 抉择->#2最小改动 | 方案验收->问人 | 不可逆->问人"

if [ -f "$CACHE" ]; then
    # 用 Python 解析 context-cache.md，按 --- 分 section，分配到 L1/L2/L3
    LAYERED=$(${PYTHON_BIN:-python3} - "$CACHE" "$TURN_COUNT" <<'PYEOF'
import sys, re

cache_path = sys.argv[1]
turn = int(sys.argv[2])

with open(cache_path, encoding='utf-8') as f:
    text = f.read()

# Remove HTML comments and CTX-COMPACT marker
text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
text = text.replace('CTX-COMPACT:AI-ONLY', '')

# Split into sections by --- separators
sections = [s.strip() for s in text.split('---') if s.strip()]

# Assign sections to layers
l1_parts = []
l2_parts = []
l3_parts = []

for sec in sections:
    lines = [l.strip() for l in sec.split('\n') if l.strip()]
    if not lines:
        continue
    first_line = lines[0] if lines else ''

    if '铁律:' in first_line or '铁律' in first_line:
        # L1: 铁律 + 哲学 + 软完成语 (前~20行)
        l1_lines = [l for l in lines if not l.startswith('操作约束') and not l.startswith('权威')
                     and not l.startswith('Hook') and not l.startswith('三源') and not l.startswith('Read展开')]
        l1_parts.extend(l1_lines[:20])
        # 操作约束/Hook/三源 → L2
        meta_lines = [l for l in lines if l.startswith('操作约束') or l.startswith('-')
                      or l.startswith('权威') or l.startswith('Hook') or l.startswith('三源') or l.startswith('Read展开')]
        if meta_lines:
            l2_parts.append('操作约束+Hook速查+三源:')
            l2_parts.extend(meta_lines[:15])
    elif '反模式' in first_line:
        l2_parts.extend(lines[:15])
    elif '教训' in first_line:
        l3_parts.extend(lines[:13])
    elif '架构铁律' in first_line or '命名:' in first_line:
        l2_parts.extend(lines[:12])
    elif '错误处理' in first_line or '测试:' in first_line or '禁止:' in first_line:
        l3_parts.extend(lines)
    elif '原则:' in first_line:
        l3_parts.append(first_line)

# Build L1
l1 = '\n'.join(l1_parts[:15]) if l1_parts else ''
if l1:
    l1 = '[L1·铁律+哲学] context-cache.md 脱水上下文\n' + l1

# Build L2 (Turn 0 or every 5 turns)
l2 = ''
l2_turns = (turn == 0) or (turn % 5 == 0)
if l2_turns and l2_parts:
    l2 = '\n'.join(l2_parts[:25])
    if l2:
        l2 = f'[L2·操作+反模式+架构] 第{turn}轮刷新 (每5轮)\n' + l2

# Build L3 (Turn 0 or every 12 turns)
l3 = ''
l3_turns = (turn == 0) or (turn % 10 == 0)
if l3_turns and l3_parts:
    l3 = '\n'.join(l3_parts[:20])
    if l3:
        l3 = f'[L3·教训+禁止项] 第{turn}轮刷新 (每10轮)\n' + l3

# Output in JSON format for bash parsing
import json
result = {'l1': l1, 'l2': l2, 'l3': l3}
print(json.dumps(result, ensure_ascii=False))
PYEOF
)

    # Parse JSON output from Python
    L1=$(echo "$LAYERED" | ${PYTHON_BIN:-python3} -c "import json,sys; print(json.load(sys.stdin).get('l1',''))" 2>/dev/null)
    L2=$(echo "$LAYERED" | ${PYTHON_BIN:-python3} -c "import json,sys; print(json.load(sys.stdin).get('l2',''))" 2>/dev/null)
    L3=$(echo "$LAYERED" | ${PYTHON_BIN:-python3} -c "import json,sys; print(json.load(sys.stdin).get('l3',''))" 2>/dev/null)

    [ -z "$L1" ] && L1="$L1_FALLBACK"
else
    L1="$L1_FALLBACK"
    L2=""
    L3=""
fi

# 哲学+铁律表(从AGENTS.md)
	# ═══ 组装 L1+L2+L3(从 context-cache.md 单源) + TODO ═══
	CTX="$L1"

	# 追加 TODO (Turn0 + 每10轮)
	if [ "$TURN_COUNT" -eq 0 ] || [ $(( TURN_COUNT % 10 )) -eq 0 ]; then
	    TODO_QUEUE="$PROJECT_ROOT/.omc/state/todo-queue.md"
	    TODO_CTX="(无)"
	    [ -f "$TODO_QUEUE" ] && TODO_CTX=$(head -20 "$TODO_QUEUE" 2>/dev/null | grep -E '^\[.\]\|###' | head -5 || echo "(无)")
	    CTX="${CTX}\n\n[TODO·第${TURN_COUNT}轮] ${TODO_CTX}"
	fi

	# 追加 L2 (由 Python 按频率判定)
	[ -n "$L2" ] && CTX="${CTX}\n\n${L2}"

	# 追加 L3 (由 Python 按频率判定)
	[ -n "$L3" ] && CTX="${CTX}\n\n${L3}"

# ═══ 输出 ═══
${PYTHON_BIN:-python3} -c "
import json, sys
ctx = sys.stdin.read()
ctx = ''.join(c for c in ctx if not (0xD800 <= ord(c) <= 0xDFFF))
print(json.dumps({'continue': True, 'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': ctx}}))
" <<< "$CTX"

flywheel_event "pretool_rules_inject" "injected" "P2" "turn=$TURN_COUNT" || true
exit 0
