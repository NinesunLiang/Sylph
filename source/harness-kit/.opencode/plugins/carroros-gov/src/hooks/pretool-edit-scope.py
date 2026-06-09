#!/usr/bin/env python3
"""
pretool-edit-scope.py — PreToolUse:Edit|Write — Scope management + Rule anchor + completion-blocked reminder (DG-131)
Role: Scope file matching + auto-add + core file warning + long conversation rule anchoring + no-evidence completion reminder
Replaces pretool-edit-scope.sh (DG-105 cross-platform Python migration)

Behavior: hard-block → auto-add (transparently add affected files to scope)
Inherits pretool-rule-anchor drift protection for long conversations.
"""

import fnmatch
import json
import os
import re
import sys
import time
from pathlib import Path

# ── Import shared library ──
_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, is_mode_active, flywheel_event, hc_get


# ── Path constants ──
SCRIPT_DIR = _HOOKS_DIR
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
SCOPE_FILE = STATE_DIR / "current-scope.txt"
BLOCKED_FILE = STATE_DIR / "completion-blocked"
TURN_FILE = STATE_DIR / "session-turns.json"
EDIT_LOG_FILE = STATE_DIR / "session-edit-log.txt"
LAST_PROMPT_FILE = STATE_DIR / ".last-user-prompt"
COUPLING_MAP = STATE_DIR / "coupling-map.json"


# ── Helper: read stdin ──

def read_stdin() -> str:
    """Read full stdin."""
    return sys.stdin.read()


# ── Helper: extract file_path from tool input ──

def extract_file_path(input_str: str) -> str:
    """Extract file_path from PreToolUse stdin JSON.

    Tries tool_input.file_path → tool_input.args.filePath → args.filePath.
    Returns empty string on failure.
    """
    if not input_str:
        return ""
    try:
        data = json.loads(input_str)
    except json.JSONDecodeError:
        return ""

    ti = data.get("tool_input", {})
    if not isinstance(ti, dict):
        ti = {}

    # Direct file_path
    fp = ti.get("file_path", "")
    if fp:
        return fp

    # args dict inside tool_input
    args = ti.get("args", data.get("args", {}))
    if isinstance(args, dict):
        fp = args.get("filePath", "")
        if fp:
            return fp
        fp = args.get("file_path", "")
        if fp:
            return fp

    return ""


# ── completion-blocked detection ──

