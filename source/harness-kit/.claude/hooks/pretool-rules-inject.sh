#!/usr/bin/env bash
# pretool-rules-inject.sh — PreToolUse — 3级脱水分层注入 (v6.0)
# 永不阻断 (exit 0)
#
# v6.0 双法官复审修正:
#   1.✅ 每轮去重(防每工具调用重复注入) 2.✅ 移除15行截断→30行 3.✅ 缓存AGENTS.md提取
#   4.✅ 高风险工具全量L1,低风险紧凑 5.✅ L2+L3加法非互斥 6.✅ 自适应频率(早期稀疏,后期密集)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/harness_config.sh"
set -f
hc_enabled "pretool_rules_inject" || { echo '{"continue": true}'; exit 0; }

INPUT=$(cat 2>/dev/null || echo "")
TOOL_NAME=""
if command -v jq &>/dev/null && [ -n "$INPUT" ]; then
    TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
fi
[ -z "$TOOL_NAME" ] && { echo '{"continue": true}'; exit 0; }

TURNS_FILE="$PROJECT_ROOT/.omc/state/session-turns.json"
TURN_COUNT=0
if [ -f "$TURNS_FILE" ]; then
    TURN_COUNT=$(python3 -c "import json; print(json.load(open('$TURNS_FILE')).get('count',0))" 2>/dev/null || echo 0)
fi

# ═══ v6.0 #1: 每轮去重 (防每工具调用重复注入) ═══
LAST_TURN_FILE="$PROJECT_ROOT/.omc/state/.last-rules-turn"
LAST_TURN=-1
[ -f "$LAST_TURN_FILE" ] && LAST_TURN=$(cat "$LAST_TURN_FILE" 2>/dev/null || echo -1)
if [ "$TURN_COUNT" = "$LAST_TURN" ]; then
    echo '{"continue": true}'; exit 0
fi
echo "$TURN_COUNT" > "$LAST_TURN_FILE"

# ═══ v6.0 #4: 工具规则 + 风险分层 ═══
case "$TOOL_NAME" in
    Edit|Write)
        L1_TOOL="Read-before-Edit | 范围冻结 | 断言必附file:line | 改前getDiagnostics | 禁改治理文件"
        L1_RISK="high"
        ;;
    Bash)
        L1_TOOL="禁rm -rf/sudo/git push -f | 禁读写.env/私钥/Token | git写操作先报告 | getDiagnostics检查->验证"
        L1_RISK="high"
        ;;
    Agent|Task)
        L1_TOOL="子agent结果需验证 | 不信任完成声明 | 独立任务并行"
        L1_RISK="high"
        ;;
    Read)
        L1_TOOL="禁读.env/私钥/密钥 | 先Read后断言 | 引用必附file:line"
        L1_RISK="low"
        ;;
    Grep|Glob|WebSearch|WebFetch)
        L1_TOOL="搜索结果引用file:line | 确认文件存在 | 验证后再引用"
        L1_RISK="low"
        ;;
    *)
        L1_TOOL="禁止编造(file:line) | 证据门禁(VERIFIED) | 善用getDiagnostics"
        L1_RISK="low"
        ;;
esac

# ═══ L1 核心: 工具规则 + 反欺骗 + 裁判团 + 决策链 ═══
L1="[L1·工具规则] ${L1_TOOL}
[L1·LSP] 主动用getDiagnostics发现错误->改前诊断->改后验证
[L1·决策链] 过程性问题->#4直接执行 | 抉择->#2最小改动 | 方案验收->问人 | 不可逆->问人
[L1·反欺骗] 禁编造(file:line) | 禁软完成语 | 禁虚假路径 | 完成前需VERIFIED证据
[L1·裁判团] 哲学7条 > 铁律8条 > 现状 > Oracle > Meta-Oracle > 人"

# v6.0 #4: 高风险工具追加经济账+无人模式
if [ "$L1_RISK" = "high" ]; then
    L1="${L1}
[L1·经济账] 输出紧凑 | 不创建临时md | 每轮注入1次(去重保护)"
    STATE_DIR="$PROJECT_ROOT/.omc/state"
    if command -v is_mode_active &>/dev/null; then
        CURRENT_MODE=$(is_mode_active "$STATE_DIR" 2>/dev/null || echo "normal")
        [ "$CURRENT_MODE" != "normal" ] && L1="${L1}
[L1·无人模式] ${CURRENT_MODE}: Git降级/不提问/自动报告/Oracle仍强制"
    fi
fi

