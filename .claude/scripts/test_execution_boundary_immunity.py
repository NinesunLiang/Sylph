import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


LX_GOAL = load_module(
    ROOT / ".claude/skills/lx-goal/scripts/lx-goal.py", "lx_goal_boundary"
)
STEP_CONTRACTS = load_module(
    ROOT / ".claude/scripts/step_contracts.py", "step_contracts_boundary"
)
VERIFY_GATE = load_module(
    ROOT / ".claude/scripts/verify_gate.py", "verify_gate_boundary"
)
OMC_LINT = load_module(ROOT / ".claude/scripts/omc_lint.py", "omc_lint_boundary")
sys.path.insert(0, str(ROOT / ".claude/hooks"))
from pretool_gates import checks as PRETOOL_CHECKS


def test_on_parser_accepts_task_id_and_legacy_expiry():
    assert LX_GOAL.parse_on_args(["goal text", "3"]) == ("goal text", 3, None)
    assert LX_GOAL.parse_on_args(["goal text", "--task-id", "task-1"]) == (
        "goal text",
        6,
        "task-1",
    )


def test_on_parser_rejects_unknown_flags_without_state_side_effects():
    with pytest.raises(ValueError, match="unknown option"):
        LX_GOAL.parse_on_args(["goal text", "--bad"])
    with pytest.raises(ValueError, match="expiry"):
        LX_GOAL.parse_on_args(["goal text", "--expiry", "0"])


def test_main_on_routes_task_id_without_traceback(monkeypatch):
    calls = []
    monkeypatch.setattr(LX_GOAL, "cmd_on", lambda *args: calls.append(args))
    monkeypatch.setattr(sys, "argv", ["lx-goal.py", "on", "goal text", "--task-id", "task-1"])
    LX_GOAL.main()
    assert calls == [("goal text", 6, "task-1")]


def test_content_gate_keeps_boundary_and_redirects_over_budget():
    allowed = PRETOOL_CHECKS._check_injection(
        {"tool": "Write", "tool_input": {"content": "x" * 8000}}
    )
    redirected = PRETOOL_CHECKS._check_injection(
        {"tool": "Write", "tool_input": {"content": "x" * 8001}}
    )
    edited = PRETOOL_CHECKS._check_injection(
        {"tool": "Edit", "tool_input": {"new_string": "x" * 8001}}
    )
    assert allowed is None
    assert redirected and "content_truncated" in redirected
    assert edited and "content_truncated" in edited


def test_utf8_chunk_writer_preserves_content_and_budget(tmp_path):
    from content_writer import split_utf8_chunks, write_chunked

    content = "治理" * 5000
    chunks = split_utf8_chunks(content, max_bytes=6000)
    assert "".join(chunks) == content
    assert all(len(chunk.encode("utf-8")) <= 6000 for chunk in chunks)
    target = tmp_path / "report.md"
    write_chunked(target, content, max_bytes=6000)
    assert target.read_text(encoding="utf-8") == content


def test_start_step_replaces_pending_status_atomically(tmp_path):
    plan = tmp_path / "plan.md"
    executor = tmp_path / "executor.md"
    token = tmp_path / "token.json"
    plan.write_text("- [ ] S1: start\n  - status: pending\n", encoding="utf-8")
    executor.write_text("## Conditions\n\n", encoding="utf-8")
    token.write_text(json.dumps({"task": {}, "revision": 0}), encoding="utf-8")
    STEP_CONTRACTS.start_step_atomic(token, plan, executor, "S1")
    updated = plan.read_text(encoding="utf-8")
    assert updated.count("status: active") == 1
    assert "status: pending" not in updated


def test_completed_step_completion_is_idempotent(tmp_path):
    plan = tmp_path / "plan.md"
    executor = tmp_path / "executor.md"
    token = tmp_path / "token.json"
    plan.write_text(
        "- [x] S1: done\n  - status: completed\n  - verify: assertion:done\n",
        encoding="utf-8",
    )
    executor.write_text(
        """## Conditions
ok
## Key Changes
ok
## Decisions
- Rationale: test
## Acceptance Checklist
- [x] done
## TDD Evidence
- Dependency TDD command: exit 0
- Regression TDD command: exit 0
### EV-S1
- step: S1
- type: test
- source: test
- evidence_level: E3
- exit_code: 0
- file: test
- assertion: done
""",
        encoding="utf-8",
    )
    token.write_text(json.dumps({"stats": {"done": 1, "total": 1}}), encoding="utf-8")
    STEP_CONTRACTS.complete_step_atomic(token, plan, executor, "S1")
    assert "status: completed" in plan.read_text(encoding="utf-8")
    assert json.loads(token.read_text(encoding="utf-8"))["stats"]["done"] == 1


