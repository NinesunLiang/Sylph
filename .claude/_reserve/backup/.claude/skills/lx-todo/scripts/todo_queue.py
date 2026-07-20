#!/usr/bin/env python3

"""

todo_queue.py — .omc/state/todo-queue.md 读写操作

用法：

 python3 todo_queue.py --action list
 python3 todo_queue.py --action add --type 🐛 --priority P1 --desc "描述" --source "自发现"
 python3 todo_queue.py --action start --id 3
 python3 todo_queue.py --action complete --id 3 --commit abc1234
 python3 todo_queue.py --action upgrade --id 3 --reason "超过3文件"

exit: 0=成功, 1=参数错误, 2=文件操作失败, 3=ID不存在

"""

import argparse, sys, json, re
from pathlib import Path
from datetime import date, datetime


TRACE_FILE = Path(".omc/state/skill-trace.jsonl")

def write_trace(event: dict):
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = json.dumps({"ts": datetime.now().isoformat(), **event}, ensure_ascii=False)
    try:
        with open(TRACE_FILE, "a", encoding="utf-8") as tf:
            tf.write(entry + "\n")
    except:
        pass

QUEUE_FILE = Path(".omc/state/todo-queue.md")

def ensure_file():
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not QUEUE_FILE.exists():
        QUEUE_FILE.write_text("# Todo Queue\n\n## 待处理\n\n## 进行中\n\n## 已完成\n\n## 已升级\n", encoding="utf-8")

def parse_items(content):
    items = []
    for line in content.split('\n'):
        m = re.match(r'- \[(.)\] #(\d+) ([^\s]+) ([^\s]+) (.+?)(?:\s+·\s+(.+))?$', line.strip())
        if m:
            items.append({
                "status": m.group(1), "id": int(m.group(2)), "type": m.group(3),
                "priority": m.group(4), "desc": m.group(5), "meta": m.group(6) or ""
            })
    return items

def next_id(items):
    return max((i["id"] for i in items), default=0) + 1

def format_item(item):
    meta = f" · {item['meta']}" if item.get('meta') else ""
    return f"- [{item['status']}] #{item['id']} {item['type']} {item['priority']} {item['desc']}{meta}"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--action", required=True, choices=["list","add","start","complete","upgrade"])
    p.add_argument("--id", type=int)
    p.add_argument("--type", default="🐛")
    p.add_argument("--priority", default="P2")
    p.add_argument("--desc")
    p.add_argument("--source", default="自发现")
    p.add_argument("--commit")
    p.add_argument("--reason")
    args = p.parse_args()

    ensure_file()
    content = QUEUE_FILE.read_text(encoding="utf-8")
    items = parse_items(content)

    if args.action == "list":
        pending = [i for i in items if i["status"] == " "]
        active = [i for i in items if i["status"] == "·"]
        done = [i for i in items if i["status"] == "x"]
        upgraded = [i for i in items if i["status"] == "↑"]
        print(json.dumps({
            "total": len(items), "pending": len(pending), "active": len(active),
            "done": len(done), "upgraded": len(upgraded),
            "pending_items": pending, "next": pending[0] if pending else None
        }, ensure_ascii=False, indent=2))

    elif args.action == "add":
        if not args.desc:
            print(json.dumps({"error": "缺少 --desc"}))
            sys.exit(1)
        new_item = {
            "status": " ", "id": next_id(items), "type": args.type,
            "priority": args.priority, "desc": args.desc,
            "meta": f"source:{args.source} date:{date.today()}"
        }
        line = format_item(new_item)
        content = content.replace("## 待处理\n", f"## 待处理\n{line}\n")
        QUEUE_FILE.write_text(content, encoding="utf-8")
        write_trace({"skill": "lx-todo", "feature": "todo", "task": f"#{new_item['id']}",
                      "action": "add", "step": "捕获", "status": "success"})
        print(json.dumps({"status":"added", "item": new_item}, ensure_ascii=False))

    elif args.action in ("start", "complete", "upgrade"):
        if not args.id:
            print(json.dumps({"error": "缺少 --id"}))
            sys.exit(1)
        target = next((i for i in items if i["id"] == args.id), None)
        if not target:
            print(json.dumps({"error": f"ID #{args.id} 不存在"}))
            sys.exit(3)

        old_line = format_item(target)
        if args.action == "start":
            target["status"] = "·"
        elif args.action == "complete":
            target["status"] = "x"
            if args.commit:
                target["meta"] = f"{target.get('meta','')} commit:{args.commit}".strip()
        elif args.action == "upgrade":
            target["status"] = "↑"
            if args.reason:
                target["meta"] = f"{target.get('meta','')} reason:{args.reason}".strip()

        new_line = format_item(target)
        content = content.replace(old_line, new_line)
        QUEUE_FILE.write_text(content, encoding="utf-8")

        step_map = {"start": "执行", "complete": "关闭", "upgrade": "升级 lx-task-spec"}
        write_trace({"skill": "lx-todo", "feature": "todo", "task": f"#{target['id']}",
                      "action": args.action, "step": step_map.get(args.action, args.action),
                      "status": "success"})
        print(json.dumps({"status": args.action, "item": target}, ensure_ascii=False))

if __name__ == "__main__":
    main()
