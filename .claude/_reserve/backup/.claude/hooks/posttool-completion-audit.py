#!/usr/bin/env python3
"""
posttool-completion-audit.py — PostToolUse — 独立验证 evidence 质量（E3/E7 防御纵深）

Role: PostToolUse 独立验证证据文件质量，不依赖 completion-gate 的门禁逻辑

原理：
  completion-gate.sh 是 PreToolUse 门禁（阻断无证据的完成声明）。
  本 hook 是 PostToolUse 兜底扫描 — 即使门禁被绕过（如 ghost mode 降级），
  本 hook 仍会检查 evidence 文件质量并记录异常，形成 E3/E7 双层防御。
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, flywheel_event, read_input,
    extract_tool_name, extract_tool_input_status, output_continue,
    PROJECT_ROOT, STATE_DIR, HOME_DIR,
)


def main():
    if not hc_enabled("posttool_completion_audit"):
        output_continue()
        return

    input_str = read_input()
    if not input_str:
        output_continue()
        return

    # Only check TaskUpdate
    tool = extract_tool_name(input_str)
    if tool != "TaskUpdate":
        output_continue()
        return

    # Only check "completed" status
    status = extract_tool_input_status(input_str)
    if status != "completed":
        output_continue()
        return

    # Check evidence file
    today_str = datetime.now().strftime("%Y%m%d")
    evidence_file = STATE_DIR / f".completion-evidence-{today_str}"

    if not evidence_file.exists():
        print("[completion-audit] ⚠️ TaskUpdate completed 但无证据文件", file=sys.stderr)
        output_continue()
        return

    # Check evidence quality
    try:
        content = evidence_file.read_text(encoding="utf-8")
    except OSError:
        print("[completion-audit] ⚠️ 无法读取证据文件", file=sys.stderr)
        output_continue()
        return

    issues = []

    # 1. Length check
    MIN_CHARS = 20
    if len(content) < MIN_CHARS:
        issues.append(f"证据过短({len(content)}字符<{MIN_CHARS})")

    # 2. VERIFIED keyword check
    if "VERIFIED" not in content:
        issues.append("缺少 VERIFIED 关键字")

    # 3. file:line reference check
    fl_count = len(re.findall(r'[\w./-]+\.[a-z]+:\d+', content))
    if fl_count == 0:
        issues.append("无 file:line 引用")

    # 4. Soft completion word check
    soft_words = [
        '应该没问题', '基本完成', '大部分完成', '差不多', '理论上可行',
        '看起来正常', '之前验证过', 'should be fine', 'basically done',
        'mostly complete', 'seems to work', 'should work', 'looks good',
    ]
    for w in soft_words:
        if w in content:
            issues.append(f"含软完成语: {w}")
            break

    # 5. Structural completeness
    ac_count = len(re.findall(r'AC\s*[#:]\s*\d+|收条件|C\d+', content))
    check_count = len(re.findall(r'\[[xX]\]\s', content))
    verified_count = content.count("VERIFIED")
    step_count = len(re.findall(r'步骤\s*\d+|Step\s*\d+', content))
    if ac_count == 0 and check_count == 0 and verified_count <= 1 and step_count == 0:
        issues.append("证据缺少结构化完成标记(AC#/checkbox/VERIFIED)")

    # 6. Command output existence
    has_cmd_output = bool(re.search(
        r'✅|❌|⚠️|PASS|FAIL|ERROR|OK|WARN|'
        r'\d+\s*passed|\d+\s*failed|'
        r'error:|Error:|ERROR:|'
        r'[a-z]+\.[a-z]+:\d+:\d+|'
        r'compilation|build.succeeded|BUILD',
        content,
    ))
    has_shell = bool(re.search(r'(?m)^[\$>]\s', content))
    has_paths = len(re.findall(r'/[\w/-]+\.[a-z]+', content)) > 3
    if not has_cmd_output and not has_shell and not has_paths:
        issues.append("证据无实际命令输出(仅有断言，缺少执行痕迹)")

    if issues:
        audit_log = STATE_DIR / "completion-audit.jsonl"
        record = {
            "ts": int(time.time()),
            "type": "evidence_quality",
            "issues": issues,
            "file": str(evidence_file),
            "content_len": len(content),
            "fl_count": fl_count,
        }
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            with open(str(audit_log), "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass
        print(f"[completion-audit] ⚠️ 证据质量缺陷: {'; '.join(issues)}", file=sys.stderr)

        # Log to flywheel
        flywheel_log = HOME_DIR / ".claude" / "flywheel.log"
        try:
            flywheel_log.parent.mkdir(parents=True, exist_ok=True)
            with open(str(flywheel_log), "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d')},completion_audit_defect,P1,carror-os\n")
        except OSError:
            pass
    else:
        print("[completion-audit] ✅ 证据质量通过", file=sys.stderr)

    output_continue()
    flywheel_event("posttool_completion_audit", "evidence_audited", "P2")


if __name__ == "__main__":
    main()
