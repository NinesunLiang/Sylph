#!/usr/bin/env python3
"""
validate-skill.py — Skill 原子化合规性校验入口
v2: 在 lx-validate-skill 被清理后(e75adf4)，改为调用轻量替代品 validate_skill_refs.py
Cross-platform Python resolution (DG-105)
"""
import sys
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_skill_refs.py"

if not VALIDATOR.exists():
    print("❌ 校验脚本不存在: {}".format(VALIDATOR), file=sys.stderr)
    sys.exit(1)

# Run the validator with passed args
cmd = [sys.executable, str(VALIDATOR)] + sys.argv[1:]
result = subprocess.run(cmd)
sys.exit(result.returncode)
