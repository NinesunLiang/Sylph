#!/usr/bin/env python3
"""pretool-oracle-gate.py — Oracle review pre-gate (Python3 cross-platform)

Replaces pretool-oracle-gate.sh on Windows where bash is unavailable.
Block mechanism/governance file edits without 24h Oracle/Meta-Oracle ACCEPT verdict.
DG-67 dual-sign materialized as hard gate (DG-115).

Called as PreToolUse hook on Edit|Write matcher.

C4: Consolidated oracle-gate state into single oracle-gate-state.json.
    - Single json.load for all state (fail-open on 5s timeout)
    - Backward compatible: falls back to legacy file paths
"""

import json
import os
import re
import sys
import time
import hashlib
import signal
from datetime import datetime

# ── Timeout handler (fail-open) ──────────────────────────────────────

class TimeoutError(Exception):
    pass

def _timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def _timeout_wrapper(func, timeout=5, *args, **kwargs):
    """Execute func with a timeout. Returns (result, timed_out)."""
    # Signal-based timeout only on Unix
    if hasattr(signal, 'SIGALRM'):
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)
        try:
            result = func(*args, **kwargs)
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
            return result, False
        except TimeoutError:
            signal.signal(signal.SIGALRM, old_handler)
            return None, True
        except Exception:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
            raise
    else:
        # Windows fallback: no SIGALRM, just run normally
        try:
            result = func(*args, **kwargs)
            return result, False
        except Exception:
            raise

# ── Paths ────────────────────────────────────────────────────────────

HOME = os.path.expanduser("~")

IS_WINDOWS = os.name == "nt"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
STATE_DIR = os.path.join(PROJECT_ROOT, ".omc", "state")

# C4: Consolidated state file
CONSOLIDATED_STATE = os.path.join(STATE_DIR, "oracle-gate-state.json")

# Legacy paths (fallback)
LEGACY_REQUIRED = os.path.join(STATE_DIR, "oracle-gate-required")
LEGACY_APPROVED = os.path.join(STATE_DIR, "oracle-gate-approved")
LEGACY_ORACLE_VERDICT = os.path.join(STATE_DIR, "oracle-verdicts.md")
LEGACY_META_VERDICT = os.path.join(STATE_DIR, "meta-oracle-verdicts.md")
LEGACY_YAML = os.path.join(PROJECT_ROOT, ".claude", "harness.yaml")

# ── Consolidated state helpers ───────────────────────────────────────

