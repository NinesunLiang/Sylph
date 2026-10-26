"""test_client_report_format.py — 客户版退出报告（report --format client）

背景：内部版 goal-report.md 含大量治理术语（EV 块、uncertified 代码、GateKeeper、
verdict status/confidence），适合 AI 与人自用，**不能直接交给客户**。

客户版合同（本测试钉死）：
1. 文件落盘，标题为「交付报告」，含项目/日期/结论
2. 含「需要你决定的事」表格
3. **不得**出现内部术语：EV- / uncertified / skipped_risks / GateKeeper /
   plan.step. / **status** / **confidence**
4. 状态用客户语言：建议验收 / 建议暂缓验收
5. 交付项用「状态 + 验证情况」呈现，不暴露内部 step 编号语义之外的东西
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "lx-goal.py"

# 禁止写字节码缓存：本测试用 importlib 从路径加载 lx-goal.py，
# 若不关会生成 __pycache__/*.pyc 污染源码树，进而被判「模板过期」。
sys.dont_write_bytecode = True


def _load_module():
    spec = importlib.util.spec_from_file_location("lx_goal_client_report", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


DATE = "20261027"
TASK = "client-report-task"


def _write_task_files(plan_dir: Path) -> None:
    plan_dir.mkdir(parents=True)
    (plan_dir / "research.md").write_text(
        "# Research\n\n## 背景\n- fixture\n", encoding="utf-8"
    )
    (plan_dir / "plan.md").write_text(
        "# Plan\n\n"
        "## Gate\n- level: L1\n\n"
        "## 依赖树\n- fixture\n\n"
        "## Phase 1\n"
        "- [x] S1: 企业官网首页改版\n"
        "  - status: completed\n"
        "  - acceptance: 页面在手机上好用\n"
        "  - verify: command:pytest\n",
        encoding="utf-8",
    )
    (plan_dir / "executor.md").write_text(
        "# Executor\n\n"
        "## TDD Evidence\n"
        "### EV-S1\n- step: S1\n- type: test\n- source: fixture\n"
        "- exit_code: 0\n- assertion: 首页在 375px 宽可用\n",
        encoding="utf-8",
    )


@pytest.fixture
def goal_ctx(tmp_path, monkeypatch):
    mod = _load_module()
    plan_dir = tmp_path / "tasks" / DATE / TASK
    _write_task_files(plan_dir)

    tokens = tmp_path / "tokens"
    token_path = tokens / DATE / f"{TASK}.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(
        json.dumps({
            "schema_version": "v1.0",
            "revision": 0,
            "mode": "goal",
            "session": {"id": TASK, "level": "L1"},
            "task_dir": str(plan_dir.resolve()),
            "status": "active",
            "goal": {"state": "EXECUTING", "description": "把企业官网首页改成响应式",
                     "activated_at": "2026-10-27T10:00:00+00:00",
                     "expires_at": "2026-10-27T16:00:00+00:00"},
            "hard_boundary_hits": [{
                "description": "修改生产数据库索引",
                "reason": "不可逆操作需人类执行",
                "human_action": "由你在维护窗口执行该 SQL",
            }],
            "blocked_human": [{
                "description": "首页主图用哪一张",
                "ai_recommendation": "用第二张（留白更适合移动端）",
                "rationale": "移动端首屏信息密度更低",
            }],
            "skipped_risks": [{
                "description": "历史页面 SEO 兼容改造",
                "risk_level": "high",
                "reason": "超出本次范围",
                "impact": "老页面收录暂不变",
            }],
            "retry_count": 0,
            "stats": {"done": 1, "total": 1},
            "task": {"current_step": None, "status": "executing"},
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr(mod, "TOKENS_DIR", tokens)
    monkeypatch.setattr(mod, "TASKS_DIR", tmp_path / "tasks")
    monkeypatch.setattr(mod, "PLANS_DIR", tmp_path / "tasks")
    monkeypatch.setattr(mod, "CURRENT_PLAN_DIR", plan_dir.resolve())

    # GateKeeper 摘要走子进程；测试里屏蔽，保证 hermetic 且不拖慢
    class _NoRun:
        stdout = ""

    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: _NoRun())

    return {"mod": mod, "plan_dir": plan_dir, "tmp_path": tmp_path}


def test_writes_client_report_file(goal_ctx):
    mod, plan_dir = goal_ctx["mod"], goal_ctx["plan_dir"]
    out = goal_ctx["tmp_path"] / "client.md"
    mod.cmd_report(format="client", out=str(out))
    assert out.is_file(), "客户版报告必须落盘"
    text = out.read_text(encoding="utf-8")
    assert "交付报告" in text
    assert "把企业官网首页改成响应式" in text


def test_client_language_no_internal_jargon(goal_ctx):
    mod, plan_dir = goal_ctx["mod"], goal_ctx["plan_dir"]
    out = goal_ctx["tmp_path"] / "client.md"
    mod.cmd_report(format="client", out=str(out))
    text = out.read_text(encoding="utf-8")
    for jargon in ("EV-S1", "uncertified", "skipped_risks", "GateKeeper",
                   "plan.step.", "**status**", "**confidence**"):
        assert jargon not in text, f"客户版不得出现内部术语: {jargon!r}"


def test_client_has_decision_table(goal_ctx):
    mod, plan_dir = goal_ctx["mod"], goal_ctx["plan_dir"]
    out = goal_ctx["tmp_path"] / "client.md"
    mod.cmd_report(format="client", out=str(out))
    text = out.read_text(encoding="utf-8")
    assert "需要你决定" in text
    # 三条真实决策都要进来：硬边界 / 待拍板 / 中高风险跳过
    assert "修改生产数据库索引" in text, "硬边界项要交给客户"
    assert "首页主图用哪一张" in text, "待拍板项要交给客户"
    assert "历史页面 SEO 兼容改造" in text, "中高风险跳过项要交给客户"


def test_client_status_is_plain_language(goal_ctx):
    mod, plan_dir = goal_ctx["mod"], goal_ctx["plan_dir"]
    out = goal_ctx["tmp_path"] / "client.md"
    mod.cmd_report(format="client", out=str(out))
    text = out.read_text(encoding="utf-8")
    assert ("建议验收" in text) or ("建议暂缓验收" in text)


def test_client_shows_human_readable_step_titles(goal_ctx):
    """交付项必须显示 plan.md 里的标题，不能只给 S1/S2 这种内部编号。"""
    mod, plan_dir = goal_ctx["mod"], goal_ctx["plan_dir"]
    out = goal_ctx["tmp_path"] / "client.md"
    mod.cmd_report(format="client", out=str(out))
    text = out.read_text(encoding="utf-8")
    assert "企业官网首页改版" in text, "交付项应显示人类可读标题"
    assert "| 1 | S1 |" not in text, "不得只显示内部 step 编号"


def test_internal_format_still_default(goal_ctx):
    """回归：不传 format 时仍生成内部版 goal-report.md（原行为不变）。"""
    mod, plan_dir = goal_ctx["mod"], goal_ctx["plan_dir"]
    mod.cmd_report()
    internal = plan_dir / "state" / "goal-report.md"
    assert internal.is_file(), "默认仍须生成内部版报告"
    assert "**status**" in internal.read_text(encoding="utf-8")
