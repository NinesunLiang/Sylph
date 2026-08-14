"""test_index28_fixes.py — 源仓库遗留问题修复 TDD（先红后绿）。

P1: carros_base.py --help 崩溃（__doc__ 为 None——docstring 被 future import 抢占首位）
P2: handoff task_desc 取到标题行占位（## Goal → "Goal"）
P3: final-report 决策段缺失字段渲染 '?' 占位（应为无记录/跳过）
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / ".claude" / "scripts"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "carros_base.py"), *args],
        capture_output=True, text=True, cwd=str(REPO), timeout=60)


def test_help_prints_usage_without_crash():
    """P1: --help/-h/help 不再崩溃且输出用法。"""
    for flag in ("--help", "-h", "help"):
        proc = _run(flag)
        assert proc.returncode == 0, f"{flag} 崩溃: {proc.stderr[-300:]}"
        assert "Usage" in proc.stdout or "init" in proc.stdout, f"{flag} 无用法输出"


def test_derive_task_desc_from_goal_content():
    """P2: 从 ## Goal 节取内容行，而非标题本身。"""
    sys.path.insert(0, str(SCRIPTS))
    from carros_base import _derive_task_desc
    with tempfile.TemporaryDirectory() as td:
        plan = Path(td) / "plan.md"
        plan.write_text("# Plan\n## Goal\n修复 --help 崩溃\n## Scope\n...\n", encoding="utf-8")
        assert _derive_task_desc({}, plan) == "修复 --help 崩溃"


def test_derive_task_desc_skips_bare_header():
    """P2: ## Goal 下无内容时返回空串（不取 'Goal' 标题）。"""
    sys.path.insert(0, str(SCRIPTS))
    from carros_base import _derive_task_desc
    with tempfile.TemporaryDirectory() as td:
        plan = Path(td) / "plan.md"
        plan.write_text("# Plan\n## Goal\n## Scope\nX\n", encoding="utf-8")
        assert _derive_task_desc({}, plan) == ""


def test_derive_task_desc_token_wins():
    """P2: token 自带描述优先于 plan。"""
    sys.path.insert(0, str(SCRIPTS))
    from carros_base import _derive_task_desc
    token = {"description": "令牌描述"}
    assert _derive_task_desc(token, None) == "令牌描述"


def test_report_no_question_mark_placeholders():
    """P3: 审计事件缺字段时报告不渲染 '?' 占位（跳过或标注无记录）。"""
    sys.path.insert(0, str(SCRIPTS))
    from carros_utils import generate_final_report
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        try:
            os.chdir(root)
            (root / ".omc" / "audit").mkdir(parents=True)
            (root / ".omc" / "audit" / "2026-08-15.jsonl").write_text(
                json.dumps({"event_type": "verify_decision"}) + "\n"
                + json.dumps({"event_type": "fallback_event"}) + "\n"
                + json.dumps({"event_type": "oracle_decision"}) + "\n",
                encoding="utf-8")
            task = root / "task"
            task.mkdir()
            (task / "executor.md").write_text("# Executor Evidence Ledger\n", encoding="utf-8")
            (task / "plan.md").write_text("# Plan\n## Goal\nX\n", encoding="utf-8")
            token = {"session": {"id": "t"}, "status": "archived",
                     "stats": {"done": 1, "total": 1}}
            report = generate_final_report(token, task)
        finally:
            os.chdir(old_cwd)
    bad = [l for l in report.splitlines()
           if "?" in l and ("决策" in l or "验证" in l or "Fallback" in l or "Oracle" in l)]
    assert not bad, f"报告仍含 '?' 占位: {bad}"
