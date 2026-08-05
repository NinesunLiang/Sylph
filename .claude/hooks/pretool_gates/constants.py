"""
constants.py — Pure data module extracted from pretool-gate.py.
All constants, patterns, regex lists, and gate definitions.
"""
from __future__ import annotations
import re
from pathlib import Path

# ROOT detection (shared across all pretool_gates modules)
_script_path = Path(__file__).resolve()
ROOT = _script_path.parents[2]
if not (ROOT / ".claude").is_dir():
    ROOT = Path(".").resolve()

# ── State paths ──
OMC = ROOT / ".omc"
STATE_DIR = OMC / "state"
AUDIT = STATE_DIR / "audit"
CRITICAL_STATE = STATE_DIR / "context-critical.json"
FALLBACK_REQUIRED = STATE_DIR / "fallback-blocked-required"
FALLBACK_APPROVED = STATE_DIR / "fallback-blocked-approved"
TEMP_BYPASS = STATE_DIR / "temp-bypass.json"
REDIRECT_STREAK = STATE_DIR / "redirect-streak.json"
GOAL_SIGNAL = STATE_DIR / "tokens" / "autonomous.active"
GOAL_MODE_FILE = STATE_DIR / "tokens" / "lx-goal.json"
GOAL_MODE_LEGACY = STATE_DIR / "unattended-mode.json"
TRUST_BREACH = STATE_DIR / "trust-breach.json"
STATE_TOKEN = OMC / "state" / "token.json"
TOKENS = OMC / "tokens"

# ── Sensitive patterns ──
SENSITIVE_PATTERNS = [
    r"(^|/)\.env(\.|$|/)", r"(^|/)\.ssh(/|$)", r"(^|/)\.aws(/|$)",
    r"(^|/)\.gcp(/|$)", r"(^|/)\.azure(/|$)", r"id_rsa", r"id_ed25519",
    r"private[_-]?key", r"(^|/)secret\b", r"(^|/)credential(s)?\b",
    r"(^|/)password\b", r"(^|/)\.[a-z_-]*(token|oauth|jwt|api[_-]?key)[a-z_-]*\b",
    r"cookie",
    # ── 治理文件保护域 ──
    r"(^|/)\.claude/hooks/",
    r"(^|/)\.claude/settings\.json",
    r"(^|/)scripts/carroros-gates/",
    r"(^|/)\.harness-evidence/",
    r"(^|/)AGENTS\.md$",
    r"(^|/)AGENTS\.compact\.md$",
]

# ── Dangerous command patterns ──
DANGEROUS_COMMANDS = [
    r"(^|\s)rm\s+-rf\s+(/\s|\.\s|~\s|\*\s|/$|\.$|~$|\*$)",
    r"(^|\s)rm\s+-r\s+(/\s|\.\s|~\s|\*/)",
    r"rm\s+-rf?\s+['\"]?(/|~|\*)(\s|$|'|\")",
    r"rm\s+-rf?\s+['\"]?\.['\"]?(\s|$)",
    r"^sudo\b",
    r"^chmod\s+777\b", r"^chown\b", r"^git\s+push\s+(-f|--force)",
    r"^dd\s+if=", r"^mkfs\.", r"^fdisk\b", r":\(\)\{\s*:\|:\s*&\s*\};:",
]

WARN_ONLY_COMMANDS = [
    r"(^|\s)rm\s+-rf?\s+['\"]?/(?!\s|$|'|\")",
    r"(^|\s)rm\s+-rf?\s+['\"]?~/(?!/|$|'|\")",
]

ASK_USER_COMMANDS = [
    r"\bcurl\b.*\|\s*(sh|bash)", r"\bwget\b.*\|\s*(sh|bash)",
    r"\bnpm\s+install\b", r"\bpip\s+install\b", r"\bbrew\s+install\b",
    r"\bcargo\s+install\b", r"\bdocker\s+run\b", r"\bkubectl\b",
    r"\bterraform\s+apply\b", r"\bterraform\s+destroy\b",
]

# ── Oracle keywords ──
ORACLE_TRIGGER_KW = [
    "oracle", "acceptance", "final", "archive", "phase_end",
    "merge", "release", "deploy", "production",
]
ORACLE_FORCE_KW = ["auth", "payment", "migration", "permission"]

# ── Tool constants ──
STALE_LOCK_THRESHOLD = 1800  # 30 min
READ_TOOLS = {"read", "grep", "glob", "search_files", "list", "ls", "find", "cat"}
WRITE_TOOLS = {"edit", "write", "multiedit", "notebookedit"}
PLAN_FILE_PATTERNS = ["plan.md", "plan"]

# ── Injection detection patterns ──
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+(instructions|rules|guidelines)", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(previous|prior)\s+(instructions|context)", re.IGNORECASE),
    re.compile(r"(?:^|[.!?;]\s)you\s+are\s+(?:now|actually|really)\s+(?:a|an)\s+(?:hacker|ai|assistant|bot|system|admin|root|god)", re.IGNORECASE),
    re.compile(r"(new|override|replace)\s+(instructions|directive|system)\s*:", re.IGNORECASE),
    re.compile(r"output\s+(your\s+)?(system\s+)?(prompt|instructions)", re.IGNORECASE),
]

_EXTERNAL_DATA_MAX_LEN = 8000
