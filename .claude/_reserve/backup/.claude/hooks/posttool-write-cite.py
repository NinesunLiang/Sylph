#!/usr/bin/env python3
"""
posttool-write-cite.py — PostToolUse:Write|Edit — 检测写入 claude-next.md 时验证教训格式
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, flywheel_event, hc_emit_hook_json


def main():
    if not hc_enabled("posttool_write_cite"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    try:
        input_data = sys.stdin.read()
    except Exception:
        input_data = ""

    # 提取 file_path
    file_path = ""
    if input_data.strip():
        try:
            parsed = json.loads(input_data)
            ti = parsed.get("tool_input", {}) or parsed.get("args", {})
            file_path = ti.get("file_path", "") or ti.get("filePath", "") or ""
        except (json.JSONDecodeError, Exception):
            pass

    if not file_path:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 只关心 claude-next.md
    basename = Path(file_path).name
    if basename != "claude-next.md":
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 读取新内容
    new_content = ""
    if input_data.strip():
        try:
            parsed = json.loads(input_data)
            new_content = parsed.get("tool_input", {}).get("new_content", "") or ""
        except (json.JSONDecodeError, Exception):
            pass

    if not new_content:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ─── 格式验证 ─────────────────────────────────────
    issues = []
    today = date.today().isoformat()

    # 检查最近添加的教训（找最后一个 ## [...] 条目）
    entries = re.findall(r'^## \[([^\]]*)\] (.*)', new_content, re.MULTILINE)
    last_entry = entries[-1] if entries else None

    if not last_entry:
        issues.append("⚠️ 未找到标准教训标题格式（## [YYYY-MM-DD] {教训标题}）")
    else:
        entry_date, entry_title = last_entry
        # 检查日期格式
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', entry_date):
            issues.append("⚠️ 标题日期格式错误（应为 [YYYY-MM-DD]）")
        # 检查标题非空
        if not entry_title.strip() or entry_title.strip() == "{教训标题}":
            issues.append("⚠️ 教训标题为空或是占位符")

    # 检查三个必填字段
    for field in ("**问题**", "**根因**", "**纠正**"):
        if field not in new_content:
            issues.append(f"⚠️ 缺少字段 {field}")

    # 检查内容非占位符
    if re.search(r'\{描述[^}]*\}|\{为什么[^}]*\}|\{正确做法[^}]*\}', new_content):
        issues.append("⚠️ 内容含未填充占位符（{...}）")

    # ─── 输出结果 ─────────────────────────────────────
    if not issues:
        msg = "✅ claude-next.md 教训格式合规。升华检查：已记录，未来达到 20 条时可升华到 kernel.md。"
        print(msg, file=sys.stderr)
        print(hc_emit_hook_json(msg, "PostToolUse", True))
        flywheel_event("posttool_write_cite", "format_ok", "P2")
    else:
        issue_list = "\n".join(issues)
        msg = (
            f"⚠️ claude-next.md 格式问题，建议修正：\n{issue_list}\n\n"
            f"标准格式：\n"
            f"## [{today}] {{教训标题}}\n"
            f"<!-- @{today} hits:1 -->\n"
            f"**问题**：{{描述}}\n"
            f"**根因**：{{为什么}}\n"
            f"**纠正**：{{正确做法}}"
        )
        print(msg, file=sys.stderr)
        print(hc_emit_hook_json(msg, "PostToolUse", True))
        flywheel_event("posttool_write_cite", "format_issue", "P2")

    sys.exit(0)


if __name__ == "__main__":
    main()
