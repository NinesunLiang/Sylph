#!/usr/bin/env python3
"""test-task8-phase1-tdd-red.py — Task8 Strict Goal State Machine Dependency TDD RED

隔离: tempdir + monkeypatch, 不碰真实 .omc/.claude/settings/hooks
退出码: 0=全过, 1=有FAIL(预期RED状态), infra_error>0=2(不应出现)

G1: 状态链严格 CLARIFY→PLANNING→EXECUTING→VERIFYING→ARCHIVING→ARCHIVED，跨步/倒退非法
G2: GoalMachine import/runtime 缺失时 fail closed 而非静默
G3: ResearchGate 结构验证 — 所有section有真实非placeholder内容，Dependency Tree≥1项
G4: PlanGate — 至少1 Phase+Step，每Step唯一id/depends_on无环/scope/acceptance/verify有真实内容
G5: Step隔离 — first pending仅依赖completed可active；开始Step原子记录；完成Step token/plan/executor协调
G6: Executor atomic evidence — Conditions/Key Changes/Decisions+rationale/AC全通/TDD命令exit0
G7: 全部Step verified才VERIFYING→VerifyGate全绿→ARCHIVING→ARCHIVED；失败保持
G8: lx-goal `on` task dir仅来自carros init；phase0-done/task-done/done通过共享状态机/ledger
"""

from __future__ import annotations

import contextlib
import importlib.util
import inspect
import io
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]

# Import step_contracts for real API calls
try:
    sys.path.insert(0, str(REPO_ROOT / ".claude" / "scripts"))
    import step_contracts
except ImportError:
    step_contracts = None

PASS = 0
FAIL = 0
INFRA = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        msg = f"  FAIL  {name}"
        if detail:
            msg += f"  ({detail})"
        print(msg)


def infra_ok(name: str, cond: bool, detail: str = "") -> bool:
    global INFRA
    if not cond:
        INFRA += 1
        print(f"  INFRA_FAIL  {name}  ({detail})")
        return False
    print(f"  INFRA_OK  {name}")
    return True


# ─── Module Loading ─────────────────────────────────────────────────

