#!/usr/bin/env python3
"""
pipeline-step.py — Lightweight pipeline step tracker for C3 流程结构化
Python 移植版，完全等价 pipeline-step.sh v1.0

Tracks current step in L3/L4 task pipeline across sessions.
State file: .omc/state/pipeline-step.json

Commands:
  get       — Print current pipeline step
  set N     — Set step to N (0-7)
  advance   — Advance to next step
  inject    — Inject pipeline context (for hooks)
  status    — Full status with timestamp

用法: python3 pipeline-step.py {get|set N|advance|inject|status}
"""

import json
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
STATE_FILE = STATE_DIR / "pipeline-step.json"

STEPS = [
    "idle:当前无活跃任务",
    "列方案(澄清):澄清需求、列出候选方案",
    "细分最小可验证步骤:拆解为独立可验证子步骤",
    "实现:按 step 清单逐一实现，范围冻结",
    "Debug:收集错误按依赖排序修复，3 轮上限",
    "强证据验收:逐条核对完成标准",
    "Oracle专家复验:对抗性审查",
    "下一步(循环):全量回归→判断终止",
]


def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def _read_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _write_state(data: dict):
    _ensure_dir(STATE_FILE.parent)
    STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_step() -> int:
    data = _read_state()
    return data.get("step", 0)


def set_step(step: int):
    data = {"step": step, "updated": int(time.time())}
    _write_state(data)


def cmd_get():
    step = get_step()
    label = STEPS[step].split(":", 1)[0] if step < len(STEPS) else "?"
    print(f"{step}: {label}")


def cmd_set(args: list[str]):
    try:
        step = int(args[0]) if args else 0
    except ValueError:
        step = 0
    if step < 0:
        step = 0
    if step > 7:
        step = 7
    set_step(step)
    label = STEPS[step].split(":", 1)[0] if step < len(STEPS) else "?"
    print(f"pipeline-step → {step}: {label}")


def cmd_advance():
    cur = get_step()
    nxt = min(cur + 1, 7)
    set_step(nxt)
    cur_label = STEPS[cur].split(":", 1)[0] if cur < len(STEPS) else "?"
    nxt_label = STEPS[nxt].split(":", 1)[0] if nxt < len(STEPS) else "?"
    print(f"pipeline-step: {cur_label} → {nxt_label}")


def cmd_inject():
    step = get_step()
    if step < len(STEPS):
        label, desc = STEPS[step].split(":", 1)
    else:
        label = "?"
        desc = ""
    print(f"[Pipeline Step {step}/7] {label} — {desc}")


def cmd_status():
    step = get_step()
    print(f"Pipeline Step: {step}/7")
    for i, s in enumerate(STEPS):
        label = s.split(":", 1)[0]
        marker = ">" if i == step else " "
        print(f"  {marker} [{i}] {label}")
    if STATE_FILE.exists():
        data = _read_state()
        updated = data.get("updated", "?")
        print(f"Last updated: {updated}")


def print_usage():
    print("Usage: pipeline-step.py {get|set N|advance|inject|status}", file=sys.stderr)


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "get"

    if cmd == "get":
        cmd_get()
    elif cmd == "set":
        cmd_set(args[1:])
    elif cmd == "advance":
        cmd_advance()
    elif cmd == "inject":
        cmd_inject()
    elif cmd == "status":
        cmd_status()
    else:
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
