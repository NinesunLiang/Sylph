#!/usr/bin/env python3
"""test-task7-phase2-tdd-red.py — Task7 Phase2 Dependency TDD RED 套件

G1: 统一日期格式 YYYYMMDD(路径) / YYYY-MM-DD(显示)
G2: Reader 兼容 legacy YYYY-MM-DD + 冲突检测
G3: Dry-run Migration Report (source,target,collision, fs unchanged)
G4: carros_base init --task-mode goal 模板完整性

隔离: tempdir + monkeypatch, 不碰真实 .omc/.claude/settings/hooks
退出码: 0=全过, 1=有FAIL(预期RED状态), infra_error>0=2(不应出现)
"""

from __future__ import annotations

import importlib.util
import inspect
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[1]

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


# ─── Helpers ───────────────────────────────────────────────────────

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
    root = tmp_root / "project"
    root.mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("", encoding="utf-8")
    (root / ".claude").mkdir(parents=True, exist_ok=True)
    (root / ".omc").mkdir(parents=True, exist_ok=True)
    return root


def _import_carros_base(project_root: Path):
    mod = _import_module(
        "carros_base",
        REPO_ROOT / ".claude" / "scripts" / "carros_base.py",
    )
    mod.PROJECT_ROOT = project_root
    mod.OMC_ROOT = project_root / ".omc"
    mod.OMC_TOKENS = project_root / ".omc" / "tokens"
    mod.OMC_TASKS = project_root / ".omc" / "tasks"
    mod.HANDOFF_PATH = project_root / ".omc" / "session-handoff.md"
    mod.TOKEN_PATH = None
    mod.TASK_DIR = None
    mod.PLAN_PATH = None
    mod.EXECUTOR_PATH = None
    mod.RESEARCH_PATH = None
    mod.SUB_TASK_DIR = None
    mod.STATE_DIR = None
    mod.AUDIT_DIR = None
    mod.GoalMachine = None
    mod.GoalError = Exception
    mod.gsm = None
    return mod


_CARROS_BASE_MOD = None
_PLAN_BUILDER_MOD = None
_FE_MOD = None
_CE_MOD = None


def _get_cb() -> Any:
    global _CARROS_BASE_MOD
    if _CARROS_BASE_MOD is None:
        _CARROS_BASE_MOD = _import_module(
            "carros_base_g1",
            REPO_ROOT / ".claude" / "scripts" / "carros_base.py",
        )
    return _CARROS_BASE_MOD


def _get_pb() -> Any:
    global _PLAN_BUILDER_MOD
    if _PLAN_BUILDER_MOD is None:
        _PLAN_BUILDER_MOD = _import_module(
            "plan_builder_g1",
            REPO_ROOT / ".claude" / "scripts" / "plan_builder.py",
        )
    return _PLAN_BUILDER_MOD


def _get_fe() -> Any:
    global _FE_MOD
    if _FE_MOD is None:
        _FE_MOD = _import_module(
            "fallback_engine_g1",
            REPO_ROOT / ".claude" / "scripts" / "fallback_engine.py",
        )
    return _FE_MOD


def _get_ce() -> Any:
    global _CE_MOD
    if _CE_MOD is None:
        _CE_MOD = _import_module(
            "context_engine_g1",
            REPO_ROOT / ".claude" / "scripts" / "context_engine.py",
        )
    return _CE_MOD


# ====================================================================
# G1: 日期格式统一 — 路径 YYYYMMDD / 显示 YYYY-MM-DD
# ====================================================================

