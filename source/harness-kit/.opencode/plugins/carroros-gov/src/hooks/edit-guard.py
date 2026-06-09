#!/usr/bin/env python3
"""
edit-guard.py — PreToolUse:Edit — 编辑源文件前强制先 Read，实施 Read-before-Edit 门禁
Role: 编辑源文件前强制先 Read，实施 Read-before-Edit 门禁
对应 edit-guard.sh 的 Python 移植，保持完全相同的逻辑
"""

import json
import os
import re
import sys
from pathlib import Path

# Import shared library
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness_lib import (
    hc_enabled,
    is_mode_active,
    hc_get,
    flywheel_event,
    hc_emit_hook_json,
    agentic_menu,
)

# ─── Path setup ───
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
READ_LOG = STATE_DIR / "read-tracker.txt"


def main():
    # ── Guard: check if edit_guard is enabled ──
    if not hc_enabled("edit_guard"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Read stdin JSON ──
    input_str = sys.stdin.read()
    try:
        input_data = json.loads(input_str)
    except json.JSONDecodeError:
        # Invalid JSON → fail-open
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Mode detection: ghost/goal → skip Read-before-Edit gate ──
    mode = is_mode_active(str(STATE_DIR))
    if mode != "normal":
        msg = f"⚠️ {mode}模式: 跳过 Read-before-Edit 检查"
        print(hc_emit_hook_json(msg, "PreToolUse", True))
        sys.exit(0)

    # ── Extract file_path (two possible locations) ──
    tool_input = input_data.get("tool_input", {}) or {}
    args = input_data.get("args", {}) or {}
    file_path = tool_input.get("file_path", "") or args.get("filePath", "") or ""

    if not file_path:
        # No path → fail-open
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Check source extension match ──
    source_ext_str = hc_get("project.source_extensions", "*.go")
    source_ext_list = source_ext_str.split() if source_ext_str else ["*.go"]

    basename = os.path.basename(file_path)
    matched = False
    for ext in source_ext_list:
        ext = ext.strip()
        if not ext:
            continue
        # Convert shell glob pattern (*.go, *.py, etc.) to regex
        pattern = re.escape(ext).replace(r"\*", ".*")
        pattern = "^" + pattern + "$"
        if re.match(pattern, basename, re.IGNORECASE):
            matched = True
            break

    if not matched:
        # Not a source file → pass through
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Normalize path ──
    try:
        real_path = str(Path(file_path).resolve())
    except Exception:
        real_path = file_path

    # ── Fail-open: read-tracker doesn't exist ──
    if not READ_LOG.exists():
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Check if file was already read (exact line match) ──
    try:
        read_lines = READ_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in read_lines:
            if line.strip() == real_path:
                print(json.dumps({"continue": True}))
                sys.exit(0)
    except Exception:
        pass

    # ── Block: file not read yet ──
    # Double check mode again (mirrors shell script logic)
    mode2 = is_mode_active(str(STATE_DIR))
    if mode2 != "normal":
        print("[edit-guard] 自主模式: 跳过 Read-before-Edit 检查", file=sys.stderr)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    flywheel_event("edit_guard", "blocked", "P2")
    agentic_menu(
        "Read-before-Edit",
        f"文件: {file_path} — 宪法第六条: 修改代码前必须先阅读当前内容",
        "先 Read 再编辑", f"Read {file_path} 后再进行编辑操作",
        "强制编辑", "跳过 Read 检查，直接编辑",
    )


if __name__ == "__main__":
    main()
