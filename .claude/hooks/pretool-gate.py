#!/usr/bin/env python3
"""
CarrorOS PreToolUse Unified Gate — merged from 7 individual hooks.

Execution order (short-circuit on first BLOCK):
  1. sensitive-edit   — block sensitive path access (.env, .ssh, keys)
  2. fallback-check   — block if task is blocked/waiting_user
  3. action-gate      — block dangerous commands; ask_user for risky ones
  4. plan-gate        — block if task files missing
  5. edit-scope       — block writes outside declared scope
  6. verify-gate      — block unverified step completion marks in plan.md
  7. oracle-gate      — L2 三层: 结构化危险 BLOCK / 不可解析+高危 ESCALATE / 模糊 hint(R6-A)

Design constraints (from data_todo.md / 总结.md):
  - Single Python process per tool call (was 7)
  - Audit once per block decision, not per hook
  - Oracle: BLOCK 仅属结构化危险语义, 模糊关键词层维持 hint+audit(终审 R6-A)
  - First BLOCK short-circuits; later checks skip
"""

from __future__ import annotations

import json
import re
import secrets
import shlex
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Bootstrap: self-locate project root ──
_script_path = Path(__file__).resolve()
ROOT = _script_path.parents[2]
if not (ROOT / ".claude").is_dir():
    ROOT = Path(".").resolve()
import os
os.chdir(str(ROOT))

# ── Inline minimal hooklib (avoid import overhead for single-process gate) ──
OMC = ROOT / ".omc"
TOKENS = OMC / "tokens"
TASKS = OMC / "tasks"
AUDIT = OMC / "audit"
CRITICAL_STATE = OMC / "state" / "context-critical.json"
FALLBACK_REQUIRED = OMC / "state" / "fallback-blocked-required"
FALLBACK_APPROVED = OMC / "state" / "fallback-blocked-approved"
TEMP_BYPASS = OMC / "state" / "temp-bypass.json"
GOAL_SIGNAL = OMC / "state" / "tokens" / "autonomous.active"
GOAL_MODE_FILE = OMC / "state" / "tokens" / "lx-goal.json"
GOAL_MODE_LEGACY = OMC / "state" / "unattended-mode.json"

# ── Round7 PKG-1: token 读取委托 SSOT(单一真相源,禁第二实现)──
# 导入约定:直插 lib 目录按顶层模块导入——hooks/lib 是带 __init__ 的正规包,
# 走 `lib.task_ssot` 包路径会被它无条件遮蔽(regular>namespace,见 PKG-1 记录)。
# launcher 对崩溃(非 0/2 退出码)按非阻断错误处理=门禁静默失效,
# 故导入失败不抛出:_SSOT_ERR 记录,写门禁 fail-closed(见 _check_edit_scope)。
sys.path.insert(0, str(ROOT / ".claude" / "scripts" / "lib"))
try:
    from task_ssot import latest_active_token as _ssot_latest_active_token
    from task_ssot import latest_terminal_token as _ssot_latest_terminal_token
    _SSOT_ERR: Exception | None = None
except Exception as exc:  # pragma: no cover - 仅在生产环境 lib 缺失时触发
    _ssot_latest_active_token = None
    _ssot_latest_terminal_token = None
    _SSOT_ERR = exc


def _goal_mode() -> bool:
    """lx-goal 无人值守模式——与 lx-goal.py is_mode_active() 同语义:
    信号存在 + mode file active + 未过期(防 DG-46 半态: 过期残留信号不算激活)。
    hook 单发进程,成本=一次 stat + 一次小文件读。"""
    if not GOAL_SIGNAL.exists():
        return False
    path = GOAL_MODE_FILE if GOAL_MODE_FILE.exists() else GOAL_MODE_LEGACY
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not data.get("active"):
        return False
    expires = data.get("expires_at")
    if expires:
        try:
            if datetime.now(timezone.utc) >= datetime.fromisoformat(expires):
                return False
        except Exception:
            pass
    return True


def _is_governance(path: str) -> bool:
    """检查路径是否为治理文件（硬阻断）"""
    p = path.replace("\\", "/")
    gov_patterns = [
        r"(^|/)\.claude/hooks/",
        r"(^|/)\.claude/settings\.json",
        r"(^|/)scripts/carroros-gates/",
        r"(^|/)\.claude/kernel\.md$",
        r"(^|/)AGENTS\.md$",
    ]
    return any(re.search(pat, p, re.IGNORECASE) for pat in gov_patterns)


SENSITIVE_PATTERNS = [
    r"(^|/)\.env(\.|$|/)", r"(^|/)\.ssh(/|$)", r"(^|/)\.aws(/|$)",
    r"(^|/)\.gcp(/|$)", r"(^|/)\.azure(/|$)", r"id_rsa", r"id_ed25519",
    r"private[_-]?key", r"(^|/)secret\b", r"(^|/)credential(s)?\b", r"(^|/)password\b", r"(^|/)\.[a-z_-]*(token|oauth|jwt|api[_-]?key)[a-z_-]*\b", r"cookie",
    # ── 治理文件保护域 ──
    r"(^|/)\.claude/hooks/",       # hook 脚本（AI 不可修改）
    r"(^|/)\.claude/scripts/",     # 治理工具脚本
    r"(^|/)\.claude/settings\.json",  # hook 注册配置
    r"(^|/)scripts/carroros-gates/",    # harness 治理配置
    r"(^|/)\.harness-evidence/",       # harness 捕获的证据（防篡改）
    # DG-136 fix (2026-07-23): AGENTS.md 软冻结增加机械保护
    r"(^|/)AGENTS\.md$",             # 项目宪法文件
    r"(^|/)AGENTS\.compact\.md$",    # 压缩版宪法
]

DANGEROUS_COMMANDS = [
    r"(^|\s)rm\s+-rf\s+(/\s|\.\s|~\s|\*\s|/$|\.$|~$|\*$)", r"(^|\s)rm\s+-r\s+(/\s|\.\s|~\s|\*/)", r"^sudo\b",
    # PKG-5 C5: 引号/嵌套壳变形——rm -rf 后仅跟引号+根/家目录/星号也命中
    # (2026-07-20 刺杀实证: bash -c 'rm -rf /' 仅靠 (^|\s) 锚点可绕过)
    r"rm\s+-rf?\s+['\"]?(/|~|\*)",
    r"^chmod\s+777\b", r"^chown\b", r"^git\s+push\s+(-f|--force)",
    r"^dd\s+if=", r"^mkfs\.", r"^fdisk\b", r":\(\)\{\s*:\|:\s*&\s*\};:",
]

ASK_USER_COMMANDS = [
    r"\bcurl\b.*\|\s*(sh|bash)", r"\bwget\b.*\|\s*(sh|bash)",
    r"\bnpm\s+install\b", r"\bpip\s+install\b", r"\bbrew\s+install\b",
    r"\bcargo\s+install\b", r"\bdocker\s+run\b", r"\bkubectl\b",
    r"\bterraform\s+apply\b", r"\bterraform\s+destroy\b",
]

ORACLE_TRIGGER_KW = [
    "oracle", "acceptance", "final", "archive", "phase_end",
    "merge", "release", "deploy", "production",
]
ORACLE_FORCE_KW = ["auth", "payment", "migration", "permission"]

# ── R6-A: oracle 精确分类(终审 0:3 否决 hint-only 整体终态后施工) ──
# 四层: 结构化危险语义 → BLOCK;反模式匹配 → REDIRECT(拦截+引导);
#        不可解析+高危信号 → ESCALATE(ASK_USER 人类独占);模糊关键词 → hint+audit;其余 → PASS。
# BLOCK 层扫原文(引号藏不住危险),但 env 赋值只在真实生效位锚定
# (命令首/分隔符后/sh -c 引号内首)——grep 参数、commit message 不误伤。
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
# 优先级 P0: 精确匹配反模式行为(初始规则集映射 anti-patterns.md 典型反模式):
#   - 多命令 \n 换行(应 && 链式)
#   - 同文件反复 head/wc/cat(空转)
#   - 治理文件绕过企图
#   - 连续 cd 无实质操作
# 每条反模式配 redirect_guidance(告诉 AI 正确做法)
_ORACLE_ANTI_PATTERN_RULES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"(?:^|(?:[;&|]|&&)\s*)[a-z]+\s+[^\n;]*\\n\s*[a-z]", re.IGNORECASE),
     "multi_cmd_newline",
     "多命令请用 && 连接单行而非 \\n 换行:\n  × cd dir\\npython script.py\n  ✓ cd dir && python script.py"),
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
    """R6-A + ADR-0012 精确分类: 返回 (verdict, detail),verdict ∈ BLOCK/REDIRECT/ESCALATE/FORCE/TRIGGER/PASS。"""
    if _ORACLE_ENV_BYPASS_RE.search(command):
        return "BLOCK", "env_bypass_attempt"
    if _ORACLE_TEMP_BYPASS_SELF_RE.search(command):
        return "BLOCK", "temp_bypass_user_only"
    if _ORACLE_APPROVAL_PATH_RE.search(command) and _ORACLE_WRITE_OP_RE.search(command):
        return "BLOCK", "approval_state_self_mint"
    # ADR-0012: 反模式匹配 → REDIRECT（在结构危险之后,不可解析/模糊之前）
    # 先匹配硬编码规则（P0-P1），再匹配动态加载规则（stop-flywheel 升华产生）
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
    # 模糊 hint 层: 词边界 + 引号掩码(git --author / 引号内文本 auth 不再误报)
    masked = _ORACLE_QUOTED_RE.sub(lambda m: " " * len(m.group(0)), command)
    if any(re.search(rf"\b{kw}\b", masked, re.IGNORECASE) for kw in ORACLE_FORCE_KW):
        return "FORCE", "force_kw"
    if any(re.search(rf"\b{kw}\b", masked, re.IGNORECASE) for kw in ORACLE_TRIGGER_KW):
        return "TRIGGER", "trigger_kw"
    return "PASS", ""

