#!/usr/bin/env python3
"""
extract_pattern.py — 对话模式提取器

由 lx-learner Phase 0 调用。扫描对话 transcript JSONL，检测重复操作模式。

用法:
  python3 extract_pattern.py --transcript <transcript.jsonl> [--min-repeats 3]
  python3 extract_pattern.py --text "<对话文本>" [--min-repeats 3]

输出 (JSON):
  { "patterns": [...], "count": N }
  exit 0: 检测到模式
  exit 2: 未检测到
"""

import sys
import os
import json
import re
import argparse
from pathlib import Path
from collections import Counter


def tokenize_action(text: str) -> list[str]:
    """从文本中提取动作关键词。"""
    action_patterns = [
        r'(审查|检查|扫描|review|check|scan|audit|inspect)\s*(\S+)',
        r'(修复|fix|repair|patch)\s*(\S+)',
        r'(生成|创建|构建|generate|create|build|make)\s*(\S+)',
        r'(测试|test|verify|validate)\s*(\S+)',
        r'(部署|deploy|release|publish)\s*(\S+)',
        r'(分析|analyze|investigate|trace)\s*(\S+)',
        r'(优化|optimize|improve|refactor)\s*(\S+)',
        r'(运行|执行|run|execute)\s*(\S+)',
    ]

    actions = []
    for pattern in action_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                actions.append('_'.join(m).lower())
            else:
                actions.append(m.lower())
    return actions


def extract_tool_sequences(transcript_path: str) -> list[dict]:
    """从 transcript JSONL 提取工具调用序列。"""
    sequences = []
    path = Path(transcript_path)

    if not path.exists():
        return sequences

    current_sequence = []
    current_turn = None

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            turn = entry.get('turn', entry.get('turn_number', ''))
            role = entry.get('role', '')
            content = entry.get('content', '')

            if turn != current_turn:
                if current_sequence:
                    sequences.append({
                        'turn': current_turn,
                        'actions': current_sequence.copy()
                    })
                current_turn = turn
                current_sequence = []

            if role == 'user' or role == 'human':
                actions = tokenize_action(str(content))
                if actions:
                    current_sequence.extend(actions)

    if current_sequence:
        sequences.append({
            'turn': current_turn,
            'actions': current_sequence.copy()
        })

    return sequences


def find_repeated_patterns(sequences: list[dict], min_repeats: int = 3) -> list[dict]:
    """在序列中查找重复的动作模式。"""
    # 收集所有动作
    all_actions = []
    for seq in sequences:
        all_actions.extend(seq['actions'])

    # 频率统计
    action_counts = Counter(all_actions)
    repeated = {action: count for action, count in action_counts.items()
                if count >= min_repeats}

    patterns = []
    for action, count in repeated.items():
        # 找该动作出现的轮次
        turns = []
        for seq in sequences:
            if action in seq['actions']:
                turns.append(seq['turn'])

        # 推断模式类型
        action_lower = action.lower()
        if any(kw in action_lower for kw in ['review', 'check', 'scan', 'audit', '审查', '检查', '扫描']):
            pattern_type = 'repeated_review'
        elif any(kw in action_lower for kw in ['fix', 'repair', '修复']):
            pattern_type = 'repeated_fix'
        elif any(kw in action_lower for kw in ['generate', 'create', 'build', '生成', '创建', '构建']):
            pattern_type = 'repeated_generation'
        elif any(kw in action_lower for kw in ['test', 'verify', '测试', '验证']):
            pattern_type = 'repeated_testing'
        else:
            pattern_type = 'repeated_workflow'

        # 置信度
        if count >= 7:
            confidence = 'high'
        elif count >= 4:
            confidence = 'medium'
        else:
            confidence = 'low'

        score = min(10, count + (2 if confidence == 'high' else 1 if confidence == 'medium' else 0))

        patterns.append({
            'type': pattern_type,
            'action': action,
            'repeat_count': count,
            'turns': turns[:10],
            'confidence': confidence,
            'score': score
        })

    # 按分数排序
    patterns.sort(key=lambda p: p['score'], reverse=True)
    return patterns


def extract_from_text(text: str, min_repeats: int = 3) -> list[dict]:
    """从原始文本中提取重复模式（简化版）。"""
    actions = tokenize_action(text)
    action_counts = Counter(actions)
    repeated = {action: count for action, count in action_counts.items()
                if count >= min_repeats}

    patterns = []
    for action, count in repeated.items():
        score = min(10, count + 1)
        patterns.append({
            'type': 'repeated_workflow',
            'action': action,
            'repeat_count': count,
            'confidence': 'high' if count >= 5 else 'medium' if count >= 3 else 'low',
            'score': score
        })

    patterns.sort(key=lambda p: p['score'], reverse=True)
    return patterns


def main():
    parser = argparse.ArgumentParser(description="对话模式提取器")
    parser.add_argument("--transcript", help="transcript JSONL 文件路径")
    parser.add_argument("--text", help="原始对话文本")
    parser.add_argument("--min-repeats", type=int, default=3, help="最小重复次数（默认 3）")
    parser.add_argument("--min-score", type=int, default=5, help="最低分数阈值（默认 5）")

    args = parser.parse_args()

    if args.transcript:
        sequences = extract_tool_sequences(args.transcript)
        patterns = find_repeated_patterns(sequences, args.min_repeats)
    elif args.text:
        patterns = extract_from_text(args.text, args.min_repeats)
    else:
        print(json.dumps({"error": "需要 --transcript 或 --text"}, ensure_ascii=False))
        sys.exit(2)

    # 过滤低分
    patterns = [p for p in patterns if p['score'] >= args.min_score]

    result = {
        "patterns": patterns,
        "count": len(patterns)
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if patterns:
        sys.exit(0)
    else:
        sys.exit(2)


if __name__ == '__main__':
    main()
