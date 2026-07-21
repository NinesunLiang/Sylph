#!/usr/bin/env python3
"""read-tracker.py — PostToolUse:Read — 记录已读文件路径供 edit-guard 检查 Read-before-Edit
Role: 记录已读文件路径供 edit-guard 检查 Read-before-Edit
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, hc_get, flywheel_event


def main():
    # ── Guard ──
    if not hc_enabled("read_tracker"):
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
    project_root = (hooks_dir / "../..").resolve()
    state_dir = project_root / ".omc" / "state"
    read_log = state_dir / "read-tracker.txt"

    # ── Extract file_path ──
    tool_input = input_data.get("tool_input", {}) or {}
    args_data = input_data.get("args", {}) or {}
    file_path = tool_input.get("file_path", "") or args_data.get("filePath", "") or ""

    if not file_path:
        print('{"continue": true}')
        sys.exit(0)

    # ── Normalize path ──
    try:
        # Try realpath equivalent
        real_path = str(Path(file_path).resolve())
    except Exception:
        real_path = file_path

    # ── Ensure state dir exists ──
    os.makedirs(str(state_dir), exist_ok=True)

    # ── Rotation: check line count ──
    rotation_line_count = int(hc_get("read_tracker.rotation_line_count", "500"))
    archive_gens = int(hc_get("read_tracker.archive_generations", "4"))

    if read_log.exists():
        try:
            line_count = len(read_log.read_text(encoding="utf-8", errors="replace").splitlines())
        except Exception:
            line_count = 0

        if line_count > rotation_line_count:
            # Rotate: shift archive files
            i = archive_gens
            while i >= 1:
                src = read_log.with_suffix(f".txt.{i}")
                dst = read_log.with_suffix(f".txt.{i + 1}")
                if src.exists():
                    try:
                        src.rename(dst)
                    except Exception:
                        pass
                i -= 1
            if read_log.exists():
                try:
                    read_log.rename(read_log.with_suffix(".txt.1"))
                except Exception:
                    pass

    # ── Dedup: check if already tracked ──
    if read_log.exists():
        try:
            content = read_log.read_text(encoding="utf-8", errors="replace")
            for line in content.splitlines():
                if line.strip() == real_path:
                    print('{"continue": true}')
                    sys.exit(0)
        except Exception:
            pass

    # ── Append ──
    try:
        with open(str(read_log), "a", encoding="utf-8") as f:
            f.write(real_path + "\n")
    except Exception:
        pass

    print('{"continue": true}')
    flywheel_event("read_tracker", "file_read_tracked", "P2", "tracked")
    sys.exit(0)


if __name__ == "__main__":
    main()
