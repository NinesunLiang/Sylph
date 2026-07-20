#!/usr/bin/env python3
"""lsp-suggest.py — PreToolUse:Grep — 检测 Grep 搜索导出符号时建议改用 LSP 工具

Role: 检测 Grep 搜索导出符号时建议改用 LSP 工具
Replaces lsp-suggest.sh with pure Python3 (cross-platform).
"""

import json
import os
import re
import sys

from pathlib import Path

# ── Import harness shared library ──────────────────────────────────
_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, hc_get, flywheel_event

# ── Path resolution ────────────────────────────────────────────────
PROJECT_ROOT = (_HOOKS_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
SUGGESTED_FILE = STATE_DIR / "lsp-suggested"


# ── Pattern extraction ─────────────────────────────────────────────

def _extract_pattern(input_data):
    """Extract the 'pattern' field from tool_input."""
    ti = input_data.get("tool_input", {})
    pattern = ti.get("pattern", "")
    if pattern:
        return pattern
    # Fallback: args might contain pattern
    args = input_data.get("args", {})
    if isinstance(args, dict):
        pattern = args.get("pattern", "")
    return pattern


# ── Pattern validation ─────────────────────────────────────────────

def _has_regex_metacharacters(pattern):
    """Check if pattern contains regex metacharacters (non-pure symbol search)."""
    return bool(re.search(r"[.*+?\[\](){}|^$\\\\]", pattern))


def _is_exported_symbol_pattern(pattern, symbol_regex):
    """Check if pattern matches the exported symbol regex (default: uppercase-start)."""
    return bool(re.search(symbol_regex, pattern))


def _is_pure_identifier(pattern):
    """Check if pattern contains only alphanumeric chars and underscores."""
    return bool(re.match(r"^[A-Za-z0-9_]+$", pattern))


# ── Main ───────────────────────────────────────────────────────────

def main():
    # Feature gate
    if not hc_enabled("lsp_suggest"):
        print(json.dumps({"continue": True}))
        return

    # Read stdin
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        print(json.dumps({"continue": True}))
        return

    # Extract pattern
    pattern = _extract_pattern(input_data)
    if not pattern:
        print(json.dumps({"continue": True}))
        return

    # Exclude: contains regex metacharacters (non-pure symbol search)
    if _has_regex_metacharacters(pattern):
        print(json.dumps({"continue": True}))
        return

    # Exclude: doesn't match exported symbol regex (default: uppercase-start)
    symbol_regex = hc_get("lsp_suggest.exported_symbol_regex", "^[A-Z]")
    if not _is_exported_symbol_pattern(pattern, symbol_regex):
        print(json.dumps({"continue": True}))
        return

    # Exclude: too short
    min_len_str = hc_get("lsp_suggest.min_symbol_length", "3")
    try:
        min_len = int(min_len_str)
    except (ValueError, TypeError):
        min_len = 3
    if len(pattern) < min_len:
        print(json.dumps({"continue": True}))
        return

    # Exclude: contains non-alphanumeric characters (not a pure symbol name)
    if not _is_pure_identifier(pattern):
        print(json.dumps({"continue": True}))
        return

    # Already suggested this session → pass
    if SUGGESTED_FILE.exists():
        print(json.dumps({"continue": True}))
        return

    # First detection of exported symbol Grep → suggest + write marker
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SUGGESTED_FILE.touch()

    example_file = hc_get("lsp_suggest.example_file", "model/tasks_mongo.go")

    lsp_suggestion = (
        f"[LSP 建议] 检测到导出符号查找: \"{pattern}\"\n"
        f"LSP 工具可精确定位（无噪音），推荐：\n"
        f"  - 全局搜索: lsp_workspace_symbols(query=\"{pattern}\", file=\"{example_file}\")\n"
        f"  - 找定义:   lsp_goto_definition(file=..., line=..., character=...)\n"
        f"  - 找引用:   lsp_find_references(file=..., line=..., character=...)\n"
        f"如需 LSP 结果，改用 LSP 工具；继续 Grep 自动放行。"
    )
    print(lsp_suggestion, file=sys.stderr)

    print(json.dumps({"continue": True}))

    flywheel_event("lsp_suggest", "lsp_suggestion", "P2", "suggested_lsp_alternative")


if __name__ == "__main__":
    main()
