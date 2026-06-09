#!/usr/bin/env python3
"""
posttool-anti-pattern-detect.py — PostToolUse:TaskUpdate|Edit|Write — 反模式自动检测

Role: 根据 .claude/anti-patterns.md 自动检测 A2/F1/H1 反模式输出
哲学 #6：先天对 AI 0 信任 — 自动化检测语义层面的反模式
哲学 #4：没通过验证等于没做 — A2 虚假完成硬阻断

阻断策略设计理由 (Oracle 审计 2026-05-15):
  A2/H1 → hard block (exit 2): 铁律 #1 违反，可机械验证（软完成语 + 无证据 / 百分比 + 无来源）
  F1  → hard block (exit 2): 铁律 #1 违反，可机械验证（推测词 + 无 file:line）
  与 E5 RCA (completion-gate.sh:warning-only) 的区别:
    E5 检测"缺失的流程步骤"(RCA 是否包含)，主观判断 → warning
    F1 检测"断言缺乏证据支撑"(是否有 file:line)，客观可验证 → hard block
  一致性原则: 可机械验证的铁律违反 → hard block；需主观判断的流程缺失 → warning
"""

import json
import os
import re
import sys
import time
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, is_mode_active, flywheel_event,
    read_input, extract_tool_name, output_continue,
    PROJECT_ROOT, STATE_DIR,
)

# ── Anti-pattern patterns (from .sh) ──

A2_SOFT_WORDS = r'应该没问题了|基本完成|大部分通过|should be fine|basically done|mostly complete'
A2_EVIDENCE = r'\[已验证:|\[已测试:|exit [0-9]|PASS|✅|VERIFIED'

F1_HEDGE = r'应该是|通常是|一般来说|probably|seems to|I think|按理说|一般情况下'
F1_EVIDENCE = r'\[已验证:|\[已测试:'

H1_SCORE = r'[0-9]+(\.[0-9]+)?%|评分\s*[0-9]+\s*/\s*[0-9]+|得分\s*[0-9]+(\.[0-9]+)?|throughput [0-9]+|accuracy [0-9]+'
H1_SOURCE = r'(https?://[^\s\)]+|file:line|\[已验证:|\[已测试:|source:|来源:|ref:)'


def extract_result(input_str: str) -> str:
    """Extract tool_response.result from stdin JSON."""
    try:
        data = json.loads(input_str)
        return (data.get("tool_response", {}).get("result") or "").strip()
    except (json.JSONDecodeError, Exception):
        return ""


def log_violation(violation_log: Path, vtype: str, mode: str, result_snippet: str = ""):
    """Log violation to ghost-violations.jsonl for autonomous mode."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": int(time.time()),
            "type": vtype,
            "mode": mode,
            "result": result_snippet[:200],
        }
        with open(str(violation_log), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def main():
    if not hc_enabled("anti_pattern_detect"):
        output_continue()
        return

    input_str = read_input()
    if not input_str:
        output_continue()
        return

    # Check mode (ghost/goal → downgrade to record-only)
    mode = is_mode_active()
    autonomous = mode != "normal"

    # Extract result
    result = extract_result(input_str)
    if not result:
        output_continue()
        return

    # ── A2: 虚假完成检测 ──
    a2_triggered = False
    if re.search(A2_SOFT_WORDS, result, re.IGNORECASE):
        if not re.search(A2_EVIDENCE, result):
            a2_triggered = True

    # ── F1: 假设驱动检测 ──
    f1_triggered = False
    if re.search(F1_HEDGE, result, re.IGNORECASE):
        if not re.search(F1_EVIDENCE, result):
            f1_triggered = True

    # ── H1: 语义编造检测 ──
    h1_triggered = False
    if re.search(H1_SCORE, result, re.IGNORECASE):
        if not re.search(H1_SOURCE, result, re.IGNORECASE):
            h1_triggered = True

    # ── Output response ──

    # A2 or H1 → hard block (autonomous → record + pass)
    if a2_triggered or h1_triggered:
        print("⛔ [反模式检测] 检测到反模式输出:", file=sys.stderr)
        if a2_triggered:
            print("  🚫 A2 虚假完成: 检测到软完成语（应该没问题了/基本完成/大部分通过），缺少结构化证据标记", file=sys.stderr)
        if h1_triggered:
            print("  🚫 H1 语义编造: 检测到无来源的百分比/评分指标", file=sys.stderr)

        if autonomous:
            print(f"[{mode}] A2/H1 反模式已记录（自主模式不阻断）", file=sys.stderr)
            log_violation(STATE_DIR / "ghost-violations.jsonl", "A2_H1", mode, result)
            flywheel_event("anti_pattern_detect", "recorded_autonomous", "P2")
            output_continue()
            return
        else:
            print('{"continue": false}', file=sys.stderr)
            flywheel_event("anti_pattern_detect", "blocked", "P2")
            sys.exit(2)

    # F1 → hard block (autonomous → record + pass)
    if f1_triggered:
        print("⛔ [反模式检测] 检测到假设驱动断言:", file=sys.stderr)
        print("  🚫 F1 假设驱动: 检测到推测性断言「应该是/通常是/一般来说」缺少 file:line 证据", file=sys.stderr)

        if autonomous:
            print(f"[{mode}] F1 反模式已记录（自主模式不阻断）", file=sys.stderr)
            log_violation(STATE_DIR / "ghost-violations.jsonl", "F1", mode)
            flywheel_event("anti_pattern_detect", "recorded_autonomous", "P2")
            output_continue()
            return
        else:
            print('{"continue": false}', file=sys.stderr)
            flywheel_event("anti_pattern_detect", "blocked", "P2")
            sys.exit(2)

    output_continue()


if __name__ == "__main__":
    main()
