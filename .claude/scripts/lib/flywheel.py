#!/usr/bin/env python3
"""
flywheel.py — CarrorOS 飞轮升华管道

Error DNA → kernel 升华 → anti-patterns.md 沉淀
飞轮数据落 .omc/knowledge/，不进默认 Context。
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


KNOWLEDGE_DIR = ".omc/knowledge"


def _knowledge_root(project_root: Path) -> Path:
    """Get .omc/knowledge/ directory, create if needed."""
    kd = project_root / KNOWLEDGE_DIR
    kd.mkdir(parents=True, exist_ok=True)
    return kd


def read_error_dna(task_dir: Path, n: int = 50) -> list:
    """Read recent Error DNA records from a task directory."""
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
    return records[-n:]


def extract_patterns(errors: list) -> list:
    """从 Error DNA 中提取可复用的错误模式."""
    grouped = {}

    for err in errors:
        text = err.get("error", "")
        normalized = re.sub(r";\s*attempt=\d+", "", text).lower()
        prefix = normalized[:80]
        item = grouped.setdefault(prefix, {
            "error": text,
            "step": err.get("step", "?"),
            "retry_count": 0,
            "count": 0,
        })
        item["retry_count"] = max(item["retry_count"], err.get("retry_count", 0))
        item["count"] += 1

    patterns = []
    for item in grouped.values():
        text = item["error"].lower()
        retry = item["retry_count"]
        count = item["count"]

        # Classify pattern
        pattern_type = "unknown"
        if any(k in text for k in ["timeout", "timed out"]):
            pattern_type = "timeout"
        elif any(k in text for k in ["assert", "expected", "got"]):
            pattern_type = "assertion"
        elif any(k in text for k in ["import error", "module not found", "cannot find module"]):
            pattern_type = "import"
        elif any(k in text for k in ["syntax", "parse error", "unexpected token"]):
            pattern_type = "syntax"
        elif any(k in text for k in ["permission", "access denied", "forbidden"]):
            pattern_type = "permission"
        elif any(k in text for k in ["not found", "no such file", "enoent"]):
            pattern_type = "not_found"

        if retry >= 2 or count >= 3:
            pattern_type += "_recurring"

        patterns.append({
            "error": item["error"][:200],
            "step": item["step"],
            "pattern": pattern_type,
            "retry_count": retry,
            "count": count,
        })

    return patterns


def get_anti_patterns_path(project_root: Path) -> Path:
    """Path to anti-patterns.md."""
    return project_root / ".claude" / "references" / "anti-patterns.md"


def write_anti_patterns(project_root: Path, patterns: list) -> Optional[Path]:
    """将升华后的模式写入 anti-patterns.md."""
    if not patterns:
        return None

    ap_path = get_anti_patterns_path(project_root)
    existing = []
    if ap_path.exists():
        existing = ap_path.read_text(encoding="utf-8").splitlines()

    lines = []
    lines.append("# Anti-Patterns — 经验沉淀")
    lines.append(f"")
    lines.append(f"_Updated: {datetime.now(timezone.utc).isoformat()}_")
    lines.append(f"")
    lines.append("## 已识别模式\n")

    for p in patterns:
        lines.append(f"- **{p['pattern']}** (step={p['step']}, retry={p['retry_count']})")
        lines.append(f"  - `{p['error'][:120]}`")
        lines.append(f"")

    # Merge with existing
    if existing:
        lines.append("\n## 历史记录\n")
        lines.extend(existing[-50:])

    ap_path.write_text("\n".join(lines), encoding="utf-8")
    return ap_path


def write_claude_next(project_root: Path, entry: str) -> Path:
    """将优化建议写入 claude-next.md (knowledge 目录)."""
    kd = _knowledge_root(project_root)
    cn_path = kd / "claude-next.md"

    lines = []
    if cn_path.exists():
        lines.append(cn_path.read_text(encoding="utf-8"))

    lines.append(f"- [{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}] {entry}")

    cn_path.write_text("\n".join(lines[-200:]), encoding="utf-8")
    return cn_path


def run_flywheel(project_root: Path, task_dir: Optional[Path] = None) -> dict:
    """
    运行飞轮管道主流程。
    1. 读 Error DNA
    2. 提取模式
    3. 写 anti-patterns.md
    4. 写 knowledge/

    Returns summary dict.
    """
    result = {"patterns_found": 0, "anti_patterns_written": False, "knowledge_entries": 0}

    # Collect errors from the requested task dir when provided; otherwise scan all task dirs.
    all_errors = []
    tasks_root = project_root / ".omc" / "tasks"
    if task_dir is not None:
        all_errors.extend(read_error_dna(task_dir))
    elif tasks_root.exists():
        for dna_file in tasks_root.rglob("error-dna.jsonl"):
            try:
                all_errors.extend(read_error_dna(dna_file.parent))
            except Exception:
                pass

    if not all_errors:
        result["note"] = "no errors found in any task"
        return result

    # Extract patterns
    patterns = extract_patterns(all_errors)
    result["patterns_found"] = len(patterns)

    # Write anti-patterns
    if patterns:
        ap = write_anti_patterns(project_root, patterns)
        result["anti_patterns_written"] = ap is not None
        result["anti_patterns_path"] = str(ap) if ap else None

    # Write knowledge entries
    for p in patterns[:5]:
        entry = f"Pattern '{p['pattern']}' detected in step {p['step']}: {p['error'][:80]}"
        write_claude_next(project_root, entry)
        result["knowledge_entries"] += 1

    return result
