#!/usr/bin/env python3
"""
posttool-audit.py — 审计事件写入

CC hook: PostToolUse
在每次工具调用后，将审计事件写入 .omc/state/audit/YYYYMMDD.jsonl。
"""

import json
import sys
from datetime import datetime
from pathlib import Path


AUDIT_DIR = Path.cwd() / ".omc" / "state" / "audit"


def main():
    stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not stdin_data:
        print(json.dumps({"continue": True}))
        return 0

    try:
        payload = json.loads(stdin_data)
    except json.JSONDecodeError:
        print(json.dumps({"continue": True}))
        return 0

    # ─── 提取工具调用信息 ───
    tool_name = payload.get("tool", "") or payload.get("name", "") or ""
    tool_result = payload.get("result", "") or ""
    tool_args = payload.get("arguments", {}) or payload.get("args", {})

    record = {
        "schema_version": "v1.0",
        "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "event": "tool_executed",
        "data": {
            "tool": tool_name,
            "args": tool_args,
            "result_length": len(str(tool_result)),
            "result_ok": "error" not in str(tool_result).lower()[:200],
        }
    }

    # ─── 写入 audit ───
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y%m%d")
    audit_file = AUDIT_DIR / f"{date_str}.jsonl"
    try:
        with open(audit_file, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass  # 静默失败 — audit 写入失败不阻断执行

    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    main()
