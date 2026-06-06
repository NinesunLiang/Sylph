#!/usr/bin/env python3
"""handoff.py — 跨平台会话交接
用途：compact 前后记忆保护
双平台：macOS/Windows python3 兼容
版本：v2 — 支持 OpenCode + Claude Code 双平台
"""

import json
import os
import re
import sys


def extract_from_todo_queue(todo_file: str, max_queries: int = 20) -> list:
    """从 todo-queue.md 提取最近用户询问"""
    if not os.path.isfile(todo_file):
        return []
    queries = []
    try:
        with open(todo_file, encoding='utf-8') as f:
            content = f.read()
        # 匹配「最近用户询问」段
        in_queries = False
        for line in content.split('\n'):
            if '最近用户询问' in line:
                in_queries = True
                continue
            if in_queries:
                if line.startswith('#') or line.startswith('---'):
                    break
                if line.strip().startswith('- ') or line.strip().startswith('* '):
                    queries.append(line.strip()[2:])
    except Exception:
        return []
    return queries[-max_queries:]


def extract_task_status(state_dir: str) -> dict:
    """提取任务执行情况"""
    status = {
        'summary': '',
        'completed': [],
        'pending': [],
        'branch': '',
        'files': [],
        'task_detail': '',
        'decision_log': '',
    }
    # 从 session-handoff.md 恢复
    handoff_file = os.path.join(state_dir, 'session-handoff.md')
    if os.path.isfile(handoff_file):
        try:
            with open(handoff_file, encoding='utf-8') as f:
                content = f.read()
            for line in content.split('\n'):
                if 'Branch:' in line:
                    status['branch'] = line.split(':', 1)[1].strip()
                if 'Active Feature:' in line:
                    status['summary'] = line.split(':', 1)[1].strip()
                if 'Modified:' in line:
                    fs = line.split(':', 1)[1].strip()
                    status['files'] = [f.strip() for f in fs.split(';') if f.strip()]
        except Exception:
            pass
    return status


def write_json(filepath: str, data: dict):
    """安全写入 JSON"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def before_compact(state_dir: str):
    """compact 前：写入 handoff"""
    todo_file = os.path.join(state_dir, 'todo-queue.md')
    user_queries = extract_from_todo_queue(todo_file, 20)

    task_status = extract_task_status(state_dir)

    task_detail_path = os.path.join(state_dir, 'task-detail.md')
    os.makedirs(os.path.dirname(task_detail_path), exist_ok=True)
    # 写入任务详情
    try:
        with open(task_detail_path, 'w', encoding='utf-8') as f:
            f.write("# 任务详情（自动生成）\n\n")
            f.write(f"摘要: {task_status.get('summary', '无')}\n")
            f.write(f"分支: {task_status.get('branch', '')}\n")
            for fname in task_status.get('files', []):
                f.write(f"- {fname}\n")
    except Exception:
        pass

    handoff = {
        'queries': user_queries,
        'task_summary': task_status.get('summary', ''),
        'task_detail': f"file://{task_detail_path}",
        'completed_tasks': task_status.get('completed', []),
        'pending_tasks': task_status.get('pending', []),
        'working_branch': task_status.get('branch', ''),
        'modified_files': task_status.get('files', []),
        'version': 'v2',
    }
    write_json(os.path.join(state_dir, 'session-handoff-v2.json'), handoff)

    # 也输出到 stdout（供 plugin 使用）
    print(json.dumps(handoff, ensure_ascii=False))


def after_compact(state_dir: str) -> str:
    """compact 后：构建有序的恢复 context"""
    handoff_file = os.path.join(state_dir, 'session-handoff-v2.json')
    if not os.path.isfile(handoff_file):
        return ""

    with open(handoff_file, encoding='utf-8') as f:
        handoff = json.load(f)

    context_parts = []

    # TOP：哲学铁律
    compact_rules_file = os.path.join(state_dir, '..', 'AGENTS.compact.md')
    compact_rules_abs = os.path.abspath(compact_rules_file)
    if os.path.isfile(compact_rules_abs):
        with open(compact_rules_abs, encoding='utf-8') as f:
            context_parts.append(f.read().strip())

    # MIDDLE：文件链接
    task_detail = handoff.get('task_detail', '')
    if task_detail:
        context_parts.append(f"[任务详情]({task_detail})")
    context_parts.append(f"[决策日志](file://{state_dir}/session-handoff-v2.json)")

    # BOTTOM：最近 + 总结
    context_parts.append("---")
    context_parts.append(f"当前: {handoff.get('task_summary', '无')}")
    context_parts.append(f"已完成: {len(handoff.get('completed_tasks', []))}")
    context_parts.append(f"待完成: {len(handoff.get('pending_tasks', []))}")

    for q in handoff.get('queries', []):
        context_parts.append(f"用户: {q}")

    # 最后：铁律底线
    context_parts.append("")
    context_parts.append("【必须遵守】")
    context_parts.append("禁止编造|用户裁定|证据门禁|Git门禁|范围冻结|隐私防线|断言真实|哲学先行")

    return "\n".join(context_parts)


def main():
    if len(sys.argv) < 2:
        print("用法: handoff.py <before-compact|after-compact> [--smoke]")
        return 1

    cmd = sys.argv[1]
    state_dir = os.environ.get(
        'STATE_DIR',
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.omc', 'state'))
    )

    if cmd == '--smoke':
        print("handoff.py: smoke test OK")
        return 0
    elif cmd == 'before-compact':
        before_compact(state_dir)
    elif cmd == 'after-compact':
        result = after_compact(state_dir)
        print(result)
    else:
        print(f"未知命令: {cmd}")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
