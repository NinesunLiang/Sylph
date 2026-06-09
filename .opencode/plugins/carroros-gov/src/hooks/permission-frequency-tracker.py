#!/usr/bin/env python3
"""
permission-frequency-tracker.py — PostToolUse:* — 统计当前会话中 permission-required* 文件的创建次数
写入 .omc/state/permission-frequency.json
永不阻断
"""

import json
import os
import sys
import time
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, flywheel_event


def main():
    if not hc_enabled("permission_frequency_tracker"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    try:
        input_data = sys.stdin.read()
    except Exception:
        input_data = ""

    project_root = (_HOOKS_DIR / "../..").resolve()
    state_dir = project_root / ".omc" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    perm_file = state_dir / "permission-frequency.json"

    # 提取 file_path 字段
    file_path = ""
    tool_use_id = ""
    if input_data.strip():
        try:
            parsed = json.loads(input_data)
            ti = parsed.get("tool_input", {}) or parsed.get("args", {})
            file_path = ti.get("file_path", "") or ti.get("filePath", "") or ""
            tool_use_id = parsed.get("tool_use_id", "") or parsed.get("id", "") or ""
        except (json.JSONDecodeError, Exception):
            pass

    if not file_path:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 只关注门禁标记文件路径
    basename = Path(file_path).name
    if not basename.startswith("permission-req") and \
       not basename.startswith("permission-app") and \
       not basename.startswith("permission-mar"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 基于 tool_use_id 去重写入
    now = int(time.time())

    # 读取现有记录
    data = {
        "total_count": 0,
        "files": {},
        "tool_ids": [],
        "session_start": now,
        "last_updated": now
    }
    if perm_file.exists():
        try:
            with open(str(perm_file), "r") as f:
                existing = json.load(f)
                data["total_count"] = existing.get("total_count", 0)
                data["files"] = existing.get("files", {})
                data["tool_ids"] = existing.get("tool_ids", [])
                data["session_start"] = existing.get("session_start", now)
        except (json.JSONDecodeError, IOError):
            pass

    # 去重：同一 tool_use_id 不重复计数
    if tool_use_id and tool_use_id in data["tool_ids"]:
        data["last_updated"] = now
        with open(str(perm_file), "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 更新计数
    data["total_count"] += 1
    if tool_use_id:
        data["tool_ids"].append(tool_use_id)

    # 按文件名聚合
    if basename not in data["files"]:
        data["files"][basename] = {"count": 0, "paths": []}
    data["files"][basename]["count"] += 1
    if file_path not in data["files"][basename]["paths"]:
        data["files"][basename]["paths"].append(file_path)

    data["last_updated"] = now

    try:
        with open(str(perm_file), "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    flywheel_event("permission_frequency_tracker", f"counted_{basename}", "P3")
    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