def check_completion_blocked():  # type: () -> str | None
    """Check .omc/state/completion-blocked state file.

    Returns None (no block) or a warning string to include in additionalContext.
    Follows same logic as shell version: >5min or >=2 blocks → auto-clear.
    """
    if not BLOCKED_FILE.exists():
        return None

    try:
        with open(str(BLOCKED_FILE), encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        # Invalid file → clear
        _safe_remove(BLOCKED_FILE)
        return None

    now = time.time()
    blocked_at = data.get("blocked_at", 0)
    count = data.get("block_count", 0)
    age = now - blocked_at

    if age > 300 or count >= 2:
        # Auto-clear (anti-deadlock)
        _safe_remove(BLOCKED_FILE)
        return None

    # Increment block count
    count += 1
    data["block_count"] = count
    try:
        with open(str(BLOCKED_FILE), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass

    flywheel_event("pretool_edit_scope", f"completion_blocked_turn{count}", "P2")
    return (
        f"⚠️ [completion-blocked·第{count}轮] Reminder: you tried to mark "
        f"TaskUpdate(completed) without VERIFIED evidence.\n"
        f"Please: (1) run a verification command (2) cite output with VERIFIED: [已测试: ...] tag "
        f"(3) retry TaskUpdate(completed).\n"
        f"Note: pre-completion-gate still hard-blocks TaskUpdate(completed). "
        f"This Edit/Write warning stops after 2 rounds, but evidence is required to mark complete."
    )


def _safe_remove(path: Path):
    """Remove file if exists, ignore errors."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


# ── Protected file warning (stderr only) ──

def warn_protected_file(basename: str):
    """Emit core file warning to stderr if basename matches protected list."""
    protected = hc_get("protected_files.warn_on_edit", "package.json go.mod Cargo.toml main.go pom.xml")
    for f_name in protected.split():
        if basename == f_name:
            flywheel_event("pretool_edit_scope", "protected_file_warn", "P2")
            print(
                f"⚠️ 正在编辑核心文件: {basename}。"
                f"请确认已声明影响范围并获得用户确认(§6.2)。",
                file=sys.stderr,
            )
            break


# ── Rule anchor check: drift detection for long sessions ──

def rule_anchor_check():
    """Long conversation rule anchoring — merged from pretool-rule-anchor.sh.

    Emits reminders to stderr every N turns beyond threshold, with drift signal detection.
    """
    if not TURN_FILE.exists():
        return

    try:
        with open(str(TURN_FILE), encoding="utf-8") as f:
            turn_data = json.load(f)
        current_turn = int(turn_data.get("count", 0))
    except (json.JSONDecodeError, ValueError, OSError):
        return

    threshold = int(hc_get("rule_anchor.turn_threshold", "15"))
    interval = int(hc_get("rule_anchor.interval", "5"))

    if current_turn < threshold:
        return

    offset = current_turn - threshold
    if interval > 0 and offset % interval != 0:
        return

    # Detect drift signal words in last user prompt
    drift_detected = False
    drift_words = ["顺手", "顺便", "另外也", "同时也", "顺带", "捎带"]
    if LAST_PROMPT_FILE.exists():
        try:
            last_prompt = LAST_PROMPT_FILE.read_text(encoding="utf-8", errors="replace")
            for word in drift_words:
                if word in last_prompt:
                    drift_detected = True
                    break
        except OSError:
            pass

    if drift_detected:
        print(
            f"⚠️ [第{current_turn}轮·漂移预警] 检测到范围扩展词。"
            f"只改当前任务文件，额外问题记 TODO。",
            file=sys.stderr,
        )
    else:
        print(
            f"📌 [第{current_turn}轮·规则锚定] 长会话提醒："
            f"①file:line ②VERIFIED证据 ③git批准 ④范围冻结 ⑤3轮上限 ⑥改动可追溯",
            file=sys.stderr,
        )


# ── Coupling reminder ──

def coupling_remind(rel_path: str):
    """Check coupling-map.json and emit coupled file reminders to stderr.

    Mirrors the shell version's python -c inline script.
    """
    coupling_enabled = hc_get("coupling.enabled", "true")
    if coupling_enabled.lower() != "true":
        return

    if not COUPLING_MAP.exists():
        return

    try:
        with open(str(COUPLING_MAP), encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    file_coupling = data.get("file_coupling", {})
    coupled = file_coupling.get(rel_path, [])

    # Try stripped match
    if not coupled:
        rel_stripped = rel_path.lstrip("./")
        for key, values in file_coupling.items():
            if key.lstrip("./") == rel_stripped:
                coupled = values
                break

    if not coupled:
        return

    source = data.get("source", "git_co_change")

    if source == "static_import_analysis":
        lines = []
        for entry in coupled[:5]:
            reason = entry.get("reason", "")
            label = f"({reason})" if reason else ""
            lines.append(f" - {entry['file']} {label}")
        print(f"[耦合提醒] 编辑 {rel_path} 时，以下文件可能需要同步检查:", file=sys.stderr)
        for line in lines:
            print(line, file=sys.stderr)
    else:
        file_list = ", ".join(
            f"{e['file']}({e.get('count', 1)}次)" for e in coupled[:5]
        )
        print(
            f"[耦合提醒] {rel_path} 历史上常与以下文件一起变更: {file_list}",
            file=sys.stderr,
        )


# ── Auto-scope fallback ──

def run_auto_scope() -> str:
    """Run auto-scope.sh if available; returns stderr message or empty string."""
    auto_script = PROJECT_ROOT / ".claude" / "scripts" / "auto-scope.sh"
    if auto_script.exists():
        import subprocess
        try:
            result = subprocess.run(
                ["bash", str(auto_script)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            msg = result.stderr.strip() or result.stdout.strip()
            return msg or "已完成自动推导"
        except (OSError, subprocess.TimeoutExpired):
            pass
    return "无 auto-scope 脚本"


# ── Record to session edit log ──

def record_edit_log(rel_path: str):
    """Append path to session edit log, skipping /tmp/ files."""
    if rel_path.startswith("/tmp/"):
        return
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(str(EDIT_LOG_FILE), "a", encoding="utf-8") as f:
            f.write(f"{rel_path}\n")
    except OSError:
        pass


# ── Scope match ──

def is_in_scope(rel_path: str, basename: str, patterns: list[str]) -> bool:
    """Check if path matches any scope pattern (glob, basename, or directory prefix)."""
    for pattern in patterns:
        if not pattern.strip():
            continue
        # Trim whitespace
        p = pattern.strip()

        # Direct fnmatch
        if fnmatch.fnmatch(rel_path, p):
            return True
        # Wildcard prefix (e.g. glob but with implicit */ prefix)
        if fnmatch.fnmatch(rel_path, "*" + p):
            return True
        # Basename match (for auto-scope that only generates basename)
        if "/" not in p and fnmatch.fnmatch(basename, p):
            return True
        # Directory prefix (pattern ends with / or /*)
        if p.endswith("/") and rel_path.startswith(p):
            return True
        if p.endswith("/*") and rel_path.startswith(p[:-2]):
            return True
    return False


# ── Read scope patterns ──

def read_scope_patterns() -> list[str]:
    """Read non-empty, non-comment lines from scope file."""
    if not SCOPE_FILE.exists():
        return []
    patterns = []
    try:
        with open(str(SCOPE_FILE), encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    patterns.append(stripped)
    except OSError:
        pass
    return patterns


# ── Main ──

def main():
    # ── Feature gate ──
    if not hc_enabled("pretool_edit_scope"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Read input ──
    input_str = read_stdin()
    if not input_str:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── completion-blocked check ──
    blocked_msg = check_completion_blocked()
    if blocked_msg:
        result = {
            "continue": True,
            "additionalContext": blocked_msg,
        }
        print(json.dumps(result, ensure_ascii=True))
        sys.exit(0)

    # ── Extract file_path ──
    file_path = extract_file_path(input_str)
    if not file_path:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    basename = os.path.basename(file_path)
    rel_path = file_path
    if str(PROJECT_ROOT) in file_path:
        rel_path = file_path.replace(str(PROJECT_ROOT), "").lstrip("/")

    # ── Protected file warning ──
    warn_protected_file(basename)

    # ── Mode detection ──
    mode = is_mode_active(str(STATE_DIR))

    # ── No scope file → auto-scope + pass through ──
    if not SCOPE_FILE.exists():
        auto_msg = run_auto_scope()
        print(f"ℹ️  auto-scope: {auto_msg}", file=sys.stderr)
        coupling_remind(rel_path)
        rule_anchor_check()
        record_edit_log(rel_path)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Read scope patterns ──
    patterns = read_scope_patterns()

    # ── Scope matching ──
    if is_in_scope(rel_path, basename, patterns):
        coupling_remind(rel_path)
        rule_anchor_check()
        record_edit_log(rel_path)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Not in scope → auto-add (non-blocking) ──
    coupling_remind(rel_path)

    if mode != "normal":
        flywheel_event("pretool_edit_scope", f"scope_autoexpand_{mode}", "P3", f"file={rel_path}")
        print(
            f"ℹ️ [scope|{mode}] {rel_path} 自动加入编辑范围（无人值守模式，范围自动扩展）",
            file=sys.stderr,
        )
    else:
        print(
            f"ℹ️ [scope] {rel_path} 自动加入编辑范围（之前未在 scope 中）",
            file=sys.stderr,
        )

    # Append to scope file
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(str(SCOPE_FILE), "a", encoding="utf-8") as f:
            f.write(f"{rel_path}\n")
    except OSError:
        pass

    record_edit_log(rel_path)
    rule_anchor_check()

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