def test_completion_reconciles_token_total_with_plan_steps(tmp_path):
    plan = tmp_path / "plan.md"
    executor = tmp_path / "executor.md"
    token = tmp_path / "token.json"
    plan.write_text(
        """- [a] S1: first
  - status: active
  - depends_on: none
  - scope: local
  - acceptance: first evidence
  - verify: assertion:first
- [ ] S2: second
  - status: pending
  - depends_on: S1
  - scope: local
  - acceptance: second evidence
  - verify: assertion:second
- [ ] S3: third
  - status: pending
  - depends_on: S2
  - scope: local
  - acceptance: third evidence
  - verify: assertion:third
""",
        encoding="utf-8",
    )
    executor.write_text(
        """## Conditions
- local
## Key Changes
- local
## Decisions
- Rationale: test
## Acceptance Checklist
- [x] S1 evidence
## TDD Evidence
- Dependency TDD command: test -> exit 0
- Regression TDD command: test -> exit 0
### EV-S1
- step: S1
- type: test
- source: test
- evidence_level: E3
- exit_code: 0
- file: test
- assertion: first evidence
""",
        encoding="utf-8",
    )
    token.write_text(json.dumps({"task": {"status": "active"}, "stats": {"done": 0, "total": 1}}), encoding="utf-8")

    STEP_CONTRACTS.complete_step_atomic(token, plan, executor, "S1")

    updated = json.loads(token.read_text(encoding="utf-8"))
    assert updated["stats"] == {"done": 1, "total": 3}
    assert updated["task"]["status"] == "active"


def test_verify_rules_do_not_fallback_to_another_step():
    plan = """- [a] S1: first
  - verify:
- [ ] S2: second
  - verify: assertion:only-s2
"""
    assert VERIFY_GATE.parse_verify_rules(plan, "S1") == []


def test_default_templates_are_contract_shaped(tmp_path, monkeypatch):
    carros = load_module(ROOT / ".claude/scripts/carros_base.py", "carros_templates")
    monkeypatch.setattr(carros, "PLAN_PATH", tmp_path / "plan.md")
    monkeypatch.setattr(carros, "EXECUTOR_PATH", tmp_path / "executor.md")
    carros._write_default_plan(["S1"])
    carros._write_default_executor()
    plan = (tmp_path / "plan.md").read_text(encoding="utf-8")
    executor = (tmp_path / "executor.md").read_text(encoding="utf-8")
    assert "- verify: assertion: step S1 evidence is recorded" in plan
    assert "- Rationale:" in executor
    assert "Dependency TDD command:" in executor
    assert "Regression TDD command:" in executor
    sys.modules.pop("carros_templates", None)


def test_default_token_starts_in_planning_state():
    carros = load_module(ROOT / ".claude/scripts/carros_base.py", "carros_planning")
    token = carros._default_token("task", steps=["S1"])
    assert token["task"]["current_step"] is None
    assert token["task"]["status"] == "planning"
    sys.modules.pop("carros_planning", None)


def test_cmd_tick_is_idempotent_for_completed_step(tmp_path, monkeypatch):
    carros = load_module(ROOT / ".claude/scripts/carros_base.py", "carros_tick_idempotent")
    plan = tmp_path / "plan.md"
    executor = tmp_path / "executor.md"
    token = tmp_path / "token.json"
    plan.write_text("- [x] S1: done\n  - status: completed\n", encoding="utf-8")
    executor.write_text("", encoding="utf-8")
    token.write_text(json.dumps({"status": "active", "task": {"status": "completed"}}), encoding="utf-8")
    monkeypatch.setattr(carros, "TOKEN_PATH", token)
    monkeypatch.setattr(carros, "PLAN_PATH", plan)
    monkeypatch.setattr(carros, "EXECUTOR_PATH", executor)
    assert carros.cmd_tick("S1") == 0
    sys.modules.pop("carros_tick_idempotent", None)


