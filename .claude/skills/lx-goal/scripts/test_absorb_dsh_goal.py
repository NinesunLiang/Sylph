"""test_absorb_dsh_goal.py — 吸收 DSH goal 可靠性机制的契约测试（TDD 红灯）

背景：lx-goal 运行于 Claude Code / OpenCode（无 DSH 平台工具）。
本文件定义「吸收 DSH goal 设计机制」后的行为契约 C1–C8。

当前 lx-goal.py v1.5.0 不满足任何一条 → 本文件预期全红。
实现阶段（方案获批后）让本文件转绿，且不破坏既有 test_goal_*.py。

契约（来源：@deepseek-ai/dsh-goal、dsh-tool-goal、dsh-goal-round-driver 设计）：
  C1 事件溯源   — 每次成功变更追加 goal.change 事件（revision 连续 + 完整后置快照）
  C2 命令层 CAS — 所有变更命令接受 expected_revision，陈旧值拒绝且不落盘
  C3 pause/resume — 一等状态：保留 phase，续跑 disarm/arm
  C4 round 预算 — rounds_started / max_goal_rounds，耗尽后阻止继续执行
  C5 blocked 连续轮次 — 同一条件连续 3 轮才正式 blocked；换条件重置计数
  C6 严格回放 — 事件流 revision 跳号/时间戳倒退 → 读侧检测为损坏
  C7 clear tombstone — 保留历史 + cleared 标记，不再视为活跃
  C8 续跑武装 — armed 标志；激活不自动跨会话继承，resume 需显式
"""

import importlib.util
import inspect
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
GOAL = ROOT / ".claude/skills/lx-goal/scripts/lx-goal.py"
spec = importlib.util.spec_from_file_location("lx_goal_absorb", GOAL)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

DATE = "20260817"
STATE = "EXECUTING"

# 契约 C2 要求全部变更命令都支持 expected_revision
MUTATION_CMDS = (
    "cmd_task_done",
    "cmd_skip_risk",
    "cmd_hard_boundary_hit",
    "cmd_blocked_human",
    "cmd_phase0_done",
    "cmd_plan_done",
    "cmd_done",
    "cmd_off",
)


def _scaffold(tmp_path):
    """Hermetic goal token（EXECUTING）+ 三件套文档，仿 e2e fixture。"""
    plan_dir = tmp_path / "tasks" / DATE / "absorb-task"
    plan_dir.mkdir(parents=True)
    docs = {
        "research.md": (
            "# Research\n\n## 背景\nb\n\n## 约束\nc\n\n## 已知信息\nk\n\n"
            "## 不确定性\nu\n\n## 全貌\nv\n\n## 依赖树\n- x\n\n"
            "## 方案\np\n\n## Dependency TDD\ncommand: pytest; exit_code: 0\n"
        ),
        "plan.md": (
            "# Plan\n\n## Gate\n- level: L2\n\n## Phase 1\n"
            "- [x] S1: done\n  - status: completed\n"
            "  - acceptance: ok\n  - verify: command:pytest\n"
        ),
        "executor.md": (
            "# Executor\n\n## Conditions\n- hermetic\n\n## Key Changes\n- fixture\n\n"
            "## Decisions\n- Rationale: fixture\n\n"
            "## Acceptance Checklist\n- [x] ok\n\n"
            "## TDD Evidence\n- command: pytest; exit_code: 0\n"
        ),
    }
    for name, body in docs.items():
        (plan_dir / name).write_text(body, encoding="utf-8")

    tokens = tmp_path / "tokens"
    token_path = tokens / DATE / "absorb-task.json"
    token_path.parent.mkdir(parents=True)
    token_path.write_text(json.dumps({
        "schema_version": "v1.0",
        "revision": 1,
        "mode": "goal",
        "session": {"id": "absorb-task", "level": "L2"},
        "task_dir": str(plan_dir.resolve()),
        "status": "active",
        "goal": {"state": STATE, "description": "absorb contract"},
        "stats": {"done": 1, "total": 1},
        "task": {"current_step": "S1", "status": "executing"},
    }), encoding="utf-8")

    return {"plan_dir": plan_dir, "token_path": token_path, "tokens": tokens}


def _bind(ctx, monkeypatch):
    monkeypatch.setattr(module, "CURRENT_PLAN_DIR", ctx["plan_dir"].resolve())