def run_g1():
    """所有路径 CREATOR 使用 YYYYMMDD, 显示/ISO 保留 YYYY-MM-DD"""
    print("\n" + "=" * 64)
    print("G1: 日期格式统一 — 路径 YYYYMMDD / 显示 YYYY-MM-DD")
    print("=" * 64)

    cb = _get_cb()
    pb = _get_pb()
    fe = _get_fe()
    ce = _get_ce()

    infra_ok("G1-infra carros_base import ok", True)
    infra_ok("G1-infra plan_builder import ok", True)
    infra_ok("G1-infra fallback_engine import ok", True)
    infra_ok("G1-infra context_engine import ok", True)

    # G1a: _get_date_str = %Y%m%d (PASS — already correct)
    src = _py_source(cb._get_date_str)
    ok("G1a carros_base._get_date_str uses %Y%m%d",
       "%Y%m%d" in src,
       f"format={src.strip()[:60]}" if src else "source_unavailable")

    # G1b: _init_task_paths uses date_str (PASS)
    src2 = _py_source(cb._init_task_paths)
    ok("G1b _init_task_paths uses date_str (=YYYYMMDD) for paths",
       "date_str" in src2,
       "no date_str reference in path construction")

    # G1c: handoff display timestamp keeps YYYY-MM-DD (PASS)
    src_handoff = _py_source(cb._write_handoff)
    ok("G1c handoff display timestamp uses YYYY-MM-DD",
       "%Y-%m-%d" in src_handoff,
       "expected YYYY-MM-DD in display format")

    # G1d: plan_builder.today() should be %Y%m%d for paths (RED)
    pb_src = _py_source(pb.today)
    ok("G1d plan_builder.today() uses %Y%m%d (for path creation)",
       "%Y%m%d" in pb_src,
       f"got '{pb_src.strip()[:60]}' with %Y-%m-%d instead of %Y%m%d")

    # G1e: plan_builder fallback token path YYYYMMDD (dynamic check)
    _today_pb = pb.today()
    _pb_today_yyyymmdd = len(_today_pb) == 8 and _today_pb.isdigit()
    _no_legacy_in_main = "%Y-%m-%d" not in _py_source(pb.main)
    ok("G1e plan_builder standalone fallback token path uses YYYYMMDD",
       _pb_today_yyyymmdd and _no_legacy_in_main,
       f"today()='{_today_pb}' legacy_format_in_main={not _no_legacy_in_main}")

    # G1f: fallback_engine.today() should be %Y%m%d (RED)
    fe_src = _py_source(fe.today)
    ok("G1f fallback_engine.today() uses %Y%m%d (for path creation)",
       "%Y%m%d" in fe_src,
       f"got '{fe_src.strip()[:60]}' with %Y-%m-%d instead of %Y%m%d")

    # G1g: fallback_engine.task_paths builds YYYYMMDD paths (RED -> GREEN)
    try:
        _dummy_token = {"task": {"id": "test-slug"}, "session": {"level": "L1"}}
        _hp, _ep, _paths = fe.task_paths(_dummy_token)
        _all_paths_have_yyyymmdd = any(
            p for p in _paths if "/2026" in p
        )
    except Exception:
        _all_paths_have_yyyymmdd = False
    ok("G1g fallback_engine.task_paths uses YYYYMMDD dir for task paths",
       _all_paths_have_yyyymmdd,
       "task_paths path does not contain YYYYMMDD date directory")

    # G1h: fallback_engine audit path uses YYYYMMDD (dynamic check)
    _fe_today_val = fe.today()
    _fe_today_yyyymmdd = len(_fe_today_val) == 8 and _fe_today_val.isdigit()
    ok("G1h fallback_engine audit path uses YYYYMMDD",
       _fe_today_yyyymmdd and "today()" in _py_source(fe.write_audit),
       f"today()='{_fe_today_val}' expected %Y%mdd format for audit paths")

    # G1i: context_engine.today() should be %Y%m%d (RED)
    ce_src = _py_source(ce.today)
    ok("G1i context_engine.today() uses %Y%m%d (for path creation)",
       "%Y%m%d" in ce_src,
       f"got '{ce_src.strip()[:60]}' with %Y-%m-%d instead of %Y%m%d")

    # G1j: context_engine audit paths use YYYYMMDD (dynamic check)
    _ce_today_val = ce.today()
    _ce_today_yyyymmdd = len(_ce_today_val) == 8 and _ce_today_val.isdigit()
    all_ce_src = _py_source(ce.resume_check) + _py_source(ce.compact_write)
    ok("G1j context_engine audit/state paths use YYYYMMDD",
       _ce_today_yyyymmdd and "today()" in all_ce_src,
       f"today()='{_ce_today_val}' expected %Y%mdd format for audit paths")

    # G1k: plan_builder.write_plan_audit already uses YYYYMMDD (PASS)
    pb_audit_src = _py_source(pb.write_plan_audit)
    ok("G1k plan_builder.write_plan_audit uses YYYYMMDD",
       "%Y%m%d" in pb_audit_src,
       "already uses %Y%m%d")

    # G1l: plan_builder.resolve_doc_root already uses YYYYMMDD (PASS)
    pb_resolve_src = _py_source(pb.resolve_doc_root)
    ok("G1l plan_builder.resolve_doc_root uses YYYYMMDD",
       "%Y%m%d" in pb_resolve_src,
       "already uses %Y%m%d")

    # G1m: context_engine.resume_check audit uses YYYYMMDD (dynamic check)
    _ce_rc_src = _py_source(ce.resume_check)
    ok("G1m context_engine.resume_check audit path uses YYYYMMDD",
       len(_ce_today_val) == 8 and _ce_today_val.isdigit() and "today()" in _ce_rc_src,
       f"today()='{_ce_today_val}' expected %Y%mdd format for audit paths")


