#!/usr/bin/env python3

"""

extract_ac.py — 从 plan.md 提取指定 Task 的 AC 列表

用法：python3 extract_ac.py --feature <name> --task <RPE-xxx>

输出：JSON AC 列表

"""

import argparse, sys, json, re
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--feature", required=True)
    p.add_argument("--task", required=True)
    args = p.parse_args()

    plan_file = Path(f"rpe/{args.feature}/plan.md")
    if not plan_file.exists():
        print(json.dumps({"status": "error", "error": f"plan.md not found: {plan_file}"}))
        sys.exit(2)

    content = plan_file.read_text(encoding="utf-8")
    pattern = rf"(?s)({re.escape(args.task)}.*?)(?=RPE-\d+|\Z)"
    match = re.search(pattern, content)
    if not match:
        print(json.dumps({"status": "not_found", "task": args.task}))
        sys.exit(0)

    task_block = match.group(1)
    ac_items = re.findall(r"- \[.\] (AC-\d+[^:\n]*:[^\n]+)", task_block)
    ac_list = [{"id": m.split(":")[0].strip(), "desc": ":".join(m.split(":")[1:]).strip()} for m in ac_items]

    print(json.dumps({
        "status": "success", "task": args.task,
        "ac_count": len(ac_list), "ac_list": ac_list
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
