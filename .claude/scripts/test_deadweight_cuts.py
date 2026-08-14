"""死代码清理回归测试（cut-deadweight-p0p1）。

「修复=砍掉」的 4 组回归防线，防止死代码/悬空引用/垃圾残留回潮：
  1. gate-contract.yaml 契约 required_gates == 实际路由门禁（pretool-gate.py 单一真源）
  2. atomic schema 无悬空 ref（target 必须存在）
  3. .omc/state 无一次性评测残留
  4. checks.py 无未路由死函数
"""

from __future__ import annotations
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
GATE_CONTRACT = ROOT / ".claude" / "scripts" / "gate-contract.yaml"  # 契约已随重组移至 .claude/scripts/
CHECKS_PY = ROOT / ".claude" / "hooks" / "pretool_gates" / "checks.py"
SCHEMAS_ATOMIC = ROOT / ".claude" / "schemas" / "atomic"
OMC_STATE = ROOT / ".omc" / "state"

# 路由真源：.claude/hooks/pretool-gate.py L1_GATES / GATES（index18 G5 单一真源）
ROUTED_L1 = {"sensitive-edit", "governance-bypass", "action", "secret-scan", "stall"}
ROUTED_L2 = ROUTED_L1 | {
    "verify", "oracle", "document-quality", "g2-large-file", "g3-reviews",
    "g5-wide-glob", "g6-budget", "action-loop", "numeric-claim", "injection-guard",
}

# 路由门禁对应的实现函数（pretool-gate.py 路由表）
ROUTED_FUNCS = {
    "_check_sensitive_edit", "_check_governance_bypass", "_check_action_gate",
    "_check_secret_scan", "_check_stall", "_check_verify_gate", "_check_oracle_gate",
    "_check_document_quality", "_check_g2_large_file", "_check_g3_reviews",
    "_check_g5_wide_glob", "_check_g6_budget", "_check_action_loop",
    "_check_numeric_claim", "_check_injection",
}


def _load_gate_contract():
    with open(GATE_CONTRACT, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_gate_contract_l1_matches_routed():
    data = _load_gate_contract()
    actual = set(data["L1"]["required_gates"])
    assert actual == ROUTED_L1, f"契约 L1 与实际路由不一致: 差异={sorted(actual ^ ROUTED_L1)}"


def test_gate_contract_l2_matches_routed():
    data = _load_gate_contract()
    actual = set(data["L2"]["required_gates"])
    assert actual == ROUTED_L2, f"契约 L2 与实际路由不一致: 差异={sorted(actual ^ ROUTED_L2)}"


def _collect_ref_targets(node, out):
    if isinstance(node, dict):
        if node.get("type") == "ref" and node.get("target"):
            out.append(str(node["target"]))
        for v in node.values():
            _collect_ref_targets(v, out)
    elif isinstance(node, list):
        for item in node:
            _collect_ref_targets(item, out)


def test_no_dangling_schema_refs():
    dangling = []
    for f in sorted(SCHEMAS_ATOMIC.glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        refs = []
        _collect_ref_targets(data, refs)
        for target in refs:
            if not (SCHEMAS_ATOMIC / target).exists():
                dangling.append(f"{f.name} -> {target}")
    assert not dangling, f"悬空 schema 引用: {dangling}"


STALE_FILES = [
    "eval-report-index4.readiness.json",
    "eval-report.readiness.json",
    "external-eval-bundle.json",
    "data-quality-report.json",
    "hud-stdin-cache.json",
]


def test_stale_state_files_removed():
    leftover = [name for name in STALE_FILES if (OMC_STATE / name).exists()]
    assert not leftover, f"垃圾残留仍在 .omc/state: {leftover}"


def test_no_unrouted_gate_functions():
    src = CHECKS_PY.read_text(encoding="utf-8")
    defined = set(re.findall(r"^def (_check_\w+)", src, re.M))
    unrouted = defined - ROUTED_FUNCS
    assert not unrouted, f"未路由死函数: {sorted(unrouted)}"
    assert defined == ROUTED_FUNCS, f"实现函数与路由表不一致: 缺失={sorted(ROUTED_FUNCS - defined)}"
