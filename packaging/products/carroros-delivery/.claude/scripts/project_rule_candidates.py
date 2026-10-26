"""Extract source-bound project-rule candidates for JEV feedback only."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Callable

SOURCE_FILES = ("README.md", "CLAUDE.md", "AGENTS.md")
CANDIDATE_SCHEMA = "carros.project_rule_candidates.v1"
RULE_SIGNAL = re.compile(r"必须|禁止|不得|应当|需要|红线|规则|规范|must|should|never|always", re.I)


def collect_sources(root: str | Path) -> list[dict]:
    """Collect only approved project documents, with stable line evidence."""
    root = Path(root)
    sources = []
    for name in SOURCE_FILES:
        path = root / name
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        sources.append({"path": name, "lines": lines})
    return sources


def source_blocks(root: str | Path) -> list[dict]:
    blocks = []
    for source in collect_sources(root):
        for number, text in enumerate(source["lines"], start=1):
            text = text.strip()
            if text:
                blocks.append({"source": f"{source['path']}:{number}", "text": text})
    return blocks


def validate_candidates(raw: list[dict], fixed_rule_texts: set[str]) -> list[dict]:
    """Keep only source-bound, feedback-only candidates distinct from fixed rules."""
    candidates = []
    seen = set()
    for item in raw:
        source = str(item.get("source") or "")
        text = str(item.get("text") or "").strip()
        if not source or ":" not in source or not text or text in fixed_rule_texts:
            continue
        if source.split(":", 1)[0] not in SOURCE_FILES:
            continue
        key = hashlib.sha256(f"{source}\n{text}".encode()).hexdigest()[:12]
        if key in seen:
            continue
        seen.add(key)
        candidates.append({
            "candidate_id": f"project.{key}",
            "source": source,
            "text": text,
            "judge_by": item.get("judge_by", "jev"),
            "status": "candidate",
            "enforcement": "feedback_only",
        })
    return candidates


def extract_candidates(root: str | Path, extractor: Callable[[list[dict]], list[dict]] | None,
                       fixed_rule_texts: set[str]) -> dict:
    """Run an injected LLM extractor; unavailable extraction never invents rules."""
    blocks = source_blocks(root)
    if extractor is None:
        raw, reason = [], "extractor_unavailable"
    else:
        raw, reason = extractor(blocks), None
    return {
        "schema_version": CANDIDATE_SCHEMA,
        "mode": "feedback_only",
        "sources": [source["path"] for source in collect_sources(root)],
        "candidates": validate_candidates(raw, fixed_rule_texts),
        "unavailable_reason": reason,
    }


def heuristic_extractor(blocks: list[dict]) -> list[dict]:
    """Conservative local fallback: select only explicit rule-like source lines."""
    return [block for block in blocks if RULE_SIGNAL.search(block["text"])]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="提取项目规则候选（仅反馈，不阻断）")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default=".omc/state/project-rules/candidates.json")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    result = extract_candidates(root, heuristic_extractor, set())
    write_candidates(result, root / args.out)
    print(f"PROJECT_RULE_CANDIDATES={len(result['candidates'])}")
    return 0


def write_candidates(result: dict, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
