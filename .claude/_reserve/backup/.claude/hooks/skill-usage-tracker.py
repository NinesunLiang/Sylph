#!/usr/bin/env python3
"""skill-usage-tracker.py — UserPromptSubmit|PostToolUse:Skill — 记录 skill 调用频率
Role: 无侵入 skill 使用率追踪 — 双路径: UserPromptSubmit + PostToolUse:Skill
"""
import json
import os
import re
import sys
import time
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, flywheel_event


def main():
    # ── Guard ──
    if not hc_enabled("skill_usage_tracker"):
        print('{"continue": true}')
        sys.exit(0)

    # ── Read stdin ──
    input_str = sys.stdin.read()
    try:
        input_data = json.loads(input_str)
    except json.JSONDecodeError:
        print('{"continue": true}')
        sys.exit(0)

    # ── Path setup ──
    hooks_dir = Path(__file__).resolve().parent
    log_dir = (hooks_dir / "../.." / ".omc" / "state").resolve()
    os.makedirs(str(log_dir), exist_ok=True)

    skill_usage_log = log_dir / "skill-usage.jsonl"

    # ── Path A: PostToolUse:Skill (CLI args: tool_name from first arg or env) ──
    tool_name = input_data.get("tool_name", "") or os.environ.get("TOOL_NAME", "")

    if tool_name == "Skill":
        tool_input = input_data.get("tool_input", {}) or {}
        skill = tool_input.get("skill", "")
        if skill:
            skill_dir = hooks_dir / ".." / "skills" / skill
            if skill_dir.resolve().is_dir():
                ts = int(time.time())
                entry = json.dumps({"skill": skill, "ts": ts}, ensure_ascii=True)
                with open(str(skill_usage_log), "a", encoding="utf-8") as f:
                    f.write(entry + "\n")
                flywheel_event("skill_usage_tracker", "skill_invoked", "P2", skill)

        print('{"continue": true}')
        sys.exit(0)

    # ── Path B: UserPromptSubmit — scan for /lx-xxx commands ──
    prompt = input_data.get("prompt", "")
    if not prompt:
        print('{"continue": true}')
        sys.exit(0)

    # Extract skill reference (lx-xxx)
    match = re.search(r"/?(lx-[a-z][a-z0-9-]*)", prompt)
    if not match:
        print('{"continue": true}')
        sys.exit(0)

    skill = match.group(1).lstrip("/")

    skill_dir = hooks_dir / ".." / "skills" / skill
    if not skill_dir.resolve().is_dir():
        print('{"continue": true}')
        sys.exit(0)

    ts = int(time.time())
    entry = json.dumps({"skill": skill, "ts": ts}, ensure_ascii=True)
    with open(str(skill_usage_log), "a", encoding="utf-8") as f:
        f.write(entry + "\n")

    flywheel_event("skill_usage_tracker", "skill_invoked", "P2", skill)

    print('{"continue": true}')
    sys.exit(0)


if __name__ == "__main__":
    main()