def _load_consolidated_state():
    """Load all state from oracle-gate-state.json.
    
    Returns a dict with keys: enabled, captcha_required, captcha_approved,
    captcha_timestamp, oracle_verdict_valid, meta_verdict_valid, verdict_timestamp.
    
    On failure or timeout, returns empty dict (triggers fail-open fallback).
    
    C4: Single json.load replaces multiple file reads.
    """
    def _do_load():
        if os.path.isfile(CONSOLIDATED_STATE):
            with open(CONSOLIDATED_STATE, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    try:
        state, timed_out = _timeout_wrapper(_do_load, timeout=5)
        if timed_out:
            _flywheel_event("oracle_gate", "state_read_timeout", "P2")
            return {}
        if state is None:
            return {}  # File doesn't exist, will trigger fallback
        return state
    except Exception:
        _flywheel_event("oracle_gate", "state_read_error", "P2")
        return {}


def _save_consolidated_state(state_dict):
    """Write consolidated state to oracle-gate-state.json.
    
    C4: Single json.dump replaces multiple file writes.
    """
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = CONSOLIDATED_STATE + ".tmp." + str(os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, ensure_ascii=True)
        os.rename(tmp, CONSOLIDATED_STATE)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _cleanup_legacy_state_files():
    """After successful migration, optionally clean up old legacy files.
    Kept for backward compat during transition; safe to call repeatedly."""
    legacy_files = [
        LEGACY_REQUIRED, LEGACY_APPROVED,
    ]
    for path in legacy_files:
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass


# ── Feature gate ────────────────────────────────────────────────────

def _is_feature_enabled():
    """Check if oracle_gate feature is enabled.
    
    Uses consolidated state first, falls back to legacy yaml parsing.
    """
    # Try consolidated state first
    state = _load_consolidated_state()
    if state.get("enabled") is not None:
        return bool(state["enabled"])
    
    # Fallback: read harness.yaml directly
    if os.path.isfile(LEGACY_YAML):
        try:
            with open(LEGACY_YAML, "r", encoding="utf-8") as f:
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
    # L0
    if re.search(r"(?:\.claude/hooks/|\.claude/scripts/|settings\.json$|harness\.yaml$)", file_path):
        return True
    # L1
    if re.search(r"(?:AGENTS\.md$|kernel\.md$|CLAUDE\.md$)", file_path):
        return True
    # L2
    if re.search(r"(?:\.claude/reference/|\.claude/nodes/|\.claude/schemas/|feature-registry\.yaml$|anti-patterns\.md$|\.hooks/unified\.yaml$)", file_path):
        return True
    return False


# ── CAPTCHA bypass ──────────────────────────────────────────────────

def _check_captcha_bypass():
    """Content-verified + 5min freshness CAPTCHA check.
    
    C4: Uses consolidated state first, falls back to legacy files.
    """
    state = _load_consolidated_state()
    
    required = state.get("captcha_required", "")
    approved = state.get("captcha_approved", "")
    ts = state.get("captcha_timestamp", 0)
    
    if required and approved:
        # Check from consolidated state
        if required == approved:
            age = time.time() - ts
            if age <= 300:  # 5 minutes
                # Valid — consume (clear captcha fields, keep other state)
                state["captcha_required"] = ""
                state["captcha_approved"] = ""
                state["captcha_timestamp"] = 0
                _save_consolidated_state(state)
                return True
            else:
                # Expired — clear
                state["captcha_required"] = ""
                state["captcha_approved"] = ""
                state["captcha_timestamp"] = 0
                _save_consolidated_state(state)
                return False
        else:
            # Mismatch — clear
            state["captcha_required"] = ""
            state["captcha_approved"] = ""
            state["captcha_timestamp"] = 0
            _save_consolidated_state(state)
            return False
    
    # Fallback: legacy files
    if not (os.path.isfile(LEGACY_APPROVED) and os.path.isfile(LEGACY_REQUIRED)):
        return False

    try:
        with open(LEGACY_REQUIRED, "r", encoding="utf-8") as f:
            expected = f.read().strip().split("\n")[0]
        with open(LEGACY_APPROVED, "r", encoding="utf-8") as f:
            actual = f.read().strip().split("\n")[0]
    except OSError:
        return False

    if not expected or expected != actual:
        for p in (LEGACY_REQUIRED, LEGACY_APPROVED):
            try:
                os.remove(p)
            except OSError:
                pass
        return False

    # Check 5-minute freshness
    try:
        mtime = os.path.getmtime(LEGACY_REQUIRED)
        if time.time() - mtime > 300:
            for p in (LEGACY_REQUIRED, LEGACY_APPROVED):
                try:
                    os.remove(p)
                except OSError:
                    pass
            return False
    except OSError:
        return False

    # Valid bypass — consume files
    for p in (LEGACY_REQUIRED, LEGACY_APPROVED):
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
            content = f.read(4096)
    except OSError:
        return False

    if not re.search(r"(?:ACCEPT|APPROVED|approve|accept)", content):
        return False

    vdate = re.search(r"20\d{2}-\d{2}-\d{2}", content)
    if vdate:
        try:
            vts = datetime.strptime(vdate.group(0), "%Y-%m-%d").timestamp()
            if time.time() - vts < 86400:
                return True
        except (ValueError, OSError):
            pass
        return False
    return True


def _has_recent_verdict():
    """Check for recent ACCEPT verdict.
    
    C4: Uses consolidated state first, falls back to legacy verdict files.
    """
    state = _load_consolidated_state()
    
    oracle_valid = state.get("oracle_verdict_valid", False)
    meta_valid = state.get("meta_verdict_valid", False)
    verdict_ts = state.get("verdict_timestamp", 0)
    
    if (oracle_valid or meta_valid) and verdict_ts > 0:
        age = time.time() - verdict_ts
        if age < 86400:  # 24 hours
            return True
    
    # Fallback: legacy verdict files
    oracle_v = LEGACY_ORACLE_VERDICT
    meta_v = LEGACY_META_VERDICT
    return _check_verdict_file(oracle_v) or _check_verdict_file(meta_v)


# ── Autonomous mode detection ──────────────────────────────────────

def _check_auto_mode():
    markers = [
        os.path.join(STATE_DIR, "tokens", "autonomous.active"),
        os.path.join(STATE_DIR, "tokens", "lx-ghost.json"),
        os.path.join(STATE_DIR, "tokens", "lx-goal.json"),
    ]
    for marker in markers:
        if os.path.isfile(marker):
            return True
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
    # ── Enable check with fail-open timeout ──
    def _check_enabled():
        return _is_feature_enabled()

    try:
        enabled, timed_out = _timeout_wrapper(_check_enabled, timeout=5)
        if timed_out:
            _flywheel_event("oracle_gate", "timeout_fail_open", "P2")
            print(json.dumps({"continue": True}))
            return
    except Exception:
        _flywheel_event("oracle_gate", "error_fail_open", "P2")
        print(json.dumps({"continue": True}))
        return

    if not enabled:
        print(json.dumps({"continue": True}))
        return

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

    # Autonomous mode check
    if _check_auto_mode():
        _log_auto_mode_skip(file_path)
        msg = f"[oracle-gate] AUTO MODE: would have blocked {file_path}, recorded as skip"
        print(msg, file=sys.stderr)
        print(json.dumps({"continue": True}))
        return

    # Block
    captcha = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
    os.makedirs(STATE_DIR, exist_ok=True)
    
    # Write both consolidated state and legacy file for backward compat
    try:
        with open(os.path.join(STATE_DIR, "oracle-gate-required"), "w") as f:
            f.write(captcha)
    except OSError:
        pass
    
    # Also write to consolidated state
    state = _load_consolidated_state()
    state["captcha_required"] = captcha
    state["captcha_approved"] = ""
    state["captcha_timestamp"] = time.time()
    _save_consolidated_state(state)

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
