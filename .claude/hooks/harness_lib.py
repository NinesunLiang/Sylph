#!/usr/bin/env python3
"""
harness_lib.py — 共享库（Python 版）
提供 hc_enabled, is_mode_active, hc_get, flywheel_event, agentic_menu 等函数
对应 harness_config.sh + agentic-ui.sh 的 Python 移植
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── Path resolution ───

_HOOKS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = (_HOOKS_DIR / "../..").resolve()
_STATE_DIR = _PROJECT_ROOT / ".omc" / "state"
_HC_CACHE = _STATE_DIR / ".harness-cache"
_HC_YAML = _PROJECT_ROOT / ".claude" / "harness.yaml"


# ─── hc_get: read key from harness cache ───

def _ensure_cache():
    """Load harness cache into a dict if fresh/valid. Returns dict or empty dict."""
    result = {}
    if _HC_CACHE.exists() and _HC_CACHE.stat().st_size > 0:
        content = _HC_CACHE.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            line = line.strip()
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            result[key] = val
        # Check sentinel
        if "__parsed_count__" in result:
            # Check freshness: cache newer than yaml or no yaml
            if not _HC_YAML.exists() or _HC_CACHE.stat().st_mtime >= _HC_YAML.stat().st_mtime:
                return result
    # Cache miss or stale: try rebuild
    if not _HC_YAML.exists():
        return {}
    # Try python yaml rebuild (same logic as shell: simple parser, no PyYAML dependency)
    try:
        data = _parse_yaml_simple(str(_HC_YAML))
        if len(data) >= 50:  # min_keys threshold
            _STATE_DIR.mkdir(parents=True, exist_ok=True)
            lines = [f"__parsed_count__={len(data)}"]
            for k, v in sorted(data.items()):
                escaped_val = v.replace(chr(10), '\\n')
                lines.append(f"{k}={escaped_val}")
            _HC_CACHE.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return data
    except Exception:
        pass
    return {}


def _parse_yaml_simple(path):
    """Simple 2-level YAML parser (no PyYAML dependency) — mirrors harness_config.sh logic."""
    result = {}
    current_section = ""
    current_list_key = ""
    current_list = []

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n\r")
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                if current_list_key and current_list:
                    result[current_list_key] = " ".join(current_list)
                    current_list_key = ""
                    current_list = []
                continue

            indent = len(line) - len(line.lstrip())

            if stripped.startswith("- "):
                if current_list_key:
                    item = stripped[2:].strip().strip("\"").strip("'")
                    current_list.append(item)
                continue

            if current_list_key and current_list:
                result[current_list_key] = " ".join(current_list)
                current_list_key = ""
                current_list = []

            if ":" in stripped:
                colon_idx = stripped.index(":")
                key = stripped[:colon_idx].strip()
                value = stripped[colon_idx + 1:].strip()

                if value and value[0] in ("\"", "'") and value[-1] == value[0]:
                    value = value[1:-1]

                if indent == 0:
                    if value:
                        result[key] = value
                    else:
                        current_section = key
                elif indent > 0 and current_section:
                    flat_key = f"{current_section}.{key}"
                    if value:
                        result[flat_key] = value
                    else:
                        current_list_key = flat_key
                        current_list = []

    if current_list_key and current_list:
        result[current_list_key] = " ".join(current_list)

    return result


def hc_get(key, default=""):
    """Read config value from harness cache."""
    cache = _ensure_cache()
    return cache.get(key, default)


# ─── hc_enabled ───

def hc_enabled(feature_name):
    """Check if a feature is enabled in harness.yaml (default: True).

    Checks hooks_enabled.{name} (hyphen→underscore) first,
    then skills_enabled.{name} (native name), returns True if not explicitly false.
    """
    hook_key = feature_name.replace("-", "_")

    val = hc_get(f"hooks_enabled.{hook_key}", "")
    if val:
        return val.strip().lower() == "true"

    val = hc_get(f"skills_enabled.{feature_name}", "")
    if val:
        return val.strip().lower() == "true"

    # Default enabled
    return True


# ─── is_mode_active: Ghost / Goal mode detection ───

def is_mode_active(state_dir=None):
    """Detect active execution mode.

    Returns 'ghost', 'goal', or 'normal'.

    Priority: ghost > goal > normal
    New format: lx-ghost.json / lx-goal.json in tokens/ subdir
    Legacy: ghost-mode.json, ghost-mode.active, unattended-mode.json, .unattended-mode
    """
    if state_dir is None:
        state_dir = str(_STATE_DIR)

    now = datetime.now(timezone.utc)
    state_path = Path(state_dir)

    def _check_token_json(filepath):
        """Check a JSON token file for active status. Returns 'active', 'expired', or None."""
        fp = Path(filepath)
        if not fp.exists():
            return None
        try:
            data = json.loads(fp.read_text(encoding="utf-8", errors="replace"))
            expires = data.get("expires_at", "")
            if not expires:
                return "active"
            exp = datetime.fromisoformat(expires)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now < exp:
                return "active"
            # expired — clean up
            fp.unlink(missing_ok=True)
            return "expired"
        except Exception:
            return "invalid"

    # Check lx-ghost.json (new format)
    result = _check_token_json(str(state_path / "tokens" / "lx-ghost.json"))
    if result == "active":
        return "ghost"

    # Check ghost-mode.json (legacy)
    result = _check_token_json(str(state_path / "ghost-mode.json"))
    if result == "active":
        return "ghost"

    # Check ghost-mode.active (plain file marker)
    if (state_path / "ghost-mode.active").exists():
        return "ghost"

    # Check lx-goal.json (new format)
    result = _check_token_json(str(state_path / "tokens" / "lx-goal.json"))
    if result == "active":
        return "goal"

    # Check unattended-mode.json (legacy)
    result = _check_token_json(str(state_path / "unattended-mode.json"))
    if result == "active":
        return "goal"

    # Check .unattended-mode (plain file marker)
    if (state_path / ".unattended-mode").exists():
        return "goal"

    return "normal"


# ─── flywheel_event: ROI event logging ───

def flywheel_event(hook_name="unknown", event_type="triggered", severity="P2", project="carror-os"):
    """Log structured event to ~/.claude/flywheel.log."""
    log_dir = Path.home() / ".claude"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "flywheel.log"
    date_str = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(str(log_path), "a", encoding="utf-8") as f:
            f.write(f"{date_str},{hook_name}_{event_type},{severity},{project}\n")
    except Exception:
        pass


# ─── hc_emit_hook_json: safe JSON hook response ───

def hc_emit_hook_json(text, event="PreToolUse", continue_val=True):
    """Emit a JSON hook response with safe escaping."""
    # Strip lone surrogates
    text = "".join(c for c in text if not 0xD800 <= ord(c) <= 0xDFFF)
    # Replace literal \\uDxxx escape sequences
    text = re.sub(r'\\*\\u[Dd][89a-fA-F][0-9a-fA-F]{2}', 'U+FFFD', text)
    result = {
        "continue": continue_val,
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": text.strip()
        }
    }
    return json.dumps(result, ensure_ascii=True)


# ─── agentic_menu: standardized menu output ───

def agentic_menu(title, reason, opt1_label, opt1_desc, opt2_label, opt2_desc,
                 opt3_label="取消操作", opt3_desc="不执行任何操作"):
    """Output a menu prompt (mimics agentic-ui.sh agentic_menu)."""
    flywheel_event("agentic_ui", "menu_shown", "P2", title)
    menu_text = f"""

📋 [{title}]
═══════════════════════════════════════════════════════════════
原因：{reason}

请选择：
  1. {opt1_label} — {opt1_desc}
  2. {opt2_label} — {opt2_desc}
  3. {opt3_label} — {opt3_desc}

输入数字 (1-3):
"""
    print(menu_text, file=sys.stderr, flush=True)
    sys.exit(2)
