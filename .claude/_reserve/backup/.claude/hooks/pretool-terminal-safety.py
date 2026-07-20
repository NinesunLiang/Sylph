#!/usr/bin/env python3
"""
pretool-terminal-safety.py — PreToolUse:Bash — 终端命令格式校验
永不阻断 (exit 0) 但超长命令(>2000字符)除外 — 告警+flywheel, >2000字符硬阻断
"""

import json
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, hc_get, flywheel_event, hc_emit_hook_json


def main():
    if not hc_enabled("pretool_terminal_safety"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    try:
        input_data = sys.stdin.read()
    except Exception:
        input_data = ""

    cmd = ""
    if input_data.strip():
        try:
            parsed = json.loads(input_data)
            ti = parsed.get("tool_input", {}) or {}
            cmd = ti.get("command", "") or parsed.get("args", {}).get("command", "") or ""
        except (json.JSONDecodeError, Exception):
            pass

    if not cmd:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    warnings = []

    # Rule 1: python3 -c with complex code (>100 chars)
    if re.search(r'(?:python3|python)\s+-c', cmd) and len(cmd) > 100:
        warnings.append(
            f"[terminal-safety] python3 -c过长({len(cmd)}字符) "
            f"→ 建议用 python3 << 'PY' heredoc"
        )

    # Rule 2: git chain (git .*&&.*git)
    if re.search(r'git\s+.*&&.*git', cmd):
        warnings.append(
            "[terminal-safety] git链式操作 → 建议拆分: git add / git commit / git push 各一行"
        )

    # Rule 4: git commit with #
    if re.search(r'git\s+commit.*#\s*[0-9]', cmd):
        warnings.append(
            "[terminal-safety] git commit含# → 可能被截断, 改用中文冒号或括号"
        )

    # Rule 6: long python3 -c (>120 chars) — WARNING only
    if re.search(r'(?:python3|python)\s+-c', cmd) and len(cmd) > 120:
        warnings.append(
            f"[terminal-safety] python3 -c过长({len(cmd)}字符) "
            f"→ 建议用 python3 << 'PY' heredoc 或 Write 脚本文件"
        )

    # Rule 6b: any command > max_command_length chars → HARD BLOCK
    try:
        max_cmd_len = int(hc_get("terminal_safety.max_command_length", "2000"))
    except (ValueError, TypeError):
        max_cmd_len = 2000

    if len(cmd) > max_cmd_len:
        import datetime
        script_name = f"scripts/task-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.sh"
        msg = (
            f"🛑 [terminal-safety·Rule6] 命令超过{max_cmd_len}字符 ({len(cmd)}字符) — 不可复制执行\n"
            f"   AI 必须用 Write 创建: {script_name}"
        )
        print(msg, file=sys.stderr)
        flywheel_event("pretool_terminal_safety", "blocked_long_command", "P1", f"len={len(cmd)}")
        result = hc_emit_hook_json(
            f"[terminal-safety·Rule6] 命令过长({len(cmd)}字符)，请用 Write 创建脚本文件。",
            "PreToolUse",
            True
        )
        print(result)
        sys.exit(2)

    # Rule 3: path pile-up
    path_matches = re.findall(r'[^\s]+\.(?:go|py|ts|js|sh|yaml|json|md|rs|rb|java|css|html|toml)', cmd)
    path_count = len(path_matches)
    if path_count > 8:
        warnings.append(
            f"[terminal-safety] 路径堆砌({path_count}个文件) → 建议每行一个文件"
        )

    if warnings:
        for w in warnings:
            print(w, file=sys.stderr)
        flywheel_event("pretool_terminal_safety", "warned", "P2", f"patterns={len(warnings)}")

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
