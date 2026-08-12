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

CRITICAL_HOOKS = {"pretool-gate.py"}


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


def _run_one_hook(hook_name, stdin_data, launcher_dir, project_root, env):
    """Run a single hook, forwarding stdout/stderr. Returns exit code."""
    hook_path = os.path.join(launcher_dir, hook_name)

    # Critical hook missing → block
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
            return 2
        _emit_continue("hook-launcher: hook not found: " + hook_name, hook_name)
        return 0

    cmd = ["bash", hook_path] if hook_name.endswith(".sh") else [sys.executable, hook_path]
    try:
        result = subprocess.run(
            cmd, input=stdin_data, capture_output=True, text=True,
            timeout=120, env=env,
        )
    except subprocess.TimeoutExpired:
        _emit_continue("hook-launcher: hook timed out (120s): " + hook_name, hook_name)
        return 0
    except FileNotFoundError:
        _emit_continue("hook-launcher: python3/bash not found for: " + hook_name, hook_name)
        return 0
    except Exception as e:
        _emit_continue("hook-launcher: spawn failed: " + hook_name + ": " + str(e), hook_name)
        return 0

    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)

    if result.returncode != 0 and not result.stdout.strip():
        _emit_continue("hook-launcher: hook crashed (exit=" + str(result.returncode) + "): " + hook_name, hook_name)
        return 0
    return result.returncode if result.stdout.strip().startswith("{") else 0


def main():
    if len(sys.argv) < 2:
        _emit_continue("hook-launcher: missing hook name")
        return

    # 进程合并（降噪）：argv[1] 可含空格分隔的多个 hook 名，串行执行。
    # 聚合输出；任一 hook BLOCK（exit 2 + JSON）→ 停止并转发该 JSON。
    hook_names = [n for n in sys.argv[1].split() if n.strip()]
    if not hook_names:
        _emit_continue("hook-launcher: empty hook list")
        return

    launcher_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.normpath(os.path.join(launcher_dir, "..", ".."))

    # Read stdin before spawning children (CC event data)
    try:
        stdin_data = sys.stdin.read()
    except Exception:
        stdin_data = ""

    os.chdir(project_root)
    env = os.environ.copy()
    env.pop("NIGHT_DENY_ROOT", None)

    for hook_name in hook_names:
        rc = _run_one_hook(hook_name, stdin_data, launcher_dir, project_root, env)
        if rc != 0:
            # hook 已输出 BLOCK JSON 并 exit 2 → 停止后续 hook
            sys.exit(rc)


if __name__ == "__main__":
    main()
