#!/usr/bin/env python3
"""error_dna_logger.py — 错误 DNA 收集器

功能：
  - 捕获 GoalMachine/Gate 验证失败
  - 记录错误类型、触发条件、修复建议
  - 写入 .omc/error-dna.jsonl 供后续分析

使用：
  from error_dna_logger import log_error
  log_error("PlanGateError", "缺少 Phase 声明", fix="在 plan.md 添加 ## Phase N")
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ERROR_DNA_PATH = Path(".omc/error-dna.jsonl")


def log_error(
    error_type: str,
    description: str,
    fix: str | None = None,
    context: dict | None = None,
):
    """记录错误到 error-dna.jsonl"""
    ERROR_DNA_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": error_type,
        "description": description,
        "fix": fix,
        "context": context or {},
    }
    
    with ERROR_DNA_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
