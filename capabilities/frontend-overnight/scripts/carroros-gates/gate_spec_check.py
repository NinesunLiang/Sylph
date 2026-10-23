#!/usr/bin/env python3
"""gate_spec_check.py — 门禁 spec↔实现一致性校验（2026-10-23 P7 / 审计 D10 根因修复）

契约：gate-spec.yaml 每个 gate 声明 checks[]（判据 id）；实现脚本内必须有标记行
    GATE_CHECKS <gate_id>: <id> [<id> ...]
本校验要求 实现声明 ⊇ spec 声明：
  - 实现脚本文件不存在            → 缺项
  - spec 判据未在任何标记行出现   → 缺项
缺项 → 输出 GATE_SPEC_MISMATCH（preflight 计入 fails → NO-GO）。

用法: gate_spec_check.py [--workflow-root DIR]
退出: 0=一致  1=GATE_SPEC_MISMATCH  2=spec 文件缺失/解析失败
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

import yaml

MARK_RE = re.compile(r"^\s*#\s*GATE_CHECKS\s+([A-Z]\d+)\s*:\s*(.+)$", re.MULTILINE)
DEFAULT_SPEC = Path(__file__).resolve().parent.parent.parent / "gate-spec.yaml"


def parse_marks(impl_text: str) -> dict[str, set[str]]:
    """提取实现脚本里的 GATE_CHECKS 标记行 → {gate_id: {check, ...}}（同 gate 多行合并）。"""
    out: dict[str, set[str]] = {}
    for m in MARK_RE.finditer(impl_text):
        out.setdefault(m.group(1), set()).update(m.group(2).split())
    return out


def check_spec(spec_path: Path, gates_dir: Path) -> tuple[list[str], dict]:
    """返回 (missing: list[str], report: dict)。missing 非空 = 不一致。"""
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
    gates = spec.get("gates", {})
    marks_cache: dict[str, dict[str, set[str]]] = {}
    missing: list[str] = []
    report: dict[str, dict] = {}
    for gid, gdef in sorted(gates.items()):
        impl = Path(gdef.get("impl", ""))
        impl_file = gates_dir / impl
        spec_checks = list(gdef.get("checks", []))
        if not impl_file.is_file():
            missing += [f"{gid}: 实现文件缺失 {impl}（判据 {spec_checks}）"]
            report[gid] = {"ok": False, "declared": [], "missing": spec_checks}
            continue
        marks = marks_cache.get(str(impl_file))
        if marks is None:
            marks = parse_marks(impl_file.read_text(encoding="utf-8"))
            marks_cache[str(impl_file)] = marks
        declared = marks.get(gid, set())
        gap = [c for c in spec_checks if c not in declared]
        report[gid] = {"ok": not gap, "declared": sorted(declared), "missing": gap}
        for c in gap:
            missing.append(f"{gid}: 判据未实现 {c}（spec 要求 {spec_checks}，标记行声明 {sorted(declared) or '无'}）")
    return missing, report


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    spec = DEFAULT_SPEC
    if "--workflow-root" in argv:
        i = argv.index("--workflow-root")
        spec = Path(argv[i + 1]) / "gate-spec.yaml" if i + 1 < len(argv) else DEFAULT_SPEC
    if not spec.is_file():
        print(f"ERROR: gate-spec 不存在 {spec}", file=sys.stderr)
        return 2
    gates_dir = Path(__file__).resolve().parent
    missing, report = check_spec(spec, gates_dir)
    for gid, r in report.items():
        print(("  ✓" if r["ok"] else "  ✗") + f" {gid}: " + ("一致" if r["ok"] else "; ".join(r["missing"])))
    if missing:
        print(f"GATE_SPEC_MISMATCH（{len(missing)} 项）", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1
    print("gate-spec 一致：实现 ⊇ spec")
    return 0


if __name__ == "__main__":
    sys.exit(main())
