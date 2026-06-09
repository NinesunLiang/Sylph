#!/usr/bin/env python3
"""
harness_core.py — 共享库核心（Python 版）
高频函数: hc_enabled, output_continue, read_input, flywheel_event, hc_get
用于频繁调用的 hook，减少 import 开销。

版本对照：harness_config.sh v6.6.4 → harness_core.py v1.0
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── Constants ───

_HOOKS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = (_HOOKS_DIR / "../..").resolve()
_STATE_DIR = _PROJECT_ROOT / ".omc" / "state"
_EVIDENCE_FILE = _STATE_DIR / "hook-evidence.jsonl"
_HC_CACHE = _STATE_DIR / ".harness-cache"
_HC_YAML = _PROJECT_ROOT / ".claude" / "harness.yaml"
_FLYWHEEL_LOG = Path.home() / ".claude" / "flywheel.log"
_PYTHON_CACHE = Path.home() / ".carror-python-path"

HC_SESSION_ID = os.environ.get("HC_SESSION_ID", "unknown")
HC_EVENT_NAME = os.environ.get("HC_EVENT_NAME", "unknown")


# ─── Cross-platform Python binary resolution ───

def _resolve_python_bin():
    """Resolve Python binary path. Priority: env var > file cache > PATH > glob scan"""
    cached = os.environ.get("PYTHON_BIN", "")
    if cached:
        return cached

    # Fast path: cached result from file
    if _PYTHON_CACHE.exists():
        try:
            cached_path = _PYTHON_CACHE.read_text(encoding="utf-8").strip()
            if cached_path and os.path.isfile(cached_path) and os.access(cached_path, os.X_OK):
                return cached_path
        except Exception:
            pass

    # Step 1: bash PATH
    import shutil
    py3 = shutil.which("python3")
    if py3:
        _PYTHON_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _PYTHON_CACHE.write_text(py3, encoding="utf-8")
        return py3

    py = shutil.which("python")
    if py:
        _PYTHON_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _PYTHON_CACHE.write_text(py, encoding="utf-8")
        return py

    # Step 2-3: Windows paths (fallback)
    for p in [
        "/c/Python3*/python.exe", "/c/Python3*/python3.exe",
        "/c/Program Files/Python3*/python.exe",
        "/c/Users/*/AppData/Local/Programs/Python/Python3*/python.exe",
    ]:
        matches = list(Path("/").glob(p.lstrip("/")))
        if matches:
            _PYTHON_CACHE.parent.mkdir(parents=True, exist_ok=True)
            _PYTHON_CACHE.write_text(str(matches[0]), encoding="utf-8")
            return str(matches[0])

    return "python3"


PYTHON_BIN = _resolve_python_bin()


# ─── hc_get: read key from harness cache ───

_HC_CACHE_LOADED = None


def _ensure_cache():
    """Load harness cache into a dict if fresh/valid. Returns dict or empty dict."""
    global _HC_CACHE_LOADED

    if _HC_CACHE_LOADED == "ready":
        return _load_cache_file()
    if _HC_CACHE_LOADED == "empty":
        return {}

    _STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Cache exists and contains sentinel
    if _HC_CACHE.exists() and _HC_CACHE.stat().st_size > 0:
        content = _HC_CACHE.read_text(encoding="utf-8", errors="replace")
        if "__parsed_count__=" in content:
            if not _HC_YAML.exists():
                _HC_CACHE_LOADED = "ready"
                return _parse_cache_content(content)
            if _HC_CACHE.stat().st_mtime >= _HC_YAML.stat().st_mtime:
                _HC_CACHE_LOADED = "ready"
                return _parse_cache_content(content)
            else:
                # yaml newer — rebuild
                pass
        else:
            # missing sentinel — rebuild
            _HC_CACHE.unlink(missing_ok=True)

    # Rebuild cache from yaml
    if not _HC_YAML.exists():
        _HC_CACHE_LOADED = "empty"
        return {}

    data = _parse_yaml_simple(str(_HC_YAML))
    min_keys = int(os.environ.get("HC_MIN_PARSED_KEYS", "50"))
    if len(data) < min_keys:
        sys.stderr.write(f"[harness_lib] YAML parse possibly failed: {len(data)} keys < {min_keys} threshold.\n")
        _HC_CACHE.write_text("", encoding="utf-8")
        _HC_CACHE_LOADED = "empty"
        return {}

    _write_cache(data)
    _HC_CACHE_LOADED = "ready"
    return data


def _load_cache_file():
    """Load cache dict from disk file."""
    if not _HC_CACHE.exists():
        return {}
    content = _HC_CACHE.read_text(encoding="utf-8", errors="replace")
    return _parse_cache_content(content)


def _parse_cache_content(content):
    """Parse cache key=value lines into dict."""
    result = {}
    for line in content.splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        result[key] = val
    return result


def _write_cache(data):
    """Write cache dict to disk."""
    lines = [f"__parsed_count__={len(data)}"]
    for k, v in sorted(data.items()):
        escaped_val = str(v).replace("\n", "\\n")
        lines.append(f"{k}={escaped_val}")
    # Atomic write: tmp + rename
    tmp_path = _HC_CACHE.with_suffix(".tmp")
    _HC_CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp_path.rename(_HC_CACHE)


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


# ─── Hook runtime evidence tracking ───

def _write_evidence(name, event="hc_enabled", exit_code=0):
    """Write evidence entry to hook-evidence.jsonl."""
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        entry = json.dumps({
            "hook": name,
            "ts": ts,
            "session": HC_SESSION_ID,
            "event": HC_EVENT_NAME,
            "exit": exit_code
        }, ensure_ascii=True)
        with open(str(_EVIDENCE_FILE), "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


# ─── hc_enabled: check feature enablement ───

def hc_enabled(feature_name):
    """Check if a feature is enabled in harness.yaml (default: True).

    Checks hooks_enabled.{name} (hyphen→underscore) first,
    then skills_enabled.{name} (native name), returns True if not explicitly false.
    """
    hook_key = feature_name.replace("-", "_")

    val = hc_get(f"hooks_enabled.{hook_key}", "")
    if val:
        result = val.strip().lower() == "true"
        if result:
            _write_evidence(feature_name, "hc_enabled", 0)
        return result

    val = hc_get(f"skills_enabled.{feature_name}", "")
    if val:
        result = val.strip().lower() == "true"
        if result:
            _write_evidence(feature_name, "hc_enabled", 0)
        return result

    # Default enabled
    _write_evidence(feature_name, "hc_enabled", 0)
    return True


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


# ─── read_input: 从 stdin 读取完整输入 ───

READ_BUFFER = []


def read_input():
    """从 stdin 读取完整输入（兼容 hc_read_config），返回字符串。"""
    if READ_BUFFER:
        return READ_BUFFER.pop(0)
    try:
        return sys.stdin.read()
    except Exception:
        return ""


# ─── output_continue: 标准 continue 输出 ───

def output_continue():
    """输出 continue JSON（等价的简短函数名）"""
    hc_emit_hook_json("ok")


# ─── flywheel_event: ROI event logging ───

def flywheel_event(hook_name="unknown", event_type="triggered", severity="P2", project="carror-os"):
    """Log structured event to ~/.claude/flywheel.log."""
    log_dir = Path.home() / ".claude"
    log_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(str(_FLYWHEEL_LOG), "a", encoding="utf-8") as f:
            f.write(f"{date_str},{hook_name}_{event_type},{severity},{project}\n")
    except Exception:
        pass
