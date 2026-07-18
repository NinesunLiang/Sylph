#!/usr/bin/env python3
"""
stop-flywheel.py — CarrorOS Stop hook（飞轮自动触发 + 升华检查）

会话停止时：
  1. run_flywheel：error-dna → 模式提取 → anti-patterns.md + claude-next.md
  2. 升华检查：claude-next 条目 hits≥5 → 升华至 anti-patterns.md（kernel 候选），
     记录 sublimation-log.jsonl（铁律 6：不直接改 kernel.md/AGENTS.md，升华候选由人类裁决晋升）

设计：快速（<2s）、永不阻断（exit 0）、失败静默。
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
ROOT = HOOK_DIR.parents[1]
os.chdir(str(ROOT))
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))

KNOWLEDGE = ROOT / ".omc" / "knowledge"
CLAUDE_NEXT = KNOWLEDGE / "claude-next.md"
SUBLIMATION_LOG = KNOWLEDGE / "sublimation-log.jsonl"
ANTI_PATTERNS = ROOT / ".claude" / "references" / "anti-patterns.md"

SUBLIMATION_HITS = 5


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _run_flywheel() -> dict:
    try:
        from lib.flywheel import run_flywheel
        return run_flywheel(ROOT)
    except Exception as exc:
        return {"error": str(exc)}


def _sublimation_check() -> list[str]:
    """claude-next 中 hits≥5 的模式 → anti-patterns.md + 升华日志。返回升华的模式。"""
    if not CLAUDE_NEXT.exists():
        return []
    try:
        lines = CLAUDE_NEXT.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    # 统计每个 pattern 的 hits（每行 1 hit），跳过已升华
    pattern_counts: Counter[str] = Counter()
    for line in lines:
        if "已升华" in line or "升华到" in line:
            continue
        m = re.search(r"Pattern '([^']+)'", line)
        if m:
            pattern_counts[m.group(1)] += 1

    candidates = [p for p, c in pattern_counts.items() if c >= SUBLIMATION_HITS]
    if not candidates:
        return []

    # 已存在于 anti-patterns.md 的模式跳过
    existing = ""
    if ANTI_PATTERNS.exists():
        try:
            existing = ANTI_PATTERNS.read_text(encoding="utf-8")
        except Exception:
            existing = ""

    sublimated: list[str] = []
    for pattern in candidates:
        if f"`{pattern}`" in existing or pattern in existing:
            continue
        hits = pattern_counts[pattern]
        entry = (
            f"\n### {pattern}（飞轮升华 {datetime.now(timezone.utc).strftime('%Y-%m-%d')}）\n"
            f"- 来源：claude-next 自动升华，hits={hits}（阈值≥{SUBLIMATION_HITS}）\n"
            f"- 触发条件：error-dna 中反复出现的 `{pattern}` 失败模式\n"
            f"- 正确行为：见 .omc/knowledge/claude-next.md 相关条目；晋升 kernel.md 需人类裁决\n"
        )
        try:
            with ANTI_PATTERNS.open("a", encoding="utf-8") as f:
                f.write(entry)
            with SUBLIMATION_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": _now_iso(), "pattern": pattern, "hits": hits,
                    "target": "anti-patterns.md", "kernel_promotion": "pending_human_review",
                }, ensure_ascii=False) + "\n")
            sublimated.append(pattern)
        except Exception:
            pass
    return sublimated


def main() -> None:
    # 读 stdin（Stop payload），但不依赖其内容
    try:
        sys.stdin.read()
    except Exception:
        pass

    result = _run_flywheel()
    sublimated = _sublimation_check()

    if result.get("patterns_found") or sublimated:
        print(
            f"🛞 [flywheel] patterns={result.get('patterns_found', 0)} "
            f"anti_patterns={result.get('anti_patterns_written', False)} "
            f"sublimated={sublimated or 'none'}",
            file=sys.stderr, flush=True,
        )

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
