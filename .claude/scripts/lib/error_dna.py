#!/usr/bin/env python3
"""
error_dna.py — CarrorOS Error DNA 自动生成与检索

每步失败自动生成 Error DNA 记录。
最多 retry 3 次，仍失败则 BLOCKED。
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


MAX_RETRIES = 3


def record_error(
    task_dir: Path,
    step_id: str,
    error_text: str,
    artifact_path: Optional[str] = None,
    retry_count: int = 0,
) -> dict:
    """记录失败为 Error DNA。返回 DNA 记录。

    K1 噪声过滤: error 文本 < 8 字符(如 "t"/"err" 测试噪声)不入库,
    返回带 quarantined 标记的记录 — 防再染(存量隔离见 .omc/error-dna.quarantine.jsonl)。
    """
    if len((error_text or "").strip()) < 8:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": step_id,
            "error": (error_text or "")[:500],
            "artifact": artifact_path or "",
            "retry_count": retry_count,
            "suggested_action": "quarantined: noise below MIN_ERROR_LEN(8)",
            "quarantined": True,
        }
    dna = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": step_id,
        "error": error_text[:500],
        "artifact": artifact_path or "",
        "retry_count": retry_count,
        "suggested_action": _suggest_action(error_text),
    }

    # Append to error DNA log
    dna_path = task_dir / "error-dna.jsonl"
    dna_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dna_path, "a") as f:
        f.write(json.dumps(dna, ensure_ascii=False) + "\n")

    return dna


def _suggest_action(error_text: str) -> str:
    """基于错误文本给出常见建议。"""
    text = error_text.lower()
    suggestions = {
        "timeout": "increase timeout or split step",
        "not found": "check file path or install dependency",
        "assertion": "check test logic or expected value",
        "syntax error": "fix code syntax",
        "import error": "install missing package",
        "permission": "check file permissions",
        "connection": "check network or service availability",
    }
    for keyword, action in suggestions.items():
        if keyword in text:
            return action
    return "investigate error manually"


def get_recent_errors(task_dir: Path, step_id: Optional[str] = None, n: int = 5) -> list:
    """读取 recent error DNA 记录。"""
    dna_path = task_dir / "error-dna.jsonl"
    if not dna_path.exists():
        return []
    records = []
    with open(dna_path) as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if step_id:
        records = [r for r in records if r.get("step") == step_id]
    return records[-n:]


def check_retry_gate(task_dir: Path, step_id: str) -> tuple:
    """
    Retry gate check.
    Returns (allowed: bool, retry_count: int, message: str)
    """
    errors = get_recent_errors(task_dir, step_id)
    retry_count = sum(1 for e in errors if e.get("retry_count", 0) > 0 or e.get("error"))

    if retry_count >= MAX_RETRIES:
        return False, retry_count, f"MAX_RETRIES ({MAX_RETRIES}) reached for {step_id}"

    return True, retry_count, f"retry {retry_count}/{MAX_RETRIES} allowed"