# ────────────────────────────────────────────────────────────
# C1 事件溯源：每次成功变更追加 goal.change 事件
# ────────────────────────────────────────────────────────────
def test_c1_event_log_appends_on_every_mutation(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)

    module.cmd_skip_risk("风险A", "low", "r", "i")
    module.cmd_skip_risk("风险B", "low", "r", "i")

    token = json.loads(ctx["token_path"].read_text(encoding="utf-8"))
    events = token.get("goal", {}).get("events", [])
    assert len(events) == 2, f"期望 2 条 goal.change 事件，实际 {len(events)}"
    revs = [ev["revision"] for ev in events]
    assert revs == list(range(revs[0], revs[0] + len(revs))), f"revision 必须连续: {revs}"
    for ev in events:
        assert "snapshot" in ev, "每条事件必须携带完整后置快照"
        assert ev["snapshot"].get("revision") == ev["revision"]


# ────────────────────────────────────────────────────────────
# C2 命令层 CAS：所有变更命令接受 expected_revision
# ────────────────────────────────────────────────────────────
def test_c2_mutation_commands_accept_expected_revision():
    for name in MUTATION_CMDS:
        fn = getattr(module, name)
        params = inspect.signature(fn).parameters
        assert "expected_revision" in params, f"{name} 缺少 expected_revision 参数"


def test_c2_stale_revision_is_rejected_without_write(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)
    before = json.loads(ctx["token_path"].read_text(encoding="utf-8"))

    with pytest.raises((SystemExit, module.CASConflict if hasattr(module, "CASConflict") else Exception)):
        module.cmd_skip_risk("风险A", "low", "r", "i", expected_revision=before["revision"] - 1)

    after = json.loads(ctx["token_path"].read_text(encoding="utf-8"))
    assert after == before, "陈旧 revision 被拒后 token 不得有任何变化"


# ────────────────────────────────────────────────────────────
# C3 pause/resume：一等状态，保留 phase，续跑 disarm/arm
# ────────────────────────────────────────────────────────────
def test_c3_pause_resume_commands_exist():
    for name in ("cmd_pause", "cmd_resume"):
        assert hasattr(module, name), f"缺少 {name}"


def test_c3_pause_preserves_phase_and_disarms(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)

    module.cmd_pause()
    token = json.loads(ctx["token_path"].read_text(encoding="utf-8"))
    goal = token["goal"]
    assert goal["state"] == STATE, "pause 不得改变 phase（严格向前状态机不受影响）"
    assert goal.get("paused") is True
    assert goal.get("armed") is False, "pause 必须 disarm 续跑"


def test_c3_resume_rearms(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)

    module.cmd_pause()
    module.cmd_resume()
    token = json.loads(ctx["token_path"].read_text(encoding="utf-8"))
    goal = token["goal"]
    assert goal.get("paused") is False
    assert goal.get("armed") is True, "resume 必须重新 arm 续跑"


# ────────────────────────────────────────────────────────────
# C4 round 预算：rounds_started / max_goal_rounds，耗尽阻止继续
# ────────────────────────────────────────────────────────────
def test_c4_round_start_command_exists_and_increments(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)
    assert hasattr(module, "cmd_round_start"), "缺少 cmd_round_start"

    module.cmd_round_start()
    token = json.loads(ctx["token_path"].read_text(encoding="utf-8"))
    goal = token["goal"]
    assert goal.get("rounds_started", 0) == 1


def test_c4_round_budget_exhausted_blocks_continuation(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)
    token = json.loads(ctx["token_path"].read_text(encoding="utf-8"))
    token["goal"]["rounds_started"] = token["goal"].get("max_goal_rounds", 6)
    ctx["token_path"].write_text(json.dumps(token), encoding="utf-8")

    rc = module.cmd_round_start()
    assert rc != 0, "round 预算耗尽后必须阻止继续执行（返回非 0）"


# ────────────────────────────────────────────────────────────
# C5 blocked 连续轮次：同一条件连续 3 轮才正式 blocked；换条件重置
# ────────────────────────────────────────────────────────────
def test_c5_first_blocked_call_is_only_candidate(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)

    module.cmd_blocked_human("决策A", "推荐B", "依据C")
    token = json.loads(ctx["token_path"].read_text(encoding="utf-8"))
    goal = token["goal"]
    assert goal.get("blocked") is not True, "第一轮不得直接正式 blocked"
    assert "blocked_candidate" in goal, "第一轮必须记录 blocked_candidate（含 round + 条件指纹）"
    assert goal["blocked_candidate"]["round"] >= 1


