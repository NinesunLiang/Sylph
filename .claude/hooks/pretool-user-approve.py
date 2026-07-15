#!/usr/bin/env python3
"""
pretool-user-approve.py — UserPromptSubmit hook

Detects /approve <token> and /deny commands in user chat messages.
Implements CAPTCHA-based approval pattern for CarrorOS blocked tasks.
"""
import json
import os
import re
import sys
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
ROOT = HOOK_DIR.parents[1]
STATE_DIR = ROOT / ".omc" / "state"
FALLBACK_REQUIRED = STATE_DIR / "fallback-blocked-required"
FALLBACK_APPROVED = STATE_DIR / "fallback-blocked-approved"


def main() -> None:
    prompt = sys.stdin.read()

    # ─── /deny — clear approval state ───
    if re.search(r'(?:^|[^a-zA-Z0-9_])/deny\b', prompt):
        _safe_unlink(FALLBACK_REQUIRED)
        _safe_unlink(FALLBACK_APPROVED)
        print("🚫 /deny — 阻塞状态已清除。如需重新启用可输入 /approve <token>。",
              file=sys.stderr, flush=True)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ─── /approve <token> — validate and approve ───
    match = re.search(r'(?:^|[^a-zA-Z0-9_])/approve\s+([0-9a-fA-F]{6,16})\b', prompt)
    if not match:
        # No approval command — pass through
        print(json.dumps({"continue": True}))
        sys.exit(0)

    token = match.group(1)

    if not FALLBACK_REQUIRED.exists():
        print("ℹ️ /approve 忽略：当前无待解除的阻塞状态。",
              file=sys.stderr, flush=True)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    expected = FALLBACK_REQUIRED.read_text().strip()
    if token == expected:
        # Token matches — write approval file
        FALLBACK_APPROVED.write_text(token)
        print(f"✅ /approve 已接受！任务阻塞将在下次操作时自动解除。",
              file=sys.stderr, flush=True)
    else:
        print(f"❌ /approve 失败：验证码不匹配。请检查输入的 token。",
              file=sys.stderr, flush=True)

    print(json.dumps({"continue": True}))
    sys.exit(0)


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


if __name__ == "__main__":
    main()
