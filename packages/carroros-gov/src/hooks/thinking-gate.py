#!/usr/bin/env python3
"""thinking-gate.py — UserPromptSubmit — 检测 thinking 内容残留
Role: 检测用户消息中是否包含 thinking/reasoning 内容残留
"""
import json
import os
import re
import sys
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import flywheel_event


# ── Constants ──
THINKING_FLYWHEEL_TAG = "thinking-gate"
EVIDENCE_LOG = os.path.expanduser("~/.hermes/cron/output/thinking-leak-events.json")


def main():
    # ── Read user message ──
    prompt = ""
    if not sys.stdin.isatty():
        input_str = sys.stdin.read()
        try:
            input_data = json.loads(input_str)
            prompt = input_data.get("prompt", "")
        except (json.JSONDecodeError, AttributeError):
            prompt = input_str
    else:
        # Fallback: use first argument
        if len(sys.argv) > 1:
            prompt = sys.argv[1]

    # ── Detect thinking leak signals ──
    leak_type = ""
    leak_evidence = ""

    # H1: reasoning_content or thinking field structure in user message
    if re.search(r'(reasoning_content|"thinking"\s*:\s*\{|type.*?thinking)', prompt):
        leak_type = "H1-user-copy"
        leak_evidence = "用户消息中包含 thinking 字段结构"

    # ── If leak detected, record and notify ──
    if leak_type:
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        leak_event = json.dumps({
            "ts": timestamp,
            "type": leak_type,
            "evidence": leak_evidence
        })

        # Log to stderr
        sys.stderr.write(f"[{THINKING_FLYWHEEL_TAG}] {leak_event}\n")
        flywheel_event(THINKING_FLYWHEEL_TAG, "leak_detected", "P1")

        # Append to evidence log
        log_dir = os.path.dirname(EVIDENCE_LOG)
        os.makedirs(log_dir, exist_ok=True)
        try:
            with open(EVIDENCE_LOG, "a", encoding="utf-8") as f:
                f.write(leak_event + "\n")
        except Exception:
            pass

        # Notify AI context
        sys.stderr.write(f"[thinking-gate] ⚠️ 检测到 thinking 内容残留 ({leak_type})\n")
        sys.stderr.write("[thinking-gate] 提示: 如果使用 OpenCode，请确保 transform.ts 已剥离 reasoning_content 字段\n")

    # ── Always pass through (never block) — output the original prompt ──
    print(prompt)
    sys.exit(0)


if __name__ == "__main__":
    main()
