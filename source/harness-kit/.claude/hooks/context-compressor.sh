#!/usr/bin/env bash
# context-compressor.sh — SessionStart — 移花接木：源文件不动，运行时拼接压缩缓存
# Role: 检测源文件 mtime → 拼接 compact 文件 → 缓存到 .omc/state/context-cache.md
# 哲学 #1 (less is more): CLAUDE.md 指向缓存，每次会话只注入 ~3KB
# 哲学 #4 (验证): mtime 防过期

source "$(dirname "$0")/harness_config.sh"
hc_enabled "context_compressor" || exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"
STATE_DIR="$PROJECT_ROOT/.omc/state"
CACHE="$STATE_DIR/context-cache.md"

mkdir -p "$STATE_DIR"

# 跨平台 mtime 提取: macOS (stat -f%m) / Linux (stat -c%Y)
_stat_mtime() { stat -f%m "$1" 2>/dev/null || stat -c%Y "$1" 2>/dev/null || echo 0; }

# 源文件（用来比对 mtime）和对应的 compact 文件（用来拼接缓存）
# 格式: src1|compact1 src2|compact2 ...
SRC_COMPACT_PAIRS="
$PROJECT_ROOT/AGENTS.md|$CLAUDE_DIR/AGENTS-compact.md
$CLAUDE_DIR/anti-patterns.md|$CLAUDE_DIR/anti-patterns-compact.md
$CLAUDE_DIR/claude-next.md|$CLAUDE_DIR/claude-next-compact.md
$CLAUDE_DIR/kernel.md|$CLAUDE_DIR/kernel-compact.md
"

# 检查任意源文件是否比缓存新
NEED_REGEN=false
if [ ! -f "$CACHE" ]; then
    NEED_REGEN=true
else
    CACHE_MTIME=$(_stat_mtime "$CACHE")
    set -f
    for pair in $SRC_COMPACT_PAIRS; do
        src="${pair%%|*}"
        [ ! -f "$src" ] && continue
        SRC_MTIME=$(_stat_mtime "$src")
        if [ "$SRC_MTIME" -gt "$CACHE_MTIME" ]; then
            NEED_REGEN=true
            break
        fi
    done
fi

if [ "$NEED_REGEN" = false ]; then
    flywheel_event "context_compressor" "cache_hit" "L0" || true
    exit 0
fi

flywheel_event "context_compressor" "regenerating" "L1" || true

# 拼接 compact 文件 → 缓存
> "$CACHE"
{
    echo "<!-- CONTEXT-COMPRESSOR: $(date +%Y-%m-%dT%H:%M:%S) 自动生成 -->"
echo "<!-- 源文件: AGENTS.md + anti-patterns.md + claude-next.md + kernel.md (compact 镜像) -->"
    echo "<!-- 移花接木: 注入 compact 版本，完整版请 Read 源文件 -->"
    echo ""
} >> "$CACHE"

ALL_OK=true
set -f
for pair in $SRC_COMPACT_PAIRS; do
    compact="${pair##*|}"
    if [ -f "$compact" ]; then
        cat "$compact" >> "$CACHE"
        { echo ""; echo "---"; echo ""; } >> "$CACHE"
    else
        echo "[context-compressor] ⚠️ compact 文件缺失: $compact" >&2
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = true ]; then
    CACHE_SIZE=$(wc -c < "$CACHE" | tr -d ' ')
    echo "[context-compressor] ✅ 缓存已更新: $CACHE ($CACHE_SIZE bytes)" >&2

    # DG-103: 计算 token 节省量写入 token-savings.json
    TOTAL_SRC=0; TOTAL_COMPACT=0
    set -f
    for pair in $SRC_COMPACT_PAIRS; do
        src="${pair%%|*}"; compact="${pair##*|}"
        [ -f "$src" ] && TOTAL_SRC=$((TOTAL_SRC + $(wc -c < "$src" | tr -d ' ')))
        [ -f "$compact" ] && TOTAL_COMPACT=$((TOTAL_COMPACT + $(wc -c < "$compact" | tr -d ' ')))
    done
    SAVED=$((TOTAL_SRC - TOTAL_COMPACT))
    if [ "$TOTAL_SRC" -gt 0 ]; then
        RATIO=$(echo "scale=1; $SAVED * 100 / $TOTAL_SRC" | bc 2>/dev/null || echo "0")
    else
        RATIO="0"
    fi
    ${PYTHON_BIN:-python3} -c "
import json, os, time
tf = '$STATE_DIR/token-savings.json'
tl = '$STATE_DIR/token-savings.jsonl'
d = {}
if os.path.exists(tf):
    try:
        with open(tf) as f: d = json.load(f)
    except: pass
# 本会话
session = {
    'ts': '$(date -u +%Y-%m-%dT%H:%M:%SZ)',
    'source_bytes': $TOTAL_SRC,
    'compact_bytes': $TOTAL_COMPACT,
    'saved_bytes': $SAVED,
    'ratio_pct': float($RATIO),
    'session_id': '${SESSION_ID:-unknown}'
}
d['session_bytes'] = $SAVED
d['session_source_bytes'] = $TOTAL_SRC
d['session_compact_bytes'] = $TOTAL_COMPACT
d['session_ratio_pct'] = float($RATIO)
d['cumulative_bytes'] = d.get('cumulative_bytes', 0) + $SAVED
d['cumulative_events'] = d.get('cumulative_events', 0) + 1
d['last_updated'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
with open(tf, 'w') as f: json.dump(d, f)
# 跨会话时间序列 (JSONL追加)
with open(tl, 'a') as f: f.write(json.dumps(session) + '\n')
" 2>/dev/null || true
    echo "[context-compressor] 💰 本次(输入侧): ${RATIO}% | 累计: $(${PYTHON_BIN:-python3} -c \"import json;d=json.load(open('$STATE_DIR/token-savings.json'));print(f'{d.get(\\\"cumulative_events\\\",0)}次 {d.get(\\\"cumulative_bytes\\\",0)}bytes')\" 2>/dev/null)" >&2
else
    echo "[context-compressor] ⚠️ 部分 compact 文件缺失，缓存不完整" >&2
fi
exit 0  # 永不阻断
