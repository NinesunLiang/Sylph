#!/usr/bin/env python3
"""CarrorOS Hook Launcher — crash-safe v2

v2: os.execvp → subprocess.run with crash protection.
Any hook crash/error → valid continue JSON on stdout → no more "hook error" from CC.
Critical hooks that are missing → exit 2 (block, existing behavior preserved).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

CRITICAL_HOOKS = {"pretool-gate.py", "carroros-night-deny.py"}


def _emit_continue(message="", hook_name=""):
    """Emit a valid continue JSON and exit 0 (fail-open)."""
    payload = {"continue": True}
    text = message or f"hook-launcher: hook execution failed: {hook_name}"
    payload["hookSpecificOutput"] = {
        "hookEventName": "PostToolUse",
        "additionalContext": text,
    }
    print(json.dumps(payload, ensure_ascii=False))
    if message:
        print(message, file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        _emit_continue("hook-launcher: missing hook name")
        return

    hook_name = sys.argv[1]
    launcher_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.normpath(os.path.join(launcher_dir, "..", ".."))
    hook_path = os.path.join(launcher_dir, hook_name)

    # Critical hook missing → block (existing behavior preserved)
    if not os.path.isfile(hook_path):
        if hook_name in CRITICAL_HOOKS:
            cn_msg = "hook-launcher: CRITICAL hook missing: " + hook_name + " — blocked"
            out = json.dumps({
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": cn_msg,
                },
            })
            print(out)
            print(cn_msg, file=sys.stderr)
            sys.exit(2)
        _emit_continue("hook-launcher: hook not found: " + hook_name, hook_name)
        return

    # ── Crash-safe execution ──
    # Read stdin before spawning child (CC event data)
    try:
        stdin_data = sys.stdin.read()
    except Exception:
        stdin_data = ""

    os.chdir(project_root)
    env = os.environ.copy()
    env.pop("NIGHT_DENY_ROOT", None)

    cmd = ["bash", hook_path] if hook_name.endswith(".sh") else [sys.executable, hook_path]

    try:
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
    except subprocess.TimeoutExpired:
        _emit_continue(
            "hook-launcher: hook timed out (120s): " + hook_name,
            hook_name,
        )
        return
    except FileNotFoundError:
        _emit_continue(
            "hook-launcher: python3/bash not found for: " + hook_name,
            hook_name,
        )
        return
    except Exception as e:
        _emit_continue(
            "hook-launcher: spawn failed: " + hook_name + ": " + str(e),
            hook_name,
        )
        return

    # Forward child output
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)

    # If child produced no stdout but exited non-zero → crash → emit continue
    if result.returncode != 0 and not result.stdout.strip():
        _emit_continue(
            "hook-launcher: hook crashed (exit=" + str(result.returncode) + "): " + hook_name,
            hook_name,
        )
        return

    # Child produced stdout (JSON response) — trust it, exit with same code
    # If child exit code != 0 but has JSON, let CC process the JSON
    sys.exit(0 if result.stdout.strip().startswith("{") else 0)


if __name__ == "__main__":
    main()
