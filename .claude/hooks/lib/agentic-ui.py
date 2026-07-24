#!/usr/bin/env python3
"""
agentic-ui.py — 共享库（非 Hook） — Agentic UI 标准化输出函数

Role: 提供统一的菜单/确认/CAPTCHA/状态输出，替代各 hook 中分散的纯文本 stderr

This is a utility module; functions are primarily accessed via harness_lib.py.
Exports additional UI functions beyond what harness_lib.py provides.
"""

import json
import sys
from typing import Optional


# ── UI Constants ──

SEPARATOR = "═══════════════════════════════════════════════════════════════"
INDENT = "  "

ICONS = {
    "block": "⛔",
    "warn": "⚠️",
    "info": "ℹ️",
    "success": "✅",
    "lock": "🔐",
    "captcha": "🔑",
    "menu": "📋",
    "danger": "🚫",
}


def banner(level: str, title: str, message: str):
    """Print a formatted banner to stderr."""
    icon = ICONS.get(level, "ℹ️")
    print(f"\n{icon} [{title}] {message}\n", file=sys.stderr)


def separator():
    """Print separator line to stderr."""
    print(SEPARATOR, file=sys.stderr)


def status(level: str, title: str, message: str, detail: str = ""):
    """Print a formatted status block to stderr."""
    icon = ICONS.get(level, "ℹ️")
    print(f"\n{icon} [{title}]\n{SEPARATOR}\n{message}", file=sys.stderr)
    if detail:
        print(f"{INDENT}{detail}", file=sys.stderr)
    print("", file=sys.stderr)


def breakdown(title: str, *items: str):
    """Print a breakdown list to stderr."""
    print(f"\n{ICONS['info']} [{title}]\n{SEPARATOR}", file=sys.stderr)
    for item in items:
        print(f"{INDENT}{item}", file=sys.stderr)
    print("", file=sys.stderr)


def table(title: str, headers: list, rows: list):
    """Print a simple table to stderr."""
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    sep = "+" + "+".join("-" * w for w in widths) + "+"

    print(f"\n{ICONS['info']} {title}", file=sys.stderr)
    print(sep, file=sys.stderr)
    print("|" + "|".join(f" {h:{w}} " for h, w in zip(headers, widths)) + "|", file=sys.stderr)
    print(sep, file=sys.stderr)
    for row in rows:
        padded = [str(c) if i < len(row) else "" for i, c in enumerate(row)]
        print("|" + "|".join(f" {p:{w}} " for p, w in zip(padded, widths)) + "|", file=sys.stderr)
    print(sep, file=sys.stderr)
    print("", file=sys.stderr)


def progress(step: int, total: int, description: str):
    """Print a progress line to stderr."""
    print(f"{ICONS['info']} [{step}/{total}] {description}...", file=sys.stderr)


def context(message: str) -> dict:
    """Build an additionalContext dict for hook output.

    Returns dict for use with hc_emit_hook_json.
    """
    return {"continue": True, "hookSpecificOutput": {"additionalContext": f"[AGENTIC] {message}"}}


def context_block(message: str):
    """Build a blocking additionalContext and exit.

    Equivalent to agentic_context_block() in agentic-ui.sh.
    """
    result = {
        "continue": False,
        "hookSpecificOutput": {
            "additionalContext": f"[AGENTIC:BLOCK] {message}",
        },
    }
    print(json.dumps(result, ensure_ascii=True))
    sys.exit(2)
