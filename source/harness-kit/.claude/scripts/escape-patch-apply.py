#!/usr/bin/env python3
"""escape-patch-apply.py — Error-DNA 补丁应用器
Cross-platform Python resolution (DG-105)

Role: 读取 escape-patches.json，经 Oracle/人工审核后应用补丁，关闭逃逸通道
用法: escape-patch-apply.py [status|apply <key>|reject <key>|history]
哲学 #6: 不自动打补丁 — 所有补丁必须经人工/Oracle 审核
"""
import sys
import json
import time
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc/state"
PATCH_FILE = STATE_DIR / "escape-patches.json"
HISTORY_FILE = STATE_DIR / "escape-patch-history.jsonl"
STATE_DIR.mkdir(parents=True, exist_ok=True)

action = sys.argv[1] if len(sys.argv) > 1 else "status"

if action == "status":
    if not PATCH_FILE.is_file():
        print("📋 Error-DNA 补丁队列: 空 — 无待处理补丁")
        sys.exit(0)
    print("📋 Error-DNA 补丁队列:")
    with PATCH_FILE.open(encoding="utf-8") as f:
        patches = json.load(f)
    if not patches:
        print("  ✅ 所有补丁已处理完毕")
        sys.exit(0)
    status_emoji = {"pending": "🟡", "applied": "🟢", "rejected": "🔴"}
    for key, p in sorted(patches.items()):
        emoji = status_emoji.get(p.get("status", "pending"), "⚪")
        print(f"  {emoji} [{key}] {p.get('severity','?')} | {p.get('target','?')}")
        print(f"      建议: {p.get('recommendation','')[:120]}")
        print(f"      状态: {p.get('status','?')} | ts={p.get('ts','?')}")
        print("")
    print("操作: escape-patch-apply.py apply <key> | reject <key> | history")

elif action == "apply":
    if len(sys.argv) < 3:
        print("❌ 用法: escape-patch-apply.py apply <key>")
        sys.exit(1)
    KEY = sys.argv[2]
    if not PATCH_FILE.is_file():
        print("❌ 无补丁文件")
        sys.exit(1)

    with PATCH_FILE.open(encoding="utf-8") as f:
        patches = json.load(f)
    p = patches.get(KEY)
    if not p:
        print(f"❌ 补丁 '{KEY}' 不存在")
        sys.exit(1)

    patch_detail = f"类型: {p['type']}\n目标: {p['target']}\n严重性: {p['severity']}\n建议: {p['recommendation']}\n命令: {p.get('command','')[:200]}"

    print("═══════════════════════════════════════")
    print("  Error-DNA 补丁审核 (Oracle 门禁)")
    print("═══════════════════════════════════════")
    print(patch_detail)
    print("───────────────────────────────────────")
    print()
    print("确认应用补丁？输入 'yes' 确认:")
    if sys.stdin.isatty():
        CONFIRM = input().strip()
    else:
        print("❌ 非交互式终端，拒绝自动应用补丁")
        sys.exit(1)
    if CONFIRM != "yes":
        print("❌ 已取消")
        sys.exit(0)

    patches[KEY]["status"] = "applied"
    patches[KEY]["applied_at"] = int(time.time())
    with PATCH_FILE.open("w", encoding="utf-8") as f:
        json.dump(patches, f, indent=2, ensure_ascii=False)
    entry = {"key": KEY, "action": "applied", "type": patches[KEY]["type"], "ts": int(time.time())}
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"✅ 补丁 '{KEY}' 已应用")
    print("⚠️  请按建议手动修改相关文件，然后运行 smoke test 验证。")

elif action == "reject":
    if len(sys.argv) < 3:
        print("❌ 用法: escape-patch-apply.py reject <key>")
        sys.exit(1)
    KEY = sys.argv[2]
    print("拒绝原因（可选）:")
    if sys.stdin.isatty():
        REASON = input().strip()
    else:
        REASON = "非交互式环境，无手动原因"

    with PATCH_FILE.open(encoding="utf-8") as f:
        patches = json.load(f)
    p = patches.get(KEY)
    if not p:
        print(f"❌ 补丁 '{KEY}' 不存在")
        sys.exit(1)
    patches[KEY]["status"] = "rejected"
    patches[KEY]["rejected_at"] = int(time.time())
    patches[KEY]["reject_reason"] = REASON
    with PATCH_FILE.open("w", encoding="utf-8") as f:
        json.dump(patches, f, indent=2, ensure_ascii=False)
    entry = {"key": KEY, "action": "rejected", "type": patches[KEY]["type"], "ts": int(time.time()), "reason": REASON}
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"🔴 补丁 '{KEY}' 已拒绝")

elif action == "history":
    if not HISTORY_FILE.is_file():
        print("📋 补丁历史: 空")
        sys.exit(0)
    print("📋 Error-DNA 补丁历史:")
    with HISTORY_FILE.open(encoding="utf-8") as f:
        entries = [json.loads(l) for l in f if l.strip()]
    for e in entries[-20:]:
        emoji = "🟢" if e["action"] == "applied" else "🔴"
        print(f"  {emoji} [{e['key']}] {e['action']} | {e['type']}")
    print(f"  总计: {len(entries)} 条")

else:
    print("用法: escape-patch-apply.py [status|apply <key>|reject <key>|history]")
    print("流程: detect → record → review → apply/reject → verify")
    print("哲学 #6: 不自动打补丁 — 所有补丁必须经人工/Oracle 审核")
    sys.exit(1)
