#!/usr/bin/env bash
# escape-patch-apply.sh — Error-DNA 补丁应用器
# Role: 读取 escape-patches.json，经 Oracle/人工审核后应用补丁，关闭逃逸通道
# 用法: escape-patch-apply.sh [status|apply <key>|reject <key>|history]
# 哲学 #6: 不自动打补丁 — 所有补丁必须经人工/Oracle 审核

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STATE_DIR="$PROJECT_ROOT/.omc/state"
PATCH_FILE="$STATE_DIR/escape-patches.json"
HISTORY_FILE="$STATE_DIR/escape-patch-history.jsonl"
mkdir -p "$STATE_DIR" 2>/dev/null

case "${1:-status}" in
    status)
        if [ ! -f "$PATCH_FILE" ]; then
            echo "📋 Error-DNA 补丁队列: 空 — 无待处理补丁"
            exit 0
        fi
        echo "📋 Error-DNA 补丁队列:"
        python3 - "$PATCH_FILE" <<'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    patches = json.load(f)
if not patches:
    print("  ✅ 所有补丁已处理完毕")
    sys.exit(0)
status_emoji = {'pending': '🟡', 'applied': '🟢', 'rejected': '🔴'}
for key, p in sorted(patches.items()):
    emoji = status_emoji.get(p.get('status', 'pending'), '⚪')
    print(f"  {emoji} [{key}] {p.get('severity','?')} | {p.get('target','?')}")
    print(f"      建议: {p.get('recommendation','')[:120]}")
    print(f"      状态: {p.get('status','?')} | ts={p.get('ts','?')}")
    print("")
PYEOF
        echo "操作: escape-patch-apply.sh apply <key> | reject <key> | history"
        ;;

    apply)
        KEY="${2:-}"
        [ -z "$KEY" ] && { echo "❌ 用法: escape-patch-apply.sh apply <key>"; exit 1; }
        [ ! -f "$PATCH_FILE" ] && { echo "❌ 无补丁文件"; exit 1; }
        
        PATCH_DETAIL=$(python3 - "$PATCH_FILE" "$KEY" <<'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    patches = json.load(f)
p = patches.get(sys.argv[2])
if not p: print("NOT_FOUND"); sys.exit(0)
print(f"类型: {p['type']}\n目标: {p['target']}\n严重性: {p['severity']}")
print(f"建议: {p['recommendation']}\n命令: {p.get('command','')[:200]}")
PYEOF
)
        [ "$PATCH_DETAIL" = "NOT_FOUND" ] && { echo "❌ 补丁 '$KEY' 不存在"; exit 1; }

        echo "═══════════════════════════════════════"
        echo "  Error-DNA 补丁审核 (Oracle 门禁)"
        echo "═══════════════════════════════════════"
        echo "$PATCH_DETAIL"
        echo "───────────────────────────────────────"
        echo ""
        echo "确认应用补丁？输入 'yes' 确认:"
        read -r CONFIRM
        [ "$CONFIRM" != "yes" ] && { echo "❌ 已取消"; exit 0; }

        python3 - "$PATCH_FILE" "$KEY" "$HISTORY_FILE" <<'PYEOF'
import json, sys, time
patch_file, key, history_file = sys.argv[1], sys.argv[2], sys.argv[3]
with open(patch_file) as f:
    patches = json.load(f)
patches[key]['status'] = 'applied'
patches[key]['applied_at'] = int(time.time())
with open(patch_file, 'w') as f:
    json.dump(patches, f, indent=2, ensure_ascii=False)
entry = {'key': key, 'action': 'applied', 'type': patches[key]['type'], 'ts': int(time.time())}
with open(history_file, 'a') as f:
    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
print(f"✅ 补丁 '{key}' 已应用")
PYEOF
        echo "⚠️  请按建议手动修改相关文件，然后运行 smoke test 验证。"
        ;;

    reject)
        KEY="${2:-}"
        [ -z "$KEY" ] && { echo "❌ 用法: escape-patch-apply.sh reject <key>"; exit 1; }
        echo "拒绝原因（可选）:"
        read -r REASON
        python3 - "$PATCH_FILE" "$KEY" "$HISTORY_FILE" "${REASON:-无}" <<'PYEOF'
import json, sys, time
patch_file, key, history_file = sys.argv[1], sys.argv[2], sys.argv[3]
reason = sys.argv[4] if len(sys.argv) > 4 else ''
with open(patch_file) as f:
    patches = json.load(f)
patches[key]['status'] = 'rejected'
patches[key]['rejected_at'] = int(time.time())
patches[key]['reject_reason'] = reason
with open(patch_file, 'w') as f:
    json.dump(patches, f, indent=2, ensure_ascii=False)
entry = {'key': key, 'action': 'rejected', 'type': patches[key]['type'], 'ts': int(time.time()), 'reason': reason}
with open(history_file, 'a') as f:
    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
print(f"🔴 补丁 '{key}' 已拒绝")
PYEOF
        ;;

    history)
        [ ! -f "$HISTORY_FILE" ] && { echo "📋 补丁历史: 空"; exit 0; }
        echo "📋 Error-DNA 补丁历史:"
        python3 - "$HISTORY_FILE" <<'PYEOF'
import json, sys
with open(sys.argv[1]) as f:
    entries = [json.loads(l) for l in f if l.strip()]
for e in entries[-20:]:
    emoji = '🟢' if e['action'] == 'applied' else '🔴'
    print(f"  {emoji} [{e['key']}] {e['action']} | {e['type']}")
print(f"  总计: {len(entries)} 条")
PYEOF
        ;;

    *)
        echo "用法: escape-patch-apply.sh [status|apply <key>|reject <key>|history]"
        echo "流程: detect → record → review → apply/reject → verify"
        echo "哲学 #6: 不自动打补丁 — 所有补丁必须经人工/Oracle 审核"
        exit 1
        ;;
esac
