#!/usr/bin/env python3
"""posttool-write-lock.py — PostToolUse:Edit|Write — 写操作后释放 OMA 并发锁
Role: 写操作后释放 OMA 并发锁
"""
import json
import os
import subprocess
import sys
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, hc_project_root, flywheel_event


def main():
    # ── Guard ──
    if not hc_enabled("posttool_write_lock"):
        print('{"continue": true}')
        sys.exit(0)

    # ── Read stdin ──
    input_str = sys.stdin.read()
    try:
        input_data = json.loads(input_str)
    except json.JSONDecodeError:
        print('{"continue": true}')
        sys.exit(0)

    # ── Extract tool_name ──
    tool_name = input_data.get("tool_name", "") or input_data.get("tool", "") or ""

    # Also check args/argv for position-based tool name
    args_data = input_data.get("args", {}) or {}
    if not tool_name:
        tool_name = args_data.get("tool", "") or args_data.get("tool_name", "")

    if not tool_name:
        tool_name = os.environ.get("TOOL_NAME", "")

    tool_name = tool_name.lower()

    # ── Only check Edit/Write/Replace-like tools ──
    if tool_name not in ("edit", "write", "replace", "str_replace"):
        print('{"continue": true}')
        sys.exit(0)

    # ── Extract file_path ──
    file_path = ""
    tool_input = input_data.get("tool_input", {}) or {}
    file_path = tool_input.get("filePath", "") or tool_input.get("file_path", "") or ""

    if not file_path:
        # Try args
        file_path = args_data.get("filePath", "") or args_data.get("file_path", "")

    # ── Release OMA lock ──
    if file_path:
        hooks_dir = Path(__file__).resolve().parent
        project_root = (hooks_dir / "../..").resolve()
        oma_script = project_root / ".claude" / "scripts" / "oma_lock_manager.py"
        if oma_script.exists():
            try:
                subprocess.run(
                    [sys.executable, str(oma_script), "release", file_path],
                    capture_output=True, timeout=5
                )
            except Exception:
                pass

    print('{"continue": true}')
    flywheel_event("posttool_write_lock", "lock_released", "P2", "released")
    sys.exit(0)


if __name__ == "__main__":
    main()