STALE_LOCK_THRESHOLD = 1800  # 30 min: auto-clear blocked state older than this

READ_TOOLS = {"read", "grep", "glob", "search_files", "list", "ls", "find", "cat"}
WRITE_TOOLS = {"edit", "write", "multiedit", "notebookedit"}
PLAN_FILE_PATTERNS = ["plan.md", "plan"]


# ── Helpers ──

def _read_stdin() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        if not raw:
            return {}
        data = json.loads(raw)
        # PKG-5 C3: JSON null/标量/数组 → 归一为 {}(下游全程假定 dict,
        # null 会让 _extract_tool  AttributeError 崩溃=门禁静默失效面)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _check_temp_bypass() -> bool:
    """Check if a user-authorized temp bypass is active.

    Bypass file: .omc/state/temp-bypass.json
    Format: {"reason": "...", "expires_at": "ISO8601"}
    If expired, auto-delete the file.
    """
    if not TEMP_BYPASS.exists():
        return False
    try:
        data = json.loads(TEMP_BYPASS.read_text(encoding="utf-8"))
        expires = data.get("expires_at", "")
        if expires:
            try:
                from datetime import datetime, timezone
                exp = datetime.fromisoformat(expires)
                if datetime.now(timezone.utc) >= exp:
                    TEMP_BYPASS.unlink(missing_ok=True)
                    return False
            except Exception:
                pass
        return True
    except Exception:
        TEMP_BYPASS.unlink(missing_ok=True)
        return False

def _extract_tool(payload: dict) -> str:
    return str(payload.get("tool_name") or payload.get("tool") or payload.get("name") or "")

def _extract_input(payload: dict) -> dict[str, Any]:
    for key in ("tool_input", "input", "arguments", "args"):
        val = payload.get(key)
        if isinstance(val, dict):
            return val
    return payload

def _extract_path(payload: dict) -> str:
    data = _extract_input(payload)
    return str(data.get("file_path") or data.get("filePath") or data.get("path") or data.get("filename") or "")

def _extract_command(payload: dict) -> str:
    data = _extract_input(payload)
    return str(data.get("command") or payload.get("command") or "")

def _ok(msg: str = "OK") -> int:
    print(json.dumps({"continue": True, "message": f"PreToolGate: {msg}"}, ensure_ascii=False))
    return 0

def _block(reason: str, suggestion: str = "") -> int:
    """Block a tool call with HUMAN-READABLE reason and next step.

    Sylph-inspired pattern: instead of a terse machine-only message,
    give the user the context they need to decide what to do next.
    Also supports a TEMP_KEY bypass mechanism for user-authorized overrides.
    """
    safe_reason = reason[:300]
    msg_parts = [f"⛔ 操作被阻断: {safe_reason}"]
    if suggestion:
        msg_parts.append(f"💡 建议: {suggestion}")
    if _goal_mode():
        # lx-goal 无人值守: 人类不在场——保持 fail-closed(危险操作绝不执行),
        # 但指引模型「记录→继续其他任务」,不把唯一出路设为「请用户操作」(=停下来求人)。
        msg_parts.append(
            "🤖 goal 无人值守模式: 此操作已按人类独占裁决/安全门拦截。勿等待或询问人类——"
            "执行 `python3 .claude/skills/lx-goal/scripts/lx-goal.py blocked-human \"<操作>\" \"<AI建议>\" \"<依据>\"`"
            "(中高风险用 `skip-risk \"<描述>\" <level> \"<理由>\" \"<影响>\"`)记录后,继续其他任务;"
            "退出报告将自动汇总此项交由人类裁决。"
        )
    else:
        bypass_hint = (
            "🔑 如需临时授权跳过此检查，请运行: "
            "`! python3 .claude/scripts/temp-bypass.py --minutes 60 --reason \"你的理由\"`"
        )
        msg_parts.append(bypass_hint)
    full_msg = "\n".join(msg_parts)

    print(json.dumps({
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": full_msg,
        }
    }, ensure_ascii=False))
    sys.stderr.write(f"PreToolGate: BLOCKED - {safe_reason}\n")
    return 2

def _redirect(reason: str, guidance: str = "") -> int:
    """Redirect a tool call — block the bad action & tell AI the right way.

    REDIRECT 是 ADR-0012 新增的 oracle 判决级别,位于 PASS 与 FORCE 之间:
      PASS → REDIRECT → FORCE/TRIGGER → ESCALATE → BLOCK
    行为: continue=False(阻止工具调用),additionalContext 包含 reason+guidance,
    AI 看到指引后自行修正并重试——零人工介入。
    """
    safe_reason = reason[:300]
    msg_parts = [f"🔄 操作重定向: {safe_reason}"]
    if guidance:
        msg_parts.append(f"💡 正确做法:\n{guidance}")
    if _goal_mode():
        msg_parts.append("🤖 goal 模式: 修正后自动重试")
    full_msg = "\n".join(msg_parts)
    # 日志到 redirects.jsonl
    try:
        _REDIRECT_LOG = OMC / "redirects.jsonl"
        _REDIRECT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _REDIRECT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "event": "redirect",
                "reason": safe_reason,
                "guidance": guidance,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False) + "\n")
    except OSError:
        pass
    sys.stderr.write(f"PreToolGate: REDIRECTED - {safe_reason}\n")
    print(json.dumps({
        "continue": False,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": full_msg,
        }
    }, ensure_ascii=False))
    return 2


def _match_any(text: str, patterns: list[str]) -> str | None:
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return pat
    return None

def _is_sensitive(path: str) -> bool:
    p = path.replace("\\", "/")
    return any(re.search(pat, p, re.IGNORECASE) for pat in SENSITIVE_PATTERNS)

def _append_audit(event: dict) -> None:
    """Round7 PKG-4(audit schema 升级): 所有 gate 事件统一注入 task_id/step_id,
    E7 校准账 jq 可按 task/step 聚合统计 overturn。失败静默(原契约)。"""
    try:
        from datetime import datetime, timezone
        AUDIT.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        event.setdefault("timestamp", datetime.now(timezone.utc).replace(microsecond=0).isoformat())
        # PKG-4: task_id/step_id 全事件注入(调用点已显式提供的优先)
        if "task_id" not in event or "step_id" not in event:
            try:
                token = _active_token()
                if token:
                    session = token.get("session", {}) or {}
                    task = token.get("task", {}) or {}
                    event.setdefault(
                        "task_id",
                        session.get("id") or (task.get("id") if isinstance(task, dict) else None) or "unknown",
                    )
                    if isinstance(task, dict) and task.get("current_step"):
                        event.setdefault("step_id", task.get("current_step"))
            except Exception:
                pass
        with (AUDIT / f"{day}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass

def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}

# 终态集合：archived/done/completed 的 token 永不复活为"活跃任务"。
# 根因(2026-07-20 幻影 token 事件)：本函数按 mtime 取最新，而水位同步每轮
# 回写该 token 刷新 mtime → 陈旧任务自我续命，劫持状态注入与 scope 门。
def _latest_token() -> Path | None:
    """委托 task_ssot(单一真相源);SSOT 不可用 → None(fail-closed 由写门禁兜底)。"""
    if _ssot_latest_active_token is None:
        return None
    return _ssot_latest_active_token(TOKENS)

def _active_token() -> dict[str, Any] | None:
    """Returns normalized token dict, or None."""
    path = _latest_token()
    if not path:
        return None
    token = _read_json(path)
    if not isinstance(token, dict) or not token:
        return None
    task = token.get("task", {})
    if not isinstance(task, dict):
        token["task"] = {"name": str(task), "status": token.get("status", "active")}
    return token

def _task_dir(token: dict) -> Path | None:
    task = token.get("task", {})
    if not isinstance(task, dict):
        return None
    explicit = task.get("dir") or token.get("task_dir")
    if explicit:
        p = ROOT / explicit if not Path(explicit).is_absolute() else Path(explicit)
        if p.exists():
            return p
    return None

def _parse_scope(plan_text: str) -> list[str]:
    in_scope = False
    files: list[str] = []
    for line in plan_text.splitlines():
        s = line.strip()
        if s.lower().startswith("## scope") or s.lower().startswith("## scope freeze"):
            in_scope = True
            continue
        if in_scope and s.startswith("## "):
            break
        if in_scope:
            m = re.match(r"[-*]\s+`?([^`\s]+)`?", s)
            if m:
                files.append(m.group(1).replace("\\", "/"))
    return files

def _strip_dot_slash(s: str) -> str:
    """只剥前缀 "./";lstrip("./") 会吃掉点目录前导点(.claude→claude)致 scope 永不命中
    (2026-07-20 潜伏 bug 实证: plan scope 点前缀条目全灭,仅绝对路径条目幸免)"""
    return s[2:] if s.startswith("./") else s


def _in_scope(path: str, scope: list[str]) -> bool:
    """Check if a path is within the declared scope.

    使用 canonical path（realpath）防止 ../ symlink 等路径绕过。
    支持 glob 通配符（**/*.py 等）。
    精确匹配和直接父目录匹配，删除宽松前缀匹配（防误放行）。
    """
    try:
        p_real = os.path.realpath(path)
    except Exception:
        p_real = path.replace("\\\\", "/")
    p = _strip_dot_slash(p_real)
    for item in scope:
        s_orig = item.replace("\\\\", "/")
        # DG-134 fix: 先 realpath（基于 cwd 解析为绝对路径），再 strip
        # 避免 .claude/ → strip → claude/ → realpath 丢点号的 bug
        try:
            s_abs = os.path.realpath(s_orig)
        except Exception:
            s_abs = s_orig
        s = _strip_dot_slash(s_abs)
        # glob 模式
        if "*" in s or "?" in s:
            import fnmatch
            if fnmatch.fnmatch(p, s) or fnmatch.fnmatch(os.path.basename(p), s):
                return True
            # also try matching against any part of the path
            parts = p.split("/")
            for i in range(len(parts)):
                if fnmatch.fnmatch("/".join(parts[i:]), s):
                    return True
            continue
        s_dir = s.rstrip("/")
        # 精确匹配
        if p == s_dir or p == "/" + s_dir:
            return True
        # 直接父目录匹配（路径在 scope 目录下）
        prefix = s_dir + "/"
        if p.startswith(prefix) or p.startswith("/" + prefix):
            return True
        # 后缀匹配（绝对路径 vs 相对 scope）
        if p.endswith("/" + s_dir):
            return True
    return False