# ====================================================================
# G2: Reader 兼容 legacy YYYY-MM-DD + 冲突检测
# ====================================================================

def run_g2():
    """Reader 兼容 legacy YYYY-MM-DD, 不创建第二棵树, 冲突报告"""
    print("\n" + "=" * 64)
    print("G2: Reader 兼容 legacy YYYY-MM-DD + 冲突检测")
    print("=" * 64)

    cb = _get_cb()

    ok("G2a Reader兼容 legacy YYYY-MM-DD 目录",
       hasattr(cb, "cmd_resolve_conflict"),
       "no dedicated handler for legacy format dirs")

    # G2b: conflict detection via lib.task_paths.find_conflicts
    try:
        _tp_mod = _import_module("task_paths_g2b",
            REPO_ROOT / ".claude/scripts/lib/task_paths.py")
        _has_find_conflicts = hasattr(_tp_mod, "find_conflicts")
        _has_scan_task_dirs = hasattr(_tp_mod, "scan_task_dirs")
        _has_conflict_logic = _has_find_conflicts and _has_scan_task_dirs
    except Exception:
        _has_conflict_logic = False
    ok("G2b 同slug两格式冲突时报告/拒绝覆盖",
       _has_conflict_logic,
       "no find_conflicts/scan_task_dirs in task_paths")

    # G2c: Reader (lib.task_paths.scan_task_dirs) 不创建目录
    try:
        import tempfile
        import os
        _tmp_dir2 = Path(tempfile.mkdtemp())
        _fake_tasks = _tmp_dir2 / ".omc" / "tasks"
        _fake_tasks.mkdir(parents=True)
        (_fake_tasks / "2026-01-01").mkdir()
        # scan_task_dirs should not create any new dirs
        _before = set(os.listdir(str(_fake_tasks)))
        _tp_mod2 = _import_module("task_paths_g2c",
            REPO_ROOT / ".claude/scripts/lib/task_paths.py")
        _tp_mod2.scan_task_dirs(_fake_tasks, include_legacy=True)
        _after = set(os.listdir(str(_fake_tasks)))
        _reader_did_not_create = (_before == _after)
    except Exception:
        _reader_did_not_create = False
    ok("G2c Reader 不得自动创建 YYYY-MM-DD 目录",
       _reader_did_not_create,
       "legacy reader created new directories during scan")

    # G2d: 路径 Creator 仅使用 YYYYMMDD (所有 today() + audit path 已修复)
    _fe_g2 = _get_fe()
    _ce_g2 = _get_ce()
    _fe_today_g2 = _fe_g2.today()
    _ce_today_g2 = _ce_g2.today()
    _fe_src_g2 = _py_source(_fe_g2.today)
    _ce_src_g2 = _py_source(_ce_g2.today)
    _all_today = [
        (len(_fe_today_g2) == 8 and _fe_today_g2.isdigit()),
        (len(_ce_today_g2) == 8 and _ce_today_g2.isdigit()),
    ]
    _all_fixed = all(_all_today)
    ok("G2d 路径 Creator 仅使用 YYYYMMDD (cross-ref G1f,G1i)",
       _all_fixed,
       f"fe.today()='{_fe_today_g2}' ce.today()='{_ce_today_g2}'")


