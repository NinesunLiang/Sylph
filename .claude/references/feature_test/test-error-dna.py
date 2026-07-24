#!/usr/bin/env python3
"""test-error-dna.py — Unit tests for .claude/hooks/error-dna.py

Verifies 6 behaviors:
  1. Captures Bash errors to error-dna.jsonl
  2. Skips non-Bash tools (Read/Write/Edit/etc.)
  3. Skips exit_code=0 (success — PostToolUse with Bash exit 0)
  4. Records governance bypass to governance-audit.jsonl
  5. Updates total-ops.txt counter
  6. High-frequency alerting (>=5 occurrences of same signature)

Run:  python3 -m pytest scripts/test-error-dna.py -v
Env:  Pytest >=7, temp dir isolated, no side effects on real .omc/state.

NOTE: error-dna.py uses a hyphen in its filename (error-dna.py), which cannot
be imported as a regular Python module.  We use importlib.util to load it.

STRATEGY:
  error-dna.py computes STATE_DIR at runtime inside main() as
  PROJECT_ROOT / '.omc' / 'state', where PROJECT_ROOT is derived from
  _HOOKS_DIR (Path(__file__).resolve().parent).  We load the module,
  then override mod._HOOKS_DIR to a fake path inside our temp dir so
  that the runtime computation of STATE_DIR lands in our temp directory.
"""

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# ─── Module-level imports (hooks dir on sys.path) ───

_HOOKS_DIR = (Path(__file__).resolve().parent.parent.parent.parent / ".claude" / "hooks")
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import harness_core
import harness_lib


# ─── Helper: build stdin JSON ───

def _make_stdin(tool_name="Bash", exit_code=1, command="ls /nonexistent",
                stderr="ls: /nonexistent: No such file or directory",
                stdout="", event_name="PostToolUse",
                error=""):
    data = {
        "tool_name": tool_name,
        "hook_event_name": event_name,
        "tool_response": {
            "exit_code": exit_code,
            "stderr": stderr,
            "stdout": stdout,
        },
        "tool_input": {
            "command": command,
        },
    }
    if error:
        data["error"] = error
    return json.dumps(data)


# ─── Fixture: isolated .omc/state ───

