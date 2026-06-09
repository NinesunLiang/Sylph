#!/usr/bin/env python3
"""pretool-blast-radius.py — PreToolUse:Bash — 全局破坏性命令拦截 (DG-101)
Role: 检测 git checkout . / rm -rf 等全量操作，提醒改用选择性路径
"""
import json
import re
import sys
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, flywheel_event


def main():
    # ── Guard ──
    if not hc_enabled("blast_radius"):
        print('{"continue": true}')
        sys.exit(0)

    # ── Read stdin ──
    input_str = sys.stdin.read()
    if not input_str:
        print('{"continue": true}')
        sys.exit(0)

    try:
        input_data = json.loads(input_str)
    except json.JSONDecodeError:
        print('{"continue": true}')
        sys.exit(0)

    # ── Extract command ──
    tool_input = input_data.get("tool_input", {}) or {}
    args_data = input_data.get("args", {}) or {}
    command = tool_input.get("command", "") or args_data.get("command", "") or ""

    if not command:
        print('{"continue": true}')
        sys.exit(0)

    # ═══ Hard block: git checkout . (DG-100 root cause) ═══
    # 1a: git checkout . (full revert — DG-100 root cause)
    if re.search(r'git checkout (HEAD )?(-- )?\.(\s|;|$|\||&)', command):
        sys.stderr.write("[blast-radius] 🔴 硬阻断: 'git checkout .' 会全量恢复所有文件。\n")
        sys.stderr.write("[blast-radius]    DG-100: 本操作曾在 2026-05-22 导致 71 文件静默退化。\n")
        sys.stderr.write("[blast-radius]    正确做法: git checkout HEAD -- path/to/specific/file\n")
        flywheel_event("blast_radius", "blocked_checkout_dot", "P0", f"cmd={command[:80]}")
        result = {
            "continue": True,
            "reason": "git checkout . 全量回退已被 blast-radius 硬阻断 (DG-100)。请改用选择性路径恢复。"
        }
        print(json.dumps(result, ensure_ascii=True))
        sys.exit(2)

    # 1b: git reset --hard (full revert variant — Oracle discovery)
    if re.search(r'git reset --hard(\s|;|$|\||&)', command):
        sys.stderr.write("[blast-radius] 🔴 硬阻断: 'git reset --hard' 会丢弃所有未提交修改。\n")
        sys.stderr.write("[blast-radius]    DG-100: 此操作等同于 'git checkout .' 的全量回退效果。\n")
        flywheel_event("blast_radius", "blocked_reset_hard", "P0", f"cmd={command[:80]}")
        result = {
            "continue": True,
            "reason": "git reset --hard 全量回退已被 blast-radius 硬阻断 (DG-100)。"
        }
        print(json.dumps(result, ensure_ascii=True))
        sys.exit(2)

    warn = ""

    # 2. git checkout -- without specific file path
    if re.search(r'git checkout --($| )', command) and "/" not in command:
        warn = "[blast-radius] ⚠️  'git checkout --' 未指定具体文件路径，可能误恢复。"

    # 3. git add -A / git add . (full staging)
    if not warn and re.search(r'git add (-A|--all|\.)', command):
        warn = "[blast-radius] ⚠️  'git add -A' 会暂存所有文件。确认无敏感文件混入 (检查 .gitignore)。"

    # 4. package-release.sh run reminder
    if not warn and "package-release.sh" in command:
        warn = "[blast-radius] 📦 打包前建议先跑: bash .claude/scripts/audit-hooks.sh --check-source-mirror"

    if warn:
        sys.stderr.write(warn + "\n")
        flywheel_event("blast_radius", "warned", "P3", f"cmd={command[:80]}")

    print('{"continue": true}')
    sys.exit(0)


if __name__ == "__main__":
    main()
