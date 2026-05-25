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

AGENTS="$PROJECT_ROOT/AGENTS.md"
CACHE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$CACHE_DIR"

# ─── AGENTS.md标记段提取(缓存) ───
extract_section() {
    local tag="$1" cache_key="$2"
    local cache_file="$CACHE_DIR/.pretool-cache-${cache_key}"
    local ah; ah=$(sha256sum "$AGENTS" 2>/dev/null | cut -d' ' -f1 || echo "no-sha256")
    if [ -f "$cache_file" ]; then
        local ch; ch=$(head -1 "$cache_file" 2>/dev/null)
        [ "$ch" = "$ah" ] && [ -n "$ah" ] && { tail -n +2 "$cache_file"; return; }
    fi
    local result=""
    [ -f "$AGENTS" ] && result=$(${PYTHON_BIN:-python3} -c "
import re
with open('$AGENTS', encoding="utf-8") as f: text = f.read()
m = re.search(r'<!-- pretool:${tag}-start -->(.*?)<!-- pretool:${tag}-end -->', text, re.DOTALL)
if m:
    lines = [l.strip() for l in m.group(1).strip().split(chr(10)) if l.strip() and '<!--' not in l]
    kept = [l for l in lines if l[0] in '#|>-*' or (len(l)>1 and l[1]=='.' and l[0].isdigit()) or l.split()[0].rstrip(':').isdigit()][:40]
    print(chr(10).join(kept))
" 2>/dev/null)
    echo "$ah" > "$cache_file"
    echo "$result" >> "$cache_file"
    echo "$result"
}

# ═══ L1 核心(每轮) ═══
L1="[L1·铁律8条] ①禁编造(file:line) ②用户裁定 ③证据门禁(VERIFIED) ④Git门禁 ⑤范围冻结 ⑥隐私防线 ⑦断言真实 ⑧哲学先行
[L1·哲学] #4验>#6信>#3守>#7文>#5人>#2益>#1简
[L1·LSP] 主动getDiagnostics发现错误->诊断->验证
[L1·反欺骗] 禁软完成语 | 禁编造 | 禁虚假路径 | VERIFIED强制
[L1·裁判团] 哲学7条 > 铁律8条 > 现状 > Oracle > Meta-Oracle > 人
[L1·决策链] 过程问题->#4直接执行 | 抉择->#2最小改动 | 方案验收->问人 | 不可逆->问人"

# 哲学+铁律表(从AGENTS.md)
L1_PHIL=$(extract_section "l1" "l1")
[ -n "$L1_PHIL" ] && L1="${L1}

[L1·哲学&铁律] 第${TURN_COUNT}轮 (AGENTS.md)
${L1_PHIL}"

# ═══ Turn 0 或 每10轮: L3 项目+方向 ═══
if [ "$TURN_COUNT" -eq 0 ] || [ $(( TURN_COUNT % 10 )) -eq 0 ]; then
    TODO_QUEUE="$PROJECT_ROOT/.omc/state/todo-queue.md"
    TODO_CTX="(无)"
    [ -f "$TODO_QUEUE" ] && TODO_CTX=$(head -20 "$TODO_QUEUE" 2>/dev/null | grep -E '^\[.\]\|###' | head -5 || echo "(无)")
    L3_CTX=$(extract_section "l3" "l3")
    [ -n "$L3_CTX" ] && L1="${L1}

[L3·项目+方向] 第${TURN_COUNT}轮 (AGENTS.md)
${L3_CTX}
方向感: 输出位置+建议下一步 | 软完成语禁令
TODO: ${TODO_CTX}"
fi

# ═══ Turn 0 或 自适应L2(早期不注/中期5轮/后期3轮) ═══
L2_FREQ=5
[ "$TURN_COUNT" -le 8 ] && L2_FREQ=999
[ "$TURN_COUNT" -ge 25 ] && L2_FREQ=3

if [ "$TURN_COUNT" -eq 0 ] || ([ $(( TURN_COUNT % L2_FREQ )) -eq 0 ] && [ "$TURN_COUNT" -ge 5 ]); then
    L2_CTX=$(extract_section "l2" "l2")
    [ -n "$L2_CTX" ] && L1="${L1}

[L2·方法论] 第${TURN_COUNT}轮 (AGENTS.md, freq=${L2_FREQ})
${L2_CTX}"
fi

# ═══ 输出 ═══
${PYTHON_BIN:-python3} -c "
import json, sys
ctx = sys.stdin.read()
ctx = ''.join(c for c in ctx if not (0xD800 <= ord(c) <= 0xDFFF))
print(json.dumps({'continue': True, 'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': ctx}}))
" <<< "$L1"

flywheel_event "pretool_rules_inject" "injected" "P2" "turn=$TURN_COUNT" || true
exit 0