def test_cmd_verify_is_idempotent_for_completed_step(tmp_path, monkeypatch):
    carros = load_module(ROOT / ".claude/scripts/carros_base.py", "carros_verify_idempotent")
    plan = tmp_path / "plan.md"
    executor = tmp_path / "executor.md"
    token = tmp_path / "token.json"
    plan.write_text("- [x] S1: done\n  - status: completed\n", encoding="utf-8")
    executor.write_text("", encoding="utf-8")
    token.write_text(json.dumps({"status": "active", "task": {"status": "completed"}}), encoding="utf-8")
    monkeypatch.setattr(carros, "TOKEN_PATH", token)
    monkeypatch.setattr(carros, "TASK_DIR", tmp_path)
    monkeypatch.setattr(carros, "PLAN_PATH", plan)
    monkeypatch.setattr(carros, "EXECUTOR_PATH", executor)
    monkeypatch.setattr(carros, "HANDOFF_PATH", tmp_path / "handoff.md")
    assert carros.cmd_verify("S1") == 0
    sys.modules.pop("carros_verify_idempotent", None)


def test_plan_scope_sync_populates_hook_scope(tmp_path, monkeypatch):
    carros = load_module(ROOT / ".claude/scripts/carros_base.py", "carros_scope_sync")
    plan = tmp_path / "plan.md"
    token_path = tmp_path / "token.json"
    plan.write_text("## Scope\n- .claude/scripts/carros_base.py\n- tests/\n\n## Phase 1\n", encoding="utf-8")
    token_path.write_text(json.dumps({"task": {"scope": []}}), encoding="utf-8")
    monkeypatch.setattr(carros, "PLAN_PATH", plan)
    monkeypatch.setattr(carros, "TOKEN_PATH", token_path)
    token = json.loads(token_path.read_text(encoding="utf-8"))
    updated = carros._sync_token_scope_from_plan(token)
    assert updated["scope"] == [".claude/scripts/carros_base.py", "tests/"]
    assert json.loads(token_path.read_text(encoding="utf-8"))["scope"] == updated["scope"]
    sys.modules.pop("carros_scope_sync", None)


def test_lint_counts_active_plan_steps(tmp_path, capsys):
    task_dir = tmp_path / ".omc/tasks/20260811/task"
    task_dir.mkdir(parents=True)
    token_dir = tmp_path / ".omc/tokens/20260811"
    token_dir.mkdir(parents=True)
    (token_dir / "task.json").write_text(
        json.dumps({
            "status": "active",
            "session": {"id": "task"},
            "stats": {"done": 0, "total": 2},
        }),
        encoding="utf-8",
    )
    (task_dir / "plan.md").write_text(
        "- [a] S1: active\n- [ ] S2: pending\n",
        encoding="utf-8",
    )
    result = OMC_LINT.run_lint(tmp_path)
    captured = capsys.readouterr().out
    assert "S1" in captured
    assert "Mismatch: token total=2, plan total=1" not in captured
    assert "Consistent: done=0, total=2" in captured
    assert result["exit_code"] == 1