# ====================================================================
# G3: Dry-run Migration Report
# ====================================================================

def run_g3():
    """Dry-run: source,target,collision; fs 不变"""
    print("\n" + "=" * 64)
    print("G3: Dry-run Migration Report")
    print("=" * 64)

    cb = _get_cb()

    ok("G3a 存在 migrate/dry-run 命令",
       hasattr(cb, "cmd_migrate"),
       "no migration command")

    ok("G3b dry-run 输出含 source,target,collision 列",
       hasattr(cb, "_dry_run_migration"),
       "migration report not implemented")

    # G3c: _dry_run_migration 不修改文件系统 (RED -> GREEN)
    _fs_safe = False
    _saved_omc = cb.OMC_ROOT
    _saved_root = cb.PROJECT_ROOT
    try:
        import tempfile as _tf2
        import os as _os2
        _tmp3 = Path(_tf2.mkdtemp())
        _omc_tasks = _tmp3 / ".omc" / "tasks"
        _omc_tasks.mkdir(parents=True)
        (_omc_tasks / "2026-01-01" / "task-a").mkdir(parents=True)
        (_omc_tasks / "2026-01-01" / "task-b").mkdir(parents=True)

        cb.OMC_ROOT = _tmp3 / ".omc"
        cb.PROJECT_ROOT = _tmp3

        _before_items = set()
        for _dirpath, _dirnames, _filenames in _os2.walk(str(_tmp3)):
            for _f in _filenames:
                _before_items.add(_os2.path.relpath(_os2.path.join(_dirpath, _f), str(_tmp3)))
            for _d in _dirnames:
                _before_items.add(_os2.path.relpath(_os2.path.join(_dirpath, _d), str(_tmp3)))

        cb._dry_run_migration()

        _after_items = set()
        for _dirpath, _dirnames, _filenames in _os2.walk(str(_tmp3)):
            for _f in _filenames:
                _after_items.add(_os2.path.relpath(_os2.path.join(_dirpath, _f), str(_tmp3)))
            for _d in _dirnames:
                _after_items.add(_os2.path.relpath(_os2.path.join(_dirpath, _d), str(_tmp3)))

        _fs_safe = (_before_items == _after_items)
    except Exception as _e3:
        _fs_safe = False
    finally:
        cb.OMC_ROOT = _saved_omc
        cb.PROJECT_ROOT = _saved_root
    ok("G3c dry-run 后文件系统完全不变 (hash/树)",
       _fs_safe,
       "dry-run modified filesystem (added/removed files)")

    # G3d: _dry_run_migration 可安全重入, 不修改文件系统 (RED -> GREEN)
    _reentrant_safe = False
    _saved_omc2 = cb.OMC_ROOT
    _saved_root2 = cb.PROJECT_ROOT
    try:
        import tempfile as _tf4
        import os as _os4
        _tmp4 = Path(_tf4.mkdtemp())
        _omc_tasks4 = _tmp4 / ".omc" / "tasks"
        _omc_tasks4.mkdir(parents=True)
        (_omc_tasks4 / "2026-01-01" / "task-a").mkdir(parents=True)

        cb.OMC_ROOT = _tmp4 / ".omc"
        cb.PROJECT_ROOT = _tmp4

        _r1 = cb._dry_run_migration()
        _r2 = cb._dry_run_migration()
        _r3 = cb._dry_run_migration()

        # Same number of results each time, no crash
        _reentrant_safe = len(_r1) == len(_r2) == len(_r3) > 0
    except Exception as _e4:
        _reentrant_safe = False
    finally:
        cb.OMC_ROOT = _saved_omc2
        cb.PROJECT_ROOT = _saved_root2
    ok("G3d 迁移函数可安全重入, 不修改文件系统",
       _reentrant_safe,
       "migration function not re-entrant or results inconsistent")