def _check_verified(step_id: str | None, task_id: str | None = None,
                    task_dir: Path | None = None) -> bool:
    """VerifyGate 审计回读 — step + task 双绑定，无通配，fail-closed。

    仅当审计中存在 (step_id, task_id) 双匹配的 VERIFIED 事件才放行。
    历史无 task_id 事件、跨任务事件、畸形事件一律不计（PKG-A）。
    扫描: .omc/audit(verify_gate 写) + .omc/state/audit(carros_base fallback)
          + 任务自身 state/audit(carros_base 主写点)。
    """
    if not step_id or not task_id:
        return False
    dirs = [AUDIT, OMC / "state" / "audit"]
    if task_dir:
        dirs.append(Path(task_dir) / "state" / "audit")
    for d in dirs:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.jsonl")):
            with f.open("r", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        e = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    # carros_base.py: {"event": "verify", "data": {"step", "result", "task_id"}}
                    if e.get("event") == "verify":
                        data = e.get("data", {})
                        if (isinstance(data, dict)
                                and data.get("result") == "VERIFIED"
                                and data.get("step") == step_id
                                and data.get("task_id") == task_id):
                            return True
                    # verify_gate.py: {"event_type": "verify_decision", "decision", "step", "task_id"}
                    if (e.get("event_type") == "verify_decision"
                            and e.get("decision") == "VERIFIED"
                            and e.get("step") == step_id
                            and e.get("task_id") == task_id):
                        return True
    return False


# ── Gate Checks (ordered, each returns None=pass or str=block_reason) ──

def _auto_init(target_path: str | None = None) -> None:
    """自动 init：无 token 写操作时后台初始化 task 文档系统"""
    import subprocess
    try:
        script = ROOT / ".claude/scripts/carros_base.py"
        if not script.exists():
            return
        cmd = [sys.executable, str(script), "init", "--auto"]
        if target_path:
            cmd += ["--target", target_path]
        subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=10)
    except Exception:
        pass

def _check_sensitive_edit(payload: dict) -> str | None:
    """Gate 1: block sensitive path writes only (reads are safe).

    分层阻断:
    - 治理文件（hooks/ settings.json gate-contract.yaml AGENTS.md kernel.md）→ 硬阻断 continue:False
    - 业务敏感文件（.env / .ssh / 密钥）→ 软阻断 continue:True + additionalContext
    """
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path:
        return None
    # 治理文件 → 硬阻断（独立检查，不依赖 SENSITIVE_PATTERNS）
    if _is_governance(path):
        safe = path[:200]
        if _goal_mode():
            # goal 模式: 降级为 warn-only, AI 需要修改治理文件完成任务
            msg = f"⚠️ [goal-mode] 治理文件写入: {safe} — goal 模式下降级放行，非 goal 模式本应硬阻断"
            sys.stderr.write(f"PreToolGate: GOV_WARN (goal-mode) - {safe}\n")
            print(json.dumps({"continue": True, "message": msg}, ensure_ascii=False))
            _append_audit({"event_type": "governance_goal_warn", "path": path, "tool": tool})
            return None  # 放行，让后续 gate 继续检查
        # 非 goal 模式: 软阻断 — warn + audit + 注入原因，由 AI 的铁律#7+哲学链自决
        reason_text = (
            f"⚠️ GOVERNANCE_WARN: 治理文件 {safe} 被修改。\n"
            f"  规则: .claude/settings.json 和 .claude/hooks/* 受 Gate 1 保护，AI 不应直接修改。\n"
            f"  哲学&铁律: 治理文件不可改，但 AI 自决（哲学→铁律→现状→ROI→行动）。\n"
            f"  如果你确定当前修改必要（如修复 bug、遵循人类指令），继续即可。\n"
            f"  audit 已记录此事件供退出报告审查。"
        )
        sys.stderr.write(f"PreToolGate: GOV WARN (path={safe})\n{reason_text}\n")
        _append_audit({"event_type": "governance_warn", "path": path, "tool": tool})
        print(json.dumps({"continue": True, "message": reason_text}, ensure_ascii=False))
        return None
    # 业务敏感文件 → 软阻断
    if _is_sensitive(path):
        return (f"BLOCK 敏感路径 {path}，需要确认后才能修改|"
                f"⛔ 检测到敏感文件写入: {path}。\n"
                f"原因: .env/.ssh/密钥文件可能包含凭据,CarrorOS 铁律禁止自主修改。\n"
                f"可选方案:\n"
                f"  1. 确认修改安全后使用临时 bypass:\n"
                f"     `python3 .claude/scripts/temp-bypass.py --minutes 10 --reason \"已确认安全\"`\n"
                f"  2. 如需创建新密钥,使用专用工具而非直接编辑敏感文件\n"
                f"预期结果: 授权后继续;未授权则跳过")
    return None

