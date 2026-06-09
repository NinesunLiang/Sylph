#!/usr/bin/env python3
"""
posttool-read-cite.py — PostToolUse:Read [默认关闭] — 读取文件后提示引用规范
Role: 读取文件后提示引用规范
对应 posttool-read-cite.sh 的 Python 移植
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, output_continue, read_input, HOME_DIR


def _fnmatch(name, pattern):
    """Simple shell glob matching (supports *.go style patterns)."""
    import fnmatch
    return fnmatch.fnmatch(name, pattern)


def main():
    # hc_enabled check
    if not hc_enabled("posttool_read_cite"):
        output_continue()
        return

    flywheel_event("posttool_read_cite", "active", "P2")

    raw_input = sys.stdin.read()

    # Parse input
    try:
        data = json.loads(raw_input)
    except json.JSONDecodeError:
        output_continue()
        return

    # Extract file_path
    file_path = ""
    tool_input = data.get("tool_input", {}) or {}
    args = data.get("args", {}) or {}
    if isinstance(tool_input, dict):
        file_path = tool_input.get("file_path", "")
    if not file_path and isinstance(args, dict):
        file_path = args.get("filePath", "")

    if not file_path:
        output_continue()
        return

    basename = Path(file_path).name
    msg = ""

    # 从配置读取需要引用提醒的扩展名列表
    from harness_lib import hc_get
    cite_exts = hc_get("project.cite_extensions", "*.go *.api")
    cite_match = False
    for ext in cite_exts.split():
        if _fnmatch(basename, ext):
            cite_match = True
            msg = f"已读取{basename}。引用代码事实时必须标注[已验证: file:line]，禁止凭记忆引用。"
            break

    # 特殊文件额外提醒
    if basename == "PROJECT_MASTER.md":
        cite_match = True
        msg = "已读取PROJECT_MASTER.md（唯一权威数据源）。状态机/数据表引用必须标注行号。"
    elif basename in ("kernel.md", "style-guide.md", "go-style-guide.md"):
        cite_match = True
        msg = "已加载代码规范。写代码时遵循此规范。"

    if not cite_match:
        output_continue()
        return

    result = {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg
        }
    }
    print(json.dumps(result, ensure_ascii=True))
    sys.exit(0)


if __name__ == "__main__":
    main()