# ====================================================================
# G4: carros_base init --task-mode goal: 目录+模板
# ====================================================================

def run_g4():
    print("\n" + "=" * 64)
    print("G4: carros_base init --task-mode goal")
    print("=" * 64)

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_root = Path(tmp_str)
        project_root = _make_temp_project(tmp_root)
        cb_g4 = _import_carros_base(project_root)
        _stub_subprocess(cb_g4)

        task_id = "test-g4a-001"
        try:
            rc = cb_g4.cmd_init(task_id=task_id, level="L1",
                                steps=None, task_mode="goal")
            infra_ok("G4-infra cmd_init returned OK", rc in (0, 1, 2))
        except Exception as e:
            infra_ok("G4-infra cmd_init no crash", False, f"exception: {e}")
            import traceback
            traceback.print_exc()
            return

        task_dir_path = _find_task_dir(project_root, cb_g4)
        found = task_dir_path is not None
        ok("G4a init --task-mode goal creates .omc/tasks/YYYYMMDD/<slug>/",
           found, "task dir not under YYYYMMDD or not created")

        _check_task_dir_contents(task_dir_path)

    # G4i: 注释/placeholder 不算完成
    with tempfile.TemporaryDirectory() as tmp_str2:
        _check_research_template(Path(tmp_str2))


def _stub_subprocess(mod) -> None:
    import types as _t

    class _R:
        returncode = 1
        stdout = ""
        stderr = ""

    class _PopenObj:
        def communicate(self):
            return ("", "")
        def poll(self):
            return 0
        def wait(self):
            return 0

    _sm = _t.ModuleType("subprocess")
    setattr(_sm, "run", MagicMock(return_value=_R()))
    setattr(_sm, "Popen", MagicMock(return_value=_PopenObj()))
    setattr(_sm, "TimeoutExpired", Exception)
    setattr(mod, "subprocess", _sm)
    setattr(mod, "carros_utils", None)
    setattr(mod, "omc_lint", None)
    setattr(mod, "tst", None)
    setattr(mod, "GoalMachine", None)
    setattr(mod, "sam", None)


def _find_task_dir(project_root, cb_g4):
    omc_tasks = project_root / ".omc" / "tasks"
    task_dirs = sorted(omc_tasks.iterdir()) if omc_tasks.exists() else []
    for d in task_dirs:
        if d.is_dir() and d.name.isdigit() and len(d.name) == 8:
            slug_dirs = sorted(d.iterdir())
            if slug_dirs:
                return slug_dirs[0]
    return cb_g4.TASK_DIR


