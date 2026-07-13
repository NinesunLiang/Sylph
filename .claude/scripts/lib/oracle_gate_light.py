#!/usr/bin/env python3
"""
oracle_gate_light.py — CarrorOS Oracle 条件接入（轻量版，同级模型）

仅为 L2 高 residual risk 场景提供辅助判断。
不进 VerifyGate — Oracle 是辅助，不是验证。
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def should_trigger_oracle(
    level: str,
    risk_level: Optional[str] = None,
    retry_count: int = 0,
    user_requested: bool = False,
) -> tuple:
    """
    判断是否需要触发 Oracle。

    触发条件（任一满足）：
    - L2 + residual risk == high
    - retry_count >= 2（两次失败）
    - 用户显式要求

    Returns (trigger: bool, reason: str)
    """
    if user_requested:
        return True, "user_requested"

    if level == "L1":
        return False, "L1 tasks: no oracle"

    if level in ("L2", "L2_ENHANCE"):
        if retry_count >= 2:
            return True, f"retry_count={retry_count} >= 2"
        if risk_level == "high":
            return True, "L2 + high residual risk"
        if risk_level == "medium":
            # medium risk = optional, defer
            return False, "L2 + medium risk (deferred)"

    return False, "no trigger conditions met"


def run_oracle(
    prompt: str,
    model_hint: str = "deepseek-v4-flash",
    timeout: int = 30,
) -> str:
    """
    运行 Oracle（同级模型，非高阶模型）。
    调用 local DeepSeek proxy (127.0.0.1:9998)。
    """
    api_url = "http://127.0.0.1:9998/v1/messages"

    payload = json.dumps({
        "model": model_hint,
        "max_tokens": 1024,
        "temperature": 0.3,
        "messages": [
            {"role": "user", "content": f"""You are Oracle, an auxiliary reviewer.
Review the following and return a brief verdict (≤300 chars).
Focus on: residual risk, missing edge cases, factual errors.

{prompt}
"""}
        ]
    })

    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", api_url,
             "-H", "Content-Type: application/json",
             "-H", "x-api-key: test",
             "-d", payload],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode != 0:
            return f"[Oracle unavailable] curl error: {result.stderr[:200]}"
        try:
            resp = json.loads(result.stdout)
            content = ""
            for c in resp.get("content", []):
                if c.get("type") == "text":
                    content += c.get("text", "")
            return content[:600] if content else "[Oracle empty response]"
        except (json.JSONDecodeError, KeyError) as e:
            return f"[Oracle parse error] {str(e)[:200]}"
    except subprocess.TimeoutExpired:
        return "[Oracle timeout]"
    except Exception as e:
        return f"[Oracle error] {str(e)[:200]}"


def verdict_from_oracle(text: str) -> str:
    """
    提取 Oracle 裁决摘要。
    不进 VerifyGate，只辅助判断。
    """
    text_lower = text.lower()
    if "reject" in text_lower or "fail" in text_lower or "issue" in text_lower:
        return "REVIEW_NEEDED"
    if "accept" in text_lower or "pass" in text_lower or "ok" in text_lower:
        return "PASS"
    return "ADVISORY"
