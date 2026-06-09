#!/usr/bin/env python3
"""
pretool-git-gate.py — PreToolUse:Bash — Git 提交前 pre-commit 检查门禁（铁律 #4 物化）
检测 git commit 前是否有 pre-commit 检查。非 git commit 命令透传。
"""

import json
import os
import re
import sys
import time
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, is_mode_active, flywheel_event, hc_emit_hook_json


def get_file_mtime(path):
    """Get file modification time in epoch seconds."""
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0


def main():
    if not hc_enabled("pretool_git_gate"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    try:
        input_data = sys.stdin.read()
    except Exception:
        input_data = ""

    # 提取命令
    command = ""
    if input_data.strip():
        try:
            parsed = json.loads(input_data)
            ti = parsed.get("tool_input", {}) or {}
            command = ti.get("command", "") or parsed.get("args", {}).get("command", "") or ""
        except (json.JSONDecodeError, Exception):
            pass

    if not command:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    project_root = (_HOOKS_DIR / "../..").resolve()
    state_dir = project_root / ".omc" / "state"

    # 模式检测: ghost/goal 降级
    mode = is_mode_active(str(state_dir))
    if mode != "normal":
        print(f"[pretool-git-gate] {mode} mode — git commit pre-commit 检查已记录（模式降级，不阻断）", file=sys.stderr)
        flywheel_event("pretool_git_gate", "mode_skip", "P2")
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 非 git commit 命令透传
    if not re.search(r'^git\s+commit\b', command):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # git commit --dry-run / --help 透传
    if re.search(r'git\s+commit\s+--(dry-run|help)', command):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 检查 .pre-commit-verified 标记文件（5分钟内有效）
    marker_file = project_root / ".pre-commit-verified"
    marker_valid = False

    if marker_file.exists():
        mtime = get_file_mtime(str(marker_file))
        now = time.time()
        if mtime > 0 and now > 0:
            age = now - mtime
            if age <= 300:
                marker_valid = True

    if marker_valid:
        print("[pretool-git-gate] pre-commit 已验证（标记文件 5 分钟内有效）", file=sys.stderr)
        flywheel_event("pretool_git_gate", "pre_commit_verified", "P3")
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 无有效标记 → 阻断并输出铁律 #4 提示
    block_msg = """
⛔ [Git Gate] pre-commit 检查未通过 — 铁律 #4 门禁阻断

铁律 #4 (Git 门禁): 编译 → 功能 → 报告 → Boss 批准 → 提交，跳步=回滚

检测到 git commit 前缺少有效的 pre-commit 验证标记。
请先执行 pre-commit 检查（如 /lx-pre-commit），通过后系统将自动
生成 .pre-commit-verified 标记文件，5 分钟内 git commit 放行。

  ✓ 运行 /lx-pre-commit 完成质量门禁
  ✓ 或在终端执行 git commit（绕过 AI 门禁）
"""
    print(block_msg, file=sys.stderr)
    flywheel_event("pretool_git_gate", "blocked_no_pre_commit", "P1")
    result = hc_emit_hook_json(
        "[Git Gate] 铁律#4 门禁阻断: git commit 前缺少 pre-commit 验证标记。请先运行 /lx-pre-commit 完成质量门禁。",
        "PreToolUse",
        False
    )
    print(result)
    sys.exit(2)


if __name__ == "__main__":
    main()
