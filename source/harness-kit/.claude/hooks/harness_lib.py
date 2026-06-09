#!/usr/bin/env python3
"""
harness_lib.py — 共享库（Python 版）
提供 hc_enabled, hc_get, is_mode_active, flywheel_event, agentic_menu 等函数
完全等价 harness_config.sh + agentic-ui.sh, 跨平台通用。

版本对照：harness_config.sh v6.6.4 → harness_lib.py v1.0
"""

import json
import os
import re
import secrets
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

# ─── hc_init: 标准路径变量初始化（替代各 hook 内联的 SCRIPT_DIR/PROJECT_ROOT/STATE_DIR）───
# 用法: from harness_lib import hc_init; SCRIPT_DIR, PROJECT_ROOT, STATE_DIR = hc_init()
# 效果: 返回标准路径三元组 + 自动 mkdir -p STATE_DIR

HC_SESSION_ID = os.environ.get("HC_SESSION_ID", "unknown")
HC_EVENT_NAME = os.environ.get("HC_EVENT_NAME", "unknown")


def hc_init(caller_path=None):
    """初始化标准路径变量。返回 (SCRIPT_DIR, PROJECT_ROOT, STATE_DIR)。
    
    如果 caller_path 传入，SCRIPT_DIR 基于调用者文件路径；
    否则从 _HOOKS_DIR 推断。
    """
    if caller_path:
        script_dir = Path(caller_path).resolve().parent
    else:
        script_dir = _HOOKS_DIR

    # 向上找 PROJECT_ROOT（.claude 目录的父目录）
    project_root = _PROJECT_ROOT
    state_dir = project_root / ".omc" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return str(script_dir), str(project_root), str(state_dir)


# ─── Cross-platform Python binary resolution ───

def _resolve_python_bin():
    """解析 Python 二进制路径。优先: env var > file cache > PATH > glob scan"""
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


# Cache the resolved path
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

    # 缓存已存在且含 sentinel
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
        sys.stderr.write(f"[harness_lib] YAML 解析疑似失败: {len(data)} keys < {min_keys} 阈值。\n")
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


def hc_get_list(key, default=""):
    """Read list value from harness cache (space-separated)."""
    return hc_get(key, default)


