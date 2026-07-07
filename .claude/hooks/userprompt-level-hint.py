#!/usr/bin/env python3
from __future__ import annotations

import re

from carroros_hooklib import hook_continue, read_stdin_json

L2_KEYWORDS = [
    "auth", "payment", "migration", "infra", "secret", "credential",
    "权限", "鉴权", "支付", "迁移", "部署", "发布", "删除", "重构", "跨模块", "架构", "无人", "高可靠",
    "delete", "deploy", "release", "migrate", "refactor", "permission", "autonomous",
]

def extract_prompt(payload: dict) -> str:
    for key in ("prompt", "text", "message", "input"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    ti = payload.get("tool_input")
    if isinstance(ti, dict):
        for key in ("prompt", "text", "message", "input"):
            val = ti.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""

def main() -> int:
    payload = read_stdin_json()
    prompt = extract_prompt(payload)
    if len(prompt) < 5:
        return hook_continue()

    lower = prompt.lower()
    reasons = []
    for kw in L2_KEYWORDS:
        if kw.lower() in lower:
            reasons.append(kw)

    file_refs = set(re.findall(r"[\w./-]+\.\w+", prompt))
    if len(file_refs) > 3:
        reasons.append(f"files>3:{len(file_refs)}")

    if reasons:
        return hook_continue(
            "LevelHint: L2_ENHANCE suggested",
            [
                "CarrorOS LevelHint: 建议使用 L2_ENHANCE。",
                "原因: " + ", ".join(reasons[:8]),
                "请通过 carros_base.py init 写入正式 token；本 Hook 不产生治理事实。",
            ],
        )

    return hook_continue("LevelHint: L1_BASE likely")

if __name__ == "__main__":
    raise SystemExit(main())