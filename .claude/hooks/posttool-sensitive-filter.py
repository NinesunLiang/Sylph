#!/usr/bin/env python3
"""
posttool-sensitive-filter.py — PostToolUse — 轻量敏感数据输出过滤器
PostTool 阶段对工具输出做简单模式匹配掩码，阻止敏感信息进入 LLM 上下文。
与 privacy-gate.py (PreTool 读取阻断) 互补：输入阻断 + 输出过滤。

设计原则:
1. 不封装成skill — 直接 hook 级别，零人工操作
2. 不增加治理负担 — 静默掩码，不询问用户
3. 简单模式匹配 — 不是完整 DLP，低成本兜底
4. 只在输出侧做 — privacy-gate 已在输入侧阻止文件读取
"""

import json
import re
import sys
from pathlib import Path

# 敏感模式清单 — 编译后列表
_PATTERNS = [
    # API Keys
    (re.compile(r'sk-[a-zA-Z0-9]{20,}'), '[REDACTED:OPENAI_KEY]'),
    # GitHub Tokens
    (re.compile(r'(?:ghp|ghu|gho|ghs)_[a-zA-Z0-9]{36}'), '[REDACTED:GITHUB_TOKEN]'),
    # Slack Tokens
    (re.compile(r'xox[baprs]-[a-zA-Z0-9-]{20,}'), '[REDACTED:SLACK_TOKEN]'),
    # Private Key — 完整多行块
    (re.compile(
        r'-----BEGIN\s+(RSA|EC|OPENSSH|DSA|PRIVATE)\s+KEY-----'
        r'.*?'
        r'-----END\s+\1\s+KEY-----',
        re.DOTALL
    ), '[REDACTED:PRIVATE_KEY]'),
    # JWT Tokens
    (re.compile(r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'), '[REDACTED:JWT]'),
    # Bearer Tokens
    (re.compile(r'Bearer\s+[a-zA-Z0-9._-]{20,}'), '[REDACTED:BEARER_TOKEN]'),
    # AWS Access Key
    (re.compile(r'AKIA[0-9A-Z]{16}'), '[REDACTED:AWS_KEY]'),
    # OpenAI organization keys
    (re.compile(r'org-[a-zA-Z0-9]{20,}'), '[REDACTED:ORG_KEY]'),
    # Stripe keys
    (re.compile(r'sk_live_[a-zA-Z0-9]{20,}'), '[REDACTED:STRIPE_LIVE_KEY]'),
    (re.compile(r'pk_live_[a-zA-Z0-9]{20,}'), '[REDACTED:STRIPE_LIVE_KEY]'),
]


def mask_text(text: str) -> str:
    """对文本中的敏感模式做掩码替换"""
    masked = text
    for compiled_re, replacement in _PATTERNS:
        masked = compiled_re.sub(replacement, masked)
    return masked


def _mask_value(v, depth=0):
    """递归处理 JSON 中的字符串字段"""
    if depth > 10:
        return v
    if isinstance(v, str):
        return mask_text(v)
    if isinstance(v, dict):
        return {k: _mask_value(vv, depth + 1) for k, vv in v.items()}
    if isinstance(v, list):
        return [_mask_value(item, depth + 1) for item in v]
    return v


def main():
    try:
        raw = sys.stdin.read()
    except Exception:
        # fail-open: 读失败不阻塞
        print(json.dumps({"continue": True}))
        return

    if not raw or not raw.strip():
        print(json.dumps({"continue": True}))
        return

    # 尝试解析 JSON（CC PostTool hook 标准协议）
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        # 非 JSON 格式 → 做文本掩码后输出
        masked = mask_text(raw)
        print(json.dumps({"continue": True,
                          "_filtered": True,
                          "message": "sensitive data masked"}))
        sys.stderr.write(masked)
        return

    # 递归处理所有字符串字段
    try:
        masked_data = _mask_value(data)
        out = json.dumps(masked_data, ensure_ascii=False)
        sys.stdout.write(out)
    except Exception:
        # fail-open: 处理异常时不阻塞
        print(json.dumps({"continue": True,
                          "_filter_error": True}))


if __name__ == "__main__":
    main()