# --- hc_fail_closure: fail-close 自检（C5 分层失败策略）---
# 检查 harness.yaml 的 fail_closure.<层级> 是否为 "close"
# 如果 yaml 缺失该配置项 => exit(2)（默认 fail-close）
# 如果显式 "open" => 返回 False（放行，不阻断）
def hc_fail_closure(gate_name: str) -> bool:
    """C5: 检查指定安全门禁是否应 fail-close。

    返回 True（应阻断）的条件：
    - yaml 中 gate 未配置（默认 fail-close，最小权限原则 #6）
    - yaml 中 gate 显式设为 close
    返回 False（放行）的条件：
    - yaml 中 gate 显式设为 open
    异常情况（文件不存在/解析失败）：exit(2) 硬阻断
    """
    _YAML_PATH = _PROJECT_ROOT / ".claude" / "harness.yaml"
    if not _YAML_PATH.is_file():
        print(f"\u26d4 [C5] {_YAML_PATH} \u4e0d\u5b58\u5728\uff0c\u65e0\u6cd5\u68c0\u67e5 fail_closure.{gate_name}", file=sys.stderr)
        sys.exit(2)
    try:
        cache = _ensure_cache()
        val = cache.get(f"fail_closure.{gate_name}", "").strip().lower()
        if not val:
            return True
        if val == "close":
            return True
        if val == "open":
            return False
        print(f"\u26d4 [C5] fail_closure.{gate_name} \u914d\u7f6e\u503c\u5f02\u5e38: {val}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"\u26d4 [C5] fail_closure.{gate_name} \u8bfb\u53d6\u5931\u8d25: {e}", file=sys.stderr)
        sys.exit(2)


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


def hc_hook_enabled(hook_name):
    """Check only hooks_enabled (default True, auto hyphen→underscore)."""
    hook_key = hook_name.replace("-", "_")
    val = hc_get(f"hooks_enabled.{hook_key}", "true")
    return val.strip().lower() == "true"


def hc_skill_enabled(skill_name):
    """Check only skills_enabled (default True, native name)."""
    val = hc_get(f"skills_enabled.{skill_name}", "true")
    return val.strip().lower() == "true"


def hc_project_root():
    """Return project root path."""
    return str(_PROJECT_ROOT)


def hc_state_dir():
    """Return state directory path."""
    return str(_STATE_DIR)


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
        """Check a JSON token file for active status."""
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


# ─── Mode state management ───

def _mode_file_for(state_dir, mode):
    """Return mode state file path."""
    sp = Path(state_dir)
    if mode == "ghost":
        return str(sp / "tokens" / "lx-ghost.json")
    elif mode == "goal":
        return str(sp / "tokens" / "lx-goal.json")
    elif mode == "unattended":
        return str(sp / "unattended-mode.json")
    else:
        return str(sp / f"{mode}-mode.json")


def _mode_append_to_list(state_dir, mode, field, json_value):
    """Atomically append JSON value to a list field in mode status file."""
    filepath = _mode_file_for(state_dir, mode)
    if not os.path.isfile(filepath):
        return
    try:
        if isinstance(json_value, str):
            try:
                value = json.loads(json_value)
            except json.JSONDecodeError:
                value = json_value
        else:
            value = json_value
        with open(filepath, "r", encoding="utf-8") as f:
            d = json.load(f)
        lst = d.get(field, [])
        lst.append(value)
        d[field] = lst
        tmp = filepath + ".tmp." + str(os.getpid())
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        os.rename(tmp, filepath)
    except Exception:
        pass


def _mode_increment_field(state_dir, mode, field):
    """Atomically increment a numeric field in mode status file."""
    filepath = _mode_file_for(state_dir, mode)
    if not os.path.isfile(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            d = json.load(f)
        d[field] = d.get(field, 0) + 1
        tmp = filepath + ".tmp." + str(os.getpid())
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        os.rename(tmp, filepath)
    except Exception:
        pass


# ─── Mode-aware Gate functions ───

def hc_gate_mode_warn(gate_name="unknown"):
    """非 normal 模式时降级 gate 为 warn-only.
    返回 True=应降级跳过, False=继续正常门禁逻辑
    """
    mode = is_mode_active(str(_STATE_DIR))
    if mode != "normal":
        sys.stderr.write(f"[{gate_name}] WARN: {mode} mode — gate skipped (mode downgrade)\n")
        flywheel_event(gate_name, "mode_warn", "P2")
        return True
    return False


def hc_gate_mode_block(gate_name="unknown"):
    """非 normal 模式时硬阻断。
    返回 True=应阻断, False=继续正常
    """
    mode = is_mode_active(str(_STATE_DIR))
    if mode != "normal":
        sys.stderr.write(f"[{gate_name}] BLOCKED: {mode} mode — gate enforced\n")
        flywheel_event(gate_name, "mode_blocked", "P1")
        return True
    return False


# ─── Token/CAPTCHA generator ───

def hc_generate_token(length=8):
    """Generate random hex token with 4-level fallback."""
    byte_count = length // 2
    try:
        return secrets.token_hex(byte_count)
    except Exception:
        pass
    try:
        import subprocess
        result = subprocess.run(
            ["od", "-vAn", "-N", str(byte_count), "-tx1", "/dev/urandom"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.replace(" ", "").replace("\n", "")
    except Exception:
        pass
    try:
        import subprocess
        result = subprocess.run(
            ["openssl", "rand", "-hex", str(byte_count)],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    # Last resort
    import hashlib
    h = hashlib.sha256(f"{os.getpid()}{time.time()}".encode()).hexdigest()
    return h[:length]


def hc_captcha_check(required_file, approved_file, freshness_sec=300):
    """Check CAPTCHA token + freshness.
    Returns True=passed, False=not passed.
    """
    if not os.path.isfile(required_file):
        return False
    if not os.path.isfile(approved_file):
        return False
    try:
        with open(required_file, "r") as f:
            expected = f.read().strip()
        with open(approved_file, "r") as f:
            approved = f.read().strip()
        if not expected or expected != approved:
            return False
        age = time.time() - os.path.getmtime(approved_file)
        return age < freshness_sec
    except Exception:
        return False


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


# ─── UTF-8 sanitization ───

def hc_sanitize_utf8(text, source="unknown"):
    """Sanitize UTF-8 text: strip lone surrogates, replace \\uDxxx escapes.
    Returns sanitized text. Logs replacements to sanitizer-log.jsonl.
    """
    original_len = len(text)
    text = "".join(c for c in text if not 0xD800 <= ord(c) <= 0xDFFF)
    surrogate_stripped = original_len - len(text)

    replacements = []
    def _replace_and_log(m):
        matched = m.group(0)
        hex_val = m.group(1).upper()
        safe = "U+" + hex_val
        replacements.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "match_hex": hex_val,
            "replacement": safe,
            "position": m.start(),
        })
        return safe

    text = re.sub(r'\\*\\u([Dd][89a-fA-F][0-9a-fA-F]{2})', _replace_and_log, text)

    # Write sanitizer log if any changes
    if replacements or surrogate_stripped > 0:
        log_dir = _STATE_DIR if _STATE_DIR.exists() else Path.home() / ".claude"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "sanitizer-log.jsonl"
        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "surrogate_chars_stripped": surrogate_stripped,
            "text_replacements": len(replacements),
            "details": replacements[:50]
        }
        try:
            with open(str(log_path), "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    return text


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


# ─── Gate output macros ───

def hc_gate_block(name="gate", stderr_msg="blocked"):
    """Standard block output: stderr for human, stdout JSON for AI, exit 2."""
    sys.stderr.write(f"[{name}] {stderr_msg}\n")
    flywheel_event(name, "blocked", "P1")
    print(json.dumps({"continue": False, "reason": stderr_msg}))
    sys.exit(2)


def hc_gate_warn_output(name="gate", stderr_msg="warning"):
    """Standard warn output."""
    sys.stderr.write(f"[{name}] {stderr_msg}\n")
    flywheel_event(name, "warn", "P2")


def hc_gate_pass():
    """Standard pass output."""
    print(json.dumps({"continue": True}))
    sys.exit(0)


# ─── agentic_menu: standardized menu output ───

def agentic_menu(title, reason, opt1_label, opt1_desc, opt2_label, opt2_desc,
                 opt3_label="取消操作", opt3_desc="不执行任何操作"):
    """Output a menu prompt (mimics agentic-ui.sh agentic_menu)."""
    flywheel_event("agentic_ui", "menu_shown", "P2", title)
    menu_text = f"""

[{title}]
{'=' * 60}
原因：{reason}

请选择：
  1. {opt1_label} — {opt1_desc}
  2. {opt2_label} — {opt2_desc}
  3. {opt3_label} — {opt3_desc}

输入数字 (1-3):
"""
    print(menu_text, file=sys.stderr, flush=True)
    sys.exit(2)


# ─── hc_read_input: 从 stdin 读取完整输入 ───
READ_BUFFER = []


def read_input():
    """从 stdin 读取完整输入（兼容 hc_read_config），返回字符串。"""
    if READ_BUFFER:
        return READ_BUFFER.pop(0)
    try:
        return sys.stdin.read()
    except Exception:
        return ""


def hc_read_config():
    """读取 harness.yaml 配置（与 bash hc_read_config 等价）"""
    try:
        if _HC_YAML.exists():
            return _parse_yaml_simple(str(_HC_YAML))
    except Exception:
        pass
    return {}


# ─── output_continue: 标准 continue 输出 ───
def output_continue():
    """输出 continue JSON（等价的简短函数名）"""
    hc_emit_hook_json("ok")


# ─── 公开路径常量（供 from harness_lib import * / 单独引用）───
HOME_DIR = Path.home()
PROJECT_ROOT = _PROJECT_ROOT
STATE_DIR = _STATE_DIR


# ─── extract_* 工具函数（供各 hook 使用）───
def extract_event_name(text=None):
    """从 stdin 文本提取事件名称。返回 '' 或事件名。"""
    if text is None:
        text = read_input()
    for keyword in ["PreToolUse", "PostToolUse", "UserPromptSubmit", "SessionStart", "Stop"]:
        if keyword in text:
            return keyword
    return ""


def extract_tool_name(text=None):
    """提取工具名称。"""
    if text is None:
        text = read_input()
    m = re.search(r'"tool_name":\s*"([^"]+)"', text)
    return m.group(1) if m else ""


def extract_file_path(text=None):
    """提取文件路径。"""
    if text is None:
        text = read_input()
    m = re.search(r'"file_path":\s*"([^"]+)"', text)
    return m.group(1) if m else ""


def extract_tool_input_status(text=None):
    """提取工具输入状态。"""
    if text is None:
        text = read_input()
    m = re.search(r'"status":\s*"([^"]+)"', text)
    return m.group(1) if m else ""


def sanitize_text(text):
    """清理输入文本中的不可打印字符。"""
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)


def output_additional_context(text):
    """输出额外上下文（到 stderr 以便注入）。"""
    if text:
        print(f"[上下文注入] {text[:200]}", file=sys.stderr, flush=True)
