#!/usr/bin/env python3

"""检测项目类型，输出 JSON。exit 0=成功，1=未知类型"""

import os, sys, json
from pathlib import Path


def detect():
    if Path("go.mod").exists():
        return "go"
    if Path("package.json").exists():
        pkg = json.loads(Path("package.json").read_text())
        runner = "vitest" if "vitest" in str(pkg) else "jest" if "jest" in str(pkg) else "npm"
        return f"node:{runner}"
    if Path("pyproject.toml").exists() or Path("requirements.txt").exists():
        return "python"
    if Path("Cargo.toml").exists():
        return "rust"
    return None

t = detect()
if not t:
    print(json.dumps({"type": "unknown", "error": "无法识别项目类型"}))
    sys.exit(1)

base = t.split(":")[0]
runner = t.split(":")[1] if ":" in t else None
print(json.dumps({"type": base, "runner": runner, "raw": t}))
