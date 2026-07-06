#!/usr/bin/env python3
"""
pretool-edit-scope.py — 编辑范围冻结检查

CC hook: PretoolUseExecution
检查当前编辑操作是否在 plan.md 声明的 scope 内。

如果 plan.md 不存在或 scope 未声明，按照默认放行。
"""

import json
import re
import sys
from pathlib import Path


def _get_plan_scope() -> list:
    """从 plan.md 读取 scope 声明"""
    plan_path = Path.cwd() / ".omc" / "state" / "plan.md"
    if not plan_path.exists():
        return []

    content = plan_path.read_text()
    # Scope 区域：## Scope 下的文件列表
    in_scope = False
    files = []
    for line in content.split("\n"):
        if line.strip().startswith("## Scope"):
            in_scope = True
            continue
        if in_scope:
            if line.strip().startswith("## "):
                break
            # 匹配 "  - path/to/file" 或 "- path/to/file"
            m = re.match(r"\s*[-*]\s+(\S+)", line)
            if m:
                files.append(m.group(1))
    return files


def main():
    stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not stdin_data:
        print(json.dumps({"continue": True, "message": "EditScope: no input"}))
        return 0

    try:
        payload = json.loads(stdin_data)
    except json.JSONDecodeError:
        print(json.dumps({"continue": True, "message": "EditScope: unparseable input"}))
        return 0

    edit_path = payload.get("filePath", "") or payload.get("path", "")
    if not edit_path:
        print(json.dumps({"continue": True, "message": "EditScope: no file path"}))
        return 0

    scope_files = _get_plan_scope()
    if not scope_files:
        # 无 scope 声明，放行
        print(json.dumps({"continue": True, "message": "EditScope: ALLOW (no scope)"}))
        return 0

    # 检查编辑文件是否在 scope 内
    edit_rel = edit_path
    for scoped in scope_files:
        if edit_rel == scoped or edit_rel.endswith("/" + scoped) or edit_rel.endswith("\\" + scoped):
            print(json.dumps({"continue": True, "message": f"EditScope: ALLOW ({edit_rel})"}))
            return 0

    # 不在 scope 内
    msg = f"EditScope: BLOCKED — {edit_rel} not in plan scope: {scope_files}"
    print(json.dumps({"continue": False, "message": msg}))
    sys.stderr.write(msg + "\n")
    return 0


if __name__ == "__main__":
    main()
