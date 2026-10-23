"""test_line_budget.py — 轻量化棘轮（防止治理体量回涨）。

背景：PLAN_SIMPLIFY_SELF_ITERATE.md B0 要求把治理代码从 ~55k 降到 ≤15k。
2026-10-23 实测（CarrorOS_dev 基线）：非测试 .py 36,204 行，距目标仍有差距，但自此必须「只降不升」。

规则（棘轮）：
  · 每个治理目录的非测试 .py 行数不得超过 BUDGET；
  · 真正瘦身后**下调** BUDGET（只降不升），并在提交信息写明删除内容；
  · 确需新增功能：必须同时删除等量代码（净零），或在任务文档写明人类裁决。
  · 超预算 → 本测试失败（红），不静默放行。

计数口径：.claude/{dir}/**/*.py，排除 test_*.py、tests/、__pycache__、worktrees。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / ".claude"

# 2026-10-23 第二阶段标定（B/C 档：死模块删除 + frontend-overnight 迁出治理域）
BUDGET = {
    # 2026-10-24 D-020 下调（只降不升）：删 12 退役命令 + clarify_engine +
    # task_planner + sub_agent_manager 后实测 22,865；留 35 行余量。
    ".claude/scripts": 22550,    # 实测 22499（D-021 删 sub_agent_executor 后再降）
    ".claude/hooks": 7650,       # 实测 7649（到顶，再加代码必须先删）
    ".claude/workflows": 100,    # 实测 0（frontend-overnight 已迁出 → capabilities/）
    ".claude/skills": 3150,      # 实测 3093（本轮未删 skills 代码，不调）
}

# 口径（用户 2026-10-23 裁决 F）：目标只算**非测试**代码，≤25k。
# 2026-10-24 实测 33,241（本轮累计 −2,883）；缺口 ≈8.2k，靠 D 档 + 后续删除逐档下压。
TARGET_NON_TEST_LINES = 25000


def _count_lines(dir_rel: str) -> int:
    """统计目录下非测试 .py 总行数（确定性：只读文件系统）。"""
    base = ROOT / dir_rel
    assert base.is_dir(), f"目录不存在: {dir_rel}"
    total = 0
    for p in base.rglob("*.py"):
        parts = p.parts
        if "__pycache__" in parts or "worktrees" in parts:
            continue
        if p.name.startswith("test_") or "tests" in parts:
            continue
        total += len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
    return total


def test_non_test_python_within_budget():
    failures = []
    for dir_rel, budget in BUDGET.items():
        actual = _count_lines(dir_rel)
        if actual > budget:
            failures.append(f"{dir_rel}: {actual} > {budget} (+{actual - budget})")
    assert not failures, (
        "治理代码体量回涨，违反轻量化棘轮（PLAN_SIMPLIFY B0）：\n  "
        + "\n  ".join(failures)
        + "\n处置：删除等量死代码/冗余，或经人类裁决后显式上调 BUDGET 并在任务文档留证。"
    )


def test_budget_wellformed():
    """预算表本身必须健全（防止误改成 0 / 负数 / 超大值绕过棘轮）。"""
    assert all(v > 0 for v in BUDGET.values())
    assert sum(BUDGET.values()) <= 50000, "BUDGET 汇总失控，检查是否被误改"