def test_missing_task_dir_does_not_bypass_explicit_context(tmp_path, monkeypatch):
    carros = load_module(ROOT / ".claude/scripts/carros_base.py", "carros_boundary")
    tokens = tmp_path / "tokens"
    day = tokens / "20260811"
    day.mkdir(parents=True)
    token_path = day / "task.json"
    token_path.write_text(
        json.dumps({"status": "active", "session": {"id": "task"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(carros, "OMC_TOKENS", tokens)
    monkeypatch.setenv("CARROROS_TASK_ID", "task")
    monkeypatch.setenv("CARROROS_TASK_DIR", str(tmp_path / "other"))
    monkeypatch.delenv("CARROROS_TOKEN_PATH", raising=False)
    assert carros._find_latest_token() == (None, None)
    sys.modules.pop("carros_boundary", None)


def test_goal_step_contract_rejects_direct_start_before_execution(tmp_path):
    plan = tmp_path / "plan.md"
    executor = tmp_path / "executor.md"
    token = tmp_path / "token.json"
    plan.write_text(
        "- [ ] S1: start\n"
        "  - status: pending\n"
        "  - depends_on: none\n",
        encoding="utf-8",
    )
    executor.write_text("# Executor\n", encoding="utf-8")
    token.write_text(
        json.dumps({
            "mode": "goal",
            "goal": {"state": "PLANNING"},
            "task": {},
            "revision": 0,
        }),
        encoding="utf-8",
    )
    before = {p: p.read_bytes() for p in (plan, executor, token)}

    with pytest.raises(ValueError, match="Goal state=PLANNING"):
        STEP_CONTRACTS.start_step_atomic(token, plan, executor, "S1")

    assert {p: p.read_bytes() for p in (plan, executor, token)} == before


def test_carros_init_help_does_not_create_unnamed_task(monkeypatch):
    carros = load_module(ROOT / ".claude/scripts/carros_base.py", "carros_init_help")
    help_calls = []
    init_calls = []
    monkeypatch.setattr(carros, "cmd_help", lambda: help_calls.append(True) or 0)
    monkeypatch.setattr(carros, "cmd_init", lambda **kwargs: init_calls.append(kwargs) or 2)

    assert carros.main(["init", "--help"]) == 0
    assert help_calls == [True]
    assert init_calls == []
    sys.modules.pop("carros_init_help", None)


def test_complete_step_atomic_writes_verifygate_marker(tmp_path):
    """complete_step_atomic must append a durable EV-S1-VERIFIED marker so a
    red-TDD step's report gate can confirm canonical VerifyGate acceptance."""
    plan = tmp_path / "plan.md"
    executor = tmp_path / "executor.md"
    token = tmp_path / "token.json"
    plan.write_text(
        """- [a] S1: first
  - status: active
  - depends_on: none
  - scope: local
  - acceptance: red test
  - verify: assertion:red test failed as expected
""",
        encoding="utf-8",
    )
    executor.write_text(
        """## Conditions
- local
## Key Changes
- local
## Decisions
- Rationale: test
## Acceptance Checklist
- [x] S1 evidence
## TDD Evidence
- Dependency TDD command: test -> exit 0
- Regression TDD command: test -> exit 0
### EV-S1
- step: S1
- type: test
- source: test
- evidence_level: E3
- exit_code: 1
- file: test
- assertion: red test failed as expected
""",
        encoding="utf-8",
    )
    token.write_text(json.dumps({"task": {"status": "active"}, "stats": {"done": 0, "total": 1}}), encoding="utf-8")

    STEP_CONTRACTS.complete_step_atomic(token, plan, executor, "S1")

    executor_text = executor.read_text(encoding="utf-8")
    assert "### EV-S1-VERIFIED" in executor_text
    assert "- exit_code: 0" in executor_text.split("### EV-S1-VERIFIED")[1]


def test_complete_step_atomic_marker_is_idempotent(tmp_path):
    """Re-running complete_step_atomic must not duplicate the VERIFIED marker."""
    plan = tmp_path / "plan.md"
    executor = tmp_path / "executor.md"
    token = tmp_path / "token.json"
    plan.write_text(
        """- [x] S1: first
  - status: completed
  - depends_on: none
  - scope: local
  - acceptance: red test
  - verify: assertion:red test failed as expected
""",
        encoding="utf-8",
    )
    executor.write_text(
        "### EV-S1\n\n- step: S1\n- exit_code: 1\n- assertion: red\n\n"
        "### EV-S1-VERIFIED\n\n- step: S1\n- exit_code: 0\n- source: VerifyGate\n",
        encoding="utf-8",
    )
    token.write_text(json.dumps({"task": {"status": "completed"}, "stats": {"done": 1, "total": 1}}), encoding="utf-8")

    STEP_CONTRACTS.complete_step_atomic(token, plan, executor, "S1")

    assert executor.read_text(encoding="utf-8").count("### EV-S1-VERIFIED") == 1


def test_extract_section_content_ignores_backticked_section_mention():
    """A `## Decisions` mention inside prose must not be treated as the section
    header; only a real heading on its own line starts the section (E-ISO-001)."""
    text = (
        "## Key Changes\n"
        "- 引用段名 `## Decisions` 不应误判\n"
        "## Decisions\n"
        "- 决策: 任务隔离\n"
        "- rationale: 测试\n"
        "## Acceptance Checklist\n"
        "- [x] done\n"
    )
    sec = STEP_CONTRACTS._extract_section_content(text, "Decisions")
    assert "决策: 任务隔离" in sec
    assert "rationale: 测试" in sec
    assert "引用段名" not in sec
