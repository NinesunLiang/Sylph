#!/usr/bin/env bash
# compact-detect.sh — UserPromptSubmit — /compact 后知识恢复（压缩版）
# Role: 检测 /compact → 注入压缩知识 → 防 AI 失忆
# v2: 去装饰边框 + 指向 context-cache + 去冗余提取

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

source "$SCRIPT_DIR/harness_config.sh" 2>/dev/null || true
set -f
command -v hc_enabled &>/dev/null || { hc_enabled() { return 1; }; }
hc_enabled "compact_detect" || exit 0

STATE_DIR="$PROJECT_ROOT/.omc/state"
INDEX_FILE="$STATE_DIR/token-tracking-index.json"
COMPACT_STATE="$STATE_DIR/token-compact-state.json"

INPUT=$(cat 2>/dev/null || echo "")
CLEAN_INPUT=$(echo "$INPUT" | sed 's/\x1b\[[0-9;]*m//g' | tr -d '[:space:]')

case "$CLEAN_INPUT" in
    /compact|compact|/compact*) ;;
    *) exit 0 ;;
esac

mkdir -p "$STATE_DIR" 2>/dev/null || exit 0

# 读取当前 usage
USAGE=0
if [ -f "$INDEX_FILE" ]; then
    USAGE=$(python3 -c "import json;d=json.load(open('$INDEX_FILE'));print(d.get('usage',0))" 2>/dev/null || echo 0)
fi

cat > "$COMPACT_STATE" <<EOF
{"pre_compact_usage": $USAGE, "detected_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date +%s)"}
EOF

# ═══ /compact 后知识注入（压缩版） ═══
echo ""
echo "[/compact] 知识恢复中..."


# 强制刷新缓存（防会话中期源文件变更导致陈旧 — Meta-Oracle F2）
bash "$SCRIPT_DIR/context-compressor.sh" 2>/dev/null || true

# 注入 context-cache（核心规则，~4KB，一次性全覆）
CACHE="$PROJECT_ROOT/.omc/state/context-cache.md"
if [ -f "$CACHE" ]; then
    cat "$CACHE"
else
    echo "铁律: 禁止编造(file:line)/用户裁定(Boss)/证据门禁(VERIFIED)/Git门禁(编译→功能→报告→批准→提交)/范围冻结/隐私防线/断言真实/哲学先行"
    echo "禁词: 应该没问题/基本完成/理论上/should be fine/basically done"
    echo "约束: Read-before-Edit|rm -rf→BLOCKED|gh CLI write→BLOCKED|>100MB→先汇报|完成=VERIFIED"
    echo "权威: Boss>宪法>PRD>Skill>设计>代码"
fi

# 注入 kernel 架构铁律速查（约 10 行）
INJECT_KERNEL="$PROJECT_ROOT/.claude/kernel.md"
if [ -f "$INJECT_KERNEL" ]; then
    echo ""
    echo "--- 架构铁律 ---"
    grep -E '^\*\*|^## ' "$INJECT_KERNEL" 2>/dev/null | head -8
fi

# 注入会话状态恢复
if [ -f "$PROJECT_ROOT/.omc/state/session-handoff.md" ]; then
    echo ""
    echo "--- 会话交接 ---"
    grep -E '^## |Feature:|进度:|关键决策' "$PROJECT_ROOT/.omc/state/session-handoff.md" 2>/dev/null | head -8
fi
if [ -f "$PROJECT_ROOT/.omc/state/todo-queue.md" ]; then
    echo "▪ Todo:"
    head -8 "$PROJECT_ROOT/.omc/state/todo-queue.md" 2>/dev/null
fi

# session-dump 恢复
SESSION_DUMP="$PROJECT_ROOT/.omc/state/session-dump.json"
if [ -f "$SESSION_DUMP" ]; then
    python3 -c "
import json
try:
    d=json.load(open('$SESSION_DUMP'))
except: exit(0)
gs=d.get('git_state',{})
mf=gs.get('modified_files',[])
if mf: print('▪ 更改文件(%d): %s'%(len(mf),', '.join(mf[:4])))
af=d.get('active_features',[])
if af:
    names=[str(a.get('name',a)) if isinstance(a,dict) else str(a) for a in af]
    print('▪ 活跃: %s'%' | '.join(names[:3]))
el=d.get('edit_log',[])
if el: print('▪ 编辑: %d文件'%len(el))
" 2>/dev/null || true
fi

echo ""
echo "[/compact] 知识已恢复。"
echo ""

flywheel_event "compact_detect" "compact_detected" "P2" "compact_detected"
exit 0
