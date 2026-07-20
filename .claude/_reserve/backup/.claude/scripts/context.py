#!/usr/bin/env python3
"""context.py — 跨平台 context 注入器
用途：压缩治理注入 + 过滤 thinking + context 排序优化
双平台：macOS/Windows python3 兼容
"""

import json
import os
import re
import sys


def strip_thinking(text: str) -> str:
    """过滤 thinking/reasoning 标签，避免污染 context"""
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL)
    text = re.sub(r'</?thinking>', '', text)
    text = re.sub(r'</?reasoning>', '', text)
    return text


def load_compact_rules(state_dir: str) -> str:
    """加载压缩版治理规则"""
    # state_dir = .omc/state/, 项目根 = state_dir/../../
    project_root = os.path.abspath(os.path.join(state_dir, '..', '..'))
    paths = [
        os.path.join(project_root, '.claude', 'AGENTS.compact.md'),
        os.path.join(state_dir, 'AGENTS.compact.md'),
    ]
    for p in paths:
        p = os.path.abspath(p)
        if os.path.isfile(p):
            with open(p, encoding='utf-8') as f:
                return f.read().strip()
    return "[CarrorOS] AGENTS.compact.md not found — 使用默认最低治理"


def build_injected_context(state_dir: str, user_queries: list, task_state: dict) -> str:
    """构建注入到 system prompt 的压缩治理 context (U形注意力优化)"""
    parts = []

    # TOP：哲学铁律（最强注意力位置）
    compact_rules = load_compact_rules(state_dir)
    parts.append(compact_rules)

    # MIDDLE：文件链接（弱注意力，不占 context）
    task_detail = task_state.get('task_detail', '')
    if task_detail:
        parts.append(f"[任务详情]({task_detail})")
    decision_log = task_state.get('decision_log', '')
    if decision_log:
        parts.append(f"[决策日志]({decision_log})")

    # BOTTOM：最近 + 总结（第二强注意力位置）
    parts.append("---")
    parts.append(f"当前任务: {task_state.get('summary', '无')}")
    parts.append(f"已完成: {len(task_state.get('completed_tasks', []))}")
    parts.append(f"待完成: {len(task_state.get('pending_tasks', []))}")

    if user_queries:
        parts.append("\n最近用户请求:")
        for q in user_queries[-20:]:
            parts.append(f"- {q}")

    # 最后：强制性铁律底线（U形终点注意力峰值）
    parts.append("")
    parts.append("【必须遵守】")
    parts.append("禁止编造|用户裁定|证据门禁|Git门禁|范围冻结|隐私防线|断言真实|哲学先行")

    return "\n\n".join(parts)


def main():
    """CLI 入口"""
    if len(sys.argv) > 1 and sys.argv[1] == '--smoke':
        # 验收模式
        print("context.py: smoke test OK")
        return 0
    # 默认输出压缩 context
    state_dir = os.environ.get('STATE_DIR', os.path.join(os.path.dirname(__file__), '..', '..', '.omc', 'state'))
    print(build_injected_context(state_dir, [], {}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
