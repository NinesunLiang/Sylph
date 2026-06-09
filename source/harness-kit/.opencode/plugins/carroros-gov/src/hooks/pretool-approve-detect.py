#!/usr/bin/env python3
"""
pretool-approve-detect.py — UserPromptSubmit — 检测 /approve <token> 或 /deny，自动写入/清除 CAPTCHA 批准文件
Role: 拦截用户聊天中的 /approve|/deny 指令，实现对话内批准流程
对应 pretool-approve-detect.sh 的 Python 移植
"""

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, output_continue, read_input, HOME_DIR


def main():
    # Read stdin (UserPromptSubmit hook — must pass through)
    prompt = sys.stdin.read()

    script_dir = Path(__file__).resolve().parent
    project_root = (script_dir / "../..").resolve()
    state_dir = project_root / ".omc" / "state"

    # CAPTCHA 文件对定义：三套独立验证机制
    captcha_pairs = [
        (str(state_dir / "permission-required"), str(state_dir / "permission-approved"), "permission"),
        (str(state_dir / "sensitive-required"), str(state_dir / "sensitive-approved"), "sensitive"),
        (str(state_dir / "oracle-gate-required"), str(state_dir / "oracle-gate-approved"), "oracle-gate"),
    ]

    # ─── /deny 处理 ───
    if re.search(r'\b/deny\b', prompt, re.IGNORECASE):
        found = False
        for required, approved, desc in captcha_pairs:
            if os.path.isfile(required) or os.path.isfile(approved):
                for p in (required, approved):
                    try:
                        os.unlink(p)
                    except OSError:
                        pass
                found = True
        if found:
            flywheel_event("pretool_approve_detect", "user_denied", "P2")
            print("🚫 /deny — 危险操作已取消。审批文件已清理。", file=sys.stderr, flush=True)
        else:
            print("ℹ️ 当前无待批准的危险操作（/deny 忽略）。", file=sys.stderr, flush=True)
        print(prompt, end="")
        sys.exit(0)

    # ─── /approve <token> 处理 ───
    approve_match = re.search(r'(?:^|[^a-zA-Z0-9_])/approve\s+([0-9a-fA-F]{6,16})\b', prompt)
    approve_token = approve_match.group(1) if approve_match else None

    if approve_token is None:
        # 无 /approve 指令 → 透传
        print(prompt, end="")
        sys.exit(0)

    # 有 /approve → 循环验证三套 CAPTCHA
    matched = False
    for required, approved, desc in captcha_pairs:
        if not os.path.isfile(required):
            continue

        try:
            with open(required, "r") as f:
                expected = f.read().strip()
        except OSError:
            continue

        if approve_token == expected:
            try:
                with open(approved, "w") as f:
                    f.write(approve_token)
            except OSError:
                pass
            matched = True
            flywheel_event("pretool_approve_detect", "user_approved", "P2")
            print(f"✅ /approve 已接受！验证码匹配 {approve_token[:8]}，{desc} 操作已批准。", file=sys.stderr, flush=True)
            break

    if not matched:
        print("❌ /approve 失败：验证码不匹配或无可匹配的待批准操作。", file=sys.stderr, flush=True)
        flywheel_event("pretool_approve_detect", "token_mismatch", "P3")

    # 透传原始输入（Claude Code 协议要求）
    print(prompt, end="")
    sys.exit(0)


if __name__ == "__main__":
    main()
