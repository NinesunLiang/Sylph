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

        # Strip thinking from prompt before outputting
        # Remove reasoning_content JSON fields
        prompt = re.sub(
            r'"reasoning_content"\s*:\s*"[^"]*"\s*,?\s*',
            '',
            prompt,
            flags=re.DOTALL,
        )
        # Remove "thinking" top-level keys in JSON objects
        prompt = re.sub(
            r',?\s*"thinking"\s*:\s*\{[^}]*\}',
            '',
            prompt,
            flags=re.DOTALL,
        )
        # Remove <thinking>...</thinking> XML blocks
        prompt = re.sub(
            r'<thinking>.*?</thinking>',
            '',
            prompt,
            flags=re.DOTALL,
        )
        # Remove 思考块（中文 thinking 段落）
        prompt = re.sub(
            r'(?:^|\n)\s*思考[：:][^\n]*(\n[^\n]*)*(\n---\s*)?',
            '\n',
            prompt,
        )
        leak_evidence = f"已自动剥离 thinking 内容 ({leak_type})"
        sys.stderr.write(f"[thinking-gate] ✅ {leak_evidence}\n")

    # ── Never block — just pass through with continue signal ──
    # IMPORTANT: Do NOT print(prompt) here! Printing user prompt to stdout
    # causes CC's UserPromptSubmit to accumulate it as the "new input",
    # leading to repeated injection of the same text across turns.
    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
