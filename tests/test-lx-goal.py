#!/usr/bin/env python3
"""
Unit tests for lx-goal.py — goal mode orchestrator.

Covers:
  1. Module importable without error
  2. is_mode_active() returns bool under various states
  3. _sanitize() strips control characters and surrogate pairs
  4. KNOWN_SUBCOMMANDS contains expected command names
  5. _usage() output format
  6. cmd_is_active() exit codes
"""

import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest


# ── Fixture helpers ──────────────────────────────────────────────

def _fake_project_root(tmp_path: Path) -> Path:
    """Create a minimal fake project root with .omc/state/tokens dir."""
    root = tmp_path / "fake_project"
    tokens_dir = root / ".omc" / "state" / "tokens"
    tokens_dir.mkdir(parents=True, exist_ok=True)
    # Touch AGENTS.md so _find_project_root resolves here
    (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    return root


def _import_goal(project_root: Path):
    """Import lx-goal.py as a module under a fake project root.

    Uses sys.path manipulation and patching of _find_project_root
    so all path-dependent constants resolve under project_root.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "lx_goal",
        str(Path(__file__).resolve().parent.parent
            / ".claude" / "skills" / "lx-goal" / "scripts" / "lx-goal.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Override path constants after import
    mod.PROJECT_ROOT = project_root
    mod.STATE_DIR = project_root / ".omc" / "state"
    mod.TASKS_DIR = project_root / ".omc" / "tasks"
    mod.TOKENS_DIR = project_root / ".omc" / "tokens"
    mod.PLANS_DIR = mod.TASKS_DIR
    mod.MODE_FILE = mod.STATE_DIR / "tokens" / "lx-goal.json"
    mod.AUTONOMOUS_SIGNAL = mod.STATE_DIR / "tokens" / "autonomous.active"
    # Disable lifecycle SSOT for isolated testing
    mod._lc_set_mode = None
    return mod


# ── Test 1: Module importable ────────────────────────────────────

def test_module_importable(tmp_path):
    """Verify the module can be imported without syntax or runtime errors."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    assert hasattr(mod, "main")
    assert hasattr(mod, "is_mode_active")
    assert hasattr(mod, "_sanitize")


# ── Test 2: is_mode_active() returns bool ────────────────────────

def test_is_mode_active_returns_bool(tmp_path):
    """is_mode_active always returns bool, never None or str."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    result = mod.is_mode_active()
    assert isinstance(result, bool), f"Expected bool, got {type(result)}"


def test_is_mode_active_false_no_signal(tmp_path):
    """Returns False when autonomous.active signal file does not exist."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    assert mod.is_mode_active() is False


def test_is_mode_active_false_no_modefile(tmp_path):
    """Returns False when signal exists but mode file does not."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    mod.AUTONOMOUS_SIGNAL.touch()
    assert mod.is_mode_active() is False


def test_is_mode_active_false_inactive(tmp_path):
    """Returns False when mode file has active=False."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    mod.AUTONOMOUS_SIGNAL.touch()
    mode_data = {"active": False, "expires_at": None}
    mod.MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    mod.MODE_FILE.write_text(json.dumps(mode_data), encoding="utf-8")
    assert mod.is_mode_active() is False


def test_is_mode_active_true(tmp_path):
    """Returns True when signal + active + not expired."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    mod.AUTONOMOUS_SIGNAL.touch()
    expires = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
    mode_data = {"active": True, "expires_at": expires}
    mod.MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    mod.MODE_FILE.write_text(json.dumps(mode_data), encoding="utf-8")
    assert mod.is_mode_active() is True


def test_is_mode_active_false_expired(tmp_path):
    """Returns False when mode file has expired timestamp."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    mod.AUTONOMOUS_SIGNAL.touch()
    expires = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    mode_data = {"active": True, "expires_at": expires}
    mod.MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    mod.MODE_FILE.write_text(json.dumps(mode_data), encoding="utf-8")
    assert mod.is_mode_active() is False


def test_is_mode_active_false_corrupt_modefile(tmp_path):
    """Returns False when mode file is not valid JSON."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    mod.AUTONOMOUS_SIGNAL.touch()
    mod.MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    mod.MODE_FILE.write_text("{invalid json}", encoding="utf-8")
    assert mod.is_mode_active() is False


# ── Test 3: _sanitize() removes control chars ────────────────────

def test_sanitize_passes_normal_text(tmp_path):
    """Normal ASCII text passes through unchanged."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    text = "Hello, world! This is normal text 123."
    assert mod._sanitize(text) == text


def test_sanitize_removes_surrogate_pairs(tmp_path):
    """Surrogate code points (0xD800-0xDFFF) are removed.

    Construct surrogates via chr() since Python str cannot contain
    lone surrogates in literal form.
    """
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    # Lone surrogate at D800
    surrogates = chr(0xD800) + "Hello" + chr(0xDFFF)
    result = mod._sanitize(surrogates)
    assert "\ud800" not in result
    assert "\udfff" not in result
    assert result == "Hello"


def test_sanitize_removes_control_chars(tmp_path):
    """Control characters below 0x20 (except \\n \\t \\r) are removed."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    text = "\x00\x01\x02\x07\x1bHello\n\t\rWorld\x00\x1a"
    result = mod._sanitize(text)
    assert "\x00" not in result
    assert "\x01" not in result
    assert "\x07" not in result
    assert "\x1b" not in result
    assert "\x1a" not in result
    assert result == "Hello\n\t\rWorld"


def test_sanitize_preserves_newline_tab_cr(tmp_path):
    """Newline, tab, and carriage return are preserved."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    text = "line1\nline2\tcol\rmore"
    assert mod._sanitize(text) == text


def test_sanitize_handles_empty_string(tmp_path):
    """Empty string returns empty string."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    assert mod._sanitize("") == ""


def test_sanitize_unicode_passthrough(tmp_path):
    """Valid Unicode (CJK, emoji) passes through."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    text = "你好世界 \U0001f30d\U0001f680 日本語"
    result = mod._sanitize(text)
    assert result == text


# ── Test 4: KNOWN_SUBCOMMANDS has expected commands ──────────────

def test_known_subcommands_keys(tmp_path):
    """KNOWN_SUBCOMMANDS contains all expected command names."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    expected = {
        "on", "off", "status", "set", "phase0-done", "report",
        "poll", "is-active", "task-done", "verify-step", "skip-risk",
        "hard-boundary-hit", "blocked-human", "retry",
        "subagent-log", "done", "_update-lock",
        "assert-plan-dir", "checklist-verify",
    }
    assert expected == set(mod.KNOWN_SUBCOMMANDS)


def test_known_subcommands_all_callable(tmp_path):
    """Every entry in KNOWN_SUBCOMMANDS is a callable function."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    for name, func in mod.KNOWN_SUBCOMMANDS.items():
        assert callable(func), f"{name} is not callable"


def test_known_subcommands_has_no_unexpected(tmp_path):
    """Only the registered commands are exposed."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    assert len(mod.KNOWN_SUBCOMMANDS) == 19


# ── Test 5: Usage output format ──────────────────────────────────

def test_usage_format(tmp_path):
    """_usage() returns a string with expected sections."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    usage = mod._usage()
    assert isinstance(usage, str)
    assert usage.startswith("用法: lx-goal.py")
    assert "子命令:" in usage
    assert "on" in usage
    assert "off" in usage
    assert "status" in usage
    assert "report" in usage
    assert "_update-lock" not in usage


# ── Test 6: cmd_is_active exit codes ─────────────────────────────

def test_cmd_is_active_returns_int(tmp_path):
    """cmd_is_active returns 0 or 1 (int), not None or str."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    rc = mod.cmd_is_active()
    assert rc in (0, 1)


def test_cmd_is_active_exit_1_when_inactive(tmp_path):
    """Returns 1 when goal mode is not active."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    assert mod.cmd_is_active() == 1


def test_cmd_is_active_exit_0_when_active(tmp_path, capsys):
    """Returns 0 when goal mode is active, prints confirmation."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    mod.AUTONOMOUS_SIGNAL.touch()
    expires = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
    mode_data = {"active": True, "expires_at": expires}
    mod.MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    mod.MODE_FILE.write_text(json.dumps(mode_data), encoding="utf-8")
    rc = mod.cmd_is_active()
    assert rc == 0
    captured = capsys.readouterr()
    assert "goal 模式激活中" in captured.out


def test_cmd_is_active_inactive_message(tmp_path, capsys):
    """Prints '未激活' when not active."""
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    rc = mod.cmd_is_active()
    assert rc == 1
    captured = capsys.readouterr()
    assert "未激活" in captured.out


# ── Goal lifecycle behavior contracts ───────────────────────────

def _valid_research() -> str:
    return (
        "# Research\n\n"
        "## 背景\nReal background.\n\n"
        "## 约束\nReal constraints.\n\n"
        "## 已知信息\nReal facts.\n\n"
        "## 不确定性\nReal uncertainty.\n\n"
        "## 全貌\nReal overview.\n\n"
        "## 依赖树\n- Foundation before integration.\n\n"
        "## 方案\nImplement serially.\n\n"
        "## Dependency TDD\nTest dependencies first.\n"
    )


def _valid_plan() -> str:
    return (
        "# Plan\n\n## Phase 1\n"
        "- [ ] S1: implement\n"
        "  - status: pending\n"
        "  - depends_on: none\n"
        "  - scope: src/main.py\n"
        "  - acceptance: behavior passes\n"
        "  - verify: command:pytest tests/\n"
    )


def _write_goal_state(mod, task_dir: Path, token: dict) -> Path:
    date_dir = task_dir.parent.name
    token_path = mod.TOKENS_DIR / date_dir / f"{task_dir.name}.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps(token), encoding="utf-8")
    mode_data = {
        "active": True,
        "goal": "test goal",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
        "rpe_plan_dir": str(task_dir),
        "completed_tasks": [],
        "skipped_risks": [],
        "hard_boundary_hits": [],
        "blocked_human": [],
    }
    mod.MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    mod.MODE_FILE.write_text(json.dumps(mode_data), encoding="utf-8")
    return token_path


def test_cmd_on_merges_goal_fields_into_carros_token(tmp_path):
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    mod._lc_set_mode = MagicMock()
    task_dir = mod.TASKS_DIR / datetime.now().strftime("%Y%m%d") / "demo"
    task_dir.mkdir(parents=True)
    carros_token = mod.TOKENS_DIR / task_dir.parent.name / "demo.json"

    def fake_init(*args, **kwargs):
        carros_token.parent.mkdir(parents=True, exist_ok=True)
        carros_token.write_text(json.dumps({
            "schema_version": "v1.0",
            "revision": 2,
            "session": {"id": "demo", "level": "L2"},
            "task_dir": str(task_dir),
            "status": "active",
            "task": {"current_step": "S1", "status": "active"},
            "stats": {"done": 0, "total": 1},
            "mode": "goal",
        }), encoding="utf-8")
        return MagicMock(returncode=0, stdout=f"CARROROS_TASK_DIR={task_dir}\n", stderr="")

    with patch("subprocess.run", side_effect=fake_init):
        mod.cmd_on("demo", 6)

    token = json.loads(carros_token.read_text(encoding="utf-8"))
    assert token["schema_version"] == "v1.0"
    assert token["session"]["id"] == "demo"
    assert token["status"] == "active"
    assert token["stats"] == {"done": 0, "total": 1}
    assert token["goal"]["state"] == "CLARIFY"
    assert token["goal"]["description"] == "demo"


def test_phase0_done_advances_clarify_to_executing(tmp_path):
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    task_dir = mod.TASKS_DIR / "20990101" / "phase0"
    task_dir.mkdir(parents=True)
    (task_dir / "research.md").write_text(_valid_research(), encoding="utf-8")
    (task_dir / "plan.md").write_text(_valid_plan(), encoding="utf-8")
    (task_dir / "executor.md").write_text("# Executor\n", encoding="utf-8")
    token_path = _write_goal_state(mod, task_dir, {
        "schema_version": "v1.0",
        "revision": 1,
        "session": {"id": "phase0", "level": "L2"},
        "task_dir": str(task_dir),
        "status": "active",
        "task": {"current_step": "S1", "status": "planning"},
        "stats": {"done": 0, "total": 1},
        "goal": {"state": "CLARIFY", "description": "phase0"},
    })

    mod.cmd_phase0_done()

    token = json.loads(token_path.read_text(encoding="utf-8"))
    assert token["goal"]["state"] == "EXECUTING"
    assert token["phase"] == "executing"
    mode = json.loads(mod.MODE_FILE.read_text(encoding="utf-8"))
    assert mode.get("phase0_passed_at")


def test_done_invalid_state_keeps_token_and_fails_closed(tmp_path):
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    task_dir = mod.TASKS_DIR / "20990101" / "not-verified"
    task_dir.mkdir(parents=True)
    (task_dir / "executor.md").write_text(
        "# Executor\n## Acceptance Checklist\n- [x] checked\n",
        encoding="utf-8",
    )
    (task_dir / "plan.md").write_text(_valid_plan(), encoding="utf-8")
    token_path = _write_goal_state(mod, task_dir, {
        "schema_version": "v1.0",
        "revision": 1,
        "session": {"id": "not-verified", "level": "L2"},
        "task_dir": str(task_dir),
        "status": "active",
        "task": {"current_step": "S1", "status": "active"},
        "stats": {"done": 0, "total": 1},
        "goal": {"state": "EXECUTING", "description": "not verified"},
    })

    with pytest.raises(SystemExit) as exc:
        mod.cmd_done()
    assert exc.value.code == 1
    assert token_path.exists(), "failed done must not delete the active token"
    token = json.loads(token_path.read_text(encoding="utf-8"))
    assert token["goal"]["state"] == "EXECUTING"


def test_poll_reports_first_incomplete_step(tmp_path, capsys):
    root = _fake_project_root(tmp_path)
    mod = _import_goal(root)
    task_dir = mod.TASKS_DIR / "20990101" / "resume"
    task_dir.mkdir(parents=True)
    (task_dir / "plan.md").write_text(
        "# Plan\n- [x] S1: done\n- [ ] S2: continue\n",
        encoding="utf-8",
    )
    _write_goal_state(mod, task_dir, {
        "session": {"id": "resume", "level": "L2"},
        "task_dir": str(task_dir),
        "status": "active",
        "task": {"current_step": "S1", "status": "active"},
        "stats": {"done": 1, "total": 2},
        "goal": {"state": "EXECUTING"},
    })

    mod.cmd_poll()
    captured = capsys.readouterr()
    assert "S2" in captured.out
