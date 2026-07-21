#!/usr/bin/env python3
"""
error_dna.py — CarrorOS Error DNA 自动生成与检索

每步失败自动生成 Error DNA 记录。
最多 retry 3 次，仍失败则 BLOCKED。
"""

import json
import re
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


def _classify_error(text: str) -> str:
    """对错误文本做多级分类，返回分类标签。E5 增强: stderr 签名匹配 + 细粒度分类。"""
    t = text.lower()
    # Exit code / runtime signals
    if "exit code 1" in t or "exit 1" in t or "returned 1" in t:
        return "runtime_error"
    if "exit code 2" in t or "exit 2" in t:
        return "syntax_or_misuse"
    if "killed" in t:
        return "process_killed"
    # signal detection: use word boundary to avoid false match on "sign" / "assignable"
    if re.search(r"\bsignal\b", t) or re.search(r"\bsig\w*term\b", t) or re.search(r"\bsig\w*kill\b", t):
        return "process_killed"
    if "oom" in t or "out of memory" in t or "memory" in t:
        return "out_of_memory"
    if "timeout" in t or "timed out" in t or "took too long" in t:
        return "timeout"
    if "traceback" in t or "traceback" in t:
        return "python_exception"
    if "typeerror" in t or "valueerror" in t or "keyerror" in t or "importerror" in t or "attributeerror" in t:
        return "python_exception"
    # Build / compile
    if "tsc" in t or "typescript" in t and "error" in t:
        return "typescript_error"
    if "eslint" in t or "lint" in t:
        return "lint_error"
    if "build" in t and "fail" in t:
        return "build_failure"
    # Test
    if "assert" in t or "assertion" in t or "expected" in t:
        return "test_assertion"
    if "test" in t and "fail" in t:
        return "test_failure"
    # Filesystem / network
    if "not found" in t or "enoent" in t or "no such" in t:
        return "file_not_found"
    if "permission" in t or "eaccess" in t or "denied" in t:
        return "permission_denied"
    if "import" in t and ("error" in t or "fail" in t):
        return "import_error"
    if "connection" in t or "refused" in t or "network" in t:
        return "network_error"
    # Deps / config
    if "depend" in t or "package" in t or "module" in t:
        return "dependency_missing"
    if "config" in t or "configuration" in t:
        return "configuration_error"
    # Content / validation
    if "invalid" in t or "malformed" in t:
        return "invalid_input"
    if "duplicate" in t or "conflict" in t:
        return "conflict_error"
    # Fallback: unknown
    return "unknown"


def _suggest_action(error_text: str) -> str:
    """基于错误分类给出具体建议。E5 增强: 20+ 细分分类替代原 7 类。"""
    cat = _classify_error(error_text)
    suggestions = {
        "runtime_error": "check exit code, inspect logs for crash cause",
        "syntax_or_misuse": "fix command syntax or argument order",
        "process_killed": "check resource limits (memory/cpu/disk)",
        "out_of_memory": "reduce memory usage or increase limit",
        "timeout": "increase timeout or split step into smaller units",
        "python_exception": "read traceback, fix the offending line",
        "typescript_error": "fix type errors reported by tsc",
        "lint_error": "fix lint violations",
        "build_failure": "check build log for compilation errors",
        "test_assertion": "verify expected vs actual values in test",
        "test_failure": "investigate test failure root cause",
        "file_not_found": "check file path exists or create it",
        "permission_denied": "check file permissions or use sudo",
        "import_error": "install missing dependency",
        "network_error": "check network connectivity or service health",
        "dependency_missing": "install required package",
        "configuration_error": "check config file syntax and values",
        "invalid_input": "validate input format and content",
        "conflict_error": "resolve duplicate or conflicting entries",
        "unknown": "investigate error manually — classify for future automatic detection",
    }
    return suggestions.get(cat, "investigate error manually")


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
