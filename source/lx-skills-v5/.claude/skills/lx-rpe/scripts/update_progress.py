#!/usr/bin/env python3

"""

update_progress.py — lx-rpe state/progress.md 状态更新 + 链路追踪


用法： python3 update_progress.py --feature <name> --task <RPE-xxx> --action <start|complete|block|unblock>
 python3 update_progress.py --feature <name> --task <RPE-xxx> --action start --step 3 --branch go
 python3 update_progress.py --feature <name> --task <RPE-xxx> --action complete --next RPE-002
v6.0.3 新增：--step / --branch / --phase 参数，写入链路追踪
退出码：0=成功, 1=参数错误, 2=文件操作失败
"""
import argparse, sys, json, re
from pathlib import Path
from datetime import datetime

TRACE_FILE = Path(".omc/state/skill-trace.jsonl")

def write_trace(event: dict):
    """写入链路追踪记录（append JSONL）"""
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = json.dumps({"ts": datetime.now().isoformat(), **event}, ensure_ascii=False)
    with open(TRACE_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")

def get_context_sweetspot_alert():
    try:
        import subprocess, json
        r = subprocess.run("python3 .claude/scripts/context_monitor.py", shell=True, capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            d = json.loads(r.stdout.strip())
            pct = d.get("percentage", 0.0)
            if pct >= 50.0:
                return f"⚠️ [甜点区守卫] 当前上下文占比已达 {pct}% (超过 50% 最佳区间)。为保持最高智商，请勿开启新的 Task。请立即总结进展，并运行 `/compact` 压缩重置会话，或请用户开启新分支，通过读取文档恢复状态后再进行下一步！"
    except Exception:
        pass
    return ""

def main():
    p = argparse.ArgumentParser(description="lx-rpe 进度更新 + 链路追踪")
    p.add_argument("--feature", required=True, help="特性名称")
    p.add_argument("--task", required=True, help="RPE-xxx Task ID")
    p.add_argument("--action", required=True, choices=["start", "complete", "block", "unblock"], help="动作类型")
    p.add_argument("--reason", default="", help="block 原因")
    p.add_argument("--next", default="", help="下一个 Task ID")
    p.add_argument("--step", default="", help="当前 Step 编号（如 3）")
    p.add_argument("--branch", default="", help="执行分支（如 go/node/python/rust）")
    p.add_argument("--phase", default="", help="当前 Phase（如 Phase1/Phase2/Phase3）")
    args = p.parse_args()

    progress_file = Path(f"rpe/{args.feature}/state/progress.md")
    if not progress_file.exists():
        err = {"status": "error", "error": f"progress.md not found: {progress_file}"}
        print(json.dumps(err))
        write_trace({"skill": "lx-rpe", "feature": args.feature, "task": args.task,
                      "action": args.action, "step": args.step, "branch": args.branch,
                      "phase": args.phase, "status": "error", "error": "progress.md not found"})
        sys.exit(2)

    content = progress_file.read_text(encoding="utf-8")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if args.action == "start":
        content = content.replace(f"- [ ] {args.task}", f"- [·] {args.task}")
    elif args.action == "complete":
        content = content.replace(f"- [·] {args.task}", f"- [x] {args.task}")
        content = content.replace(f"- [ ] {args.task}", f"- [x] {args.task}")
        if args.next:
            content = re.sub(r"(- 下一步：).*", f"\\1{args.next}", content)
    elif args.action == "block":
        marker = f"🚫 BLOCKED [{now}]"
        if args.reason:
            marker += f": {args.reason}"
        content = content.replace(f"- [·] {args.task}", f"- [·] {args.task} {marker}")
    elif args.action == "unblock":
        content = re.sub(rf"( {re.escape(args.task)}) 🚫 BLOCKED[^\n]*", r"\1", content)

    if args.step or args.branch or args.phase:
        trace_comment = f" <!-- trace: {now}"
        if args.phase:
            trace_comment += f" phase={args.phase}"
        if args.step:
            trace_comment += f" step={args.step}"
        if args.branch:
            trace_comment += f" branch={args.branch}"
        trace_comment += f" action={args.action} -->"
        content = content.replace(
            f"- [·] {args.task}", f"- [·] {args.task}\n{trace_comment}"
        ).replace(f"- [x] {args.task}", f"- [x] {args.task}\n{trace_comment}")

    progress_file.write_text(content, encoding="utf-8")

    write_trace({"skill": "lx-rpe", "feature": args.feature, "task": args.task,
                  "action": args.action, "step": args.step, "branch": args.branch,
                  "phase": args.phase, "status": "success", "file": str(progress_file)})

    print(json.dumps({"status": "success", "feature": args.feature, "task": args.task,
                       "action": args.action, "step": args.step, "branch": args.branch,
                       "phase": args.phase, "file": str(progress_file)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
