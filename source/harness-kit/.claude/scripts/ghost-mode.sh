#!/usr/bin/env bash
# ghost-mode.sh — 切换幽灵模式/无人值守模式统一开关
# 用法: ghost-mode on|off|status|set <key> <value>|poll
# 幽灵模式: AI 按方向持续探索，不干扰人，默认 3h 过期
# 同时创建 autonomous.active 信号供所有 hook 降级

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
mkdir -p "$STATE_DIR" 2>/dev/null

MODE_FILE="$STATE_DIR/ghost-mode.json"

case "${1:-status}" in
    on)
        DIRECTION="${2:-自主探索和修复系统问题}"
        INTERVAL="${3:-600}"
        EXPIRY_HOURS="${4:-3}"
        EXPIRES=$(python3 -c "from datetime import datetime,timedelta; print((datetime.now()+timedelta(hours=$EXPIRY_HOURS)).isoformat())" 2>/dev/null)
        # 原子写入 ghost-mode.json
        tmp="${MODE_FILE}.tmp.$$"
        cat > "$tmp" <<JSON
{
  "active": true,
  "mode": "ghost",
  "direction": "$DIRECTION",
  "cycle_interval_seconds": $INTERVAL,
  "expires_at": "$EXPIRES",
  "activated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "retry_count": 0,
  "skipped_risks": []
}
JSON
        mv -f "$tmp" "$MODE_FILE" 2>/dev/null
        # 创建 autonomous.active 信号供 completion-gate 等降级
        touch "$STATE_DIR/autonomous.active"
        # 清理旧格式文件
        rm -f "$STATE_DIR/.unattended-mode" 2>/dev/null
        echo "✅ 幽灵模式已开启 — 方向: $DIRECTION, 每 ${INTERVAL}s 轮询, ${EXPIRY_HOURS}h 过期"
        echo "   autonomous.active 信号已创建，所有 hook 降级为 warn-only"
        echo "   调用 /loop ${INTERVAL}s ghost-mode.sh poll 驱动探索轮次"
        ;;

    off)
        if [ -f "$MODE_FILE" ]; then
            rm -f "$MODE_FILE"
        fi
        # 清理所有信号文件
        rm -f "$STATE_DIR/ghost-mode.active" 2>/dev/null
        rm -f "$STATE_DIR/autonomous.active" 2>/dev/null
        rm -f "$STATE_DIR/.unattended-mode" 2>/dev/null
        # 也清理 unattended-mode.json
        rm -f "$STATE_DIR/unattended-mode.json" 2>/dev/null
        echo "✅ 幽灵模式已关闭，所有 hook 恢复正常阻断"
        ;;

    status)
        if [ -f "$MODE_FILE" ]; then
            DIR=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('direction','?'))" 2>/dev/null)
            EXP=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('expires_at','无'))" 2>/dev/null)
            INT=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('cycle_interval_seconds','?'))" 2>/dev/null)
            echo "📋 幽灵模式: 🟢 开启中"
            echo "   方向: $DIR"
            echo "   间隔: ${INT}s"
            echo "   过期: $EXP"
        else
            echo "📋 幽灵模式: ⚪ 已关闭"
        fi
        if [ -f "$STATE_DIR/ghost-mode.active" ]; then
            echo "   旧格式 ghost-mode.active 存在（兼容）"
        fi
        if [ -f "$STATE_DIR/autonomous.active" ]; then
            echo "   autonomous.active 信号: ✅ 存在"
        fi
        ;;

    set)
        # 动态修改配置字段
        KEY="$2"
        VALUE="$3"
        if [ ! -f "$MODE_FILE" ]; then
            echo "❌ 幽灵模式未开启，无法修改"
            exit 1
        fi
        python3 -c "
import json
d = json.load(open('$MODE_FILE'))
d['$KEY'] = $VALUE
json.dump(d, open('$MODE_FILE','w'), indent=2)
" 2>/dev/null && echo "✅ 幽灵模式 $KEY 已更新为 $VALUE" || echo "❌ 更新失败"
        ;;

    poll)
        # ghost mode 轮询入口 — 由 loop skill 调用
        if [ ! -f "$MODE_FILE" ]; then
            echo "❌ 幽灵模式未激活，停止轮询"
            exit 1
        fi
        echo "=== 幽灵轮询 [$(date -u +%Y-%m-%dT%H:%M:%SZ)] ==="
        DIR=$(python3 -c "import json; d=json.load(open('$MODE_FILE')); print(d.get('direction','?'))" 2>/dev/null)
        echo "  方向: $DIR"
        # 状态面板：检查活跃特征 + 未提交变更
        if [ -d "$PROJECT_ROOT/rpe" ]; then
            ACTIVE=$(ls "$PROJECT_ROOT/rpe/" 2>/dev/null | head -5 | tr '\n' ' ')
            [ -n "$ACTIVE" ] && echo "  活跃特征: $ACTIVE"
        fi
        MODIFIED=$(cd "$PROJECT_ROOT" && git diff --name-only 2>/dev/null | head -10 | tr '\n' ' ')
        [ -n "$MODIFIED" ] && echo "  未提交变更: $MODIFIED"
        BLOCKED=$(ls "$PROJECT_ROOT/.omc/state/skipped-errors.md" 2>/dev/null && wc -l < "$PROJECT_ROOT/.omc/state/skipped-errors.md" 2>/dev/null || echo 0)
        echo "  已跳过风险数: ${BLOCKED}"
        echo "  命令: 自主探索并修复 ${DIR}，发现问题自行修复（最多 3 次），无法处理的记录等待人工"
        ;;

    *)
        echo "用法: ghost-mode on|off|status|set <key> <value>"
        echo ""
        echo "子命令:"
        echo "  ghost-mode on \"方向描述\" [间隔秒数=600] [过期小时=3]"
        echo "  ghost-mode off"
        echo "  ghost-mode status"
        echo "  ghost-mode set <json_key> <json_value>"
        echo "  ghost-mode poll  (loop skill 轮询入口)"
        exit 1
        ;;
esac
