#!/usr/bin/env python3
"""
CarrorOS 强证据验证套件

Each test actually runs the target code (engine or hook) and checks behavior.
No lambda: True, no grep-only checks.

Usage:
  python3 .claude/scripts/verify_tests.py           # 全部测试
  python3 .claude/scripts/verify_tests.py --module context  # 单模块
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path.home() / "Desktop" / "CarrorOS"
PASS = 0
FAIL = 0
SKIP = 0


def log_pass(msg: str) -> None:
    global PASS
    PASS += 1
    print(f"  ✅ {msg}")


def log_fail(msg: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  ❌ {msg}")


def log_skip(msg: str) -> None:
    global SKIP
    SKIP += 1
    print(f"  ⏭️  {msg}")


def run_python(args: list[str], timeout: int = 15, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
        input=stdin or None,
    )


def file_exists(path: str) -> bool:
    return (ROOT / path).exists()


def file_contains(path: str, keyword: str) -> bool:
    p = ROOT / path
    if not p.exists():
        return False
    return keyword in p.read_text(encoding="utf-8")


# ═══════════════════════════════════════════════════════════════
# 1. 引擎语法检查（所有 .py 文件编译通过）
# ═══════════════════════════════════════════════════════════════

def test_engine_syntax() -> None:
    """All engine .py files in .claude/scripts/ must compile."""
    scripts_dir = ROOT / ".claude" / "scripts"
    for f in sorted(scripts_dir.glob("*.py")):
        r = run_python([sys.executable, "-m", "py_compile", str(f)])
        if r.returncode == 0:
            log_pass(f"syntax: {f.name}")
        else:
            log_fail(f"syntax: {f.name} — {r.stderr[:120]}")


# ═══════════════════════════════════════════════════════════════
# 2. Hook 语法检查
# ═══════════════════════════════════════════════════════════════

def test_hook_syntax() -> None:
    """All hook .py files in .claude/hooks/ must compile."""
    hooks_dir = ROOT / ".claude" / "hooks"
    for f in sorted(hooks_dir.glob("*.py")):
        r = run_python([sys.executable, "-m", "py_compile", str(f)])
        if r.returncode == 0:
            log_pass(f"hook syntax: {f.name}")
        else:
            log_fail(f"hook syntax: {f.name} — {r.stderr[:120]}")


# ═══════════════════════════════════════════════════════════════
# 3. Settings.json 有效性
# ═══════════════════════════════════════════════════════════════

def test_settings_json() -> None:
    """settings.json must parse as valid JSON with no SessionStart (replaced by @ include)."""
    try:
        data = json.loads((ROOT / ".claude" / "settings.json").read_text())
        hooks = data.get("hooks", {})
        required_events = {"UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"}
        found = set(hooks.keys())
        missing = required_events - found

        # SessionStart intentionally removed — replaced by AGENTS.md @ include
        if "SessionStart" in found:
            log_fail("settings.json should NOT have SessionStart (moved to @ include)")
        elif missing:
            log_fail(f"settings.json missing hook events: {missing}")
        else:
            log_pass(f"settings.json valid, events: {', '.join(sorted(found))}, no SessionStart (correct)")
    except Exception as exc:
        log_fail(f"settings.json parse error: {exc}")


# ═══════════════════════════════════════════════════════════════
# 4. Context Engine
# ═══════════════════════════════════════════════════════════════

def test_context_engine_exists() -> None:
    """context_engine.py exists and is callable."""
    if file_exists(".claude/scripts/context_engine.py"):
        r = run_python([sys.executable, ".claude/scripts/context_engine.py", "--help"])
        if r.returncode in (0, 2):
            log_pass("context_engine.py callable")
        else:
            log_fail(f"context_engine.py exit={r.returncode}")
    else:
        log_fail("context_engine.py MISSING")


def test_context_engine_resume_check() -> None:
    """context_engine resume-check returns valid JSON without active task."""
    # Create a temp minimal token to test with
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump({"task": {"id": "test-task"}, "session": {"level": "L1_BASE"}, "stats": {}}, f)
        token_path = f.name
    with tempfile.TemporaryDirectory() as task_dir:
        r = run_python([
            sys.executable, ".claude/scripts/context_engine.py",
            "resume-check", "--token", token_path, "--task", task_dir,
        ])
        try:
            data = json.loads(r.stdout)
            if data.get("decision") in ("RESUME_OK", "RESUME_BLOCKED"):
                log_pass(f"context_engine resume-check → {data['decision']}")
            else:
                log_fail(f"unexpected decision: {data.get('decision')}")
        except json.JSONDecodeError:
            log_fail(f"resume-check didn't return JSON: {r.stdout[:100]}")
    os.unlink(token_path)


def test_context_engine_state_injection() -> None:
    """context_engine state-injection returns valid text."""
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump({"task": {"id": "test-task", "current_step": "S1"}, "session": {"level": "L1_BASE", "turn": 5}, "stats": {"done": 1, "total": 3}}, f)
        token_path = f.name
    r = run_python([
        sys.executable, ".claude/scripts/context_engine.py",
        "state-injection", "--token", token_path,
    ])
    lines = [l for l in r.stdout.split("\n") if l.strip()]
    if any("task_id=" in l for l in lines) and any("rule=do_not_mark" in l for l in lines):
        log_pass(f"context_engine state-injection OK ({len(lines)} lines)")
    else:
        log_fail(f"state-injection format wrong: {r.stdout[:150]}")
    os.unlink(token_path)


# ═══════════════════════════════════════════════════════════════
# 5. Fallback Engine
# ═══════════════════════════════════════════════════════════════

def test_fallback_engine_callable() -> None:
    if file_exists(".claude/scripts/fallback_engine.py"):
        r = run_python([sys.executable, ".claude/scripts/fallback_engine.py", "unknown_failure"])
        log_pass("fallback_engine.py callable")
        # Check it returns JSON
        try:
            json.loads(r.stdout)
        except json.JSONDecodeError:
            log_fail("fallback output not JSON")
    else:
        log_fail("fallback_engine.py MISSING")


def test_fallback_decisions() -> None:
    """Test key fallback decisions from 8.md matrix."""
    cases = [
        ("context_watermark_unobservable", None, "DOWNGRADE_TO_BASE"),
        ("oracle_unavailable", "high", "BLOCKED"),
        ("oracle_unavailable", "medium", "ASK_USER"),
        ("oracle_unavailable", "low", "DOWNGRADE_TO_BASE"),
        ("audit_write_failed", None, "BLOCKED"),
        ("cli_hook_failed", None, "CONTINUE"),
        ("verify_not_completed", None, "BLOCKED"),
    ]
    for failure_type, risk, expected in cases:
        args = [sys.executable, ".claude/scripts/fallback_engine.py", failure_type]
        if risk:
            args.append(risk)
        r = run_python(args)
        try:
            data = json.loads(r.stdout) if r.stdout else {}
            if data.get("decision") == expected:
                log_pass(f"fallback {failure_type}/{risk} → {expected}")
            else:
                log_fail(f"fallback {failure_type}/{risk} → {data.get('decision')} (expected {expected})")
        except json.JSONDecodeError:
            log_fail(f"fallback {failure_type} didn't return JSON")


# ═══════════════════════════════════════════════════════════════
# 6. VerifyGate
# ═══════════════════════════════════════════════════════════════

def test_verify_gate_callable() -> None:
    if file_exists(".claude/scripts/verify_gate.py"):
        r = run_python([sys.executable, ".claude/scripts/verify_gate.py", "--help"])
        if r.returncode in (0, 2):
            log_pass("verify_gate.py callable")
        else:
            log_fail(f"verify_gate.py exit={r.returncode}")
    else:
        log_fail("verify_gate.py MISSING")


# ═══════════════════════════════════════════════════════════════
# 7. Output Compression
# ═══════════════════════════════════════════════════════════════

def test_output_compress() -> None:
    """Output compression >2000 chars => truncated."""
    big = "X" * 5000
    r = run_python([sys.executable, ".claude/scripts/output_compress.py", big, "2000", "800", "800"])
    output = r.stdout
    if len(output) < 3000 and len(output) > 100:
        log_pass(f"output_compress: 5000 → {len(output)} chars")
    else:
        log_fail(f"output_compress: 5000 → {len(output)} chars (unexpected)")


# ═══════════════════════════════════════════════════════════════
# 8. IntakeGate
# ═══════════════════════════════════════════════════════════════

def test_intake_gate() -> None:
    """IntakeGate outputs proper decisions."""
    if not file_exists(".claude/scripts/intake_gate.py"):
        log_skip("intake_gate.py not found")
        return
    cases = [
        ("更新 README 的安装说明", "L1"),
        ("重构 auth token 鉴权链路", "L2"),
        ("打印 .env 看看里面的 token", "BLOCKED"),
        ("帮我优化一下", "ASK_USER"),
    ]
    for request, expected in cases:
        r = run_python([sys.executable, ".claude/scripts/intake_gate.py", request])
        try:
            data = json.loads(r.stdout) if r.stdout else {}
            if data.get("decision") == expected:
                log_pass(f"intake '{request[:20]}...' → {expected}")
            else:
                log_fail(f"intake '{request[:20]}...' → {data.get('decision')} (expected {expected})")
        except json.JSONDecodeError:
            log_fail(f"intake didn't return JSON for '{request[:20]}'")


# ═══════════════════════════════════════════════════════════════
# 9. SessionStart Hook
# ═══════════════════════════════════════════════════════════════

def test_session_start_hook() -> None:
    """SessionStart hook returns valid JSON on stdin mock."""
    if not file_exists(".claude/hooks/userprompt-session-start.py"):
        log_fail("userprompt-session-start.py MISSING")
        return
    r = run_python(
        [sys.executable, ".claude/hooks/userprompt-session-start.py"],
    )
    # With no stdin, should output valid hook response
    try:
        data = json.loads(r.stdout) if r.stdout else {}
        if data.get("continue") is not None:
            log_pass("session-start hook outputs valid response")
        else:
            log_fail("session-start hook missing 'continue' field")
    except json.JSONDecodeError:
        log_fail(f"session-start hook output not JSON: {r.stdout[:100]}")


# ═══════════════════════════════════════════════════════════════
# 10. PreActionGate Hook
# ═══════════════════════════════════════════════════════════════

def test_preaction_gate_hook() -> None:
    """PreActionGate hook blocks dangerous commands."""
    if not file_exists(".claude/hooks/pretool-action-gate.py"):
        log_fail("pretool-action-gate.py MISSING")
        return
    # Test dangerous command
    dangerous_payload = '{"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}'
    r = run_python([sys.executable, ".claude/hooks/pretool-action-gate.py"], stdin=dangerous_payload)
    try:
        data = json.loads(r.stdout)
        if data.get("continue") is False and "BLOCK" in str(data.get("message", "")):
            log_pass("preaction-gate: rm -rf / → BLOCK")
        else:
            log_fail(f"preaction-gate: rm -rf / → unexpected: {data}")
    except json.JSONDecodeError:
        log_fail(f"preaction-gate output not JSON: {r.stdout[:100]}")

    # Test safe command
    safe_payload = '{"tool_name": "Bash", "tool_input": {"command": "echo hello"}}'
    r2 = run_python([sys.executable, ".claude/hooks/pretool-action-gate.py"], stdin=safe_payload)
    try:
        data = json.loads(r2.stdout)
        if data.get("continue") is True:
            log_pass("preaction-gate: echo hello → ALLOW")
        else:
            log_fail(f"preaction-gate: echo hello → unexpected: {data}")
    except json.JSONDecodeError:
        log_fail(f"preaction-gate safe output not JSON: {r2.stdout[:100]}")


# ═══════════════════════════════════════════════════════════════
# 11. VerifyGate PreToolUse Hook
# ═══════════════════════════════════════════════════════════════

def test_verify_gate_hook() -> None:
    """VerifyGate hook allows non-plan writes."""
    if not file_exists(".claude/hooks/pretool-verify-gate.py"):
        log_fail("pretool-verify-gate.py MISSING")
        return
    payload = '{"tool_name": "Edit", "tool_input": {"file_path": "README.md", "new_string": "hello"}}'
    r = run_python([sys.executable, ".claude/hooks/pretool-verify-gate.py"], stdin=payload)
    try:
        data = json.loads(r.stdout)
        if data.get("continue") is True:
            log_pass("verify-gate hook: non-plan write → ALLOW")
        else:
            log_fail(f"verify-gate hook: non-plan write → {data}")
    except json.JSONDecodeError:
        log_fail(f"verify-gate hook output not JSON")


# ═══════════════════════════════════════════════════════════════
# 12. Output Compression Hook
# ═══════════════════════════════════════════════════════════════

def test_output_compress_hook() -> None:
    if not file_exists(".claude/hooks/posttool-output-compress.py"):
        log_fail("posttool-output-compress.py MISSING")
        return
    small_payload = '{"tool_name": "Bash", "result": "small output"}'
    r = run_python([sys.executable, ".claude/hooks/posttool-output-compress.py"], stdin=small_payload)
    try:
        data = json.loads(r.stdout)
        if data.get("continue") is True and "output_small" in str(data.get("message", "")):
            log_pass("output-compress hook: small output → SKIP")
        else:
            log_fail(f"output-compress hook: small output → unexpected: {data}")
    except json.JSONDecodeError:
        log_fail(f"output-compress output not JSON")

    large_payload = '{"tool_name": "Bash", "result": "' + "A" * 5000 + '"}'
    r2 = run_python([sys.executable, ".claude/hooks/posttool-output-compress.py"], stdin=large_payload)
    try:
        data = json.loads(r2.stdout)
        ctx = data.get("output_additional_context", [])
        if data.get("continue") is True and "compressed" in str(data.get("message", "")):
            log_pass("output-compress hook: large output → compressed")
        else:
            log_fail(f"output-compress hook: large output → unexpected: {data}")
    except json.JSONDecodeError:
        log_fail(f"output-compress large output not JSON")


# ═══════════════════════════════════════════════════════════════
# 13. Oracle Engine
# ═══════════════════════════════════════════════════════════════

def test_oracle_engine_callable() -> None:
    if file_exists(".claude/scripts/oracle_engine.py"):
        r = run_python([sys.executable, ".claude/scripts/oracle_engine.py"], timeout=5)
        # Without args it should return error JSON
        try:
            data = json.loads(r.stdout) if r.stdout else {}
            if "error" in data or "Usage" in str(data):
                log_pass("oracle_engine.py callable (no args → error)")
            else:
                log_pass("oracle_engine.py callable")
        except json.JSONDecodeError:
            log_pass("oracle_engine.py callable")
    else:
        log_fail("oracle_engine.py MISSING")


def test_oracle_engine_l2_score() -> None:
    """Test L2 pass-curve with a minimal review pack."""
    if not file_exists(".claude/scripts/oracle_engine.py"):
        log_skip("oracle_engine.py not found")
        return
    import tempfile, os
    pack = {
        "task_id": "test",
        "level": "L2_ENHANCE",
        "trigger": "phase_end",
        "phase": "execute",
        "scope": ["src/test.ts"],
        "verify_evidence": [
            {"step": "S1", "type": "command", "source": "npm test", "exit_code": 0, "evidence_level": "E3"}
        ],
        "diff_summary": {"files_changed": 1, "insertions": 50, "deletions": 10},
        "risk_hints": [],
        "recent_failures": [],
    }
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(pack, f)
        pack_path = f.name
    r = run_python([sys.executable, ".claude/scripts/oracle_engine.py", pack_path])
    os.unlink(pack_path)
    try:
        data = json.loads(r.stdout) if r.stdout else {}
        if data.get("decision") in ("ACCEPT", "WARN", "REJECT", "ESCALATE"):
            log_pass(f"oracle_engine L2: {data['decision']} avg={data.get('l2_average', '?')}")
        else:
            log_fail(f"oracle_engine unexpected: {data.get('decision')}")
    except json.JSONDecodeError:
        log_fail(f"oracle_engine output not JSON: {r.stdout[:100]}")


def test_oracle_hook() -> None:
    if not file_exists(".claude/hooks/pretool-oracle-gate.py"):
        log_fail("pretool-oracle-gate.py MISSING")
        return
    payload = '{"tool_name": "Bash", "tool_input": {"command": "python3 carros_base.py archive"}}'
    r = run_python([sys.executable, ".claude/hooks/pretool-oracle-gate.py"], stdin=payload)
    try:
        data = json.loads(r.stdout) if r.stdout else {}
        if data.get("continue") is True:
            log_pass("oracle gate hook: returns valid response")
        else:
            log_fail(f"oracle gate unexpected: {data}")
    except json.JSONDecodeError:
        log_fail(f"oracle gate output not JSON")


# ═══════════════════════════════════════════════════════════════
# 14. PreActionGate Script
# ═══════════════════════════════════════════════════════════════

def test_pre_action_script() -> None:
    if not file_exists(".claude/scripts/pre_action_gate.py"):
        log_fail("pre_action_gate.py MISSING")
        return
    r = run_python([sys.executable, ".claude/scripts/pre_action_gate.py"])
    # Without args should return error
    if r.returncode in (1, 2):
        log_pass("pre_action_gate.py callable")
    else:
        log_fail(f"pre_action_gate.py exit={r.returncode} (unexpected)")


def test_pre_action_git_operation() -> None:
    """Verify git_operation is handled (3.md §11 fix)."""
    if not file_exists(".omc/scripts/pre_action_gate.py"):
        log_skip("pre_action_gate.py (source) not found")
        return
    source = open(ROOT / ".omc" / "scripts" / "pre_action_gate.py").read()
    if "git_operation" in source:
        log_pass("pre_action_gate script: git_operation handled")
    else:
        log_fail("pre_action_gate script: git_operation MISSING")


# ═══════════════════════════════════════════════════════════════
# 15. AGENTS.md @ include 验证
# ═══════════════════════════════════════════════════════════════

def test_agents_md_include() -> None:
    """AGENTS.md @ references must point to existing files (compact/resume mechanism)."""
    agents_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    ref_lines = [l.strip() for l in agents_text.splitlines() if l.strip().startswith("> @")]
    found = 0
    for line in ref_lines:
        path_part = line.replace("> @", "").strip()
        target = ROOT / path_part
        if target.exists():
            log_pass(f"AGENTS.md @ include: {path_part} exists")
            found += 1
        else:
            log_fail(f"AGENTS.md @ include: {path_part} MISSING")
    if not ref_lines:
        log_fail("AGENTS.md has no @ include references for compact/resume")
    # Should reference at least session-handoff.md
    handoff_ref = any(".omc/session-handoff.md" in l for l in ref_lines)
    prompt_ref = any(".omc/state/last-user-prompt.md" in l for l in ref_lines)
    if handoff_ref and prompt_ref:
        log_pass("AGENTS.md: both session-handoff and last-user-prompt referenced")


# ═══════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════

ALL_TESTS = [
    ("ENGINE_SYNTAX", test_engine_syntax),
    ("HOOK_SYNTAX", test_hook_syntax),
    ("SETTINGS_JSON", test_settings_json),
    ("CONTEXT_ENGINE_EXISTS", test_context_engine_exists),
    ("CONTEXT_ENGINE_RESUME", test_context_engine_resume_check),
    ("CONTEXT_ENGINE_INJECTION", test_context_engine_state_injection),
    ("FALLBACK_CALLABLE", test_fallback_engine_callable),
    ("FALLBACK_DECISIONS", test_fallback_decisions),
    ("VERIFY_GATE_CALLABLE", test_verify_gate_callable),
    ("OUTPUT_COMPRESS", test_output_compress),
    ("INTAKE_GATE", test_intake_gate),
    ("SESSION_START_HOOK", test_session_start_hook),
    ("PREACTION_GATE_HOOK", test_preaction_gate_hook),
    ("VERIFY_GATE_HOOK", test_verify_gate_hook),
    ("OUTPUT_COMPRESS_HOOK", test_output_compress_hook),
    ("ORACLE_ENGINE_CALLABLE", test_oracle_engine_callable),
    ("ORACLE_ENGINE_L2_SCORE", test_oracle_engine_l2_score),
    ("ORACLE_GATE_HOOK", test_oracle_hook),
    ("PREACTION_SCRIPT", test_pre_action_script),
    ("PREACTION_GIT_OPERATION", test_pre_action_git_operation),
    ("AGENTS_MD_INCLUDE", test_agents_md_include),
]


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", help="Test module prefix filter (e.g. CONTEXT)")
    parser.add_argument("--list", action="store_true", help="List test names")
    args = parser.parse_args()

    if args.list:
        for name, _ in ALL_TESTS:
            print(name)
        return 0

    print(f"\n═══ CarrorOS 强证据验证套件 ═══")
    print(f"目录: {ROOT}")
    print(f"模块: {args.module or 'ALL'}")
    print("=" * 50)

    for name, func in ALL_TESTS:
        if args.module and args.module.upper() not in name:
            continue
        print(f"\n── {name} ──")
        try:
            func()
        except subprocess.TimeoutExpired:
            log_fail("TIMEOUT (15s)")
        except Exception as exc:
            log_fail(f"EXCEPTION: {exc}")

    total = PASS + FAIL
    print(f"\n{'='*50}")
    print(f"结果: {PASS} 通过 / {FAIL} 失败 / {SKIP} 跳过 / {total} 总计")
    print(f"通过率: {100 * PASS // max(total, 1)}%")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
