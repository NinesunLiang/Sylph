#!/usr/bin/env python3
"""
check_commit_msg.py — CarrorOS 提交信息合规检查

检查规则（C2 上下文完整度指标）：
1. 以中文开头 — 必须使用 CJK 统一表意文字开头
2. 长度不超过 72 字符 — 遵循 Git 提交信息规范
3. 不包含 # 字符 — Git 会截断 # 后的内容

Usage:
    python3 .claude/scripts/check_commit_msg.py <commit_message>

Exit codes:
    0 = 通过（符合所有规则）
    1 = 不通过（至少一条规则违例）
"""

import re
import sys


def is_cjk_start(text: str) -> bool:
    """检查文本是否以中文字符（CJK Unified Ideographs）开头"""
    if not text:
        return False
    first_char = text[0]
    return '\u4e00' <= first_char <= '\u9fff'


def check_length(text: str) -> tuple[bool, int]:
    """检查文本长度是否不超过 72 字符。返回 (通过, 实际长度)。"""
    length = len(text)
    return length <= 72, length


def check_no_hash(text: str) -> bool:
    """检查文本中是否包含 # 字符"""
    return '#' not in text


def validate_commit_msg(msg: str) -> list[str]:
    """
    对提交信息执行全部合规检查，返回违例列表。
    空列表表示全部通过。
    """
    violations: list[str] = []

    if not is_cjk_start(msg):
        violations.append("提交信息必须以中文开头")

    ok, length = check_length(msg)
    if not ok:
        violations.append(f"提交信息长度 {length} 字符超过 72 字符限制")

    if not check_no_hash(msg):
        violations.append("提交信息不能包含 '#' 字符")

    return violations


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 .claude/scripts/check_commit_msg.py <commit_message>")
        return 1

    msg = sys.argv[1]
    violations = validate_commit_msg(msg)

    if not violations:
        print("commit-msg: 通过")
        return 0

    print("commit-msg: 不通过 — 以下规则违例：")
    for v in violations:
        print(f"  - {v}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
