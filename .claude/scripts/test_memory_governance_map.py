"""test_memory_governance_map.py — 治理类长期记忆必须映射到裁决记录（2026-10-24）

边界（人类裁决）：
  · 个人偏好 / 参考类记忆留在 Claude 长期记忆，不强制映射；
  · 声明 `metadata.governance: true` 的记忆，必须写 `metadata.decision: D-xxx / ADRxxxx`，
    且该裁决在 `.claude/decisions/DECISIONS.md` 或 `.claude/references/adr/` 真实存在。
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
SLUG = str(REPO).replace("/", "-").replace("_", "-").replace(".", "-")
MEM_DIR = Path.home() / ".claude" / "projects" / SLUG / "memory"
DECISIONS = REPO / ".claude" / "decisions" / "DECISIONS.md"
ADR_DIR = REPO / ".claude" / "references" / "adr"


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    return yaml.safe_load(text[3:end]) or {}


def _decision_exists(ref: str) -> bool:
    if ref.upper().startswith("ADR"):
        num = ref[3:].lstrip("-_")
        return any(p.name.startswith(num) for p in ADR_DIR.glob("*.md"))
    if not DECISIONS.exists():
        return False
    return bool(re.search(rf"\b{re.escape(ref)}\b", DECISIONS.read_text(encoding="utf-8")))


def test_governance_memories_map_to_real_decisions():
    if not MEM_DIR.exists():
        return  # 换机器 / 无记忆目录时不误报
    failures: list[str] = []
    for md in sorted(MEM_DIR.glob("*.md")):
        if md.name == "MEMORY.md":
            continue
        meta = (_frontmatter(md).get("metadata") or {})
        if not meta.get("governance"):
            continue
        refs = meta.get("decision") or []
        if isinstance(refs, str):
            refs = [r.strip() for r in refs.split(",") if r.strip()]
        if not refs:
            failures.append(f"{md.name}: 治理类记忆缺 decision 映射")
            continue
        for ref in refs:
            if not _decision_exists(ref):
                failures.append(f"{md.name}: decision {ref} 不存在")
    assert not failures, "治理类记忆未映射到真实裁决：\n  " + "\n  ".join(failures)
