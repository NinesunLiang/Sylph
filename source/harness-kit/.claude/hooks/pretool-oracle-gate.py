#!/usr/bin/env python3
"""pretool-oracle-gate.py — Oracle review pre-gate (Python3 cross-platform)

Replaces pretool-oracle-gate.sh on Windows where bash is unavailable.
Block mechanism/governance file edits without 24h Oracle/Meta-Oracle ACCEPT verdict.
DG-67 dual-sign materialized as hard gate (DG-115).

Called as PreToolUse hook on Edit|Write matcher.
"""

import json
import os
import re
import sys
import time


HOME = os.path.expanduser("~")

# Platform routing: on macOS/Linux the bash .sh version handles execution
# (battle-tested hc_enabled integration). Python .py skips to avoid double-block.
# On Windows where bash is unavailable, .py takes over.
IS_WINDOWS = os.name == "nt"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
STATE_DIR = os.path.join(PROJECT_ROOT, ".omc", "state")

# ── Feature gate ────────────────────────────────────────────────────

def _is_feature_enabled():
    yaml_path = os.path.join(PROJECT_ROOT, ".claude", "harness.yaml")
    if os.path.isfile(yaml_path):
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "oracle_gate" in line:
                        if re.search(r":\s*false", line, re.IGNORECASE):
                            return False
                        if re.search(r":\s*true", line, re.IGNORECASE):
                            return True
        except OSError:
            pass
    # Fallback: check .harness-cache
    cache_path = os.path.join(PROJECT_ROOT, ".hooks", ".cache")
    if os.path.isfile(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "hooks_enabled.oracle_gate=false" in line:
                        return False
        except OSError:
            pass
    return True


# ── Mechanism file detection ────────────────────────────────────────

def _is_mechanism_file(file_path):
    # L0: AI生产文件 (双审)
    if re.search(r"(?:\.claude/hooks/|\.claude/scripts/|settings\.json$|harness\.yaml$)", file_path):
        return True
    # L1: AI治理文档 (双审)
    if re.search(r"(?:AGENTS\.md$|kernel\.md$|CLAUDE\.md$)", file_path):
        return True
    # L2: AI治理参考 (双审)
    if re.search(r"(?:\.claude/reference/|\.claude/nodes/|\.claude/schemas/|feature-registry\.yaml$|anti-patterns\.md$|\.hooks/unified\.yaml$)", file_path):
        return True
    # L3: 学习笔记/狗粮/故事 — 不触发双审 (DG-132)
    return False


# ── CAPTCHA bypass ──────────────────────────────────────────────────

def _check_captcha_bypass():
    """Content-verified + 5min freshness CAPTCHA check (sensitive-edit pattern)."""
    required_path = os.path.join(STATE_DIR, "oracle-gate-required")
    approved_path = os.path.join(STATE_DIR, "oracle-gate-approved")

    if not (os.path.isfile(approved_path) and os.path.isfile(required_path)):
        return False

    try:
        with open(required_path, "r", encoding="utf-8") as f:
            expected = f.read().strip().split("\n")[0]
        with open(approved_path, "r", encoding="utf-8") as f:
            actual = f.read().strip().split("\n")[0]
    except OSError:
        return False

    if not expected or expected != actual:
        # Clean up stale/mismatched files
        for p in (required_path, approved_path):
            try:
                os.remove(p)
            except OSError:
                pass
        return False

    # Check 5-minute freshness
    try:
        mtime = os.path.getmtime(required_path)
        if time.time() - mtime > 300:
            for p in (required_path, approved_path):
                try:
                    os.remove(p)
                except OSError:
                    pass
            return False
    except OSError:
        return False

    # Valid bypass — consume files
    for p in (required_path, approved_path):
        try:
            os.remove(p)
        except OSError:
            pass
    return True


# ── Verdict check ────────────────────────────────────────────────────

def _check_verdict_file(path):
    """Check if file contains a 24h ACCEPT/APPROVED verdict."""
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read(4096)  # head ~20 lines
    except OSError:
        return False

    if not re.search(r"(?:ACCEPT|APPROVED|approve|accept)", content):
        return False

    # Check date freshness
    vdate = re.search(r"20\d{2}-\d{2}-\d{2}", content)
    if vdate:
        try:
            from datetime import datetime
            vts = datetime.strptime(vdate.group(0), "%Y-%m-%d").timestamp()
            if time.time() - vts < 86400:
                return True
        except (ValueError, OSError):
            pass
        return False
    # No date stamp — current session verdict, valid
    return True


def _has_recent_verdict():
    oracle_v = os.path.join(STATE_DIR, "oracle-verdicts.md")
    meta_v = os.path.join(STATE_DIR, "meta-oracle-verdicts.md")
    return _check_verdict_file(oracle_v) or _check_verdict_file(meta_v)


# ── Autonomous mode detection ──────────────────────────────────────

def _check_auto_mode():
    """Check if goal/ghost/rpe autonomous mode is active.
    Returns True if autonomous mode is running (record & skip, don't block)."""
    markers = [
        os.path.join(STATE_DIR, "tokens", "autonomous.active"),
        os.path.join(STATE_DIR, "tokens", "lx-ghost.json"),
        os.path.join(STATE_DIR, "tokens", "lx-goal.json"),
    ]
    for marker in markers:
        if os.path.isfile(marker):
            return True
    # Also check rpe directory for active executor files
    rpe_dir = os.path.join(PROJECT_ROOT, "rpe")
    if os.path.isdir(rpe_dir):
        try:
            for f in os.listdir(rpe_dir):
                if f.endswith(".active"):
                    return True
        except OSError:
            pass
    return False


def _log_auto_mode_skip(file_path):
    """Log a blocked decision that was skipped due to autonomous mode."""
    from datetime import datetime
    log_file = os.path.join(STATE_DIR, "auto-mode-skip.log")
    entry = f"[{datetime.now().isoformat()}] auto_mode_skip: oracle_gate would have blocked {file_path}\n"
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)
    except OSError:
        pass
    _flywheel_event("oracle_gate", "auto_mode_skip", "P3")


