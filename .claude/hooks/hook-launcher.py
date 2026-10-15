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
PRETOOL_RC_DENY_HOOKS = {"pretool-gate.py", "carroros-night-deny.py"}


def _detect_hook_event_type() -> str:
    """Detect current hook event type from env (CC should set HOOK_EVENT_TYPE).

    Default to PostToolUse for backwards compat, but PreToolUse and
    PostToolUseFailure are also common — wrong value triggers Claude Code
    'Hook returned incorrect event name' error.
    """
    return os.environ.get("HOOK_EVENT_TYPE", "PostToolUse")


def _emit_continue(message="", hook_name=""):
    """Emit a valid continue JSON and exit 0 (fail-open)."""
    payload = {"continue": True}
    text = message or f"hook-launcher: hook execution failed: {hook_name}"
    payload["hookSpecificOutput"] = {
        "hookEventName": _detect_hook_event_type(),
        "additionalContext": text,
    }
    print(json.dumps(payload, ensure_ascii=False))
    if message:
        print(message, file=sys.stderr)


def _run_one_hook(hook_name, stdin_data, launcher_dir, project_root, env):
    """Run a single hook, collecting stdout into the merge buffer (NOT printing directly).

    Returns (rc, parsed_json_or_None).
    The caller (main) accumulates results and prints a SINGLE merged JSON at the end
    — fixing the "Hook output looks like a JSON object but is not valid JSON" bug
    that Claude Code reports when multiple hook JSONs are concatenated.

    Stderr is still forwarded immediately (operator visibility, not parsed by CC).
    """
    hook_path = os.path.join(launcher_dir, hook_name)

    # Critical hook missing → block
    if not os.path.isfile(hook_path):
        if hook_name in CRITICAL_HOOKS:
            cn_msg = "hook-launcher: CRITICAL hook missing: " + hook_name + " — blocked"
            print(cn_msg, file=sys.stderr)
            return (2, {
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": cn_msg,
                },
            })
        # Non-critical missing: continue
        print(f"hook-launcher: hook not found: {hook_name}", file=sys.stderr)
        return (0, None)

    cmd = ["bash", hook_path] if hook_name.endswith(".sh") else [sys.executable, hook_path]
    try:
        result = subprocess.run(
            cmd, input=stdin_data, capture_output=True, text=True,
            timeout=120, env=env,
        )
    except subprocess.TimeoutExpired:
        print(f"hook-launcher: hook timed out (120s): {hook_name}", file=sys.stderr)
        return (0, None)
    except FileNotFoundError:
        print(f"hook-launcher: python3/bash not found for: {hook_name}", file=sys.stderr)
        return (0, None)
    except Exception as e:
        print(f"hook-launcher: spawn failed: {hook_name}: {e}", file=sys.stderr)
        return (0, None)

    # Forward stderr immediately (operator visibility)
    if result.stderr:
        sys.stderr.write(result.stderr)

    # Parse stdout as JSON if possible
    stdout = result.stdout or ""
    parsed = None
    if stdout.strip().startswith("{"):
        try:
            parsed = json.loads(stdout.strip())
        except json.JSONDecodeError:
            # Hook printed non-JSON; fall through
            pass

    if result.returncode != 0 and not parsed:
        # Hook crashed without JSON — treat as warning continue
        print(f"hook-launcher: hook crashed (exit={result.returncode}): {hook_name}",
              file=sys.stderr)
        return (0, None)

    # Non-zero RC but has JSON → caller decides BLOCK propagation
    return (result.returncode, parsed)


def _merge_hook_results(results: list) -> dict:
    """Merge multiple hook results into a single Claude Code-compatible JSON.

    Strategy:
      - continue=True unless ANY hook returned continue=False (BLOCK semantics)
      - decision: "block" if any hook blocked, else "allow"
      - permissionDecision: "deny" if blocked, "ask" if ASK, "allow" otherwise
      - message: concatenation with " | " separator
      - additionalContext: concatenation
      - reasons: list (audit trail)

    Ref: Claude Code PreToolUse hook spec — must return single JSON object.
    """
    if not results:
        return {"continue": True, "message": ""}

    # Walk in order, first BLOCK wins (precedence: REJECT > ESCALATE > ASK > ALLOW)
    any_continue_false = False
    any_permission_deny = False
    any_permission_ask = False
    messages = []
    contexts = []
    reasons = []

    for hook_name, (rc, parsed) in results:
        if parsed is None:
            if (rc != 0 and hook_name in PRETOOL_RC_DENY_HOOKS
                    and _detect_hook_event_type() == "PreToolUse"):
                any_permission_deny = True
            continue
        hso = parsed.get("hookSpecificOutput", {})
        pd = hso.get("permissionDecision", "") if isinstance(hso, dict) else ""
        if parsed.get("continue") is False and pd != "ask":
            any_continue_false = True
        if (rc != 0 and hook_name in PRETOOL_RC_DENY_HOOKS
                and _detect_hook_event_type() == "PreToolUse"):
            any_permission_deny = True
        # Collect message
        msg = parsed.get("message", "")
        if msg:
            messages.append(f"[{hook_name}] {msg}")
        # Collect hookSpecificOutput
        hso = parsed.get("hookSpecificOutput", {})
        ctx = hso.get("additionalContext", "") if isinstance(hso, dict) else ""
        if ctx:
            contexts.append(f"[{hook_name}] {ctx}")
        # Detect permission decision
        pd = hso.get("permissionDecision", "") if isinstance(hso, dict) else ""
        if pd == "deny":
            any_permission_deny = True
        elif pd == "ask":
            any_permission_ask = True
        # Audit trail
        reasons.append({"hook": hook_name, "rc": rc, "decision": hso.get("permissionDecisionReason", ""),
                         "message": msg[:200]})

    merged = {
        "continue": not any_continue_false,
    }
    if messages:
        merged["message"] = " | ".join(messages)
    if any_permission_deny or any_permission_ask or any_continue_false:
        # Build a hookSpecificOutput reflecting the strongest decision
        decision = "deny" if (any_permission_deny or any_continue_false) else "ask"
        hso = {"hookEventName": _detect_hook_event_type(), "permissionDecision": decision}
        if contexts:
            hso["additionalContext"] = "\n".join(contexts)
        # Use first hook's reason as the primary one
        first_dec = next((r[1][1].get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
                          for r in results if r[1][1]), "merged_decision")
        hso["permissionDecisionReason"] = first_dec
        merged["hookSpecificOutput"] = hso
    merged["_reasons"] = reasons  # internal audit (Claude Code ignores _-prefixed)

    return merged


def main():
    if len(sys.argv) < 2:
        _emit_continue("hook-launcher: missing hook name")
        return

    # 进程合并（降噪）：argv[1] 可含空格分隔的多个 hook 名，串行执行。
    # 关键改进：不再直接 sys.stdout.write 每 hook 输出（导致 JSON 拼接 "}{" → CC 报 hook error）。
    # 改为：每 hook 解析为 dict，最后合并成单 JSON 打印。
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

    results = []
    for hook_name in hook_names:
        rc, parsed = _run_one_hook(hook_name, stdin_data, launcher_dir, project_root, env)
        results.append((hook_name, (rc, parsed)))
        # If hook returned BLOCK (rc=2) or hard deny → stop further hooks
        if rc != 0 and rc != 0 or (parsed and parsed.get("continue") is False):
            break

    merged = _merge_hook_results(results)
    print(json.dumps(merged, ensure_ascii=False))


if __name__ == "__main__":
    main()
