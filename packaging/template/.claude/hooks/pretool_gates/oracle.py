"""
oracle.py — Oracle classification engine extracted from pretool-gate.py.
"""
from __future__ import annotations
import json
import re
import shlex
import time
from pathlib import Path

from .constants import OMC, ORACLE_TRIGGER_KW, ORACLE_FORCE_KW

# ── R6-A: oracle 精确分类 ──
_ORACLE_QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"|`[^`]*`")
_ORACLE_ENV_BYPASS_RE = re.compile(
    r"(?:^|[&;|]\s*|\b(?:ba|z)?sh\s+-c\s+['\"]?)\s*(?:export\s+)?"
    r"(?:SKIP|NO|DISABLE|BYPASS)[A-Z0-9_]*(?:VERIFY|GATE|HOOKS?|AUDIT)[A-Z0-9_]*\s*=",
    re.IGNORECASE,
)
_ORACLE_APPROVAL_PATH_RE = re.compile(
    r"\.omc/state/(?:fallback-blocked-approved|temp-bypass\.json)"
)
_ORACLE_WRITE_OP_RE = re.compile(
    r"(?:>>?|\btouch\b|\btee\b|\bcp\b|\bmv\b|\bsed\s+-i\b|\bpython3?\b|\becho\b|\bprintf\b)"
)
_ORACLE_TEMP_BYPASS_SELF_RE = re.compile(
    r"(?:\b(?:python3?|bash|sh)\s+[^\n;]*?\btemp-bypass\.py\b|\btemp-bypass\.py\s+--)"
)
_ORACLE_RISK_SIGNAL_RE = re.compile(
    r"(?i)(?:skip_|bypass|temp-bypass|fallback-blocked|verify_gate|pretool-gate)"
)

# ── ADR-0012: REDIRECT 反模式匹配规则 ──
_ORACLE_ANTI_PATTERN_RULES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"(?:^|(?:[;&|]|&&)\s*)[a-z]+\s+[^\n;]*\\n\s*[a-z]", re.IGNORECASE),
     "multi_cmd_newline",
     "多命令请用 && 连接单行而非 \\\\n 换行:\n  × cd dir\\\\npython script.py\n  ✓ cd dir && python script.py"),
    (re.compile(r"(?i)(?:(?:^|(?:[;&|]|&&)\s*)(?:head|wc|l[a-z]+|cat)(?:\s+-[a-zA-Z0-9]+\s*)*\s+(\S+/)?[-.\w]+\.\w+\s*){2,}"),
     "redundant_file_probe",
     "检查文件内容请一次 read 完成,不要反复 head/cat/wc 同一文件。确认内容足够后直接推进修改"),
    (re.compile(r"echo.*>.*\.claude/(?:hooks|settings)", re.IGNORECASE),
     "gov_file_bypass",
     "治理文件(.claude/hooks/*)不可直接编辑。如需修改 hook: 使用 goal 模式(/lx-goal)"),
    (re.compile(r"(?:^|(?:[;&|]|&&)\s*)cd\s+\S+(?:\s*(?:[;&|]|&&)\s*cd\s+\S+){2,}"),
     "cd_churn",
     "连续 cd 但没有实质操作。确认目标目录后直接执行目标命令,不要空 cd 导航"),
]

# ── ADR-0012: 动态 anti-pattern redirects 缓存 ──
_ANTI_PATTERN_REDIRECTS_PATH = OMC / "state" / "anti-pattern-redirects.jsonl"
_ANTI_PATTERN_REDIRECTS_CACHE: list[tuple[re.Pattern, str, str]] | None = None
_ANTI_PATTERN_REDIRECTS_CACHE_AT: float = 0.0
_ANTI_PATTERN_REDIRECTS_TTL: float = 300.0


def _load_anti_pattern_redirects() -> list[tuple[re.Pattern, str, str]]:
    global _ANTI_PATTERN_REDIRECTS_CACHE, _ANTI_PATTERN_REDIRECTS_CACHE_AT
    now = time.time()
    if (_ANTI_PATTERN_REDIRECTS_CACHE is not None
            and now - _ANTI_PATTERN_REDIRECTS_CACHE_AT < _ANTI_PATTERN_REDIRECTS_TTL):
        return _ANTI_PATTERN_REDIRECTS_CACHE
    rules: list[tuple[re.Pattern, str, str]] = []
    if _ANTI_PATTERN_REDIRECTS_PATH.exists():
        try:
            for line in _ANTI_PATTERN_REDIRECTS_PATH.read_text(encoding="utf-8").strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pk = entry.get("pattern_key", "")
                guidance = entry.get("guidance", "")
                if not pk or not guidance:
                    continue
                esc = re.escape(pk)
                pat = re.compile(rf"\b{esc}\b", re.IGNORECASE)
                rules.append((pat, f"dyn:{pk}", guidance))
        except (OSError, ValueError):
            pass
    _ANTI_PATTERN_REDIRECTS_CACHE = rules
    _ANTI_PATTERN_REDIRECTS_CACHE_AT = now
    return rules


def _oracle_classify(command: str) -> tuple[str, str]:
    if _ORACLE_ENV_BYPASS_RE.search(command):
        return "BLOCK", "env_bypass_attempt"
    if _ORACLE_TEMP_BYPASS_SELF_RE.search(command):
        return "BLOCK", "temp_bypass_user_only"
    if _ORACLE_APPROVAL_PATH_RE.search(command) and _ORACLE_WRITE_OP_RE.search(command):
        return "BLOCK", "approval_state_self_mint"
    for pattern, detail, _ in _ORACLE_ANTI_PATTERN_RULES:
        if pattern.search(command):
            return "REDIRECT", detail
    for pattern, detail, _ in _load_anti_pattern_redirects():
        if pattern.search(command):
            return "REDIRECT", detail
    try:
        shlex.split(command, posix=True)
    except ValueError:
        if _ORACLE_RISK_SIGNAL_RE.search(command):
            return "ESCALATE", "unparsable_with_risk_signal"
    masked = _ORACLE_QUOTED_RE.sub(lambda m: " " * len(m.group(0)), command)
    if any(re.search(rf"\b{kw}\b", masked, re.IGNORECASE) for kw in ORACLE_FORCE_KW):
        return "FORCE", "force_kw"
    if any(re.search(rf"\b{kw}\b", masked, re.IGNORECASE) for kw in ORACLE_TRIGGER_KW):
        return "TRIGGER", "trigger_kw"
    return "PASS", ""