# ── Flywheel ────────────────────────────────────────────────────────

def _flywheel_event(hook, event, severity="P2"):
    log_path = os.path.join(HOME, ".claude", "flywheel.log")
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    project = os.path.basename(PROJECT_ROOT)
    line = f"{today},{hook}_{event},{severity},{project}\n"
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


# ── Main ────────────────────────────────────────────────────────────

def main():
    if not _is_feature_enabled():
        print(json.dumps({"continue": True}))
        return

    # Cross-platform Oracle gate: macOS/Linux now uses Python path too
    # (original .sh was removed during .sh→.py migration — only .py remains).
    # No platform skip needed anymore.

    # Parse stdin
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        print(json.dumps({"continue": True}))
        return

    ti = input_data.get("tool_input", {})
    args = ti.get("args", input_data.get("args", {}))
    if isinstance(args, dict):
        file_path = ti.get("file_path") or ti.get("target_file") or ti.get("path") or args.get("file_path", args.get("path", ""))
    else:
        file_path = ti.get("file_path") or ti.get("target_file") or ti.get("path", "")

    if not file_path:
        print(json.dumps({"continue": True}))
        return

    # Normalize path (use removeprefix to avoid lstrip stripping leading dots)
    if file_path.startswith("./"):
        file_path = file_path[2:]

    if not _is_mechanism_file(file_path):
        print(json.dumps({"continue": True}))
        return

    # CAPTCHA bypass check
    if _check_captcha_bypass():
        _flywheel_event("oracle_gate", "bypass_used", "P1")
        msg = f"[oracle-gate] BYPASS: CAPTCHA verified, one-time pass for {file_path}"
        print(msg, file=sys.stderr)
        print(json.dumps({"continue": True}))
        return

    # Verdict check
    if _has_recent_verdict():
        print(json.dumps({"continue": True}))
        return

    # Autonomous mode check — record & skip, don't block
    if _check_auto_mode():
        _log_auto_mode_skip(file_path)
        msg = f"[oracle-gate] AUTO MODE: would have blocked {file_path}, recorded as skip"
        print(msg, file=sys.stderr)
        print(json.dumps({"continue": True}))
        return

    # Block
    import hashlib
    captcha = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
    os.makedirs(STATE_DIR, exist_ok=True)
    try:
        with open(os.path.join(STATE_DIR, "oracle-gate-required"), "w") as f:
            f.write(captcha)
    except OSError:
        pass

    if re.search(r"(?:hooks/|scripts/)", file_path):
        mech_type = "L0 生产文件"
    elif re.search(r"(?:AGENTS\.md|kernel\.md|CLAUDE\.md)", file_path):
        mech_type = "L1 治理文档"
    elif re.search(r"(?:reference/|nodes/|schemas/|feature-registry\.yaml|anti-patterns\.md|unified\.yaml)", file_path):
        mech_type = "L2 治理参考"
    else:
        mech_type = "机制文件"

    ctx = (
        f"🔐 [Oracle 审查门禁] 编辑{mech_type}前必须先通过 Oracle 审查\n"
        f"\n"
        f"  文件: {file_path}\n"
        f"  原因: DG-67 规定机制/治理文件变更必须 Oracle + Meta-Oracle 双签\n"
        f"        DG-115 将此规则物化为硬门禁\n"
        f"\n"
        f"  放行条件 (任一):\n"
        f"  1. Oracle 已给出 ACCEPT 裁决 (24h 内)\n"
        f"  2. Meta-Oracle 已给出 ACCEPT 裁决 (24h 内)\n"
        f"\n"
        f"  绕过方法 (二选一):\\n"
        f"    a) 输入 approve {captcha} 并回车（推荐）\\n"
        f"    b) ! echo '{captcha}' > .omc/state/oracle-gate-approved\\n"
        f"\n"
        f"  非 Claude Code 平台去掉 ! 前缀。"
    )

    result = {
        "continue": False,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": ctx,
        },
    }
    print(json.dumps(result, ensure_ascii=True))

    _flywheel_event("oracle_gate", "blocked", "P1")
    msg = f"[oracle-gate] BLOCKED: {file_path} — 无 Oracle/Meta-Oracle ACCEPT 裁决 (24h)"
    print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()