def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _auto_archive_token(token_path: Path, token_data: dict, reason: str) -> None:
    """Move a stale/broken token out of the way so it stops blocking the project.

    Token is copied to archive/tokens/{date}/ with a note, then deleted from tokens/.
    Never raises — silence any I/O errors.
    """
    try:
        archive_dir = OMC / "archive" / "tokens" / token_path.parent.name
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / token_path.name
        # Mark as archived in the token data
        token_data["status"] = "archived"
        token_data.setdefault("session", {})
        token_data["session"]["archived_at"] = datetime.now(timezone.utc).isoformat()
        token_data.setdefault("task", {})
        if isinstance(token_data.get("task"), dict):
            token_data["task"]["archive_reason"] = reason
        archive_path.write_text(json.dumps(token_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        token_path.unlink()
        _append_audit({
            "event_type": "token_auto_archived",
            "actor": "hook:pretool-gate",
            "reason": reason,
            "token": token_path.name,
            "archived_to": str(archive_path),
        })
    except OSError:
        pass


def _check_fallback(_payload: dict) -> str | None:
    """Gate 2: block if task is blocked/waiting.

    Stale lock protection: if a token has been blocked longer than
    STALE_LOCK_THRESHOLD, auto-archive it instead of blocking.
    Historical bad state must not freeze the project (Boss ruling 2026-07-15).
    """
    token_path = _latest_token()
    if not token_path:
        return None
    token_data = _read_json(token_path)
    if not token_data:
        return None
    token = token_data
    task = token.get("task", {})
    if not isinstance(task, dict):
        return None
    status = task.get("status") or token.get("status") or "active"
    if status != "blocked":
        # Normal path: check waiting_user or unresolved fallback
        if status == "waiting_user":
            reason = task.get("reason") or "requires_user"
            return (f"ASK_USER Bypass 临时授权状态：{reason}|"
                    f"❓ bypass 临时授权正在使用中。\n"
                    f"原因: {reason}\n"
                    f"可选方案:\n"
                    f"  1. 等待授权过期后继续\n"
                    f"  2. 输入 /deny 取消授权\n"
                    f"预期结果: 授权使用/取消后继续")
        fallback = task.get("fallback", {}) or {}
        if fallback.get("unresolved"):
            return (f"BLOCK fallback 状态未解决：{fallback.get('reason', 'unknown')}|"
                    f"⛔ 任务处于未解决的 fallback 状态。\n"
                    f"原因: {fallback.get('reason', 'unknown')}\n"
                    f"可选方案:\n"
                    f"  1. 解决 fallback 问题后继续\n"
                    f"  2. 使用临时 bypass 授权跳过\n"
                    f"  3. 输入 /deny 保持状态\n"
                    f"预期结果: 问题解决后任务继续")
        session = token.get("session", {}) or {}
        if session.get("fallback"):
            return None
        return None
    # --- Blocked token detected ---
    reason = task.get("blocked") or task.get("reason") or "blocked"
    # Check staleness: use fallback timestamp or token created_at
    ts_str = (
        (task.get("fallback") or {}).get("timestamp")
        or (token.get("session") or {}).get("created_at")
        or ""
    )
    age = 0.0
    if ts_str:
        try:
            from datetime import datetime, timezone
            ts = datetime.fromisoformat(ts_str)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
        except Exception:
            pass
    if age >= STALE_LOCK_THRESHOLD:
        # Stale blocked token — auto-archive so it stops freezing the project
        _auto_archive_token(token_path, token_data, f"stale_blocked age={int(age)}s reason={reason}")
        return None  # pass through, project is unblocked

    # ─── Not stale enough for auto-archive → CAPTCHA approval pattern ───
    # Check if user already approved via /approve <token>
    if FALLBACK_APPROVED.exists():
        _auto_archive_token(token_path, token_data, f"user_approved reason={reason}")
        _safe_unlink(FALLBACK_REQUIRED)
        _safe_unlink(FALLBACK_APPROVED)
        return None  # pass through

    # Generate CAPTCHA for user to approve
    captcha = secrets.token_hex(3)  # 6-char hex
    try:
        FALLBACK_REQUIRED.parent.mkdir(parents=True, exist_ok=True)
        FALLBACK_REQUIRED.write_text(captcha)
    except OSError:
        pass

    # Build helpful message
    task = token.get("task", {})
    session = token.get("session", {})
    task_name = session.get("id") or task.get("name") or token_path.stem
    blocked_since = (task.get("fallback") or {}).get("timestamp") or \
                    session.get("created_at", "")[:19] or "?"
    current_step = task.get("current_step", "?")
    age_str = f"（阻塞 {int(age)} 秒）" if age > 0 else ""

    msg = (
        f"\n"
        f"╔══ CarrorOS 任务阻塞 ══════════════════════════════\n"
        f"║  任务: {task_name}\n"
        f"║  状态: blocked  {age_str}\n"
        f"║  原因: {reason}\n"
        f"║  当前步骤: {current_step}\n"
        f"║  阻塞自: {blocked_since[:19]}\n"
        f"║\n"
        f"║  📌 如需解除阻塞并归档此任务，请输入:\n"
        f"║     /approve {captcha}\n"
        f"║\n"
        f"║  📌 如需保持阻塞状态:\n"
        f"║     /deny\n"
        f"║\n"
        f"║  ⏱ 或等待 {max(1, int(STALE_LOCK_THRESHOLD/60 - age/60))} 分钟后自动解除\n"
        f"╚══════════════════════════════════════════════════\n"
    )
    print(msg, file=sys.stderr, flush=True)

    return (f"BLOCK task_blocked reason={reason}|"
            f"⛔ 任务处于 blocked 状态，需要您解除后才能继续。\n"
            f"原因: {reason}\n"
            f"可选方案:\n"
            f"  1. 输入 /approve <token> 解除阻塞\n"
            f"  2. 输入 /deny 保持阻塞状态\n"
            f"预期结果: 解除后任务继续执行")

def _check_action_gate(payload: dict) -> str | None:
    """Gate 3: block truly dangerous commands; WARN for routine ops — AI self-decide.

    改造原则(2026-07-25):
      - DANGEROUS_COMMANDS (rm -rf /, sudo, git push --force, chmod 777, dd, mkfs):
        保留 BLOCK — 不可逆破坏性操作。
      - ASK_USER_COMMANDS (npm/pip/brew install, curl|bash):
        降级 WARN — 标准开发操作,AI自主决定;仅audit+stderr提示,不阻断。
    """
    command = _extract_command(payload)
    if not command:
        return None
    hard = _match_any(command, DANGEROUS_COMMANDS)
    if hard:
        _append_audit({
            "event_type": "preaction_decision",
            "actor": "hook:pretool-gate",
            "decision": "BLOCK",
            "reason": "dangerous_command",
            "pattern": hard,
            "command_preview": command[:160],
        })
        return (f"BLOCK dangerous_command pattern={hard}|"
                f"⛔ 检测到不可逆破坏性操作。\n"
                f"原因: 该命令可能造成数据丢失或系统损坏,CarrorOS 铁律禁止自主执行。\n"
                f"可选方案:\n"
                f"  1. 确认操作安全后,使用临时 bypass 授权:\n"
                f"     `python3 .claude/scripts/temp-bypass.py --minutes 10 --reason \"已确认安全\"`\n"
                f"  2. 使用更安全的替代操作(如 rm → trash, sudo → 请求权限)\n"
                f"  3. 如确需执行,请等待用户人工介入\n"
                f"预期结果: 授权后操作继续;未授权则操作被跳过记录")
    ask = _match_any(command, ASK_USER_COMMANDS)
    if ask:
        _append_audit({
            "event_type": "preaction_decision",
            "actor": "hook:pretool-gate",
            "decision": "WARN",
            "reason": "approval_required_command",
            "pattern": ask,
            "command_preview": command[:160],
        })
        return f"WARN approval_required pattern={ask}"
    return None

def _failure_escalate(signature: str, *, window: int = 20, threshold: int = 3) -> bool:
    """同一阻断签名在最近 window 条 gate 决策事件中出现 ≥threshold 次 → True(应升级)。

    Round7 PKG-3(opus failure-escalate 意图折叠,GPT 形式=零新文件):
    同一签名反复 BLOCK = 惯性重试(E4 失效模式),继续 BLOCK 只会被忽略——
    升级为 ASK_USER 人类独占裁决。只读现有 audit jsonl,fail-open(读不出不升级)。
    """
    if not AUDIT.exists():
        return False
    try:
        files = sorted(AUDIT.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:2]
    except OSError:
        return False
    hits = 0
    seen = 0
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in reversed(lines):
            if seen >= window:
                return hits >= threshold
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if not isinstance(e, dict):
                continue
            if e.get("decision") not in ("BLOCK", "ESCALATE"):
                continue
            seen += 1
            if signature and signature in str(e.get("reason", "")):
                hits += 1
    return hits >= threshold


def _check_plan_gate(payload: dict) -> str | None:
    """Gate 4: 自适应自治 — 无 token 自动 init，不阻断

    Round7 PKG-3(E4 终态惯性):「无活跃 token」区分两种形态——
      a) 连终态任务 token 都没有(全新仓库/刚清理)→ auto-init 合法,放行;
      b) 最新任务 token 已终态 → 上一任务刚结束。
         → REDIRECT,拦截+引导开新任务,AI 自行修正后重试(防劫持环路)。
    """
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    token = _active_token()
    if not token:
        if _SSOT_ERR is not None:
            # SSOT 不可读时 "无 token" 是不可信读数——auto-init 会误生劫持 token
            # (2026-07-20 实证: 导入失败窗口连生 2 个 auto_* 残液,窄 scope 连环阻断)
            return None  # 不放 auto-init;写门禁 fail-closed 在 Gate 5 兜底
        # Round7 PKG-3: 终态惯性区分——最新任务 token 已终态 → BLOCK,不 auto-init
        if _ssot_latest_terminal_token is not None:
            terminal_path = _ssot_latest_terminal_token(TOKENS)
            if terminal_path is not None:
                terminal_data = _read_json(terminal_path)
                terminal_task = terminal_data.get("task", {}) if isinstance(terminal_data, dict) else {}
                terminal_id = (
                    terminal_task.get("id") if isinstance(terminal_task, dict) else None
                ) or terminal_path.stem
                signature = f"terminal_inertia:{terminal_id}"
                _append_audit({
                    "event_type": "terminal_inertia_block",
                    "actor": "hook:pretool-gate",
                    "decision": "BLOCK",
                    "reason": signature,
                    "terminal_token": str(terminal_path.relative_to(ROOT))
                    if terminal_path.is_relative_to(ROOT) else str(terminal_path),
                })
                suggestion = (
                    f"上一任务 {terminal_id} 已终态——auto-init 已禁用(防 2026-07-20 劫持环路)。"
                    f"开新任务: `python3 .claude/skills/lx-goal/scripts/lx-goal.py on \"<目标>\"` "
                    f"或 `python3 .claude/scripts/carros_base.py init --task <name>`"
                )
                if _failure_escalate(signature):
                    _append_audit({
                        "event_type": "failure_escalate",
                        "actor": "hook:pretool-gate",
                        "decision": "ESCALATE",
                        "reason": signature,
                    })
                    return (f"ASK_USER {signature}|同一阻断签名已 ≥3 次——惯性重试判定,"
                            f"升级人类独占裁决。\n"
                            f"原因: 同一操作被反复打断,自动重试机制已耗尽。\n"
                            f"可选方案:\n"
                            f"  1. 开新任务: `python3 .claude/skills/lx-goal/scripts/lx-goal.py on \"<目标>\"` \n"
                            f"  2. 人工排查问题: `python3 .claude/scripts/carros_base.py init --task <name>`\n"
                            f"预期结果: 问题解决后自动继续")
                return f"REDIRECT {signature}|{suggestion}"
        # 无 token → auto-init（不会阻阻断）
        path = _extract_path(payload)
        _auto_init(path)
        return None  # 放行
    task = token.get("task", {})
    if not isinstance(task, dict):
        return None
    if task.get("status") in {"blocked", "waiting_user"}:
        return f"REDIRECT task_status_{task.get('status')}|任务处于 {task.get('status')} 状态。请先解决阻塞原因后再继续。"
    task_dir = _task_dir(token)
    if not task_dir:
        return None
    plan = task_dir / "plan.md"
    if not plan.exists():
        return f"REDIRECT plan_missing task_dir={task_dir}|任务目录缺少 plan.md,请确认任务已正确初始化后重试。"
    if not task.get("current_step"):
        return "REDIRECT current_step_missing|任务缺少 current_step 状态,请确认 token 完整后重试。"
    return None

def _check_edit_scope(payload: dict) -> str | None:
    """Gate 5: 越界阻断（E1 防线 + E1增强: 逃逸升级检测）

    规避逃逸模式: CARROROS_EDIT_SCOPE=warn 不再永久放行——
    连续 ≥3 次越界后自动升级为 BLOCK（逃逸惯性惩罚）。
    """
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    if _SSOT_ERR is not None:
        return f"edit-scope: task_ssot 导入失败({_SSOT_ERR!r})——fail-closed 阻断写操作,修复 lib/task_ssot.py 后重试"
    path = _extract_path(payload)
    if not path:
        return None
    token = _active_token()
    if not token:
        return None
    # ── 权威 scope 来源: harness.yaml project.scope ──
    # 由用户/安装脚本写入，AI 不可修改（治理文件受保护）
    # 优先于 token.json scope
    _HARNESS_PATH = ROOT / "scripts" / "carroros-gates" / "harness.yaml"
    harness_scope = []
    try:
        if _HARNESS_PATH.exists():
            import yaml  # type: ignore
            with open(_HARNESS_PATH, "r") as _fh:
                _hdata = yaml.safe_load(_fh) or {}
            _proj = _hdata.get("project", {}) or {}
            hs = _proj.get("scope")
            if isinstance(hs, list):
                harness_scope = hs
            elif isinstance(hs, str):
                harness_scope = [hs]
    except Exception:
        pass

    if harness_scope:
        in_scope = _in_scope(path, harness_scope)
        if in_scope:
            return None
        # ai_self_decision.md 原则第2条: 非不可逆/风险/越权/架构调整行为 → 不打断，AI自决
        # scope 越界属于"其他行为"——记录 audit + stderr 告知，不放行但不阻断
        _append_audit({
            "event_type": "scope_violation",
            "actor": "hook:pretool-gate",
            "decision": "WARN",
            "reason": "harness_scope_violation",
            "path": path,
            "scope": harness_scope[:10],
        })
        print(f"⚠️ [edit-scope] 路径不在 project scope 内: {path}", file=sys.stderr, flush=True)
        print(f"  scope: {harness_scope[:10]}", file=sys.stderr, flush=True)
        print(f"  请评估是否确实需要编辑此路径，或调整任务 scope。", file=sys.stderr, flush=True)
        return None

    # 检查 token scope
    token_scope = token.get("scope") or []
    if token_scope:
        in_scope = _in_scope(path, token_scope)
        if in_scope:
            return None
        # ai_self_decision.md 原则第2条: scope 越界属"其他行为"——记录告知，不阻断
        _append_audit({
            "event_type": "scope_violation",
            "actor": "hook:pretool-gate",
            "decision": "WARN",
            "reason": "token_scope_violation",
            "path": path,
            "scope": token_scope[:10],
        })
        print(f"⚠️ [edit-scope] 路径不在 token scope 内: {path}", file=sys.stderr, flush=True)
        print(f"  scope: {token_scope[:10]}", file=sys.stderr, flush=True)
        print(f"  请评估后继续，或调整任务 scope。", file=sys.stderr, flush=True)
        return None
    # 无 scope 来源 → 放行（无法判定边界）
    return None

def _check_verify_gate(payload: dict) -> str | None:
    """Gate 6: block unverified step [x] marks in plan.md."""
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path or not any(path.replace("\\", "/").endswith(p) for p in PLAN_FILE_PATTERNS):
        return None
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not re.search(r"\[x\]", content, re.IGNORECASE):
        return None
    token = _active_token()
    if not token:
        return None
    task = token.get("task", {})
    if not isinstance(task, dict):
        return None
    current_step = task.get("current_step")
    session = token.get("session", {})
    task_id = session.get("id") if isinstance(session, dict) else None
    if not _check_verified(current_step, task_id, _task_dir(token)):
        _append_audit({
            "event_type": "verifygate_preaction_block",
            "actor": "hook:pretool-gate",
            "decision": "REDIRECT",
            "reason": "step_not_verified",
            "path": path,
            "current_step": current_step,
        })
        return f"REDIRECT step_{current_step}_not_VERIFIED|当前步骤 {current_step} 尚未通过验证。请先运行验证命令并提供 VERIFIED 证据后再标记完成。"
    return None

def _check_oracle_gate(payload: dict) -> str | None:
    """Gate 7: L2 oracle——精确危险 BLOCK / 不可解析 ESCALATE / 模糊 hint+audit / 安全 PASS。"""
    token = _active_token()
    if not token:
        return None
    session = token.get("session", {}) or {}
    if session.get("level", "L1_BASE") != "L2_ENHANCE":
        return None
    command = _extract_command(payload)
    if not command:
        return None
    verdict, detail = _oracle_classify(command)
    task = token.get("task", {})
    step = task.get("current_step") if isinstance(task, dict) else None
    if verdict == "REDIRECT":
        # 查找对应的 redirect_guidance（先静态规则,再动态规则）
        _guidance = ""
        for _, _detail, _guide in _ORACLE_ANTI_PATTERN_RULES:
            if _detail == detail:
                _guidance = _guide
                break
        if not _guidance:
            for _, _detail, _guide in _load_anti_pattern_redirects():
                if _detail == detail:
                    _guidance = _guide
                    break
        _append_audit({
            "event_type": "oracle_redirect",
            "actor": "hook:pretool-gate",
            "decision": "REDIRECT",
            "reason": detail,
            "current_step": step,
            "cmd_head": command[:120],
        })
        return f"REDIRECT oracle_redirect:{detail}|{_guidance}"
    if verdict == "BLOCK":
        _append_audit({
            "event_type": "oracle_gate_block",
            "actor": "hook:pretool-gate",
            "decision": "BLOCK",
            "reason": detail,
            "current_step": step,
            "cmd_head": command[:120],
        })
        return (f"BLOCK oracle_gate:{detail}|"
                f"⛔ 检测到高置信危险语义({detail})。\n"
                f"原因: 模型试图在未经人类授权的情况下绕过系统验证/审批机制,违反安全铁律。\n"
                f"可选方案:\n"
                f"  1. 移除绕过语义后重试(推荐)\n"
                f"  2. 确需绕过: 由用户人工裁决授权,执行 temp-bypass\n"
                f"预期结果: 修正后继续;未授权则跳过")
    if verdict == "ESCALATE":
        _append_audit({
            "event_type": "oracle_gate_escalate",
            "actor": "hook:pretool-gate",
            "decision": "ESCALATE",
            "reason": detail,
            "current_step": step,
            "cmd_head": command[:120],
        })
        return (f"ASK_USER oracle_gate:{detail}|"
                f"❓ 命令无法可靠解析且含高危信号,需要您判断:\n"
                f"原因: Oracle 无法确定命令是否安全——请人工确认后再执行。\n"
                f"如果确认安全: 使用临时 bypass 后重试。\n"
                f"如果不安全: 此操作将被跳过。")
    if verdict in ("FORCE", "TRIGGER"):
        phase = task.get("phase", "execute") if isinstance(task, dict) else "execute"
        _append_audit({
            "event_type": "oracle_gate_trigger",
            "actor": "hook:pretool-gate",
            "decision": "REVIEW",
            "reason": "potential_oracle_trigger_detected",
            "current_step": step,
            "phase": phase,
        })
        # 模糊层维持 hint+audit(终审认可的终态)——不阻断
        print(
            f"🔮 [oracle-gate] L2 {verdict} 触发检测：建议完成后执行双审判 "
            f"`python3 .claude/scripts/carros_base.py oracle review` 或 /lx-oracle review",
            file=sys.stderr, flush=True,
        )
    return None  # PASS 与 hint 层均放行


# ── Main dispatcher ──

STATE_TOKEN = OMC / "state" / "token.json"


def _clean_stale_state_token() -> None:
    """Auto-clear .omc/state/token.json if blocked/waiting longer than threshold.
    Prevents stale lock accumulation (ref: GPT-5.5 audit finding).

    E1 enhanced: also auto-archive cross-day tokens with done/completed/archived status
    to prevent mtime-based selector from picking stale completed tokens (phantom token fix)."""
    if not STATE_TOKEN.exists():
        return
    try:
        data = json.loads(STATE_TOKEN.read_text(encoding="utf-8"))
    except Exception:
        return
    task = data.get("task") if isinstance(data.get("task"), dict) else {}
    status = task.get("status") or (data.get("task") or {}).get("status") or ""
    if status not in ("blocked", "waiting_user"):
        return
    fb = task.get("fallback", {}) or {}
    ts_str = fb.get("timestamp") or data.get("session", {}).get("fallback", {}).get("timestamp") or ""
    if not ts_str:
        return
    try:
        from datetime import datetime, timezone
        ts = datetime.fromisoformat(ts_str)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
    except Exception:
        return
    if age < STALE_LOCK_THRESHOLD:
        return
    # Stale lock detected — auto-clear
    cleared = {
        "schema_version": 3,
        "session": {"clean": True, "note": f"Auto-cleared stale {status} from {ts_str}",
                     "cleaned_at": datetime.now(timezone.utc).isoformat()},
        "task": None,
    }
    STATE_TOKEN.write_text(json.dumps(cleared, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _append_audit({
        "event_type": "state_lock_auto_cleared",
        "actor": "hook:pretool-gate",
        "reason": f"stale_{status}_age_{int(age)}s",
        "original_timestamp": ts_str,
    })

    # E1: cross-day completed token auto-archive (phantom token prevention)
    try:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        archive_base = OMC / "archive" / "tokens"
        for date_dir in sorted(TOKENS.iterdir()):
            if not date_dir.is_dir():
                continue
            date_str = date_dir.name
            # Only process non-today dirs
            if date_str >= today:
                continue
            for token_file in date_dir.iterdir():
                if not token_file.name.endswith(".json") or token_file.name.endswith(".lock"):
                    continue
                try:
                    tdata = json.loads(token_file.read_text(encoding="utf-8"))
                except Exception:
                    continue
                t = tdata.get("task", {}) or {}
                top_status = tdata.get("status", "") or ""
                task_status = (t.get("status") if isinstance(t, dict) else "") or ""
                if task_status in ("done", "completed", "archived") or top_status in ("archived",):
                    # Move to archive
                    archive_dir = archive_base / date_str
                    archive_dir.mkdir(parents=True, exist_ok=True)
                    dest = archive_dir / token_file.name
                    # Use rename (atomic within same filesystem)
                    token_file.rename(dest)
                    _append_audit({
                        "event_type": "token_auto_archived",
                        "actor": "hook:pretool-gate",
                        "reason": f"cross_day_completed_{date_str}/{token_file.name}",
                        "dest": str(dest.relative_to(ROOT)),
                    })
    except Exception:
        pass


# Dialogue residue patterns — content that indicates AI chat output left in spec docs
HARD_BLOCK_DOC_PATTERNS = [
    r"(^|/)\.claude/references/design-docs/",
    r"(^|/)AGENTS\.md$",
    r"(^|/)kernel\.md$",
    r"(^|/)README\.md$",
]

_DIALOGUE_RESIDUE_PATTERNS = [
    r"我明白了[，,。!！]?",
    r"好的[，,。!！]?(,|，)?" + r"让我",
    r"下面给你一版",
    r"下面是一版(调整|优化|完整|修改|补充)",
    r"根据你(给|上传|提供)的",
    r"我对.*进行了全面(优化|调整|更新|修改)",
    r"我明白你的意思",
    r"可以[。.]\s*依?据?现在(已经)?定稿",
    r"对[，,]刚才那版确实",
    r"I understand[.,]",
    r"Here is a (complete|revised|optimized|updated) version",
    r"Based on your (uploaded|provided|given)",
]


def _check_document_quality(payload: dict) -> str | None:
    """Gate 8: detect dialogue residue in spec document writes.
    — Critical paths: REDIRECT (intercept+guide, AI self-fix and retry)
    — Other .md: WARN (audit only, passes through)."""
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path or not path.endswith(".md"):
        return None
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not content:
        return None
    for pat in _DIALOGUE_RESIDUE_PATTERNS:
        if re.search(pat, content, re.IGNORECASE):
            is_critical = any(re.match(hp, path.replace("\\", "/"), re.IGNORECASE) for hp in HARD_BLOCK_DOC_PATTERNS)
            decision = "BLOCK" if is_critical else "WARN"
            _append_audit({
                "event_type": "document_quality_warning",
                "actor": "hook:pretool-gate",
                "decision": decision,
                "reason": f"dialogue_residue pattern={pat}",
                "path": path,
            })
            if is_critical:
                return f"REDIRECT dialogue_residue_in_spec_doc pattern={pat} path={path}|检测到对话残渣写入关键文档。请清理多余对话用语,保留纯文档内容后重试。"
            return None  # WARN passes through
    return None


# ── Context-control gates (G2/G3/G5/G6) ──
# H2 修复注记：G1（单 tick 读文件计数）已删除——计数器是进程内存，
# hook 每次调用都是新进程，结构性不可能工作（死代码）。


def _check_g2_large_file(payload: dict) -> str | None:
    """G2: read without offset/limit and >200 lines → NARROW"""
    tool = _extract_tool(payload).lower()
    if tool not in READ_TOOLS:
        return None
    ti = _extract_input(payload)
    if ti.get("offset") or ti.get("limit"):
        return None
    path = _extract_path(payload)
    if not path:
        return None
    p = ROOT / path.removeprefix("./") if not path.startswith("/") else Path(path)
    if not p.exists():
        return None
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
        if len(lines) > 200:
            return f"NARROW large_file_no_offset path={path} lines={len(lines)} hint='use offset=1 limit=200'"
    except (OSError, UnicodeDecodeError):
        pass
    return None


def _check_g3_reviews(payload: dict) -> str | None:
    """G3: docs/carros/reviews/** → BLOCK"""
    tool = _extract_tool(payload).lower()
    if tool not in READ_TOOLS:
        return None
    path = _extract_path(payload)
    if not path:
        return None
    normalized = path.replace("\\", "/")
    if "docs/carros/reviews/" in normalized:
        return f"REDIRECT reviews path={path}|docs/carros/reviews/* 受读取保护。如需查看 review 内容,请确认权限后重试。"
    return None


def _check_g5_wide_glob(payload: dict) -> str | None:
    """G5: glob '**/*' without type narrowing → NARROW"""
    tool = _extract_tool(payload).lower()
    if tool not in READ_TOOLS:
        return None
    ti = _extract_input(payload)
    glob_val = ti.get("glob") or ti.get("pattern") or _extract_path(payload)
    if isinstance(glob_val, str) and ("**/*" in glob_val or glob_val.strip() in ("*", ".", "./*")):
        return f"NARROW wide_glob pattern={glob_val} hint='add file_glob=*.py or type filter'"
    return None


def _check_g6_budget(payload: dict) -> str | None:
    """G6: budget soft reached → CHECKPOINT_FIRST"""
    tool = _extract_tool(payload).lower()
    if tool not in READ_TOOLS and tool not in WRITE_TOOLS:
        return None
    token = _active_token()
    if not token:
        return None
    budget = token.get("budget", {})
    if not budget:
        return None
    stats = token.get("stats", {})
    turns = stats.get("tick", 0) + stats.get("turns", 0)
    soft = budget.get("max_turns_soft", 0) or 0
    hard = budget.get("max_turns_hard", 0) or 0
    if soft > 0 and turns >= soft:
        return f"CHECKPOINT_FIRST budget_soft_reached turns={turns} soft={soft} hard={hard}"
    return None


def _check_context_critical_pause(payload: dict) -> str | None:
    """GA water hard gate: while PAUSED_CONTEXT_CRITICAL, allow only recovery-class actions."""
    if not CRITICAL_STATE.exists():
        return None
    try:
        state = json.loads(CRITICAL_STATE.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    if state.get("status") != "PAUSED_CONTEXT_CRITICAL":
        return None

    tool = _extract_tool(payload).lower()
    command = _extract_command(payload).lower()
    path = _extract_path(payload).lower()
    allowed_terms = (
        "status", "checkpoint", "compact", "resume", "archive",
        "context_engine.py", "carros_base.py status", "formal_seal.py",
    )
    text = " ".join([tool, command, path])
    if any(term in text for term in allowed_terms):
        return None
    return ("BLOCK CONTEXT_CRITICAL_PAUSED allowed=status/checkpoint/compact/resume/archive|"
            f"⛔ 上下文处于紧急暂停状态(PAUSED_CONTEXT_CRITICAL)。\n"
            f"原因: 系统检测到上下文压力过高，需要先恢复。\n"
            f"可选方案:\n"
            f"  1. 运行 /compact 释放上下文\n"
            f"  2. 运行 status/checkpoint 查看当前状态\n"
            f"  3. 运行 archive 归档已完成的任务\n"
            f"预期结果: 恢复后所有操作自动解除限制")


SECRET_RE = re.compile(r"sk-[A-Za-z0-9]{20,}")
SECRET_SCAN_MAX_BYTES = 1_000_000

def _git_secret_candidates(command: str) -> list[str]:
    """从 git add/commit 命令提取待扫描文件(相对仓库根)。"""
    import subprocess
    parts = command.split()
    if len(parts) < 2 or parts[0] != "git":
        return []
    sub = parts[1]
    if sub == "commit":
        try:
            r = subprocess.run(["git", "diff", "--cached", "--name-only"],
                               capture_output=True, text=True, timeout=10)
            return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
        except Exception:
            return []
    if sub == "add":
        flags = [a for a in parts[2:] if a.startswith("-")]
        args = [a for a in parts[2:] if not a.startswith("-")]
        if "." in args or "-A" in flags or "--all" in flags:
            try:
                r = subprocess.run(["git", "ls-files", "--modified", "--others", "--exclude-standard"],
                                   capture_output=True, text=True, timeout=10)
                return [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
            except Exception:
                return []
        return args
    return []

def _check_secret_scan(payload: dict) -> str | None:
    """Gate: 阻断把明文密钥(sk-...)引入暂存区 — H9 防再染(轮换仍需人工)。"""
    tool = _extract_tool(payload).lower()
    if tool != "bash":
        return None
    command = _extract_command(payload) or ""
    if not re.match(r"^\s*git\s+(add|commit)\b", command):
        return None
    hits = []
    for rel in _git_secret_candidates(command):
        p = ROOT / rel
        try:
            if not p.is_file() or p.stat().st_size > SECRET_SCAN_MAX_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if SECRET_RE.search(text):
            hits.append(rel)
    if hits:
        _append_audit({
            "event_type": "secret_scan_block",
            "actor": "hook:pretool-gate",
            "decision": "BLOCK",
            "reason": "plaintext_secret_in_staging",
            "files": hits[:10],
        })
        return ("BLOCK plaintext_secret_in_staging files=" + ",".join(hits[:5]) + "|"
                "⛔ 检测到明文密钥(sk-...)将被添加到暂存区。\n"
                "原因: 明文密钥提交到 Git 仓库会导致凭据泄露,即使后续删除也存在于 git 历史中。\n"
                "可选方案:\n"
                "  1. 将密钥改为环境变量引用: 在 .env 或环境变量中设置,代码中读取 os.environ\n"
                "  2. 使用 .gitignore 排除包含密钥的文件\n"
                "  3. 如果是误报(如测试密钥),使用临时 bypass 授权:\n"
                "     `python3 .claude/scripts/temp-bypass.py --minutes 10 --reason \"确认安全\"`\n"
                "预期结果: 修复后密钥被移除;授权后继续提交")
    return None


# ── Gate registry ──

# ── 上下文水位门(owner 2026-07-20 规格: 50%提醒/70%只读/80%强制) ──
# 实测在 pretool-user-approve(每轮尾读 transcript usage),本门只读 state 文件。
# 提醒层由 UserPromptSubmit 注入完成;这里实现 70% 只读 + 80% 强制。
WATERMARK_STATE = OMC / "state" / "context-watermark.json"
WATERMARK_READONLY_PCT = 70.0
WATERMARK_FORCE_PCT = 80.0
WATERMARK_STALE_S = 1800  # 30 分钟未刷新=数据失效,fail-open(下轮 prompt 会刷新)
MUTATING_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def _check_watermark_gate(payload: dict) -> str | None:
    """Gate 0: 上下文水位——70% 只读(禁文件写工具),80% 强制 compact(全阻断)。"""
    try:
        data = json.loads(WATERMARK_STATE.read_text(encoding="utf-8"))
    except Exception:
        return None
    try:
        pct = float(data.get("pct", 0))
    except (TypeError, ValueError):
        return None
    at = data.get("at", "")
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(at)).total_seconds()
        if age > WATERMARK_STALE_S:
            return None
    except Exception:
        return None
    if pct >= WATERMARK_FORCE_PCT:
        _append_audit({
            "event_type": "context_watermark_hint",
            "actor": "hook:pretool-gate",
            "level": "FORCE",
            "pct": pct,
            "tool": _extract_tool(payload),
        })
        return (f"CHECKPOINT context_watermark_force:{pct}%|上下文 {pct}% ≥80%——建议立即 /compact;"
                f"compact 后水位回落自动解除。当前操作将被引导优先执行 /compact 而非继续推进。")
    if pct >= WATERMARK_READONLY_PCT and _extract_tool(payload) in MUTATING_TOOLS:
        _append_audit({
            "event_type": "context_watermark_hint",
            "actor": "hook:pretool-gate",
            "level": "READONLY",
            "pct": pct,
            "tool": _extract_tool(payload),
        })
        return (f"NARROW context_watermark_readonly:{pct}%|上下文 {pct}% ≥70%——水位偏高,"
                f"建议先 /compact 再继续写操作。当前写操作将被引导优先执行 /compact。")
    return None


# ── E4: Action-loop detection — same tool+cmd repeated >=3 times in last 20 audit events ──
_ACTION_LOOP_STREAK_FILE = OMC / "state" / "action-loop-streak"
_ACTION_LOOP_REDIRECT_THRESHOLD = 3  # 连续3次NARROW → 升级为REDIRECT（拦截+引导）
_ACTION_LOOP_ESCALATE_THRESHOLD = 4  # 连续4次NARROW → 升级为BLOCK（硬拦截）
# 惯性执行检测只关注写工具和 Bash（读工具的自然重复是正常行为）
_ACTION_LOOP_MUTATING_TOOLS = {"write", "edit", "multiedit", "notebookedit", "bash"}

# ── Gate9: 数值断言溯源（E8 防止无来源数值声明）──
# 拦截写入中 performance/evaluation 语义的数值断言，
# 要求附带可验证来源（file:line / command output / benchmark ref）
# 豁免：端口号、版本号、代码行数、配置值、操作计数
_NUMERIC_CLAIM_PATTERNS = [
    # 提升/下降类（必须溯源）
    r"(?:提升|提高|增加|增长|下降|降低|减少|节省|优化)[了约]?\s*\d+(?:\.\d+)?%?",
    r"(?:性能|速度|响应|延迟|耗时|质量|覆盖率)[^。\n]{0,10}(?:提升|提高|增加|改善|优化|降低|减少)\s*\d+(?:\.\d+)?%?",
    # 通过率/成功率类
    r"(?:通过|成功|准确|精确|召回)[率度]\s*(?:达[到至约]|:)?\s*\d+(?:\.\d+)?%",
    # 比较类
    r"(?:从|由)\s*\d+[^，。\n]{0,10}(?:提升|下降到|降低到|涨到|减到)\s*\d+",
    # 倍率类
    r"\d+(?:\.\d+)?\s*倍(?:的)?(?:性能|速度|提升|加速)?",
]
_ALLOWED_NUMERIC_CLAIM_EXEMPTIONS = [
    r"(?:修复|修复了|添加|添加了|删除|删除了|重构|重构了|实现|实现了|新增|移除了)\s*\d+\s*个",
    r"(?:第|共)\s*\d+\s*(?:步|个文件|条|次|行)",
    r"\d+\.\d+\.\d+(?:-\w+)?",  # semver
    r"(?:端口|port)\s*\d+",  # port numbers
    r"HTTP[ /]\d+",  # HTTP codes
    r"状态码[:：]?\s*\d+",
    r"文件\s*[:：]?\s*[^\s]+\.\w+:\d+",  # file:line
    r"代码行数[:：]?\s*\d+",
]

def _check_numeric_claim(payload: dict) -> str | None:
    """Gate 9: 写入内容中检测无来源的性能/指标类数值断言"""
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path or not path.endswith((".md", ".rst", ".txt", ".json", ".yaml", ".yml")):
        return None
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not content:
        return None
    # 不检查代码文件、配置文件、纯数据
    if any(path.endswith(ext) for ext in (".py", ".js", ".ts", ".go", ".rs", ".c", ".h", ".java")):
        return None
    hits = []
    for pat in _NUMERIC_CLAIM_PATTERNS:
        for m in re.finditer(pat, content, re.IGNORECASE):
            text = m.group(0)
            # 检查豁免
            exempt = any(re.match(ep, text, re.IGNORECASE) for ep in _ALLOWED_NUMERIC_CLAIM_EXEMPTIONS)
            # 检查是否已带来源引用
            has_source = bool(re.search(
                r'(?:\[已验证|\[已测试|\[内部自检|VERIFIED|source[:：]|来源[:：]|ref[:：]|https?://|[a-zA-Z0-9_./-]+\.[a-z]+:\d+)',
                text
            ))
            if not exempt and not has_source:
                hits.append(text)
    if hits:
        _append_audit({
            "event_type": "numeric_claim_warning",
            "actor": "hook:pretool-gate",
            "decision": "WARN",
            "reason": "unverified_numeric_claim",
            "path": path,
            "claims": hits[:5],
        })
        sample = " | ".join(hits[:3])
        return (f"WARN unverified_numeric_claim path={path}|"
                f"检测到无来源的数值断言（{sample}）。"
                f"建议: 在数字后标注来源引用（file:line/reference/benchmark）。此为建议,不阻断操作。")
    return None

def _check_action_loop(payload: dict) -> str | None:
    """Detects repetitive same-action calls (E4 inertial execution guard).

    Reads .omc/audit/{today}.jsonl, finds the last 20 Bash/Write tool events.
    If the same (tool_name + command_hash) appears >=3 times → soft NARROW warning.
    E4增强: 连续3次同签名NARROW → 第4次升级为BLOCK（惯性执行硬化）。
    仅跟踪写工具和 Bash（Read/Glob/Grep 自然重复不触发）。
    """
    from collections import Counter
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        audit_file = AUDIT / f"{today}.jsonl"
        if not audit_file.exists():
            return None
        lines = audit_file.read_text(encoding="utf-8").strip().splitlines()
        recent_tools: list[str] = []
        for line in reversed(lines):
            if len(recent_tools) >= 20:
                break
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("event_type") not in ("preaction_decision", "gate_bypassed", "gate_soft_warn", "verify_decision", "token_init"):
                # 只跟踪写工具和 Bash 调用（排除 Read/Glob/Grep 自然重复）
                tool = (ev.get("tool", "") or ev.get("tool_name", "") or "").lower()
                if not tool:
                    # 无 tool 字段的 audit 事件全部跳过(非正常工具调用)
                    continue
                if tool not in _ACTION_LOOP_MUTATING_TOOLS:
                    continue
                cmd = str(ev.get("command_preview", "") or ev.get("command", "") or "")
                if tool and cmd:
                    recent_tools.append(f"{tool}:{cmd[:80]}")
                else:
                    fpath = str(ev.get("path", "") or ev.get("file_path", "") or "")
                    if fpath:
                        recent_tools.append(f"{tool}:{fpath[:80]}")
                    else:
                        continue  # 无命令也无路径 → 跳过
        if len(recent_tools) < 3:
            return None
        cnt = Counter(recent_tools)
        top_sig, top_n = cnt.most_common(1)[0]
        if top_n >= 3:
            # E4增强: 读取 streak 判断是否升级
            _streak_sig = ""
            _streak_count = 0
            try:
                if _ACTION_LOOP_STREAK_FILE.exists():
                    raw = json.loads(_ACTION_LOOP_STREAK_FILE.read_text(encoding="utf-8"))
                    _streak_sig = raw.get("sig", "")
                    _streak_count = raw.get("count", 0)
            except Exception:
                _streak_sig = ""
                _streak_count = 0

            if _streak_sig == top_sig:
                _streak_count += 1
            else:
                _streak_count = 1  # 不同签名 → 重新计数
                _streak_sig = top_sig

            # 持久化 streak
            try:
                _ACTION_LOOP_STREAK_FILE.parent.mkdir(parents=True, exist_ok=True)
                _ACTION_LOOP_STREAK_FILE.write_text(
                    json.dumps({"sig": _streak_sig, "count": _streak_count}), encoding="utf-8")
            except OSError:
                pass

            _append_audit({
                "event_type": "action_loop_warn",
                "actor": "hook:pretool-gate",
                "pattern": top_sig,
                "count": top_n,
                "window": len(recent_tools),
                "streak": _streak_count,
            })

            # E4增强(规则修正2026-07-25): 连续同签名NARROW最多到REDIRECT,
            # 不升级到BLOCK——AI惯性执行不是安全风险,引导即可。
            # 4次后清理 streak 防无限重复,但始终返回 REDIRECT(允许AI修正后继续)。
            if _streak_count >= _ACTION_LOOP_ESCALATE_THRESHOLD:
                # ≥4次: 清理 streak 防无限循环,仍返回 REDIRECT
                try:
                    _ACTION_LOOP_STREAK_FILE.unlink(missing_ok=True)
                except OSError:
                    pass
                _append_audit({
                    "event_type": "action_loop_redirect",
                    "actor": "hook:pretool-gate",
                    "decision": "REDIRECT",
                    "pattern": top_sig,
                    "count": top_n,
                    "window": len(recent_tools),
                    "streak": _streak_count,
                })
                return (f"REDIRECT action-loop-redirect: {top_sig} 重复 {top_n}/{len(recent_tools)} 次|"
                        f"同一操作已重复过多——请停止当前行为,换一个不同的方法。"
                        f"如果是修复尝试,先确认前一次修复失败的原因(查看 stderr/exit code)再换方案")
            if _streak_count >= _ACTION_LOOP_REDIRECT_THRESHOLD:
                # 3次: REDIRECT（拦截+引导），不清理 streak
                _append_audit({
                    "event_type": "action_loop_redirect",
                    "actor": "hook:pretool-gate",
                    "decision": "REDIRECT",
                    "pattern": top_sig,
                    "count": top_n,
                    "window": len(recent_tools),
                    "streak": _streak_count,
                })
                return (f"REDIRECT action-loop-redirect: {top_sig} 重复 {top_n}/{len(recent_tools)} 次|"
                        f"同一操作已重复过多——请停止当前行为,换一个不同的方法。"
                        f"如果是修复尝试,先确认前一次修复失败的原因(查看 stderr/exit code)再换方案")

            return f"NARROW action-loop: {top_sig} 重复 {top_n}/{len(recent_tools)} 次 "
    except Exception:
        return None
    return None


def _check_stall(payload: dict) -> str | None:
    """检测 AI stall（长时间无有效推进）。

    读取上次工具调用时间戳，如果间隔超过阈值则 WARN。
    阈值: L1=120s, L2=60s（更严格），仅 goal/auto 模式生效。
    """
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS and tool != "bash":
        return None
    # 仅在 goal/auto 模式检查
    goal_mode = _goal_mode()
    if not goal_mode:
        return None
    gate_mode = _get_gate_mode()
    stall_sec = 120 if gate_mode == "l1" else 60
    now = datetime.now(timezone.utc).timestamp()
    _STALL_FILE = OMC / "state" / ".last-tool-ts"
    try:
        if _STALL_FILE.exists():
            last_ts = float(_STALL_FILE.read_text().strip())
            elapsed = now - last_ts
            _STALL_FILE.write_text(str(now))
            if elapsed > stall_sec:
                _append_audit({
                    "event_type": "stall_warning",
                    "actor": "hook:pretool-gate",
                    "elapsed_sec": int(elapsed),
                    "threshold": stall_sec,
                })
                return f"NARROW stall-detected: 上次工具调用已过 {int(elapsed)}s（阈值 {stall_sec}s）。建议: 检查是否需 compact 恢复上下文"
    except (OSError, ValueError):
        pass
    try:
        _STALL_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STALL_FILE.write_text(str(now))
    except OSError:
        pass
    return None


def _get_gate_mode() -> str:
    """读取当前 gate 模式（L1 轻量 / L2 完整）。

    优先级（v3 修正）:
    CI/non-tty:   harness.yaml > env（环境变量不覆盖治理配置）
    Interactive:  CLI --mode > harness.yaml > env
    """
    # 检测是否为 CI/non-tty 环境
    is_ci = _is_ci_environment()
    env_mode = os.environ.get("CARROROS_GATE_MODE", "").lower()
    # 读取 harness.yaml
    harness_mode = "l1"
    try:
        _HM = ROOT / "scripts" / "carroros-gates" / "harness.yaml"
        if _HM.exists():
            import yaml
            _hd = yaml.safe_load(_HM.read_text(encoding="utf-8")) or {}
            gm = (_hd.get("project", {}) or {}).get("gate_mode", "l1")
            if isinstance(gm, str) and gm.lower() in ("l1", "l2"):
                harness_mode = gm.lower()
    except Exception:
        pass
    # 优先级决策
    if is_ci:
        return harness_mode  # CI 环境只信 harness.yaml
    if env_mode in ("l1", "l2"):
        return env_mode  # 交互环境 CLI > harness
    return harness_mode


def _is_ci_environment() -> bool:
    """检测是否为 CI/非交互环境"""
    return (
        not sys.stdin.isatty() or
        os.environ.get("CI") == "true" or
        os.environ.get("CARROROS_CI_MODE") == "1"
    )


def _validate_bypass_token(token: str) -> bool:
    """校验 bypass token。

    格式: HMAC-SHA256(secret, nonce + action + timestamp)
    默认使用文件级 secret（.claude/hooks/.bypass_secret），不存在时返回 False
    """
    if not token or len(token) < 8:
        return False
    try:
        _SECRET_FILE = _script_path.parent / ".bypass_secret"
        if not _SECRET_FILE.exists():
            return False
        secret = _SECRET_FILE.read_text(encoding="utf-8").strip()
        if not secret:
            return False
        # Token 格式: <nonce>:<hmac>
        if ":" not in token:
            return False
        parts = token.split(":")
        if len(parts) != 2:
            return False
        import hmac
        nonce, signature = parts
        expected = hmac.new(secret.encode(), nonce.encode(), digestmod="sha256").hexdigest()[:16]
        return hmac.compare_digest(signature, expected)
    except Exception:
        return False


# ── Per-run Gate Evidence ──
def _record_gate_decision(gate_name: str, result: str | None, mode: str) -> None:
    """记录每个 gate 的执行决策到 audit（per-run evidence）"""
    now = datetime.now(timezone.utc)
    _append_audit({
        "event_type": "gate_decision",
        "gate": gate_name,
        "mode": mode,
        "decision": result[:50] if result else "PASS",
        "timestamp": now.isoformat(),
    })


def _verify_contract_compliance(mode: str, executed_gates: set[str]) -> str | None:
    """检查当前 mode 的 gate contract 是否满足。

    返回 None 表示通过，返回 str 表示违规详情。
    """
    try:
        _CONTRACT_PATH = ROOT / "scripts" / "carroros-gates" / "gate-contract.yaml"
        if not _CONTRACT_PATH.exists():
            return None  # 无 contract 文件不检查
        import yaml
        contract = yaml.safe_load(_CONTRACT_PATH.read_text(encoding="utf-8")) or {}
        mode_cfg = contract.get(mode.upper(), {}) or {}
        required = mode_cfg.get("required_gates", [])
        enforcement = mode_cfg.get("enforcement", {}) or {}
        missing = [g for g in required if g not in executed_gates]
        if not missing:
            return None
        policy = enforcement.get("missing_gate", "INFO")
        missing_str = ", ".join(missing[:5])
        if policy == "BLOCK":
            return (f"BLOCK contract-violation: {mode} missing required gates ({missing_str})|"
                    f"⛔ gate-contract.yaml 要求 gate 未执行。\n"
                    f"原因: {mode} 模式要求以下 gate 必须执行: {missing_str}\n"
                    f"可选方案: 检查 gate-contract.yaml 配置\n"
                    f"预期结果: 配置修正后自动通过")
        _append_audit({
            "event_type": "contract_warning",
            "mode": mode,
            "missing_gates": missing,
            "enforcement": policy,
        })
        return None
    except Exception:
        return None

# ── L1/L2 Gate 分级 ──
# L1: 轻量模式（日常任务），仅核心安全门
# L2: 完整模式（复杂/危险任务），全量 16 Gate
L1_GATES = [
    ("watermark", _check_watermark_gate),
    ("context-critical", _check_context_critical_pause),
    ("sensitive-edit", _check_sensitive_edit),
    ("fallback", _check_fallback),
    ("action", _check_action_gate),
    ("edit-scope", _check_edit_scope),
    ("stall", _check_stall),
]

GATES = [
    ("watermark", _check_watermark_gate),
    ("context-critical", _check_context_critical_pause),
    ("sensitive-edit", _check_sensitive_edit),
    ("fallback", _check_fallback),
    ("action", _check_action_gate),
    ("secret-scan", _check_secret_scan),
    ("plan", _check_plan_gate),
    ("edit-scope", _check_edit_scope),
    ("verify", _check_verify_gate),
    ("oracle", _check_oracle_gate),
    ("document-quality", _check_document_quality),
    # Context-control gates (G2/G3/G5/G6)
    ("g2-large-file", _check_g2_large_file),
    ("g3-reviews", _check_g3_reviews),
    ("g5-wide-glob", _check_g5_wide_glob),
    ("g6-budget", _check_g6_budget),
    ("action-loop", _check_action_loop),
    ("stall", _check_stall),
    ("numeric-claim", _check_numeric_claim),
]


def main() -> int:
    payload = _read_stdin()
    tool_name = _extract_tool(payload).lower() or "unknown"

    # 如果用户已创建临时 bypass token，跳过所有 gate 检查
    bypass_active = _check_temp_bypass()

    _clean_stale_state_token()

    # ── Gate 按模式选择 ──
    # L1: 轻量（6 个核心安全门），L2: 全量（16 个 Gate）
    gate_mode = _get_gate_mode()
    active_gates = GATES if gate_mode == "l2" else L1_GATES

    executed_gates: set[str] = set()
    for gate_name, gate_fn in active_gates:
        try:
            result = gate_fn(payload)
            _record_gate_decision(gate_name, result, gate_mode)
            executed_gates.add(gate_name)
        except Exception:
            continue
        if result:
            if result.startswith("REDIRECT"):
                # ADR-0012: REDIRECT = 阻止 + 指引 + AI 自行修正重试
                parts = result.split("|", 1)
                reason = parts[0].replace("REDIRECT ", "").strip()
                guidance = parts[1].strip() if len(parts) > 1 else ""
                return _redirect(reason, guidance)
            if result.startswith("BLOCK"):
                if bypass_active:
                    _append_audit({
                        "event_type": "gate_bypassed",
                        "actor": "hook:pretool-gate",
                        "gate": gate_name,
                        "reason": result,
                    })
                    return _ok(f"BYPASS_ALLOW [{gate_name}] (用户已授权临时跳过)")
                parts = result.split("|", 1)
                reason = parts[0].replace("BLOCK ", "").strip()
                suggestion = parts[1].strip() if len(parts) > 1 else ""
                return _block(reason, suggestion)
            if result == "HARD_BLOCK":
                # 硬阻断：_check_sensitive_edit 已打印 continue:False 到 stdout
                # 直接返回 0，禁止 _ok 覆盖输出
                return 0
            elif result.startswith("ASK_USER"):
                parts = result.split("|", 1)
                reason = parts[0].replace("ASK_USER ", "").strip()
                suggestion = parts[1].strip() if len(parts) > 1 else ""
                return _block(reason, suggestion)
            elif result.startswith(("NARROW", "CHECKPOINT_FIRST", "CHECKPOINT", "WARN")):
                # 软门（G1/G2/G5/G6）：柔性约束——WARN 提示 + audit，不阻断
                _append_audit({
                    "event_type": "gate_soft_warn",
                    "actor": "hook:pretool-gate",
                    "gate": gate_name,
                    "reason": result,
                })
                goal_mode = _goal_mode()
                if not goal_mode:
                    print(f"⚠️ [{gate_name}] {result}", file=sys.stderr, flush=True)
                continue

    # ── Gate Contract Compliance Check ──
    contract_result = _verify_contract_compliance(gate_mode, executed_gates)
    if contract_result and contract_result.startswith("BLOCK"):
        return contract_result

    return _ok(f"ALLOW tool={tool_name}")


if __name__ == "__main__":
    raise SystemExit(main())
