#!/usr/bin/env python3
"""
pretool-sensitive-edit.py — 敏感文件操作拦截

CC hook: PretoolUseExecution
拦截对敏感文件的编辑/删除操作。
"""

import json
import re
import sys
from pathlib import Path


SENSITIVE_PATTERNS = [
    r"\.env",
    r"\.ssh[/\\]",
    r"secrets[/\\]",
    r".*\.pem$",
    r".*\.key$",
    r"id_rsa",
    r"id_ed25519",
    r"credentials",
    r"config\.json$",   # 可能含 key
]


def _is_sensitive(filepath: str) -> bool:
    for pat in SENSITIVE_PATTERNS:
        if re.search(pat, filepath, re.IGNORECASE):
            return True
    return False


def main():
    stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not stdin_data:
        print(json.dumps({"continue": True, "message": "SensitiveEdit: no input"}))
        return 0

    try:
        payload = json.loads(stdin_data)
    except json.JSONDecodeError:
        print(json.dumps({"continue": True, "message": "SensitiveEdit: unparseable input"}))
        return 0

    edit_path = payload.get("filePath", "") or payload.get("path", "")
    action = payload.get("action", "write")

    if not edit_path:
        print(json.dumps({"continue": True, "message": "SensitiveEdit: no path"}))
        return 0

    if _is_sensitive(edit_path):
        msg = f"SensitiveEdit: BLOCKED — sensitive file: {edit_path}"
        print(json.dumps({"continue": False, "message": msg}))
        sys.stderr.write(msg + "\n")
        return 0

    print(json.dumps({"continue": True, "message": f"SensitiveEdit: ALLOW ({edit_path})"}))
    return 0


if __name__ == "__main__":
    main()
