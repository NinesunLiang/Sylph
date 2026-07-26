#!/usr/bin/env python3
"""compound-verify-gate.py — ADR-0013 Phase 2: 双模型交叉校验门

在 scorecard-gate 证据溯源(Phase 1)通过后触发：
  1. 生成当前 scorecard 的状态快照（分数+证据引用）
  2. 调用第二个模型独立评分（通过 stdin/stdout 协议）
  3. 对比两个模型评分，Δ≥1.5 的维度标注 ⚠️ 仲裁中

设计原则（哲学链）:
  - 只读：不修改 scorecard.md，只生成对账报告
  - 异步：不阻断 scorecard 写入，对账报告作为补充材料
  - 可重复：同一评分输入多次运行产生相同对账结果

Usage:
    python3 .claude/hooks/compound-verify-gate.py --scorecard <path> [--save <path>]

    --scorecard  指向 scorecard.md 路径（默认 .claude/references/scorecard.md）
    --save       对账报告输出路径（默认 .omc/state/oracle/reconciliation-latest.json）

依赖:
    - pretool-scorecard-gate.py (Phase 1 证据溯源)
    - verify_contract.py (判决同源)
    - 外部评分模型通过 stdin 读取 prompt，stdout 返回 CSV

输出 JSON 契约:
    {"generated_at": "...", "dimensions": [...], "disputed": [...], "summary": {...}}
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOOK_DIR = Path(__file__).resolve().parent
ROOT = HOOK_DIR.parents[1]

DEFAULT_SCORECARD = ROOT / ".claude" / "references" / "scorecard.md"
DEFAULT_OUTPUT = ROOT / ".omc" / "state" / "oracle" / "reconciliation-latest.json"

DISPUTE_THRESHOLD = 1.5

# ── 维度提取正则（匹配 peer_review 分数列）──
# 格式:  | C1 | 指令清晰度 | 15 | 9 | 9 | **9** | **9** | 0 |
# 自评列 = col 5, 外评列 = col 6
_SCORE_LINE_RE = re.compile(
    r"^\|\s*(C\d+|E\d+|G\d+|UX\d+)\s*\|\s*([^|]+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*"
    r"\*{0,2}(\d+)\*{0,2}\s*\|\s*\*{0,2}(\d+)\*{0,2}\s*\|"
)


def _parse_scorecard(path: Path) -> list[dict]:
    """解析 scorecard 提取维度名、权重、自评、外评。"""
    dims = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _SCORE_LINE_RE.match(line.strip())
        if not m:
            continue
        dims.append({
            "key": m.group(1).strip(),
            "name": m.group(2).strip(),
            "weight": int(m.group(3)),
            "self_score": int(m.group(5)),
            "ext_score": int(m.group(6)),
        })
    return dims


def _generate_verify_prompts(dims: list[dict]) -> str:
    """为第二个模型生成评分 prompt。"""
    lines = [
        "# CarrorOS 独立外评交叉校验",
        "",
        "请对以下维度逐一评分（0-10 整数），",
        "评分依据仅限知识库中实际存在的代码和数据，非设计文档。",
        "",
        "| 编号 | 维度名 | 权重 | 关键证据文件 |",
        "|------|--------|------|-------------|",
    ]
    evidence_map = {
        "C1": ".claude/settings.json",
        "C2": ".omc/state/handoff.json, .claude/hooks/session-start.py",
        "C3": ".claude/hooks/pretool-gate.py, .claude/hooks/completion-gate.py",
        "C4": ".claude/hooks/posttool-output-schema.py",
        "C5": ".claude/settings.json, .claude/hooks/lib/lifecycle_ssot.py",
        "C6": ".omc/state/retry-budget.json, .omc/knowledge/claude-next.md",
        "C7": ".claude/hooks/stop-flywheel.py",
        "C8": ".claude/hooks/, .claude/hooks/index.md",
        "C9": ".claude/hooks/error-dna.py, .claude/hooks/verify_contract.py",
        "E1": ".claude/hooks/pretool-gate.py _check_edit_scope()",
        "E2": ".claude/hooks/posttool-claim-audit.py",
        "E3": ".claude/hooks/completion-gate.py",
        "E4": "tests/test-e4-inertia.py",
        "E5": ".claude/hooks/completion-gate.py (E5 RCA 检测)",
        "E6": ".omc/state/edit-churn-log.json",
        "E7": "tests/test-oracle-gate.py",
        "E8": ".claude/hooks/precompact-lifecycle.py",
    }
    for d in dims:
        ev = evidence_map.get(d["key"], "")
        lines.append(f"| {d['key']} | {d['name']} | {d['weight']} | {ev} |")
    lines.extend([
        "",
        "输出 CSV 格式：",
        "维度,分数,依据",
        "C1,9,\"依据...\"",
        "...",
    ])
    return "\n".join(lines)


def _reconcile(primary: list[dict], secondary: list[dict]) -> dict[str, Any]:
    """对比两个模型评分，标记仲裁项。"""
    secondary_map = {d["key"]: d for d in secondary}
    reconciled = []
    disputed = []
    for p in primary:
        s = secondary_map.get(p["key"])
        if not s:
            reconciled.append({**p, "peer_score": None, "delta": None, "status": "NO_PEER"})
            continue
        delta = abs(p["ext_score"] - s.get("peer_score", 0))
        entry = {
            **p,
            "peer_score": s.get("peer_score", 0),
            "delta": round(delta, 1),
            "status": "ARBITRATION_NEEDED" if delta >= DISPUTE_THRESHOLD else "AGREED",
        }
        reconciled.append(entry)
        if delta >= DISPUTE_THRESHOLD:
            disputed.append(entry)
    return {"reconciled": reconciled, "disputed": disputed}


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="双模型交叉校验门")
    parser.add_argument("--scorecard", default=str(DEFAULT_SCORECARD))
    parser.add_argument("--save", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--peer-csv", help="第二个模型的 CSV 评分结果（可选：不传则生成 prompt 到 stdout）")
    args = parser.parse_args()

    dims = _parse_scorecard(Path(args.scorecard))

    if not args.peer_csv:
        # Phase 1: 输出给第二个模型的 prompt
        print(_generate_verify_prompts(dims))
        return 0

    # Phase 2: 已有两个评分，做对账
    peer_lines = Path(args.peer_csv).read_text(encoding="utf-8").strip().splitlines()
    peer_dims = []
    for line in peer_lines:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 2 and parts[0].startswith(("C", "E", "G", "UX")):
            try:
                peer_dims.append({"key": parts[0], "peer_score": int(parts[1])})
            except ValueError:
                pass

    result = _reconcile(dims, peer_dims)
    output_path = Path(args.save)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dimensions": result["reconciled"],
        "disputed_count": len(result["disputed"]),
        "disputed": result["disputed"],
        "meta": {
            "threshold": DISPUTE_THRESHOLD,
            "total": len(dims),
            "agreed": len(dims) - len(result["disputed"]),
            "dispute_rate": round(len(result["disputed"]) / max(len(dims), 1) * 100, 1),
        },
    }, ensure_ascii=False, indent=2))

    print(f"✅ 交叉校验完成: {len(dims)} 维, {len(result['disputed'])} 项需仲裁")
    print(f"   对账报告: {output_path}")
    return 0 if not result["disputed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
