#!/usr/bin/env python3
"""
validate-skill.py — Skill 原子化合规性校验入口
v3: .sh → .py 轻量化迁移，调用 validate_skill_refs.py
"""

import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VALIDATOR = os.path.join(SCRIPT_DIR, "validate_skill_refs.py")

if not os.path.isfile(VALIDATOR):
    print(f"❌ 校验脚本不存在: {VALIDATOR}", file=sys.stderr)
    sys.exit(1)

python_bin = os.environ.get("PYTHON_BIN", sys.executable)
result = subprocess.run([python_bin, VALIDATOR] + sys.argv[1:])
sys.exit(result.returncode)
