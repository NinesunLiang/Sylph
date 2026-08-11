import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
GOAL = ROOT / ".claude/skills/lx-goal/scripts/lx-goal.py"
CONTRACTS = ROOT / ".claude/scripts/goal_contracts.py"
spec = importlib.util.spec_from_file_location("lx_goal_under_test", GOAL)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
contract_spec = importlib.util.spec_from_file_location("goal_contracts_under_test", CONTRACTS)
assert contract_spec is not None
contracts = importlib.util.module_from_spec(contract_spec)
assert contract_spec.loader is not None
contract_spec.loader.exec_module(contracts)


def test_goal_step_verification_binds_token_context():
    text = GOAL.read_text(encoding="utf-8")
    assert 'env["CARROROS_TOKEN_PATH"]' in text
    assert 'env["CARROROS_TASK_ID"]' in text
    assert 'env["CARROROS_TASK_DIR"]' in text


def test_goal_context_fixture_is_hermetic(monkeypatch, tmp_path):
    plan_dir = tmp_path / "20260811" / "task"
    plan_dir.mkdir(parents=True)
    tokens = tmp_path / "tokens" / "20260811"
    tokens.mkdir(parents=True)
    token_path = tokens / "task.json"
    token_path.write_text(
        '{"session": {"id": "task"}, "task_dir": "' + str(plan_dir) + '"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")

    resolved, env = module._goal_context(plan_dir)

    assert resolved == token_path
    assert env["CARROROS_TASK_ID"] == "task"
    assert env["CARROROS_TASK_DIR"] == str(plan_dir.resolve())


def test_goal_context_missing_token_is_explicit(monkeypatch, tmp_path):
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    monkeypatch.setattr(module, "TOKENS_DIR", tmp_path / "tokens")

    try:
        module._goal_context(plan_dir)
    except RuntimeError as exc:
        assert "goal token missing" in str(exc)
    else:
        raise AssertionError("missing goal token must fail closed")


def test_placeholder_contract_rejects_template_values():
    for value in ("TODO", "TBD", "待填写", "<pending-user-confirmation>", "..."):
        assert contracts.is_placeholder(value)


def test_plan_builder_emits_acceptance_fields():
    plan = ROOT / ".omc/tasks/20260811/CarrorOS--AI--C1-C9E1-E8-UX/plan.md"
    text = plan.read_text(encoding="utf-8")
    assert "acceptance:" in text
    assert "scope:" in text
    assert "verify:" in text


def test_research_dependency_tree_requires_bullet():
    research = ROOT / ".omc/tasks/20260811/CarrorOS--AI--C1-C9E1-E8-UX/research.md"
    text = research.read_text(encoding="utf-8")
    section = text.split("## 依赖树", 1)[1].split("## 方案", 1)[0]
    assert any(line.startswith("-") for line in section.splitlines())


def test_report_missing_plan_dir_is_blocked(monkeypatch, tmp_path):
    state_dir = tmp_path / "state"
    monkeypatch.setattr(module, "STATE_DIR", state_dir)
    monkeypatch.setattr(module, "_read_mode_file", lambda: ({"goal": "broken"}, "mode.json"))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: None)

    module.cmd_report()

    report = (state_dir / "goal-report.md").read_text(encoding="utf-8")
    assert "BLOCKED" in report
    assert "goal.plan_dir.missing" in report
    assert "VERIFIED: 所有计划步骤已完成" not in report


def test_task_done_accepts_already_verified_plan(monkeypatch, tmp_path):
    plan_dir = tmp_path / "task"
    plan_dir.mkdir()
    (plan_dir / "plan.md").write_text("- [x] S1: done\n", encoding="utf-8")
    mode_data = {"completed_tasks": [], "rpe_plan_dir": str(plan_dir)}
    writes = []

    monkeypatch.setattr(module, "_read_mode_file", lambda: (mode_data, "mode.json"))
    monkeypatch.setattr(module, "_get_plan_dir", lambda data: plan_dir)
    monkeypatch.setattr(module, "_resolve_current_step", lambda path: None)
    monkeypatch.setattr(module, "_write_mode_file", lambda data, path: writes.append(data.copy()))
    monkeypatch.setattr(module, "_ledger_append_block", lambda *args: None)
    monkeypatch.setattr(module, "_update_lock_counter", lambda *args: None)

    assert module.cmd_task_done("already verified") == 0
    assert writes[-1]["completed_tasks"][0]["description"] == "already verified"
