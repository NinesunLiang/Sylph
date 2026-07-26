#!/usr/bin/env python3
"""CarrorOS PKG-B: Unified Verification Verdict Contract.
Single source of truth for all 6 verdict levels. No more duplicated logic.
Philosophy: 验证 > 零信任 > 守护 > 文档 > 人本 > 增益 > 少
Disk is the only truth.
"""
from __future__ import annotations
import json
from typing import Any, Dict, Literal, Optional

VERDICT_ORDER = ("PASS", "REDIRECT", "FORCE", "TRIGGER", "ESCALATE", "BLOCK")
VERDICT_MAP = {v: i for i, v in enumerate(VERDICT_ORDER)}

_REDIRECT_GUIDANCE_MAP: dict[str, str] = {
    "multi_cmd_newline": "多命令请用 && 连接单行而非 \\n 换行。",
    "redundant_file_probe": "重复检查文件请一次性 Read，不要连续 head/wc/cat。",
    "gov_file_bypass": "治理文件不可写入，请选择 scope 内路径。",
    "cd_churn": "连续 cd 无意义，请直接用绝对路径。",
}


def classify_verdict(
    verdict: str,
    reason: str = "",
    detail_key: str = "",
) -> dict[str, Any]:
    """唯一判决生成入口，所有 hook/pipeline/sh 共享。

    返回固定 JSON 契约:
      {"continue": bool, "verdict": str, "reason": str,
       "redirect_guidance": str (仅 REDIRECT), "audit_event_type": str}
    """
    v = verdict.upper().strip()
    if v not in VERDICT_MAP:
        v = "BLOCK"
    base: dict[str, Any] = {
        "continue": v in ("PASS", "FORCE", "TRIGGER"),
        "verdict": v,
        "reason": reason or f"verdict:{v}",
    }
    if v == "REDIRECT":
        base["redirect_guidance"] = _REDIRECT_GUIDANCE_MAP.get(
            detail_key,
            "请调整行为并补充可验证证据后重试。",
        )
    base["audit_event_type"] = f"oracle_gate_{v.lower()}"
    return base


def verdict_to_exit_code(v: str) -> int:
    """判决映射到 hook 兼容退出码: 0=放行, 2=阻断(PreTool)/0=放行(PostTool)。"""
    return 0 if v in ("PASS", "FORCE", "TRIGGER") else 2


def verdict_dict(cmd: str) -> dict[str, Any]:
    """向后兼容快捷入口：输入 bash 命令返回标准化判决字典。"""
    if not cmd.strip():
        return classify_verdict("PASS")
    return classify_verdict("PASS")


if __name__ == "__main__":
    import sys
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    v_in = str(payload.get("verdict", "PASS"))
    r_in = str(payload.get("reason", ""))
    dk_in = str(payload.get("detail_key", ""))
    print(json.dumps(classify_verdict(v_in, r_in, dk_in), ensure_ascii=False))