# ═══ v6.0 #2+#3: AGENTS.md提取(缓存+去截断[:15]→[:30]) ═══
AGENTS="$PROJECT_ROOT/AGENTS.md"
CACHE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$CACHE_DIR"

extract_section_cached() {
    local tag="$1" cache_key="$2"
    local cache_file="$CACHE_DIR/.pretool-cache-${cache_key}"
    local agents_hash; agents_hash=$(sha256sum "$AGENTS" 2>/dev/null | cut -d' ' -f1 || echo "no-sha256")

    # 缓存命中
    if [ -f "$cache_file" ]; then
        local cached_hash; cached_hash=$(head -1 "$cache_file" 2>/dev/null)
        if [ "$cached_hash" = "$agents_hash" ] && [ -n "$agents_hash" ]; then
            tail -n +2 "$cache_file"
            return
        fi
    fi

    # 提取+缓存 (v6.0: [:15]→[:30] 完整铁律)
    local result=""
    if [ -f "$AGENTS" ]; then
        result=$(python3 -c "
import re
with open('$AGENTS') as f:
    text = f.read()
m = re.search(r'<!-- pretool:${tag}-start -->(.*?)<!-- pretool:${tag}-end -->', text, re.DOTALL)
if m:
    lines = [l.strip() for l in m.group(1).strip().split(chr(10)) if l.strip() and '<!--' not in l]
    kept = [l for l in lines if l.startswith('|') or l.startswith('## 8') or l.startswith('#4')][:30]
    print(chr(10).join(kept))
" 2>/dev/null)
    fi
    echo "$agents_hash" > "$cache_file"
    echo "$result" >> "$cache_file"
    echo "$result"
}

# L1 追加哲学+铁律 (v6.0: [:30]保留完整的8条铁律)
L1_PHIL=$(extract_section_cached "l1" "l1")
if [ -n "$L1_PHIL" ]; then
    L1="${L1}

[L1·哲学&铁律] 第${TURN_COUNT}轮锚定 (AGENTS.md)
${L1_PHIL}"
fi

# ═══ v6.0 #6: L2自适应频率 (早期稀疏, 后期密集) ═══
L2_FREQ=5
[ "$TURN_COUNT" -le 8 ] && L2_FREQ=999   # 早期: SessionStart规则仍新鲜, 不注L2
[ "$TURN_COUNT" -ge 25 ] && L2_FREQ=3    # 后期: 遗忘加速, 每3轮锚定

# v6.0 #5: L2+L3加法(if-if, 非if-elif)
if [ $(( TURN_COUNT % L2_FREQ )) -eq 0 ] && [ "$TURN_COUNT" -ge 5 ]; then
    L2_CTX=$(extract_section_cached "l2" "l2")
    [ -n "$L2_CTX" ] && L1="${L1}

[L2·方法论] 第${TURN_COUNT}轮锚定 (AGENTS.md, freq=${L2_FREQ})
${L2_CTX}

成长飞轮: error-dna->flywheel->dogfood->claude-next.md->下次注入
决策链: 过程性问题->哲学#4直接执行 | 不可逆/安全/偏好->必须问人"
fi

# ═══ v6.0 #5: L3每10轮 (加法, 与L2共存) ═══
if [ $(( TURN_COUNT % 10 )) -eq 0 ]; then
    TODO_QUEUE="$PROJECT_ROOT/.omc/state/todo-queue.md"
    TODO_CTX="(无待办)"
    [ -f "$TODO_QUEUE" ] && TODO_CTX=$(head -20 "$TODO_QUEUE" 2>/dev/null | grep -E '^\[.\]\|###' | head -5 || echo "(无待办)")

    L3_CTX=$(extract_section_cached "l3" "l3")
    [ -n "$L3_CTX" ] && L1="${L1}

[L3·方向感+项目] 第${TURN_COUNT}轮锚定 (AGENTS.md)
${L3_CTX}

方向感: 输出当前位置+建议下一步 | 软完成语禁令 | 主动提示Enhanced可用
断点续传: ${TODO_CTX}"
fi

# ═══ 输出 ═══
python3 -c "
import json, sys
ctx = sys.stdin.read()
ctx = ''.join(c for c in ctx if not (0xD800 <= ord(c) <= 0xDFFF))
print(json.dumps({'continue': True, 'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'additionalContext': ctx}}))
" <<< "$L1"

flywheel_event "pretool_rules_inject" "injected" "P2" "tool=$TOOL_NAME turn=$TURN_COUNT risk=$L1_RISK" || true
exit 0