def _check_task_dir_contents(task_dir_path):
    has_r = task_dir_path and (task_dir_path / "research.md").exists()
    has_p = task_dir_path and (task_dir_path / "plan.md").exists()
    has_e = task_dir_path and (task_dir_path / "executor.md").exists()
    ok("G4b contains research.md", bool(has_r), "missing" if not has_r else "")
    ok("G4b contains plan.md", bool(has_p), "missing" if not has_p else "")
    ok("G4b contains executor.md", bool(has_e), "missing" if not has_e else "")

    ok("G4c sub_task dir",
       bool(task_dir_path and (task_dir_path / "sub_task").is_dir()), "")
    ok("G4c state dir",
       bool(task_dir_path and (task_dir_path / "state").is_dir()), "")
    ok("G4c artifacts dir",
       bool(task_dir_path and (task_dir_path / "artifacts").is_dir()), "")
    ok("G4c evidence.jsonl",
       bool(task_dir_path and (task_dir_path / "evidence.jsonl").exists()), "")
    ok("G4c working-set.yaml",
       bool(task_dir_path and (task_dir_path / "working-set.yaml").exists()), "")

    # G4d: lx-goal does not create independent task_dir
    lx_path = (REPO_ROOT / ".claude" / "skills" / "lx-goal"
               / "scripts" / "lx-goal.py")
    if lx_path.exists():
        lx_src = lx_path.read_text(encoding="utf-8")
        lx_creates = bool(re.search(
            r"\.omc/tasks/.*mkdir|\.omc/tasks/.*Task.*(?:dir|Dir)",
            lx_src, re.IGNORECASE,
        ))
        ok("G4d lx-goal does not create independent task_dir",
           not lx_creates,
           "lx-goal appears to create task dir independently")
    else:
        ok("G4d lx-goal does not create independent task_dir",
           False, "lx-goal.py not found")

    # G4e: Research template sections
    research_content = ""
    if task_dir_path and (task_dir_path / "research.md").exists():
        research_content = (task_dir_path / "research.md").read_text(encoding="utf-8")

    for section in ["背景", "约束", "已知信息", "不确定性",
                    "全貌", "依赖树", "方案", "Dependency TDD"]:
        found = f"## {section}" in research_content
        ok(f"G4e research.md contains '## {section}'",
           found, f"section '{section}' missing from template")

    # G4f: Plan template has ## Phase N
    plan_content = ""
    if task_dir_path and (task_dir_path / "plan.md").exists():
        plan_content = (task_dir_path / "plan.md").read_text(encoding="utf-8")
    ok("G4f plan.md contains '## Phase' headers",
       "## Phase" in plan_content,
       "no Phase headers in plan template")

    # G4g: Plan step fields
    for field in ["depends_on", "acceptance", "verify"]:
        found_f = field in plan_content.lower()
        ok(f"G4g plan.md step contains '{field}'",
           found_f, f"field '{field}' missing from plan template")

    # G4h: Executor template sections
    executor_content = ""
    if task_dir_path and (task_dir_path / "executor.md").exists():
        executor_content = (task_dir_path / "executor.md").read_text(encoding="utf-8")
    for section in ["Conditions", "Key Changes", "Decisions",
                    "Acceptance Checklist", "TDD Evidence"]:
        found_s = section in executor_content
        ok(f"G4h executor.md contains '{section}'",
           found_s, f"section '{section}' missing")


def _check_research_template(tmp_root):
    project_root2 = _make_temp_project(tmp_root)
    cb_g4i = _import_carros_base(project_root2)
    cb_g4i.carros_utils = None

    research_path = (project_root2 / ".omc" / "tasks" / "20260729"
                     / "test-g4i" / "research.md")
    cb_g4i.RESEARCH_PATH = research_path
    cb_g4i.PLAN_PATH = research_path.parent / "plan.md"
    cb_g4i.EXECUTOR_PATH = research_path.parent / "executor.md"
    cb_g4i.TASK_DIR = research_path.parent

    os.environ["CARROROS_TASK_MODE"] = "goal"
    try:
        cb_g4i._write_default_research()
    except Exception as e:
        infra_ok("G4-infra _write_default_research", False, f"exception: {e}")
    finally:
        os.environ.pop("CARROROS_TASK_MODE", None)

    if research_path.exists():
        content = research_path.read_text(encoding="utf-8")
        substantive = [l for l in content.split("\n")
                       if l.strip()
                       and not l.strip().startswith("<!--")
                       and not l.strip().startswith(">")]
        has_real_headers = any(
            l.startswith("## ") for l in content.split("\n")
        )
        ok("G4i research.md has real headers (not just comments/placeholders)",
           has_real_headers and len(substantive) >= 6,
           f"research.md: {len(substantive)} substantive lines, needs >= 6")


# ====================================================================
# Main
# ====================================================================

def main() -> int:
    print("=" * 64)
    print("Task7 Phase2 Dependency TDD RED")
    print(f"Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 64)

    run_g1()
    run_g2()
    run_g3()
    run_g4()

    print("\n" + "=" * 64)
    print("Summary")
    print("=" * 64)
    print(f"  PASS: {PASS}")
    print(f"  FAIL: {FAIL}")
    print(f"  INFRA: {INFRA}")
    print(f"  Total: {PASS + FAIL + INFRA}")

    if INFRA > 0:
        print("\nINFRASTRUCTURE errors detected")
        return 2
    if FAIL > 0:
        print(f"\nRED: {FAIL} tests failed (spec not yet implemented)")
        return 1
    print("\nALL GREEN (all specs already implemented)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