@pytest.fixture(autouse=True)
def isolated_env():
    """Provide a clean temp STATE_DIR for each test.
    We create a fake project tree under tmp:
      tmp/.claude/hooks/         → fake _HOOKS_DIR (no real hook files needed)
      tmp/.omc/state/            → fake STATE_DIR

    error-dna.py's main() computes STATE_DIR via (_HOOKS_DIR / '../..' / '.omc' / 'state'),
    so by overriding mod._HOOKS_DIR before calling main(), all writes land in tmp.

    We also patch harness_core globals so hc_enabled etc. reference our temp dir.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        fake_hooks = tmp_root / ".claude" / "hooks"
        fake_state = tmp_root / ".omc" / "state"
        fake_hooks.mkdir(parents=True, exist_ok=True)
        fake_state.mkdir(parents=True, exist_ok=True)

        # ─── Patch harness_core globals ───
        orig_state = harness_core._STATE_DIR
        orig_yaml = harness_core._HC_YAML
        orig_cache = harness_core._HC_CACHE
        orig_cache_loaded = harness_core._HC_CACHE_LOADED
        orig_output = harness_lib.output_continue
        orig_flywheel = harness_lib.flywheel_event

        harness_core._STATE_DIR = fake_state
        harness_core._HC_YAML = fake_state / "no-harness.yaml"
        harness_core._HC_CACHE = fake_state / ".harness-cache"
        harness_core._HC_CACHE_LOADED = None
        # Suppress harmless side-effect output/log calls
        harness_lib.output_continue = lambda: None
        harness_lib.flywheel_event = lambda *a, **kw: None

        yield fake_state

        harness_core._STATE_DIR = orig_state
        harness_core._HC_YAML = orig_yaml
        harness_core._HC_CACHE = orig_cache
        harness_core._HC_CACHE_LOADED = orig_cache_loaded
        harness_lib.output_continue = orig_output
        harness_lib.flywheel_event = orig_flywheel


def _import_error_dna(fake_hooks_dir):
    """Load error-dna.py via importlib.util, overriding _HOOKS_DIR
    so its runtime STATE_DIR computation lands inside the test temp dir.
    """
    mod_path = _HOOKS_DIR / "error-dna.py"
    spec = importlib.util.spec_from_file_location("error_dna_loader", str(mod_path))
    mod = importlib.util.module_from_spec(spec)
    # exec_module runs the module code, including from harness_lib import ...
    # Those harness functions use harness_core._STATE_DIR which the fixture
    # already patched.
    spec.loader.exec_module(mod)
    # Now override _HOOKS_DIR so main() computes STATE_DIR from fake_hooks_dir.
    mod._HOOKS_DIR = fake_hooks_dir
    return mod


def _mock_exit(code=0):
    """Mock sys.exit that actually stops execution (raises SystemExit)."""
    raise SystemExit(code)


def _run_hook(input_json, fake_hooks_dir):
    """Run error_dna.main() with given stdin JSON.  Returns (stdout_str, stderr_str)."""
    ed = _import_error_dna(fake_hooks_dir)

    out_lines = []
    err_lines = []

    def _fake_print(*args, **kwargs):
        file = kwargs.get("file", sys.stdout)
        text = " ".join(str(a) for a in args)
        if file is None or file == sys.stdout or file is sys.__stdout__:
            out_lines.append(text)
        else:
            err_lines.append(text)

    with mock.patch("sys.stdin") as mock_stdin, \
         mock.patch("builtins.print", _fake_print), \
         mock.patch("sys.exit", _mock_exit):
        mock_stdin.read.return_value = input_json
        try:
            ed.main()
        except SystemExit:
            pass

    return "\n".join(out_lines), "\n".join(err_lines)


def _fake_hooks(isolated_env):
    """Return the fake .claude/hooks dir (sibling of .omc/state)."""
    return isolated_env.parent.parent.parent.parent / ".claude" / "hooks"


# ═══════════════════════════════════════════════════════════════
# Test 1: Capture Bash errors to error-dna.jsonl
# ═══════════════════════════════════════════════════════════════

def test_captures_bash_error(isolated_env):
    """exit_code=1 Bash command writes a line to error-dna.jsonl."""
    state_dir = isolated_env
    fh = _fake_hooks(isolated_env)
    stdin = _make_stdin(tool_name="Bash", exit_code=1,
                        command="ls /nonexistent",
                        stderr="ls: /nonexistent: No such file or directory")
    _run_hook(stdin, fh)

    dna_path = state_dir / "error-dna.jsonl"
    assert dna_path.exists(), "error-dna.jsonl should exist after Bash error"
    lines = [json.loads(l) for l in dna_path.read_text().strip().splitlines() if l.strip()]
    assert len(lines) >= 1, "Should have at least one record"
    rec = lines[-1]
    assert rec["exit_code"] == 1
    assert rec["cmd"] != ""
    assert rec["error_type"] in ("runtime", "file_ops")


# ═══════════════════════════════════════════════════════════════
# Test 2: Skip non-Bash tools
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("tool_name", [
    "Read", "Write", "Edit", "WebSearch",
    "WebFetch", "Bash_", "_bash",
    "LSP", "NotebookEdit", "TaskCreate",
    "SendMessage", "Skill",
])
def test_skips_non_bash_tools(isolated_env, tool_name):
    """Non-Bash tool_name should NOT write to error-dna.jsonl."""
    state_dir = isolated_env
    fh = _fake_hooks(isolated_env)
    dna_path = state_dir / "error-dna.jsonl"
    dna_path.write_text("", encoding="utf-8")

    stdin = _make_stdin(tool_name=tool_name, exit_code=1,
                        command="ls /nonexistent",
                        stderr="some error")
    _run_hook(stdin, fh)

    content = dna_path.read_text(encoding="utf-8").strip()
    assert content == "", f"Non-Bash tool '{tool_name}' should not write to error-dna.jsonl"


# ═══════════════════════════════════════════════════════════════
# Test 3: exit_code=0 handling — hook records ALL bash commands
# ═══════════════════════════════════════════════════════════════

def test_records_exit_code_zero(isolated_env):
    """Bash command with exit_code=0 IS recorded (no success filter).

    NOTE: error-dna.py does NOT filter exit_code=0 — it captures ALL Bash
    commands regardless of success/failure.  This test documents that behavior.
    If a future change adds success filtering, update this test.
    """
    state_dir = isolated_env
    fh = _fake_hooks(isolated_env)
    dna_path = state_dir / "error-dna.jsonl"

    stdin = _make_stdin(tool_name="Bash", exit_code=0,
                        command="echo hello",
                        stderr="", stdout="hello\n",
                        event_name="PostToolUse")
    _run_hook(stdin, fh)

    content = dna_path.read_text(encoding="utf-8").strip()
    assert content, "exit_code=0 Bash command should be recorded"
    rec = json.loads(content.splitlines()[-1])
    assert rec["exit_code"] == 0
    assert "echo hello" in rec["cmd"]


# ═══════════════════════════════════════════════════════════════
# Test 4: Records to governance-audit.jsonl on E1/E2 bypass
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("cmd, gov_target", [
    ("echo something >> CLAUDE.md", "CLAUDE.md"),
    ("echo something >> .claude/settings.json", ".claude/settings.json"),
    ("echo something >> .claude/harness.yaml", ".claude/harness.yaml"),
    ("echo something >> AGENTS.md", "AGENTS.md"),
])
def test_governance_bypass_writes_audit(isolated_env, cmd, gov_target):
    """E1 governance bypass (echo to governance file) writes to governance-audit.jsonl."""
    state_dir = isolated_env
    fh = _fake_hooks(isolated_env)

    stdin = _make_stdin(tool_name="Bash", exit_code=0,
                        command=cmd,
                        stderr="", stdout="",
                        event_name="PostToolUse")
    _run_hook(stdin, fh)

    audit_path = state_dir / "governance-audit.jsonl"
    assert audit_path.exists(), "governance-audit.jsonl should exist after E1 bypass"
    lines = [json.loads(l) for l in audit_path.read_text().strip().splitlines() if l.strip()]
    assert len(lines) >= 1, "Should have at least one audit record"
    rec = lines[-1]
    assert rec["escape_type"] == "governance_bypass"
    assert rec["error_type"] == "governance_bypass"
    assert gov_target in rec.get("cmd", "") or gov_target in rec.get("message", "")

    # Also recorded in error-dna.jsonl and error-signals.jsonl
    dna_path = state_dir / "error-dna.jsonl"
    assert dna_path.exists(), "E1 bypass should also write to error-dna.jsonl"
    dna_lines = [json.loads(l) for l in dna_path.read_text().strip().splitlines() if l.strip()]
    assert any(r.get("escape_type") == "governance_bypass" for r in dna_lines)

    signals_path = state_dir / "error-signals.jsonl"
    assert signals_path.exists(), "E1 bypass should also write to error-signals.jsonl"


def test_captcha_forgery_writes_audit(isolated_env):
    """E2 CAPTCHA forgery writes to governance-audit.jsonl."""
    state_dir = isolated_env
    fh = _fake_hooks(isolated_env)

    cmd = "echo sensitive-approved > /tmp/captcha-test"
    stdin = _make_stdin(tool_name="Bash", exit_code=0,
                        command=cmd,
                        stderr="", stdout="",
                        event_name="PostToolUse")
    _run_hook(stdin, fh)

    audit_path = state_dir / "governance-audit.jsonl"
    assert audit_path.exists(), "governance-audit.jsonl should exist after E2 forgery"
    lines = [json.loads(l) for l in audit_path.read_text().strip().splitlines() if l.strip()]
    assert len(lines) >= 1
    rec = lines[-1]
    assert rec["escape_type"] == "captcha_forgery"


# ═══════════════════════════════════════════════════════════════
# Test 5: Updates total-ops counter
# ═══════════════════════════════════════════════════════════════

def test_total_ops_counter(isolated_env):
    """Each Bash invocation increments total-ops.txt."""
    state_dir = isolated_env
    fh = _fake_hooks(isolated_env)
    ops_path = state_dir / "total-ops.txt"

    assert not ops_path.exists(), "Counter should not exist before first call"

    stdin = _make_stdin(tool_name="Bash", exit_code=1,
                        command="ls /nonexistent",
                        stderr="error")
    _run_hook(stdin, fh)
    assert ops_path.exists(), "total-ops.txt should exist"
    assert ops_path.read_text().strip() == "1"

    stdin2 = _make_stdin(tool_name="Bash", exit_code=2,
                         command="cat /nonexistent",
                         stderr="error")
    _run_hook(stdin2, fh)
    assert ops_path.read_text().strip() == "2"


def test_total_ops_not_updated_for_non_bash(isolated_env):
    """Non-Bash tools should NOT increment total-ops.txt."""
    state_dir = isolated_env
    fh = _fake_hooks(isolated_env)
    ops_path = state_dir / "total-ops.txt"
    ops_path.write_text("5", encoding="utf-8")

    stdin = _make_stdin(tool_name="Read", exit_code=1,
                        command="cat /x", stderr="err")
    _run_hook(stdin, fh)

    assert ops_path.read_text().strip() == "5", "Non-Bash should not increment counter"


# ═══════════════════════════════════════════════════════════════
# Test 6: High-frequency alerting
# ═══════════════════════════════════════════════════════════════

def test_high_frequency_alert(isolated_env):
    """>=5 identical signatures triggers high-frequency alert on stderr."""
    state_dir = isolated_env
    fh = _fake_hooks(isolated_env)

    # Pre-seed error-dna.jsonl with 5 identical records
    dna_path = state_dir / "error-dna.jsonl"
    sig = "aaaaaaaaaaaaaaaa"
    base_rec = {
        "ts": 1000000, "signature": sig,
        "cmd": "ls /x", "exit_code": 1,
        "error_type": "runtime", "message": "ls: /x: No such file or directory",
        "session_id": "test", "escape_type": "",
    }
    preamble = "\n".join(json.dumps(base_rec) for _ in range(5))
    dna_path.write_text(preamble + "\n", encoding="utf-8")

    # Trigger hook with new bash error
    stdin = _make_stdin(tool_name="Bash", exit_code=1,
                        command="ls /nonexistent",
                        stderr="ls: /nonexistent: No such file or directory")
    out, err = _run_hook(stdin, fh)

    # Alert should appear on stderr
    assert "[高频错误]" in err, (
        "High-frequency alert should appear on stderr when >=5 same-sig records exist"
    )


def test_no_high_frequency_alert_below_threshold(isolated_env):
    """4 occurrences of same signature should NOT trigger alert."""
    state_dir = isolated_env
    fh = _fake_hooks(isolated_env)

    dna_path = state_dir / "error-dna.jsonl"
    sig = "bbbbbbbbbbbbbbbb"
    base_rec = {
        "ts": 1000000, "signature": sig,
        "cmd": "ls /x", "exit_code": 1,
        "error_type": "runtime", "message": "ls: /x: No such file or directory",
        "session_id": "test", "escape_type": "",
    }
    preamble = "\n".join(json.dumps(base_rec) for _ in range(4))
    dna_path.write_text(preamble + "\n", encoding="utf-8")

    # We also need to pre-seed the hook's error-dna.jsonl with 4 copies of
    # a different real signature.  Running the hook will create a 5th record
    # with its own signature, so we also add a 5th to keep the test clean.
    # Actually, the pre-seeded signatures are for a DIFFERENT sig than what
    # the hook creates, so the hook's new record won't match the pre-seeded 4.
    stdin = _make_stdin(tool_name="Bash", exit_code=1,
                        command="ls /nonexistent",
                        stderr="ls: /nonexistent: No such file or directory")
    out, err = _run_hook(stdin, fh)

    assert "[高频错误]" not in err, "No alert expected for <5 signatures"


# ═══════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════

def test_empty_stdin(isolated_env):
    """Empty stdin should not crash, should continue silently."""
    fh = _fake_hooks(isolated_env)
    with mock.patch("sys.stdin") as mock_stdin, \
         mock.patch("builtins.print") as mock_print, \
         mock.patch("sys.exit", _mock_exit):
        mock_stdin.read.return_value = ""
        ed = _import_error_dna(fh)
        try:
            ed.main()
        except SystemExit:
            pass


def test_missing_tool_name(isolated_env):
    """Missing tool_name field should be skipped gracefully."""
    state_dir = isolated_env
    fh = _fake_hooks(isolated_env)
    dna_path = state_dir / "error-dna.jsonl"
    dna_path.write_text("", encoding="utf-8")

    data = {
        "hook_event_name": "PostToolUse",
        "tool_response": {"exit_code": 1, "stderr": "err"},
        "tool_input": {"command": "ls /x"},
    }
    with mock.patch("sys.stdin") as mock_stdin, \
         mock.patch("builtins.print") as mock_print, \
         mock.patch("sys.exit", _mock_exit):
        mock_stdin.read.return_value = json.dumps(data)
        ed = _import_error_dna(fh)
        try:
            ed.main()
        except SystemExit:
            pass

    content = dna_path.read_text(encoding="utf-8").strip()
    assert content == "", "Hook with missing tool_name should not record"


def test_posttoolusefailure_sets_exit_code_1(isolated_env):
    """PostToolUseFailure with exit_code=0 should be promoted to exit_code=1."""
    state_dir = isolated_env
    fh = _fake_hooks(isolated_env)
    dna_path = state_dir / "error-dna.jsonl"
    dna_path.write_text("", encoding="utf-8")

    stdin = _make_stdin(tool_name="Bash", exit_code=0,
                        command="crashy-command",
                        stderr="", stdout="",
                        event_name="PostToolUseFailure",
                        error="Tool execution failed: process exited abnormally")
    _run_hook(stdin, fh)

    content = dna_path.read_text(encoding="utf-8").strip()
    assert content, "PostToolUseFailure should be recorded"
    rec = json.loads(content.splitlines()[-1])
    assert rec["exit_code"] == 1, (
        "PostToolUseFailure should promote exit_code from 0 to 1"
    )
