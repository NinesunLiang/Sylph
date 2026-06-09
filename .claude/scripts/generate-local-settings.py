#!/usr/bin/env python3
"""generate-local-settings.py
从 settings.json 生成 settings.local.json，把所有 hook 路径从相对路径改为绝对路径
解决 Claude Code CWD 漂移到 /tmp 时所有 hook 报 No such file or directory 的问题
用法: python3 .claude/scripts/generate-local-settings.py [project-root]
      如果省略 project-root，默认取脚本所在目录的上两层
哲学 #6 (0信任): settings.local.json 被 .gitignore 排除，不泄露个人信息到安装包
"""
import sys
import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else (SCRIPT_DIR / "../..").resolve()
SETTINGS_FILE = PROJECT_DIR / ".claude/settings.json"
LOCAL_SETTINGS = PROJECT_DIR / ".claude/settings.local.json"

if not SETTINGS_FILE.is_file():
    print(f"ERROR: {SETTINGS_FILE} not found", file=sys.stderr)
    sys.exit(1)

print(f"Generating {LOCAL_SETTINGS} ...")

# Read settings.json
content = SETTINGS_FILE.read_text(encoding="utf-8")

# Replace relative hook paths with absolute paths
python_bin = "python3"  # Default
content = re.sub(
    r'"bash \.claude/hooks/',
    f'"bash {PROJECT_DIR}/.claude/hooks/',
    content
)
content = re.sub(
    r'"python3 \.claude/hooks/',
    f'"{python_bin} {PROJECT_DIR}/.claude/hooks/',
    content
)
content = re.sub(
    r'"bash \.claude/workflow-standard/',
    f'"bash {PROJECT_DIR}/.claude/workflow-standard/',
    content
)
content = re.sub(
    r'"python3 \.claude/scripts/',
    f'"{python_bin} {PROJECT_DIR}/.claude/scripts/',
    content
)

# Write local settings
LOCAL_SETTINGS.write_text(content, encoding="utf-8")

# Validate JSON
try:
    data = json.loads(content)
    count = content.count('"command":')
    print(f"✅ {LOCAL_SETTINGS} generated ({count} hook commands, all absolute paths)")
    print(f"   Project root: {PROJECT_DIR}")
    print(f"   Settings file is in .gitignore — safe from packaging")
except json.JSONDecodeError as e:
    print(f"ERROR: Invalid JSON generated: {e}", file=sys.stderr)
    LOCAL_SETTINGS.unlink(missing_ok=True)
    sys.exit(1)