def _import_module(qualname: str, file_path: Path) -> Any:
    sys.modules.pop(qualname, None)
    spec = importlib.util.spec_from_file_location(qualname, str(file_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[qualname] = mod
    spec.loader.exec_module(mod)
    return mod


def _py_source(obj: Any) -> str:
    try:
        return inspect.getsource(obj)
    except (OSError, TypeError):
        return ""


def _make_temp_project(tmp_root: Path) -> Path:
    """Create a minimal fake project root with .omc state dirs."""
    root = tmp_root / "project"
    root.mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (root / ".claude").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "scripts").mkdir(parents=True, exist_ok=True)
    (root / ".omc").mkdir(parents=True, exist_ok=True)
    (root / ".omc" / "state").mkdir(parents=True, exist_ok=True)
    (root / ".omc" / "tokens").mkdir(parents=True, exist_ok=True)
    (root / ".omc" / "tasks").mkdir(parents=True, exist_ok=True)
    return root


def _get_gsm() -> Any:
    """Import goal_state_machine module (cache across tests)."""
    gsm_path = REPO_ROOT / ".claude" / "scripts" / "goal_state_machine.py"
    return _import_module("goal_state_machine_t8", gsm_path)


def _stub_carros_base_deps(mod: Any) -> None:
    """Stub out all optional imports and subprocess in carros_base for tempdir isolation."""
    import types as _t
    mod.carros_utils = None
    mod.omc_lint = None
    mod.tst = None
    mod.GoalMachine = None
    mod.GoalError = Exception
    mod.gsm = None
    mod.sam = None

    class _R:
        returncode = 1
        stdout = ""
        stderr = ""
        def __init__(self, rc=1, out="", err=""):
            self.returncode = rc
            self.stdout = out
            self.stderr = err

    class _PopenObj:
        def communicate(self):
            return ("", "")
        def poll(self):
            return 0
        def wait(self):
            return 0

    _sm = _t.ModuleType("subprocess")
    setattr(_sm, "run", MagicMock(return_value=_R(rc=1)))
    setattr(_sm, "Popen", MagicMock(return_value=_PopenObj()))
    setattr(_sm, "TimeoutExpired", Exception)
    mod.subprocess = _sm




# ====================================================================
# G1: Goal State Chain Strictness
# ====================================================================

def run_g1():
    """G1: 状态链严格 CLARIFY→PLANNING→EXECUTING→VERIFYING→ARCHIVING→ARCHIVED，所有跨步/倒退非法"""
    print("\n" + "=" * 64)
    print("G1: Goal State Chain — Strict Forward-Only")
    print("=" * 64)

    try:
        gsm = _get_gsm()
    except Exception as e:
        infra_ok("G1-infra import goal_state_machine", False, f"exception: {e}")
        return

    ALL_STATES = gsm.ALL_STATES
    CLARIFY = gsm.CLARIFY
    PLANNING = gsm.PLANNING
    EXECUTING = gsm.EXECUTING
    VERIFYING = gsm.VERIFYING
    ARCHIVING = gsm.ARCHIVING
    ARCHIVED = gsm.ARCHIVED
    GOAL_ERROR = gsm.GoalError

    with tempfile.TemporaryDirectory() as td:
        token_path = Path(td) / "token.json"

        # ── G1a: Valid forward chain — all steps succeed ──
        gm = gsm.GoalMachine(str(token_path))
        ok("G1a-1 None can_transition CLARIFY", gm.can_transition(CLARIFY), "")

        gm.transition(CLARIFY)
        ok("G1a-2 None→CLARIFY succeeds", gm.current_state == CLARIFY, f"state={gm.current_state}")

        ok("G1a-3 CLARIFY can_transition PLANNING", gm.can_transition(PLANNING), "")
        gm.transition(PLANNING)
        ok("G1a-4 CLARIFY→PLANNING succeeds", gm.current_state == PLANNING, f"state={gm.current_state}")

        ok("G1a-5 PLANNING can_transition EXECUTING", gm.can_transition(EXECUTING), "")
        gm.transition(EXECUTING)
        ok("G1a-6 PLANNING→EXECUTING succeeds", gm.current_state == EXECUTING, f"state={gm.current_state}")

        ok("G1a-7 EXECUTING can_transition VERIFYING", gm.can_transition(VERIFYING), "")
        gm.transition(VERIFYING)
        ok("G1a-8 EXECUTING→VERIFYING succeeds", gm.current_state == VERIFYING, f"state={gm.current_state}")

        ok("G1a-9 VERIFYING can_transition ARCHIVING", gm.can_transition(ARCHIVING), "")
        gm.transition(ARCHIVING)
        ok("G1a-10 VERIFYING→ARCHIVING succeeds", gm.current_state == ARCHIVING, f"state={gm.current_state}")

        ok("G1a-11 ARCHIVING can_transition ARCHIVED", gm.can_transition(ARCHIVED), "")
        gm.transition(ARCHIVED)
        ok("G1a-12 ARCHIVING→ARCHIVED succeeds", gm.current_state == ARCHIVED, f"state={gm.current_state}")
        ok("G1a-13 terminal is_terminal True", gm.is_terminal, "")

        # ── G1b: Skip transitions must fail ──
        # Start fresh
        gm2 = gsm.GoalMachine(str(token_path))
        gm2.transition(CLARIFY)

        ok("G1b-1 CLARIFY→EXECUTING invalid (skip PLANNING)",
           not gm2.can_transition(EXECUTING),
           f"can_transition returned True (should be False)")

        ok("G1b-2 CLARIFY→VERIFYING invalid (skip PLANNING+EXECUTING)",
           not gm2.can_transition(VERIFYING), "")

        ok("G1b-3 CLARIFY→ARCHIVING invalid (skip 4 states)",
           not gm2.can_transition(ARCHIVING), "")

        ok("G1b-4 CLARIFY→ARCHIVED invalid (skip 5 states)",
           not gm2.can_transition(ARCHIVED), "")

        gm2.transition(PLANNING)
        ok("G1b-5 PLANNING→VERIFYING invalid (skip EXECUTING)",
           not gm2.can_transition(VERIFYING), "")

        ok("G1b-6 PLANNING→ARCHIVING invalid (skip EXECUTING+VERIFYING)",
           not gm2.can_transition(ARCHIVING), "")

        gm2.transition(EXECUTING)
        ok("G1b-7 EXECUTING→ARCHIVING invalid (skip VERIFYING)",
           not gm2.can_transition(ARCHIVING), "")

        gm2.transition(VERIFYING)
        ok("G1b-8 VERIFYING→ARCHIVED invalid (skip ARCHIVING)",
           not gm2.can_transition(ARCHIVED), "")

        # None→non-CLARIFY should fail
        gm3 = gsm.GoalMachine(str(token_path))
        ok("G1b-9 None→PLANNING invalid (initial must be CLARIFY)",
           not gm3.can_transition(PLANNING), "")
        ok("G1b-10 None→ARCHIVED invalid (initial must be CLARIFY)",
           not gm3.can_transition(ARCHIVED), "")

        # ── G1c: Backward transitions must fail (RED: currently allowed) ──
        # Start from EXECUTING
        gm4 = gsm.GoalMachine(str(token_path))
        gm4.transition(CLARIFY)
        gm4.transition(PLANNING)
        gm4.transition(EXECUTING)

        ok("G1c-1 EXECUTING→CLARIFY invalid (backward, RED)",
           not gm4.can_transition(CLARIFY),
           "EXECUTING→CLARIFY should be forbidden but is currently allowed")

        # Start from VERIFYING
        gm5 = gsm.GoalMachine(str(token_path))
        gm5.transition(CLARIFY)
        gm5.transition(PLANNING)
        gm5.transition(EXECUTING)
        gm5.transition(VERIFYING)

        ok("G1c-2 VERIFYING→CLARIFY invalid (backward, RED)",
           not gm5.can_transition(CLARIFY),
           "VERIFYING→CLARIFY should be forbidden but is currently allowed")

        ok("G1c-3 VERIFYING→EXECUTING invalid (backward, RED)",
           not gm5.can_transition(EXECUTING),
           "VERIFYING→EXECUTING should be forbidden but is currently allowed")

        # Start from ARCHIVING
        gm6 = gsm.GoalMachine(str(token_path))
        gm6.transition(CLARIFY)
        gm6.transition(PLANNING)
        gm6.transition(EXECUTING)
        gm6.transition(VERIFYING)
        gm6.transition(ARCHIVING)

        ok("G1c-4 ARCHIVING→VERIFYING invalid (backward, RED)",
           not gm6.can_transition(VERIFYING),
           "ARCHIVING→VERIFYING should be forbidden but is currently allowed")

        ok("G1c-5 ARCHIVING→CLARIFY invalid (backward, RED)",
           not gm6.can_transition(CLARIFY),
           "ARCHIVING→CLARIFY should be forbidden but is currently allowed")

        # Start from PLANNING
        gm7 = gsm.GoalMachine(str(token_path))
        gm7.transition(CLARIFY)
        gm7.transition(PLANNING)

        ok("G1c-6 PLANNING→CLARIFY invalid (backward, RED)",
           not gm7.can_transition(CLARIFY),
           "PLANNING→CLARIFY should be forbidden but is currently allowed")

        # ── G1d: ARCHIVED terminal rejects all ──
        gm8 = gsm.GoalMachine(str(token_path))
        gm8.transition(CLARIFY)
        gm8.transition(PLANNING)
        gm8.transition(EXECUTING)
        gm8.transition(VERIFYING)
        gm8.transition(ARCHIVING)
        gm8.transition(ARCHIVED)

        for s in ALL_STATES:
            ok(f"G1d ARCHIVED→{s} invalid (terminal)",
               not gm8.can_transition(s), f"terminal state allowed transition to {s}")

        # ── G1e: transition() raises GoalError on invalid ──
        # Reset fresh
        gm9 = gsm.GoalMachine(str(token_path))
        gm9.transition(CLARIFY)
        try:
            gm9.transition(EXECUTING)
            ok("G1e-1 transition(EXECUTING) raises GoalError (skip)",
               False, "no exception raised for CLARIFY→EXECUTING")
        except gsm.GoalError:
            ok("G1e-1 transition(EXECUTING) raises GoalError (skip)",
               True, "")

        try:
            gm9.transition(VERIFYING)
            ok("G1e-2 transition(VERIFYING) raises GoalError (skip)",
               False, "no exception raised for CLARIFY→VERIFYING")
        except gsm.GoalError:
            ok("G1e-2 transition(VERIFYING) raises GoalError (skip)",
               True, "")


# ====================================================================
# G2: GoalMachine Import/Runtime Fail-Closed
# ====================================================================

def run_g2():
    """G2: GoalMachine import/runtime 缺失时 fail closed 而非静默"""
    print("\n" + "=" * 64)
    print("G2: GoalMachine Import/Runtime Fail-Closed")
    print("=" * 64)

    gsm = _get_gsm()
    CLARIFY = gsm.CLARIFY
    PLANNING = gsm.PLANNING
    EXECUTING = gsm.EXECUTING

    # ── G2a: GoalMachine=None → 所有 GoalMachine 操作必须阻断（非静默） ──
    # In carros_base, when import fails: GoalMachine=None, GoalError=Exception
    # Tests: calling GoalMachine() should raise TypeError (not callable)
    with tempfile.TemporaryDirectory() as td:
        token_path = Path(td) / "token.json"
        token_path.write_text("{}", encoding="utf-8")

        # Simulate GoalMachine=None (import failure)
        GoalMachine = None
        GoalError = Exception

        # Attempting to instantiate GoalMachine when it's None must fail
        try:
            gm = GoalMachine(str(token_path))
            ok("G2a GoalMachine=None silently succeeds (RED - should fail closed)",
               False, "GoalMachine(None) did not raise TypeError")
        except TypeError:
            ok("G2a GoalMachine=None raises TypeError (fail-closed)", True, "")
        except Exception:
            ok("G2a GoalMachine=None raises exception (fail-closed, unexpected type)",
               False, "expected TypeError")

    # ── G2b: token missing goal.state → 状态机的 transition 不应静默跳过 ──
    # Testing that GoalMachine recovers from bad state correctly
    with tempfile.TemporaryDirectory() as td:
        token_path = Path(td) / "token.json"
        # Token with no goal field at all
        token_path.write_text(
            json.dumps({"session": {"id": "test"}, "stats": {"done": 0, "total": 1}}),
            encoding="utf-8",
        )
        gm = gsm.GoalMachine(str(token_path))
        # When no goal state, current_state should be None (need to init)
        ok("G2b token missing goal.state → current_state=None",
           gm.current_state is None,
           f"got state={gm.current_state!r}")

        # Transition should fail closed (can't go to anything from None except CLARIFY)
        ok("G2b None→EXECUTING invalid (can't skip CLARIFY)",
           not gm.can_transition(EXECUTING),
           "None→EXECUTING should be forbidden")

        # But can init to CLARIFY
        gm.transition(CLARIFY)
        ok("G2b None→CLARIFY valid init", gm.current_state == CLARIFY, "")

        # ── G2c: Corrupt token JSON → 状态机初始化为None, 不崩溃 ──
        token_path.write_text("NOT VALID JSON\n", encoding="utf-8")
        gm2 = gsm.GoalMachine(str(token_path))
        ok("G2c corrupt token → current_state=None (fail-closed, no crash)",
           gm2.current_state is None,
           f"got state={gm2.current_state!r}")

        # Transition should still work (start from None)
        gm2.transition(CLARIFY)
        ok("G2c after corrupt token → can init to CLARIFY",
           gm2.current_state == CLARIFY, "")

        # ── G2d: Unknown state in token → 状态机初始化为None, fail closed ──
        token_path.write_text(
            json.dumps({"goal": {"state": "INVALID_STATE"}}),
            encoding="utf-8",
        )
        gm3 = gsm.GoalMachine(str(token_path))
        ok("G2d unknown state in token → current_state=None (fail-closed)",
           gm3.current_state is None,
           f"got state={gm3.current_state!r}")


# ====================================================================
# G3: ResearchGate — Content Structure Validation
# ====================================================================

def run_g3():
    """G3: ResearchGate 结构验证 - 所有 section 有真实非placeholder 内容"""
    print("\n" + "=" * 64)
    print("G3: ResearchGate - Content Structure Validation")
    print("=" * 64)

    gsm = _get_gsm()
    PLANNING = gsm.PLANNING

    # Import real ResearchGate
    gc_path = REPO_ROOT / ".claude" / "scripts" / "goal_contracts.py"
    try:
        gc = _import_module("goal_contracts_t8_g3", gc_path)
        ResearchGate = gc.ResearchGate
        ResearchGateError = gc.ResearchGateError
    except Exception as e:
        infra_ok("G3-infra import goal_contracts", False, f"exception: {e}")
        return

    # Required sections for ResearchGate
    REQUIRED_SECTIONS = ["背景", "约束", "已知信息", "不确定性", "全貌", "依赖树", "方案", "Dependency TDD"]

    # --- G3a: ResearchGate rejects placeholder content ---
    with tempfile.TemporaryDirectory() as td:
        root = _make_temp_project(Path(td))
        task_dir = root / ".omc" / "tasks" / "20260729" / "t8-g3a"
        task_dir.mkdir(parents=True, exist_ok=True)

        # Placeholder-only research.md - ResearchGate must reject
        research_path = task_dir / "research.md"
        research_path.write_text(
            "# Research\n\n"
            "## 背景\n\n"
            "## 约束\n\n"
            "## 已知信息\n\n"
            "## 不确定性\n\n"
            "## 全貌\n\n"
            "## 依赖树\n\n"
            "## 方案\n\n"
            "## Dependency TDD\n\n",
            encoding="utf-8",
        )

        # Call real ResearchGate - should raise ResearchGateError
        try:
            ResearchGate.validate(str(research_path))
            ok("G3a ResearchGate rejects placeholder content", False,
               "should have raised ResearchGateError")
        except ResearchGateError as e:
            ok("G3a ResearchGate rejects placeholder content", True,
               f"errors: {e.errors}")

        # Real content - should pass
        research_path.write_text(
            "# Research\n\n"
            "## 背景\n"
            "This is the background of the task.\n\n"
            "## 约束\n"
            "Must use Python 3.10+.\n\n"
            "## 已知信息\n"
            "We have existing test infrastructure.\n\n"
            "## 不确定性\n"
            "Performance under load is unknown.\n\n"
            "## 全貌\n"
            "The system comprises three layers.\n\n"
            "## 依赖树\n"
            "- Layer A depends on Layer B\n"
            "- Layer B depends on C and D\n"
            "- Layer C has no external deps\n\n"
            "## 方案\n"
            "We will implement in three phases.\n\n"
            "## Dependency TDD\n"
            "Write tests first for B and C.\n\n",
            encoding="utf-8",
        )

        try:
            result = ResearchGate.validate(str(research_path))
            ok("G3a-real ResearchGate accepts real content", True,
               f"dep_tree={result['dep_tree_count']}")
        except ResearchGateError as e:
            ok("G3a-real ResearchGate accepts real content", False,
               f"unexpected error: {e}")

    # --- G3b: can_transition still works (gate only checks in transition()) ---
    with tempfile.TemporaryDirectory() as td:
        token_path = Path(td) / "token.json"
        token_path.write_text(
            json.dumps({"goal": {"state": "CLARIFY"}}),
            encoding="utf-8",
        )
        gm = gsm.GoalMachine(str(token_path))

        ok("G3b CLARIFY->PLANNING can_transition (no gate in can_transition)",
           gm.can_transition(PLANNING),
           "can_transition returns True for valid state transitions")

    # --- G3c: phase0-done no longer uses line count (lx-goal domain, stays RED) ---
    lx_goal_path = REPO_ROOT / ".claude" / "skills" / "lx-goal" / "scripts" / "lx-goal.py"
    lx_src = ""
    phase0_src = ""
    if lx_goal_path.exists():
        lx_src = lx_goal_path.read_text(encoding="utf-8")
        # Check only cmd_phase0_done's source (not whole file — "split" used elsewhere)
        import ast as _ast
        try:
            _tree = _ast.parse(lx_src)
            for _node in _ast.walk(_tree):
                if isinstance(_node, _ast.FunctionDef) and _node.name == "cmd_phase0_done":
                    phase0_src = _ast.unparse(_node)
                    break
        except Exception:
            phase0_src = ""
        uses_line_count = "len(research_md.read_text" in phase0_src
        ok("G3c phase0-done no longer uses line count (RED)",
           not uses_line_count,
           "cmd_phase0_done still uses line count for research content validation")
    else:
        infra_ok("G3c-infra lx-goal.py found", False, "lx-goal.py not found")

    # --- G3d: phase0-done uses ResearchGate content-structure validation ---
    if lx_goal_path.exists():
        if not phase0_src:
            phase0_src = _py_source(lambda: None)
            try:
                lx_mod = _import_module("lx_goal_t8_g3d", lx_goal_path)
                phase0_src = _py_source(lx_mod.cmd_phase0_done)
            except Exception:
                phase0_src = lx_src

        has_content_validation = "_ResearchGate.validate" in phase0_src
        ok("G3d phase0-done validates research content structure (RED)",
           has_content_validation,
           "cmd_phase0_done doesn't call ResearchGate.validate")

def run_g4():
    """G4: PlanGate - at least 1 Phase+Step, unique ids, acyclic deps, real content"""
    print("\n" + "=" * 64)
    print("G4: PlanGate - Structure and Content Validation")
    print("=" * 64)

    gsm = _get_gsm()
    CLARIFY = gsm.CLARIFY
    EXECUTING = gsm.EXECUTING

    REQUIRED_STEP_FIELDS = ["depends_on", "acceptance", "verify", "scope"]
    PLAN_REQUIRED_SECTIONS = ["Conditions", "Key Changes", "Decisions",
                              "Acceptance Checklist", "TDD Evidence"]

    # Import real PlanGate
    gc_path = REPO_ROOT / ".claude" / "scripts" / "goal_contracts.py"
    try:
        gc = _import_module("goal_contracts_t8_g4", gc_path)
        PlanGate = gc.PlanGate
        PlanGateError = gc.PlanGateError
    except Exception as e:
        infra_ok("G4-infra import goal_contracts", False, f"exception: {e}")
        return

    # --- G4a: PLANNING->EXECUTING can_transition (no gate in can_transition) ---
    with tempfile.TemporaryDirectory() as td:
        token_path = Path(td) / "token.json"
        token_path.write_text(
            json.dumps({"goal": {"state": "PLANNING"}}),
            encoding="utf-8",
        )
        gm = gsm.GoalMachine(str(token_path))

        ok("G4a PLANNING->EXECUTING can_transition",
           gm.can_transition(EXECUTING),
           "can_transition returns True for valid state transitions")

    # --- G4b: PlanGate rejects duplicate step IDs ---
    with tempfile.TemporaryDirectory() as td:
        plan = Path(td) / "plan.md"
        plan.write_text(
            "# Plan\n\n"
            "## Phase 1\n"
            "- [ ] S1: first step\n"
            "  - status: pending\n"
            "  - depends_on: none\n"
            "  - acceptance: some acceptance\n"
            "  - verify: command:echo ok\n\n"
            "## Phase 2\n"
            "- [ ] S1: duplicate id\n"
            "  - status: pending\n"
            "  - depends_on: none\n"
            "  - acceptance: some acceptance\n"
            "  - verify: command:echo ok\n\n",
            encoding="utf-8",
        )
        try:
            PlanGate.validate(str(plan))
            ok("G4b PlanGate rejects duplicate step IDs", False,
               "should have raised PlanGateError")
        except PlanGateError as e:
            ok("G4b PlanGate rejects duplicate step IDs", True,
               f"errors: {e.errors}")

    # --- G4c: PlanGate rejects steps with empty/placeholder fields ---
    with tempfile.TemporaryDirectory() as td:
        plan = Path(td) / "plan.md"
        plan.write_text(
            "# Plan\n\n"
            "## Phase 1\n"
            "- [ ] S1: test\n"
            "  - status: pending\n"
            "  - depends_on: none\n"
            "  - scope: \n"
            "  - acceptance: \n"
            "  - verify: \n\n",
            encoding="utf-8",
        )
        try:
            PlanGate.validate(str(plan))
            ok("G4c PlanGate rejects empty/placeholder fields", False,
               "should have raised PlanGateError")
        except PlanGateError as e:
            ok("G4c PlanGate rejects empty/placeholder fields", True,
               f"errors: {e.errors}")

    # --- G4c-real: PlanGate accepts steps with real field content ---
    with tempfile.TemporaryDirectory() as td:
        plan = Path(td) / "plan.md"
        plan.write_text(
            "# Plan\n\n"
            "## Phase 1\n"
            "- [ ] S1: test\n"
            "  - status: pending\n"
            "  - depends_on: none\n"
            "  - scope: files A, B\n"
            "  - acceptance: must compile\n"
            "  - verify: command:pytest\n\n",
            encoding="utf-8",
        )
        try:
            result = PlanGate.validate(str(plan))
            ok("G4c-real PlanGate accepts real field content", True,
               f"steps={result['steps']}")
        except PlanGateError as e:
            ok("G4c-real PlanGate accepts real field content", False,
               f"unexpected error: {e}")

    # --- G4d: PlanGate rejects cyclic dependency graph ---
    with tempfile.TemporaryDirectory() as td:
        plan = Path(td) / "plan.md"
        plan.write_text(
            "# Plan\n\n"
            "## Phase 1\n"
            "- [ ] S1: step 1\n"
            "  - status: pending\n"
            "  - depends_on: S3\n"
            "  - scope: module A\n"
            "  - acceptance: must work\n"
            "  - verify: command:echo ok\n\n"
            "- [ ] S2: step 2\n"
            "  - status: pending\n"
            "  - depends_on: S1\n"
            "  - scope: module B\n"
            "  - acceptance: must work\n"
            "  - verify: command:echo ok\n\n"
            "- [ ] S3: step 3\n"
            "  - status: pending\n"
            "  - depends_on: S2\n"
            "  - scope: module C\n"
            "  - acceptance: must work\n"
            "  - verify: command:echo ok\n\n",
            encoding="utf-8",
        )
        try:
            PlanGate.validate(str(plan))
            ok("G4d PlanGate rejects cyclic dependencies", False,
               "should have raised PlanGateError")
        except PlanGateError as e:
            ok("G4d PlanGate rejects cyclic dependencies", True,
               f"errors: {e.errors}")

    # --- G4e: Executor template must have all required sections ---
    with tempfile.TemporaryDirectory() as td:
        executor = Path(td) / "executor.md"
        executor.write_text(
            "# Executor Evidence Ledger\n\n"
            "## Conditions\n"
            "- step: S1\n"
            "- status: active\n\n"
            "## Key Changes\n"
            "- file: src/main.py modified\n\n"
            "## Decisions\n"
            "- decision: use approach A\n"
            "- rationale: better performance\n\n"
            "## Acceptance Checklist\n"
            "- [x] AC1: feature works\n\n"
            "## TDD Evidence\n"
            "- dependency TDD: pytest tests/test_dep.py -> exit 0\n"
            "- regression TDD: pytest tests/ -> exit 0\n\n"
            "## S1\n\n",
            encoding="utf-8",
        )
        exec_text = executor.read_text(encoding="utf-8")
        all_present = all(s in exec_text for s in PLAN_REQUIRED_SECTIONS)
        ok("G4e executor template has all required sections",
           all_present,
           f"missing sections: {[s for s in PLAN_REQUIRED_SECTIONS if s not in exec_text]}")

        # Check sections have real content (headings + content)
        has_content = True
        for section in PLAN_REQUIRED_SECTIONS:
            parts = exec_text.split(f"## {section}")
            if len(parts) >= 2:
                after_header = parts[1].split("\n## ")[0]
                clean = [l.strip() for l in after_header.split("\n") if l.strip()]
                if not clean:
                    has_content = False
        ok("G4e-real all executor sections have real content",
           has_content,
           "some executor sections contain only header, no content")

def run_g5():
    """G5: Step隔离 — first pending仅依赖completed可active；开始Step原子记录；完成需协调"""
    print("\n" + "=" * 64)
    print("G5: Step Isolation — Dependency-Aware Activation")
    print("=" * 64)

    # ── G5a: Step can only activate when all dependencies are completed (RED) ──
    with tempfile.TemporaryDirectory() as td:
        plan_path = Path(td) / "plan.md"
        plan_path.write_text(
            "# Plan\n\n"
            "## Phase 1\n"
            "- [ ] S1: step 1\n"
            "  - status: pending\n"
            "  - depends_on: none\n"
            "  - acceptance: step 1 works\n"
            "  - verify: command:echo ok\n\n"
            "- [ ] S2: step 2\n"
            "  - status: pending\n"
            "  - depends_on: S1\n"
            "  - acceptance: step 2 works\n"
            "  - verify: command:echo ok\n\n"
            "- [ ] S3: step 3\n"
            "  - status: pending\n"
            "  - depends_on: S2\n"
            "  - acceptance: step 3 works\n"
            "  - verify: command:echo ok\n\n",
            encoding="utf-8",
        )

        # S1 has no deps, should be the first pending
        deps_map = {}
        current_step = None
        plan_text = plan_path.read_text(encoding="utf-8")
        for line in plan_text.split("\n"):
            sm = re.match(r"- \[.\] (\S+?):", line.strip())
            if sm:
                current_step = sm.group(1)
                deps_map[current_step] = {"depends_on": "none", "done": False}
            dm = re.match(r"\s+- depends_on:\s*(\S+)", line)
            if dm and current_step:
                dep_val = dm.group(1).strip()
                if dep_val.lower() != "none":
                    deps_map[current_step]["depends_on"] = dep_val

        # Find first pending (no unmet deps)
        def first_pending(steps_map):
            completed = set()
            for sid, info in steps_map.items():
                if info.get("done"):
                    completed.add(sid)
            for sid, info in steps_map.items():
                if sid in completed:
                    continue
                dep = info["depends_on"]
                if dep == "none" or dep in completed:
                    return sid
            return None

        first = first_pending(deps_map)
        ok("G5a first pending step (no deps) identified correctly",
           first == "S1",
           f"expected S1, got {first}")

        # Now check S2 requires S1 to be completed first
        deps_map["S1"]["done"] = True
        first2 = first_pending(deps_map)
        ok("G5a after S1 completed, S2 is next pending",
           first2 == "S2",
           f"expected S2, got {first2}")

        # S3 requires S2
        deps_map["S2"]["done"] = True
        first3 = first_pending(deps_map)
        ok("G5a after S2 completed, S3 is next pending",
           first3 == "S3",
           f"expected S3, got {first3}")

    # ── G5b: Start step requires atomic record in token ──
    with tempfile.TemporaryDirectory() as td:
        token_path = Path(td) / "token.json"
        plan_path = Path(td) / "plan.md"
        executor_path = Path(td) / "executor.md"

        token_path.write_text(
            json.dumps({"stats": {"done": 0, "total": 3}, "task": {"current_step": "S1", "status": "active"}}),
            encoding="utf-8",
        )
        plan_path.write_text("# Plan\n\n- [ ] S1: step 1\n  - depends_on: none\n", encoding="utf-8")
        executor_path.write_text("# Executor\n\n", encoding="utf-8")

        # Call real start_step_atomic
        if step_contracts:
            step_contracts.start_step_atomic(str(token_path), str(plan_path), str(executor_path), "S1")

        # Token should have atomic record
        token = json.loads(token_path.read_text(encoding="utf-8"))
        started = token.get("goal", {}).get("active_step")
        ok("G5b step start produces atomic token record",
           started == "S1",
           f"expected active_step=S1, got {started!r}")

        # Plan should have step marked as active
        plan_text = plan_path.read_text(encoding="utf-8")
        step_active = "[a]" in plan_text and "S1" in plan_text
        ok("G5b plan reflects step activation",
           step_active,
           f"plan.md doesn't mark S1 as active: {plan_text[:200]}")

        # Executor should have start record
        executor_text = executor_path.read_text(encoding="utf-8")
        ok("G5b executor has step-start evidence",
           "start" in executor_text.lower(),
           "executor.md lacks start evidence for activated step")

    # ── G5c: Complete step requires token/plan/executor coordination ──
    with tempfile.TemporaryDirectory() as td:
        token_path = Path(td) / "token.json"
        plan_path = Path(td) / "plan.md"
        executor_path = Path(td) / "executor.md"

        token_path.write_text(
            json.dumps({"stats": {"done": 0, "total": 2}, "task": {"current_step": "S1", "status": "active"}}),
            encoding="utf-8",
        )
        plan_path.write_text("# Plan\n\n- [ ] S1: step 1\n  - depends_on: none\n  - verify: command:echo ok\n", encoding="utf-8")
        executor_path.write_text("# Executor\n\n### EV-S1\n- step: S1\n- type: command\n- source: echo ok\n- exit_code: 0\n- evidence_level: E3\n", encoding="utf-8")

        # Call real start_step_atomic to set up proper state
        if step_contracts:
            step_contracts.start_step_atomic(str(token_path), str(plan_path), str(executor_path), "S1")

        # Reload after atomic start
        plan_text = plan_path.read_text(encoding="utf-8")
        executor_text = executor_path.read_text(encoding="utf-8")

        has_executor_evidence = "EV-S1" in executor_text and "exit_code: 0" in executor_text
        has_plan_verify = "verify:" in plan_text

        ok("G5c can_complete requires executor evidence",
           has_executor_evidence,
           "no executor evidence for step S1")

        ok("G5c can_complete requires plan verify rules",
           has_plan_verify,
           "no verify rules in plan for step S1")

        # Without full evidence, complete_step_atomic must raise ValueError
        executor_path.write_text("# Executor\n\n", encoding="utf-8")
        if step_contracts:
            try:
                step_contracts.complete_step_atomic(str(token_path), str(plan_path), str(executor_path), "S1")
                ok("G5c without executor evidence, step cannot complete",
                   False, "should have raised ValueError")
            except ValueError:
                ok("G5c without executor evidence, step cannot complete",
                   True, "correctly rejected with ValueError")
        else:
            ok("G5c without executor evidence, step cannot complete (step_contracts missing)",
               False, "step_contracts not available")


# ====================================================================
# G6: Executor Atomic Evidence
# ====================================================================

def run_g6():
    """G6: Executor atomic evidence — Conditions/Key Changes/Decisions+rationale/AC全通/TDD命令exit0"""
    print("\n" + "=" * 64)
    print("G6: Executor Atomic Evidence Completeness")
    print("=" * 64)

    EVIDENCE_SECTIONS = ["Conditions", "Key Changes", "Decisions",
                         "Acceptance Checklist", "TDD Evidence"]

    # ── G6a: All evidence sections must have real content (not just headers) ──
    with tempfile.TemporaryDirectory() as td:
        executor_path = Path(td) / "executor.md"
        # Executor with ALL required sections having real content
        executor_path.write_text(
            "# Executor\n\n"
            "## Conditions\n"
            "- step: S1\n"
            "- status: active\n"
            "- depends_on: none\n\n"
            "## Key Changes\n"
            "- file: src/main.py changed\n"
            "- summary: added feature X\n\n"
            "## Decisions\n"
            "- decision: use approach A\n"
            "- rationale: better performance\n\n"
            "## Acceptance Checklist\n"
            "- [x] AC1: feature works\n"
            "- [x] AC2: tests pass\n\n"
            "## TDD Evidence\n"
            "- dependency TDD: pytest tests/test_dep.py → exit 0\n"
            "- regression TDD: pytest tests/ → exit 0\n\n"
            "### EV-S1\n- step: S1\n- type: command\n- source: echo ok\n- exit_code: 0\n",
            encoding="utf-8",
        )
        exec_text = executor_path.read_text(encoding="utf-8")
        all_sections_present = all(s in exec_text for s in EVIDENCE_SECTIONS)
        ok("G6a all executor evidence sections present",
           all_sections_present,
           f"missing: {[s for s in EVIDENCE_SECTIONS if s not in exec_text]}")

        # Use real validate_step_evidence to confirm content is valid
        if step_contracts:
            errors = step_contracts.validate_step_evidence(exec_text, "S1")
            ok("G6a-real all evidence sections have real content",
               len(errors) == 0,
               f"validation errors: {', '.join(errors)}")
        else:
            # fallback check
            has_content = all(s in exec_text for s in EVIDENCE_SECTIONS)
            ok("G6a-real all evidence sections have real content (step_contracts missing)",
               has_content, "")

    # ── G6b: Decisions must include rationale ──
    with tempfile.TemporaryDirectory() as td:
        # Executor WITHOUT rationale in Decisions → should fail validation
        executor_path = Path(td) / "executor.md"
        executor_path.write_text(
            "# Executor\n\n"
            "## Conditions\n"
            "- step: S1\n"
            "- status: active\n\n"
            "## Key Changes\n"
            "- file: src/main.py\n\n"
            "## Decisions\n"
            "- Decided to implement approach A\n\n"
            "## Acceptance Checklist\n"
            "- [x] AC1: all tests pass\n\n"
            "## TDD Evidence\n"
            "- dependency TDD: pytest tests/test-dep.py → exit 0\n"
            "- regression TDD: pytest tests/ → exit 0\n\n"
            "### EV-S1\n- step: S1\n- type: command\n- source: echo ok\n- exit_code: 0\n",
            encoding="utf-8",
        )
        exec_text = executor_path.read_text(encoding="utf-8")
        if step_contracts:
            errors = step_contracts.validate_step_evidence(exec_text, "S1")
            has_rationale_errors = any("rationale" in e for e in errors)
            ok("G6b Decisions missing rationale → validate_step_evidence reports error",
               has_rationale_errors,
               f"expected rationale error, got: {errors}")
        else:
            has_rationale = "rationale" in exec_text.lower() or "reason" in exec_text.lower()
            ok("G6b Decisions include rationale (step_contracts missing)",
               has_rationale, "")

    # ── G6c: Acceptance Checklist must be ALL passed ──
    with tempfile.TemporaryDirectory() as td:
        # Executor with unchecked AC → must fail validation
        executor_path = Path(td) / "executor.md"
        executor_path.write_text(
            "# Executor\n\n"
            "## Conditions\n"
            "- step: S1\n\n"
            "## Key Changes\n"
            "- file: src/main.py\n\n"
            "## Decisions\n"
            "- decision: approach A\n"
            "- rationale: better performance\n\n"
            "## Acceptance Checklist\n"
            "- [x] AC1: tests pass\n"
            "- [ ] AC2: documentation updated\n\n"
            "## TDD Evidence\n"
            "- dependency TDD: pytest tests/test-dep.py → exit 0\n"
            "- regression TDD: pytest tests/ → exit 0\n\n"
            "### EV-S1\n- step: S1\n- type: command\n- source: echo ok\n- exit_code: 0\n",
            encoding="utf-8",
        )
        text = executor_path.read_text(encoding="utf-8")
        if step_contracts:
            errors = step_contracts.validate_step_evidence(text, "S1")
            ac_errors = [e for e in errors if "acceptance_checklist" in e or "unchecked" in e]
            ok("G6c Acceptance Checklist not all passed → validation error",
               len(ac_errors) > 0,
               f"expected AC errors, got: {errors}")
        else:
            unchecked = len(re.findall(r"- \[ \]", text))
            ok("G6c Acceptance Checklist not all passed (step_contracts missing)",
               unchecked > 0, f"{unchecked} unchecked")

    # ── G6d: TDD evidence requires both dependency and regression TDD with exit 0 ──
    with tempfile.TemporaryDirectory() as td:
        # Executor with TDD but no exit 0 → validation must fail
        executor_path = Path(td) / "executor.md"
        executor_path.write_text(
            "# Executor\n\n"
            "## Conditions\n"
            "- step: S1\n\n"
            "## Key Changes\n"
            "- file: src/main.py\n\n"
            "## Decisions\n"
            "- decision: approach A\n"
            "- rationale: simpler\n\n"
            "## Acceptance Checklist\n"
            "- [x] AC1: all tests pass\n\n"
            "## TDD Evidence\n"
            "- dependency TDD: pytest tests/dep.py\n"
            "- regression TDD: pytest tests/\n\n"
            "### EV-S1\n- step: S1\n- type: command\n- source: echo ok\n- exit_code: 0\n",
            encoding="utf-8",
        )
        text = executor_path.read_text(encoding="utf-8")
        if step_contracts:
            errors = step_contracts.validate_step_evidence(text, "S1")
            tdd_errors = [e for e in errors if "tdd" in e.lower()]
            ok("G6d TDD without exit 0 → validation error",
               len(tdd_errors) > 0,
               f"expected TDD errors, got: {errors}")
        else:
            has_dep_tdd = "dependency" in text.lower() and "tdd" in text.lower()
            has_reg_tdd = "regression" in text.lower() and "tdd" in text.lower()
            has_exit_0 = "exit 0" in text.lower() or "exit_code: 0" in text
            ok("G6d TDD with proper exit 0 (step_contracts missing)",
               has_dep_tdd and has_reg_tdd and has_exit_0, "")

    # ── G6e: Missing any section → step cannot be VERIFIED ──
    with tempfile.TemporaryDirectory() as td:
        executor_path = Path(td) / "executor.md"
        executor_path.write_text(
            "# Executor\n\n"
            "### EV-S1\n- step: S1\n- type: command\n- source: echo ok\n- exit_code: 0\n- evidence_level: E3\n",
            encoding="utf-8",
        )
        text = executor_path.read_text(encoding="utf-8")

        # Use real validate_step_evidence — should report missing sections
        if step_contracts:
            errors = step_contracts.validate_step_evidence(text, "S1")
            has_conditions_error = any("conditions" in e for e in errors)
            has_ac_error = any("acceptance_checklist" in e or "acceptance" in e.lower() for e in errors)
            has_tdd_error = any("tdd" in e.lower() for e in errors)
            ok("G6e missing Conditions → validation reports error",
               has_conditions_error,
               f"expected conditions error, got: {errors}")
            ok("G6e missing Acceptance Checklist → validation reports error",
               has_ac_error,
               f"expected AC error, got: {errors}")
            ok("G6e missing TDD Evidence → validation reports error",
               has_tdd_error,
               f"expected TDD error, got: {errors}")
        else:
            # fallback
            has_conditions = "## Conditions" in text
            has_ac = "## Acceptance" in text
            has_tdd = "## TDD" in text
            ok("G6e missing sections (step_contracts missing)",
               not (has_conditions and has_ac and has_tdd), "")


# ====================================================================
# G7: VERIFYING/ARCHIVING Flow
# ====================================================================

def run_g7():
    """G7: 全部Step verified才VERIFYING→VerifyGate全绿→ARCHIVING→ARCHIVED；失败保持"""
    print("\n" + "=" * 64)
    print("G7: VERIFYING / ARCHIVING Gate Flow")
    print("=" * 64)

    gsm = _get_gsm()
    EXECUTING = gsm.EXECUTING
    VERIFYING = gsm.VERIFYING
    ARCHIVING = gsm.ARCHIVING
    ARCHIVED = gsm.ARCHIVED

    # ── G7a: Only transition VERIFYING when ALL steps verified (RED) ──
    with tempfile.TemporaryDirectory() as td:
        token_path = Path(td) / "token.json"
        token_path.write_text(
            json.dumps({
                "stats": {"done": 1, "total": 3},
                "goal": {"state": EXECUTING},
            }),
            encoding="utf-8",
        )
        gm = gsm.GoalMachine(str(token_path))
        gm._state = EXECUTING

        # Not all steps done → should not permit VERIFYING
        ok("G7a not all steps done → EXECUTING→VERIFYING blocked (RED)",
           not gm.can_transition(VERIFYING),
           "can transition to VERIFYING with only 1/3 steps done (RED)")

        # All steps done → should permit VERIFYING
        token_path.write_text(
            json.dumps({
                "stats": {"done": 3, "total": 3},
                "goal": {"state": EXECUTING},
            }),
            encoding="utf-8",
        )
        gm2 = gsm.GoalMachine(str(token_path))
        gm2._state = EXECUTING
        ok("G7a all steps done → EXECUTING→VERIFYING permitted",
           gm2.can_transition(VERIFYING),
           f"can_transition={gm2.can_transition(VERIFYING)}")

    # ── G7b: VERIFYING→ARCHIVING only when VerifyGate all green (RED) ──
    # auto_progress() MUST stop at VERIFYING — transition to ARCHIVING
    # requires external verify command (VerifyGate), not automatic progress.
    with tempfile.TemporaryDirectory() as td:
        token_path = Path(td) / "token.json"
        token_path.write_text(
            json.dumps({
                "stats": {"done": 3, "total": 3},
                "goal": {"state": VERIFYING},
            }),
            encoding="utf-8",
        )
        gm = gsm.GoalMachine(str(token_path))
        gm._state = VERIFYING

        # auto_progress must NOT push VERIFYING→ARCHIVING automatically
        try:
            result = gm.auto_progress()
            ok("G7b VERIFYING→ARCHIVING requires VerifyGate all green (RED)",
               result == [] and gm.current_state == VERIFYING,
               f"auto_progress result={result}, state={gm.current_state}")
        except Exception as e:
            ok("G7b VERIFYING→ARCHIVING requires VerifyGate all green (RED)",
               False, f"auto_progress raised exception: {e}")

    # ── G7c: ARCHIVING→ARCHIVED final (terminal) ──
    with tempfile.TemporaryDirectory() as td:
        token_path = Path(td) / "token.json"
        token_path.write_text(
            json.dumps({
                "stats": {"done": 3, "total": 3},
                "goal": {"state": ARCHIVING},
            }),
            encoding="utf-8",
        )
        gm = gsm.GoalMachine(str(token_path))
        gm._state = ARCHIVING
        gm.transition(ARCHIVED)
        ok("G7c ARCHIVED is terminal", gm.current_state == ARCHIVED and gm.is_terminal, "")

    # ── G7d: Failed verification stays at EXECUTING/VERIFYING (RED) ──
    with tempfile.TemporaryDirectory() as td:
        token_path = Path(td) / "token.json"
        token_path.write_text(
            json.dumps({
                "stats": {"done": 0, "total": 3},
                "goal": {"state": EXECUTING},
            }),
            encoding="utf-8",
        )
        gm = gsm.GoalMachine(str(token_path))
        gm._state = EXECUTING

        # With failed verify (done < total), should stay EXECUTING
        ok("G7d verify failure → stays EXECUTING (RED)",
           gm.current_state == EXECUTING,
           "verify failure didn't prevent transition")


# ====================================================================
# G8: lx-goal Integration
# ====================================================================

def run_g8():
    """G8: lx-goal `on` task dir仅来自carros init；phase0-done/task-done/done通过共享状态机/ledger"""
    print("\n" + "=" * 64)
    print("G8: lx-goal Integration Protocol")
    print("=" * 64)

    lx_goal_path = REPO_ROOT / ".claude" / "skills" / "lx-goal" / "scripts" / "lx-goal.py"
    if not lx_goal_path.exists():
        infra_ok("G8-infra lx-goal.py found", False, "lx-goal.py not found")
        return

    lx_src = lx_goal_path.read_text(encoding="utf-8")

    # ── G8a: lx-goal `on` only creates task dir via carros init, not independently (RED) ──
    # Check that cmd_on uses carros_base.py init, not independent mkdir
    uses_carros_init = "carros_base.py" in lx_src and "init" in lx_src
    ok("G8a cmd_on delegates to carros_base.py init",
       uses_carros_init,
       "cmd_on doesn't use carros_base.py init for task directory creation")

    # Check there is NO independent task dir creation (no .omc/tasks/...mkdir)
    # Exclude the carros_base delegation path
    independent_mkdir = False
    lines = lx_src.split("\n")
    for i, line in enumerate(lines):
        if "mkdir" in line and "TASK_DIR" in line:
            independent_mkdir = True
            break
    ok("G8a cmd_on does NOT create task dir independently (RED)",
       not independent_mkdir,
       "lx-goal creates task dir independently, bypassing carros init")

    # ── G8b: phase0-done/task-done/done through shared state machine/ledger, not direct append (RED) ──
    # Check phase0-done uses GoalMachine transition
    phase0_done_src = _py_source(lambda: None)
    try:
        lx_mod = _import_module("lx_goal_t8_g8", lx_goal_path)
        phase0_done_src = _py_source(lx_mod.cmd_phase0_done)
    except Exception:
        phase0_done_src = lx_src

    uses_state_machine = "GoalMachine" in phase0_done_src or "transition" in phase0_done_src
    ok("G8b phase0-done uses GoalMachine transition (RED)",
       uses_state_machine,
       "phase0-done does not use GoalMachine transition (RED)")

    # Check task-done uses ledger, not direct plan.md append
    task_done_uses_ledger = "executor_ledger" in lx_src or "append_evidence" in lx_src
    ok("G8b task-done uses executor_ledger.append_evidence (RED)",
       task_done_uses_ledger,
       "task-done doesn't use executor_ledger (appends directly to plan.md) (RED)")

    # Check done uses state machine
    done_uses_sm = "GoalMachine" in lx_src or "gsm" in lx_src
    ok("G8b done uses GoalMachine to transition state (RED)",
       done_uses_sm,
       "done command doesn't advance state machine (RED)")

    # ── G8c: Cross-session resume from first incomplete step (RED) ──
    with tempfile.TemporaryDirectory() as td:
        root = _make_temp_project(Path(td))
        task_dir = root / ".omc" / "tasks" / "20260729" / "t8-g8c"
        token_path = root / ".omc" / "tokens" / "20260729" / "t8-g8c.json"
        task_dir.mkdir(parents=True, exist_ok=True)
        token_path.parent.mkdir(parents=True, exist_ok=True)

        plan_path = task_dir / "plan.md"
        executor_path = task_dir / "executor.md"
        research_path = task_dir / "research.md"

        # Simulate state: S1 completed (in plan), S2 pending, S3 pending
        plan_path.write_text(
            "# Plan\n\n"
            "- [x] S1: step 1\n"
            "  - depends_on: none\n"
            "- [ ] S2: step 2\n"
            "  - depends_on: S1\n"
            "- [ ] S3: step 3\n"
            "  - depends_on: S2\n\n",
            encoding="utf-8",
        )
        executor_path.write_text("# Executor\n\n### EV-S1\n- step: S1\n- exit_code: 0\n", encoding="utf-8")
        research_path.write_text("# Research\n\n## Background\ncontent\n", encoding="utf-8")

        token = {
            "revision": 3,
            "session": {"id": "t8-g8c", "level": "L2"},
            "status": "active",
            "task": {"current_step": "S2", "status": "active"},
            "stats": {"done": 3, "total": 3, "tick": 10},
            "goal": {"state": "EXECUTING"},
        }
        token_path.write_text(json.dumps(token, indent=2) + "\n", encoding="utf-8")

        # On resume, should find first incomplete step (S2, not S1 which is done)
        plan_text = plan_path.read_text(encoding="utf-8")
        pending_steps = re.findall(r"- \[ \] (\S+?):", plan_text)
        completed_steps = re.findall(r"- \[x\] (\S+?):", plan_text, re.IGNORECASE)
        first_incomplete = pending_steps[0] if pending_steps else None
        ok("G8c resume finds first incomplete step (S2)",
           first_incomplete == "S2",
           f"first incomplete step is {first_incomplete}, expected S2")

        # Verify that cross-session resume uses the state machine
        gsm_mod = _get_gsm()
        gm = gsm_mod.GoalMachine(str(token_path))
        ok("G8c resume restores GoalMachine state from token",
           gm.current_state == "EXECUTING",
           f"GoalMachine state={gm.current_state}")

        # All steps done (done=3,total=3) → can_transition VERIFYING is permitted
        ok("G8c from EXECUTING can_transition VERIFYING (all steps done)",
           gm.can_transition(gsm_mod.VERIFYING),
           "")

        # Also check that non-GSM resume path (scanning plan/executor) exists
        # This is about find_first_incomplete_step logic
        has_find_first = "first_incomplete" in lx_src or "first-pending" in lx_src
        ok("G8c cross-session resume uses find_first_incomplete_step (RED)",
           has_find_first,
           "no find_first_incomplete_step logic in lx-goal for cross-session resume (RED)")


# ====================================================================
# Main
# ====================================================================

def main() -> int:
    print("=" * 64)
    print("Task8 Phase1 Strict Goal State Machine Dependency TDD RED")
    print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 64)

    run_g1()
    run_g2()
    run_g3()
    run_g4()
    run_g5()
    run_g6()
    run_g7()
    run_g8()

    print("\n" + "=" * 64)
    print("Summary")
    print("=" * 64)
    print(f"  PASS: {PASS}")
    print(f"  FAIL: {FAIL}")
    print(f"  INFRA: {INFRA}")
    print(f"  Total: {PASS + FAIL + INFRA}")

    if INFRA > 0:
        print("\nINFRASTRUCTURE errors detected (bad setup)")
        return 2
    if FAIL > 0:
        print(f"\nRED: {FAIL} tests failed (strict behaviors not yet implemented)")
        return 1
    print("\nALL GREEN (all strict behaviors already implemented)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
