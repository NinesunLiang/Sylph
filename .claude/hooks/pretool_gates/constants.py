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
    r"(^|/).claude/workflows/frontend-overnight/scripts/carroros-gates/",
    r"(^|/)\.harness-evidence/",
    r"(^|/)AGENTS\.md$",
    r"(^|/)AGENTS\.compact\.md$",
]

# ── Read-sensitive patterns (index26 修复) ──
# 读取侧门禁只拦「凭据/密钥」类路径；治理文件域（AGENTS.md/.claude/hooks 等）是代理
# 的指令来源，必须可读（只禁写不禁读）。与 SENSITIVE_PATTERNS 的差异即治理文件保护域。
READ_SENSITIVE_PATTERNS = [
    r"(^|/)\.env(\.|$|/)", r"(^|/)\.ssh(/|$)", r"(^|/)\.aws(/|$)",
    r"(^|/)\.gcp(/|$)", r"(^|/)\.azure(/|$)", r"id_rsa", r"id_ed25519",
    r"private[_-]?key", r"(^|/)secret\b", r"(^|/)credential(s)?\b",
    r"(^|/)password\b", r"(^|/)\.[a-z_-]*(token|oauth|jwt|api[_-]?key)[a-z_-]*\b",
    r"cookie",
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

# ── Privacy gate (index25, 人类裁决修复): 密钥内容扫描 + Bash 读写通道提取 ──
# 与 posttool-sensitive-filter.py 的掩码模式对齐；读取侧先拦截，输出侧再掩码，双层防护。
SECRET_CONTENT_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",
    r"(?:ghp|ghu|gho|ghs)_[a-zA-Z0-9]{36}",
    r"xox[baprs]-[a-zA-Z0-9-]{20,}",
    r"-----BEGIN\s+(?:RSA|EC|OPENSSH|DSA|PRIVATE)\s+KEY-----",
    r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
    r"Bearer\s+[a-zA-Z0-9._-]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"org-[a-zA-Z0-9]{20,}",
    r"(?:sk_live|pk_live)_[a-zA-Z0-9]{20,}",
]
SECRET_CONTENT_COMPILED = [re.compile(p) for p in SECRET_CONTENT_PATTERNS]
PRIVACY_SCAN_SIZE_CAP = 1_048_576  # 内容扫描护栏: 仅 <1MB 文件

# Bash 读取通道: 引号内带扩展名的路径 token（含 python open('x')）或 cat/head/tail/less/more/nl/sed 目标
BASH_READ_TOKEN_RE = re.compile(
    r"""["']([^"']+\.(?:json|ya?ml|toml|env|txt|md|py|conf|cfg|ini|xml|csv))["']"""
    r"""|(?:^|\s)(?:cat|head|tail|less|more|nl|sed)\s+(?:-[^\s]+ )*["']?([^\s'"|;&><]+)["']?"""
)

# Bash 写入通道: 重定向 / tee / sed -i / python open(w|a) / touch
BASH_WRITE_TOKEN_RE = [
    re.compile(r"""(?:^|[\s|;&])(?:>>|>)\s*["']?([^\s'"|;&><]+)"""),
    re.compile(r"""(?:^|\s)tee\s+["']?([^\s'"|;&><]+)"""),
    re.compile(r"""(?:^|\s)sed\s+-i\b.*?["']?([^\s'"|;&><]+)$"""),
    re.compile(r"""open\(\s*["']([^"']+)["']\s*,\s*["']wa?["']"""),
    re.compile(r"""(?:^|\s)touch\s+["']?([^\s'"|;&><]+)"""),
]
