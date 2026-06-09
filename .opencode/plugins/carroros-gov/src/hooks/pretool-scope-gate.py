#!/usr/bin/env python3
"""
pretool-scope-gate.py — PreToolUse:Edit|Write — 检测 Edit/Write 是否超出 current-scope.txt 声明的文件范围

哲学 #5(范围冻结): 一次一 Step，非核心 → TODO，越界 → 撤销
无 current-scope.txt 时透传。支持 glob 模式匹配。自主模式降级为记录。
"""

import fnmatch
import json
import os
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, is_mode_active, flywheel_event,
    read_input, extract_file_path, extract_tool_name, output_continue,
    PROJECT_ROOT, STATE_DIR,
)

SCOPE_FILE = STATE_DIR / "current-scope.txt"


def read_scope_patterns() -> list:
    """Read non-empty, non-comment lines from scope file."""
    if not SCOPE_FILE.exists():
        return []
    patterns = []
    try:
        with open(str(SCOPE_FILE), encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    patterns.append(stripped)
    except OSError:
        pass
    return patterns


def is_in_scope(rel_path: str, basename: str, patterns: list) -> bool:
    """Check if path matches any scope pattern."""
    for pattern in patterns:
        p = pattern.strip()
        if not p:
            continue
        # Direct fnmatch
        if fnmatch.fnmatch(rel_path, p):
            return True
        # Wildcard prefix
        if fnmatch.fnmatch(rel_path, "*" + p):
            return True
        # Basename match
        if "/" not in p and fnmatch.fnmatch(basename, p):
            return True
        # Directory prefix
        if p.endswith("/") and rel_path.startswith(p):
            return True
        if p.endswith("/*") and rel_path.startswith(p[:-2]):
            return True
    return False


def main():
    if not hc_enabled("pretool_scope_gate"):
        output_continue()
        return

    # No scope file → pass through
    if not SCOPE_FILE.exists():
        output_continue()
        return

    input_str = read_input()
    if not input_str:
        output_continue()
        return

    # Only intercept Edit/Write
    tool_name = extract_tool_name(input_str)
    if tool_name.lower() not in ("edit", "write"):
        output_continue()
        return

    # Extract file path
    file_path = extract_file_path(input_str)
    if not file_path:
        output_continue()
        return

    basename = os.path.basename(file_path)
    rel_path = file_path
    if str(PROJECT_ROOT) in file_path:
        rel_path = file_path.replace(str(PROJECT_ROOT), "").lstrip("/")

    # Read scope patterns
    patterns = read_scope_patterns()

    # Glob match
    if is_in_scope(rel_path, basename, patterns):
        output_continue()
        return

    # ── Auto-extend: reasonable directory patterns ──
    rel_dir = os.path.dirname(rel_path)
    auto_extend = False
    # Only auto-extend .claude/ subdirs and scripts/ and source/
    if rel_dir.startswith(".claude/") or rel_dir.startswith("scripts/") or rel_dir.startswith("source/"):
        dir_pattern = f"{rel_dir}/*"
        dir_exists = any(p == dir_pattern or p == f"{rel_dir}/" for p in patterns)
        if not dir_exists:
            try:
                STATE_DIR.mkdir(parents=True, exist_ok=True)
                with open(str(SCOPE_FILE), "a", encoding="utf-8") as f:
                    f.write(f"{dir_pattern}\n")
                auto_extend = True
                flywheel_event("pretool_scope_gate", "auto_extend", "P2", f"dir={rel_dir}")
            except OSError:
                pass

    if auto_extend:
        print(f"ℹ️ [Scope Gate] 自动扩展 scope: {rel_dir}/* → {SCOPE_FILE}", file=sys.stderr)
        output_continue()
        return

    # ── Mode detection: autonomous → downgrade to record ──
    mode = is_mode_active()
    if mode != "normal":
        print(f"⚠️ [Scope Gate] {mode} mode — 文件 {file_path} 超出 current-scope.txt 范围，已记录（模式降级，不阻断）", file=sys.stderr)
        flywheel_event("pretool_scope_gate", f"mode_downgrade_{mode}", "P2", f"path={file_path}")
        output_continue()
        return

    # ── Block: out of scope ──
    pattern_list = "\n".join(f"    - {p}" for p in patterns)
    print(
        f"⛔ [Scope Gate] 文件超出 current-scope.txt 声明的范围！\n\n"
        f"  目标文件: {file_path}\n"
        f"  范围文件: {SCOPE_FILE}\n\n"
        f"  当前声明的范围模式:\n"
        f"{pattern_list}\n\n"
        f"  哲学 #5(范围冻结): 一次一 Step，非核心 → TODO，越界 → 撤销。\n\n"
        f"  AI 应:\n"
        f"  1. 将 {file_path} 的变更记录到 TODO（如果是当前任务的非核心补充）\n"
        f"  2. 或更新 current-scope.txt 扩展范围（如果确实需要修改此文件）\n"
        f"  3. 或撤销本次操作，专注于 scope 内的文件\n",
        file=sys.stderr,
    )
    flywheel_event("pretool_scope_gate", "blocked_out_of_scope", "P1", f"path={file_path}")
    sys.exit(2)


if __name__ == "__main__":
    main()
