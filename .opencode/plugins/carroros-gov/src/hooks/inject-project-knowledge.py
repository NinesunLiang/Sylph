#!/usr/bin/env python3
"""
inject-project-knowledge.py — SessionStart — 注入紧凑记忆恢复文件
注入 todo-queue.md(最近询问+任务摘要) + session-handoff.md + session-dump.json + session-handoff-v2.json
"""

import json
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled


def safe_read_head(path, max_lines=40):
    """Read first max_lines lines of a file."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        return "\n".join(lines[:max_lines])
    except Exception:
        return ""


def main():
    if not hc_enabled("inject_project_knowledge"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    project_root = (_HOOKS_DIR / "../..").resolve()
    state_dir = project_root / ".omc" / "state"

    # 1. Inject todo-queue.md
    todo_file = state_dir / "todo-queue.md"
    if todo_file.exists():
        content = safe_read_head(todo_file, 40)
        if content:
            print()
            print("--- 紧凑记忆恢复: 最近询问 + 任务摘要 ---")
            print(content)
            print()

    # 2. Inject session-handoff.md
    handoff_file = state_dir / "session-handoff.md"
    if handoff_file.exists():
        content = safe_read_head(handoff_file, 30)
        if content:
            print()
            print("--- 会话交接: 进度 + 决策 ---")
            print(content)
            print()

    # 3. Inject session-dump.json summary
    dump_file = state_dir / "session-dump.json"
    if dump_file.exists():
        try:
            d = json.loads(dump_file.read_text(encoding="utf-8"))
            print()
            print("--- 会话状态摘要 ---")
            git_state = d.get("git_state", {})
            modified_files = git_state.get("modified_files", [])
            if modified_files:
                print(f"修改文件 ({len(modified_files)}): {', '.join(modified_files[:5])}")
            edit_log = d.get("edit_log", [])
            if edit_log:
                print(f"编辑文件 ({len(edit_log)}): {', '.join(edit_log[:5])}")
            error_summary = d.get("error_summary", {})
            unfixed = error_summary.get("unfixed_count", 0)
            if unfixed > 0:
                print(f"未修复错误: {unfixed}")
            active_features = d.get("active_features", [])
            if active_features:
                names = []
                for a in active_features:
                    if isinstance(a, dict):
                        names.append(str(a.get("feature", "?")))
                    else:
                        names.append(str(a))
                print(f"活跃特性: {' | '.join(names[:3])}")
            print()
        except Exception:
            pass

    # 4. Inject session-handoff-v2.json
    handoff_v2 = state_dir / "session-handoff-v2.json"
    if handoff_v2.exists():
        try:
            d = json.loads(handoff_v2.read_text(encoding="utf-8"))
            print()
            print("--- 会话恢复 (handoff-v2) ---")
            print(f"任务: {d.get('task_summary', '无')}")
            print(f"已完成: {len(d.get('completed_tasks', []))}")
            print(f"待完成: {len(d.get('pending_tasks', []))}")
            print(f"分支: {d.get('working_branch', '')}")
            print(f"修改文件: {len(d.get('modified_files', []))}")
            print(f"最近询问: {len(d.get('queries', []))} 条")
            print(f"详情: {d.get('task_detail', '')}")
            print()
            print("【必须遵守】禁止编造|用户裁定|证据门禁|Git门禁|范围冻结|隐私防线|断言真实|哲学先行")
            print()
        except Exception:
            pass

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