def test_c5_same_condition_three_rounds_becomes_blocked(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)

    for _ in range(3):
        module.cmd_blocked_human("决策A", "推荐B", "依据C")

    token = json.loads(ctx["token_path"].read_text(encoding="utf-8"))
    assert token["goal"].get("blocked") is True, "同一条件连续 3 轮后必须正式 blocked"


def test_c5_changed_condition_resets_candidate(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)

    module.cmd_blocked_human("决策A", "推荐B", "依据C")
    module.cmd_blocked_human("决策A", "推荐B", "依据C")
    module.cmd_blocked_human("决策X", "推荐Y", "依据Z")  # 换条件 → 重置

    token = json.loads(ctx["token_path"].read_text(encoding="utf-8"))
    goal = token["goal"]
    assert goal.get("blocked") is not True, "换条件后不得继承之前的连续轮次"
    assert goal["blocked_candidate"]["round"] == 1


# ────────────────────────────────────────────────────────────
# C6 严格回放：事件流损坏 → 读侧检测
# ────────────────────────────────────────────────────────────
def test_c6_replay_detects_discontinuous_revision(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)
    assert hasattr(module, "_validate_goal_events"), "缺少 _validate_goal_events"

    token = json.loads(ctx["token_path"].read_text(encoding="utf-8"))
    token["goal"]["events"] = [
        {"revision": 1, "action": "skip", "snapshot": {"revision": 1}},
        {"revision": 3, "action": "skip", "snapshot": {"revision": 3}},  # 跳号
    ]
    ctx["token_path"].write_text(json.dumps(token), encoding="utf-8")

    errors = module._validate_goal_events(json.loads(ctx["token_path"].read_text(encoding="utf-8")))
    assert errors, "revision 跳号必须被检测为损坏"


def test_c6_replay_detects_timestamp_regression(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)

    token = json.loads(ctx["token_path"].read_text(encoding="utf-8"))
    token["goal"]["events"] = [
        {"revision": 1, "action": "skip", "at": "2026-08-17T10:00:00+00:00", "snapshot": {"revision": 1}},
        {"revision": 2, "action": "skip", "at": "2026-08-17T09:00:00+00:00", "snapshot": {"revision": 2}},  # 倒退
    ]
    ctx["token_path"].write_text(json.dumps(token), encoding="utf-8")

    errors = module._validate_goal_events(json.loads(ctx["token_path"].read_text(encoding="utf-8")))
    assert errors, "时间戳倒退必须被检测为损坏"


# ────────────────────────────────────────────────────────────
# C7 clear tombstone：保留历史 + cleared 标记，不再视为活跃
# ────────────────────────────────────────────────────────────
def test_c7_clear_command_exists_and_keeps_tombstone(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)
    assert hasattr(module, "cmd_clear"), "缺少 cmd_clear"

    module.cmd_clear()
    token = json.loads(ctx["token_path"].read_text(encoding="utf-8"))
    assert token.get("goal", {}).get("cleared") is True, "clear 必须写 tombstone 标记"
    assert not ctx["token_path"].with_name(ctx["token_path"].name + ".lock").exists(), "clear 必须删除 sidecar 锁"


def test_c7_cleared_goal_is_not_active(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)
    monkeypatch.setattr(module, "TOKENS_DIR", ctx["tokens"])

    module.cmd_clear()
    active = module._find_active_goal("absorb-task", tokens_root=ctx["tokens"])
    assert active is None, "cleared 的 goal 不得再被视为活跃"


# ────────────────────────────────────────────────────────────
# C8 续跑武装：armed 标志，resume 显式
# ────────────────────────────────────────────────────────────
def test_c8_resume_sets_armed_explicitly(tmp_path, monkeypatch):
    ctx = _scaffold(tmp_path)
    _bind(ctx, monkeypatch)

    module.cmd_resume()
    token = json.loads(ctx["token_path"].read_text(encoding="utf-8"))
    assert token["goal"].get("armed") is True, "resume 必须显式武装续跑"


# ────────────────────────────────────────────────────────────
# 回归锚点：现有命令保持完好（本契约不应破坏原 API）
# ────────────────────────────────────────────────────────────
def test_existing_commands_remain_intact():
    for name in (
        "cmd_on", "cmd_off", "cmd_status", "cmd_task_done", "cmd_report",
        "cmd_poll", "cmd_blocked_human", "cmd_done", "cmd_phase0_done",
        "cmd_plan_done", "cmd_skip_risk", "cmd_hard_boundary_hit",
        "cmd_subagent_log", "cmd_checklist_verify",
    ):
        assert hasattr(module, name), f"现有命令 {name} 不得在吸收中被移除"
