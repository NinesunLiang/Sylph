#!/usr/bin/env python3
"""
test-pretool-terminal-safety.py — Verify pretool-terminal-safety.py behavior

Usage:
    python3 scripts/test-pretool-terminal-safety.py

Exit code: 0 if all pass, 1 if any fail.
"""

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / ".claude/hooks/pretool-terminal-safety.py"


def run_test(label, stdin_json):
    """Run hook with given JSON input and return (exit_code, stdout_lines, stderr)."""
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(stdin_json),
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode, result.stdout.splitlines(), result.stderr


def is_accepted(exit_code, stdout_lines):
    """True if the hook allowed the command through (exit 0 + continue:true in stdout)."""
    if exit_code != 0:
        return False
    for line in stdout_lines:
        line = line.strip()
        if line.startswith("{"):
            try:
                parsed = json.loads(line)
                if parsed.get("continue") is True:
                    return True
            except json.JSONDecodeError:
                pass
    return False


def make_input(command, extra_ti=None):
    """Build the JSON blob the hook reads from stdin."""
    d = {"tool_input": {"command": command}}
    if extra_ti:
        d["tool_input"].update(extra_ti)
    d["args"] = {"command": command}
    return d


# ── Helpers ─────────────────────────────────────────────────────────────

tests_passed = 0
tests_failed = 0

def check(label, exit_code, stdout_lines, stderr, *,
           expect_accept=True):
    global tests_passed, tests_failed
    ok = True
    reasons = []

    accepted = is_accepted(exit_code, stdout_lines)

    if expect_accept and not accepted:
        ok = False
        reasons.append(f"expected ACCEPT but got exit={exit_code}")
    if not expect_accept and accepted:
        ok = False
        reasons.append(f"expected REJECT but got exit={exit_code} (accepted)")

    if ok:
        tests_passed += 1
    else:
        print(f"FAIL [{label}]: {'; '.join(reasons)}")
        print(f"       exit={exit_code} stderr={stderr!r}")
        tests_failed += 1


def should_warn(label, exit_code, stdout_lines, stderr, pattern):
    global tests_passed, tests_failed
    ok = True
    reasons = []
    accepted = is_accepted(exit_code, stdout_lines)

    if not accepted:
        ok = False
        reasons.append(f"expected ACCEPT (warning only) but got exit={exit_code}")

    if pattern not in stderr:
        ok = False
        if not stderr:
            reasons.append(f"expected stderr to contain {pattern!r} but stderr was empty (gate may be disabled)")
        else:
            reasons.append(f"expected stderr to contain {pattern!r}, got: {stderr!r}")

    if ok:
        tests_passed += 1
    else:
        print(f"FAIL [{label}]: {'; '.join(reasons)}")
        print(f"       exit={exit_code} stderr={stderr!r}")
        tests_failed += 1


# ── Test Cases ──────────────────────────────────────────────────────────

# 1. Normal short commands — always ACK
normal_cmds = [
    "ls",
    "git status",
    "git add main.go",
    "git commit -m 'fix: typo'",
    "echo 'hello world'",
    "python3 --version",
    "python3 -c 'print(1)'",
    "make build",
    "cat /tmp/foo.txt",
    "cd /tmp && ls -la",
]
for cmd in normal_cmds:
    inp = make_input(cmd)
    e, out, err = run_test(f"normal: {cmd}", inp)
    check(f"normal: {cmd}", e, out, err, expect_accept=True)

# 2. python3 -c >100 chars → WARN (Rule 1, soft, no block)
#    Build a command exactly so it's 100-200 chars
long_py = "python3 -c " + "'" + "a" * 150 + "'"
assert len(long_py) > 100, f"long_py too short: {len(long_py)}"
e, out, err = run_test("soft_warn_100+", make_input(long_py))
should_warn("soft_warn_100+", e, out, err, "[terminal-safety]")

# 3. python3 -c >120 chars → warn via Rule 6 (still soft)
long_py2 = "python3 -c " + "'" + "b" * 200 + "'"
assert len(long_py2) > 120, f"long_py2 too short: {len(long_py2)}"
e, out, err = run_test("soft_warn_120+", make_input(long_py2))
should_warn("soft_warn_120+", e, out, err, "[terminal-safety]")

# 4. Command > 2000 chars → HARD BLOCK (exit != 0, not accepted)
long_cmd = "git " + "a" * 2100
e, out, err = run_test("hard_block_2000+", make_input(long_cmd))
check("hard_block_2000+", e, out, err, expect_accept=False)

# 5. git chain with && → warning, not block
git_chain = "git add . && git commit -m 'fix' && git push"
e, out, err = run_test("git_chain_warn", make_input(git_chain))
should_warn("git_chain_warn", e, out, err, "[terminal-safety]")

# 6. git commit with # → warning, not block
git_hash = "git commit -m '#123 fix the bug'"
e, out, err = run_test("git_hash_warn", make_input(git_hash))
should_warn("git_hash_warn", e, out, err, "[terminal-safety]")

# 7. Path pile-up (>8 files) → warning, not block
cmd_many = " ".join([f"file{i}.py" for i in range(12)])
e, out, err = run_test("path_pileup_warn", make_input(cmd_many))
should_warn("path_pileup_warn", e, out, err, "[terminal-safety]")

# 8. Empty / no-command input → always pass
for inp in [{}, {"tool_input": {}}, {"tool_input": {"command": ""}}, {"nope": True}]:
    e, out, err = run_test("empty_input", inp)
    check("empty_input", e, out, err, expect_accept=True)


# ── Summary ─────────────────────────────────────────────────────────────

print(f"\n{'=' * 50}")
print(f"Results: {tests_passed} passed, {tests_failed} failed")
print(f"{'=' * 50}")

if tests_failed:
    print(f"\nSome tests FAILED. See above for details.", file=sys.stderr)
    sys.exit(1)
else:
    print(f"\nAll tests PASSED.")
    sys.exit(0)
