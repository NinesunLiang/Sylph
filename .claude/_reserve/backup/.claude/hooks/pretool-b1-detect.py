#!/usr/bin/env python3
"""
pretool-b1-detect.py — PreToolUse:Edit|Write — 检测单次编辑是否过度（新文件创建数告警）
统计本会话已创建的新文件数，超过5个时输出告警但不阻断。记录每次新文件创建到 new-files-log.jsonl
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, hc_get, is_mode_active, flywheel_event


def main():
    if not hc_enabled("b1_detect"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    try:
        input_data = sys.stdin.read()
    except Exception:
        input_data = ""

    project_root = (_HOOKS_DIR / "../..").resolve()
    state_dir = project_root / ".omc" / "state"
    log_file = state_dir / "new-files-log.jsonl"
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")

    try:
        threshold = int(hc_get("b1_detect.new_file_threshold", "5"))
    except (ValueError, TypeError):
        threshold = 5

    # 统一模式检测
    mode = is_mode_active(str(state_dir)) if state_dir.exists() else "normal"

    # 提取 file_path 和 tool_name
    file_path = ""
    tool_name = ""
    if input_data.strip():
        try:
            parsed = json.loads(input_data)
            ti = parsed.get("tool_input", {}) or parsed.get("args", {})
            file_path = ti.get("file_path", "") or ti.get("filePath", "") or ""
            tool_name = parsed.get("tool_name", "") or parsed.get("tool", "") or ""
        except (json.JSONDecodeError, Exception):
            pass

    if not file_path:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 仅检测 Write 操作（创建新文件）
    if tool_name == "Edit":
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 判断是否为新文件创建
    if os.path.isfile(file_path):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 记录新文件
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_entry = json.dumps({
        "timestamp": timestamp,
        "session_id": session_id,
        "file_path": file_path,
        "tool": tool_name,
        "mode": mode
    }, ensure_ascii=True)

    state_dir.mkdir(parents=True, exist_ok=True)
    try:
        with open(str(log_file), "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception:
        pass

    # 统计本会话新文件数
    count = 0
    if log_file.exists():
        try:
            with open(str(log_file), encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("session_id") == session_id:
                            count += 1
                    except (json.JSONDecodeError, Exception):
                        continue
        except Exception:
            pass

    # 超过阈值输出告警
    try:
        if count > threshold:
            warn_msg = (
                f"⚠️  [B1 Detect] 本会话已创建 {count} 个新文件（阈值: {threshold}）\n"
                f"   最新: {file_path}\n"
                f"   哲学 #1 (less is more): 新文件过多，建议评估是否真正需要。\n"
            )
            print(warn_msg, file=sys.stderr)
            flywheel_event("b1_detect", "warn_excessive", "P3", f"count={count},file={file_path}")
    except Exception:
        pass

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
