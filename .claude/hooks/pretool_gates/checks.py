"""
checks.py — All _check_* gate functions extracted from pretool-gate.py.
"""
from __future__ import annotations
import json
import os
import re
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constants import (
    ROOT, OMC, STATE_DIR,
    FALLBACK_REQUIRED, FALLBACK_APPROVED, TEMP_BYPASS, TRUST_BREACH,
    SENSITIVE_PATTERNS, DANGEROUS_COMMANDS, WARN_ONLY_COMMANDS,
    ASK_USER_COMMANDS, ORACLE_TRIGGER_KW, ORACLE_FORCE_KW,
    STALE_LOCK_THRESHOLD, READ_TOOLS, WRITE_TOOLS, PLAN_FILE_PATTERNS,
    _INJECTION_PATTERNS, _EXTERNAL_DATA_MAX_LEN,
    STATE_TOKEN, TOKENS, AUDIT,
)
from .helpers import (
    _goal_mode, _is_governance, _is_sensitive,
    _extract_tool, _extract_input, _extract_path, _extract_command,
    _ok, _block, _check_temp_bypass,
    _check_trust_breach, _record_trust_breach, _is_trust_breach_reason,
    _match_any, _append_audit,
    _active_token, _task_dir,
    _in_scope, _parse_scope, _check_verified,
    _auto_init, _safe_unlink, _auto_archive_token,
    _failure_escalate, _clean_stale_state_token,
    _read_json, _latest_token,
    _ssot_err, _ssot_latest_terminal_token,
)
from .oracle import _oracle_classify, _load_anti_pattern_redirects, _ORACLE_ANTI_PATTERN_RULES


# ── Gate 1: Sensitive edit ──

def _check_sensitive_edit(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path:
        return None
    if _is_governance(path):
        safe = path[:200]
        if _goal_mode():
            msg = f"⚠️ [goal-mode] 治理文件写入: {safe} — goal 模式下降级放行"
            sys.stderr.write(f"PreToolGate: GOV_WARN (goal-mode) - {safe}\n")
            print(json.dumps({"continue": True, "message": msg}, ensure_ascii=False))
            _append_audit({"event_type": "governance_goal_warn", "path": path, "tool": tool})
            return None
        reason_text = (
            f"⚠️ GOVERNANCE_WARN: 治理文件 {safe} 被修改。\n"
            f"  规则: .claude/settings.json 和 .claude/hooks/* 受 Gate 1 保护。\n"
            f"  哲学&铁律: 治理文件不可改，但 AI 自决。\n"
            f"  audit 已记录此事件供退出报告审查。"
        )
        sys.stderr.write(f"PreToolGate: GOV WARN (path={safe})\n{reason_text}\n")
        _append_audit({"event_type": "governance_warn", "path": path, "tool": tool})
        print(json.dumps({"continue": True, "message": reason_text}, ensure_ascii=False))
        return None
    if _is_sensitive(path):
        return (f"ASK_USER 敏感路径 {path}|"
                f"检测到可能包含凭据的敏感文件，请确认是否继续修改。\n"
                f"确认后继续；未确认则停止本次操作。")
    return None


# ── Gate 2: Fallback check ──

def _check_fallback(_payload: dict) -> str | None:
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
        if status == "waiting_user":
            reason = task.get("reason") or "requires_user"
            return (f"ASK_USER Bypass 临时授权状态：{reason}|")
        fallback = task.get("fallback", {}) or {}
        if fallback.get("unresolved"):
            return (f"BLOCK fallback 状态未解决：{fallback.get('reason', 'unknown')}|"
                    f"⛔ 任务处于未解决的 fallback 状态。\n"
                    f"原因: {fallback.get('reason', 'unknown')}\n"
                    f"可选方案: 1. 解决 fallback 问题后继续  2. 使用临时 bypass  3. 输入 /deny 保持状态")
        session = token.get("session", {}) or {}
        if session.get("fallback"):
            return None
        return None
    reason = task.get("blocked") or task.get("reason") or "blocked"
    ts_str = (task.get("fallback") or {}).get("timestamp") or (token.get("session") or {}).get("created_at") or ""
    age = 0.0
    if ts_str:
        try:
            ts = datetime.fromisoformat(ts_str)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
        except Exception:
            pass
    if age >= STALE_LOCK_THRESHOLD:
        _auto_archive_token(token_path, token_data, f"stale_blocked age={int(age)}s reason={reason}")
        return None
    if FALLBACK_APPROVED.exists():
        _auto_archive_token(token_path, token_data, f"user_approved reason={reason}")
        _safe_unlink(FALLBACK_REQUIRED)
        _safe_unlink(FALLBACK_APPROVED)
        return None
    captcha = secrets.token_hex(3)
    try:
        FALLBACK_REQUIRED.parent.mkdir(parents=True, exist_ok=True)
        FALLBACK_REQUIRED.write_text(captcha)
    except OSError:
        pass
    task2 = token.get("task", {})
    session = token.get("session", {})
    task_name = session.get("id") or (task2.get("name") if isinstance(task2, dict) else None) or token_path.stem
    blocked_since = (task2.get("fallback") or {}).get("timestamp") or session.get("created_at", "")[:19] or "?"
    current_step = task2.get("current_step", "?") if isinstance(task2, dict) else "?"
    age_str = f"（阻塞 {int(age)} 秒）" if age > 0 else ""
    msg = (f"\n╔══ CarrorOS 任务阻塞 ══════════════════════════════\n"
           f"║  任务: {task_name}\n║  状态: blocked  {age_str}\n"
           f"║  原因: {reason}\n║  当前步骤: {current_step}\n"
           f"║  阻塞自: {blocked_since[:19]}\n"
           f"║  📌 如需解除阻塞并归档此任务,请输入: /approve {captcha}\n"
           f"║  📌 如需保持阻塞状态: /deny\n"
           f"║  ⏱ 或等待 {max(1, int(STALE_LOCK_THRESHOLD/60 - age/60))} 分钟后自动解除\n"
           f"╚══════════════════════════════════════════════════\n")
    print(msg, file=sys.stderr, flush=True)
    return (f"BLOCK task_blocked reason={reason}|"
            f"⛔ 任务处于 blocked 状态。\n原因: {reason}\n"
            f"可选方案: 1. 输入 /approve <token> 解除阻塞  2. 输入 /deny 保持阻塞\n"
            f"预期结果: 解除后任务继续执行")


# ── Gate 3: Action gate ──

def _check_action_gate(payload: dict) -> str | None:
    command = _extract_command(payload)
    if not command:
        return None
    hard = _match_any(command, DANGEROUS_COMMANDS)
    if hard:
        _append_audit({"event_type": "preaction_decision", "actor": "hook:pretool-gate",
                        "decision": "BLOCK", "reason": "dangerous_command",
                        "pattern": hard, "command_preview": command[:160]})
        return (f"BLOCK dangerous_command pattern={hard}|"
                f"⛔ 检测到不可逆破坏性操作。\n"
                f"可选方案: 1. 使用临时 bypass  2. 使用更安全的替代操作  3. 等待用户介入")
    ask = _match_any(command, ASK_USER_COMMANDS)
    if ask:
        _append_audit({"event_type": "preaction_decision", "actor": "hook:pretool-gate",
                        "decision": "WARN", "reason": "approval_required_command",
                        "pattern": ask, "command_preview": command[:160]})
        return f"WARN approval_required pattern={ask}"
    warn_only = _match_any(command, WARN_ONLY_COMMANDS)
    if warn_only:
        _append_audit({"event_type": "preaction_decision", "actor": "hook:pretool-gate",
                        "decision": "WARN", "reason": "path_specific_destructive",
                        "pattern": warn_only, "command_preview": command[:160]})
        return f"WARN path_specific_destructive pattern={warn_only}"
    return None


# ── Gate 4: Plan gate ──

def _check_plan_gate(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    token = _active_token()
    if not token:
        path = _extract_path(payload)
        _auto_init(path)
        return None
    task = token.get("task", {})
    if not isinstance(task, dict):
        return None
    if task.get("status") in {"blocked", "waiting_user"}:
        return f"REDIRECT task_status_{task.get('status')}|任务处于 {task.get('status')} 状态。"
    task_dir = _task_dir(token)
    if not task_dir:
        return None
    plan = task_dir / "plan.md"
    if not plan.exists():
        _append_audit({"event_type": "plan_gate_warn", "actor": "hook:pretool-gate",
                        "decision": "WARN", "reason": f"plan_missing task_dir={task_dir}"})
        print(f"⚠️ [plan-gate] plan.md 不存在: {task_dir}", file=sys.stderr, flush=True)
        return None
    if not task.get("current_step"):
        _append_audit({"event_type": "plan_gate_warn", "actor": "hook:pretool-gate",
                        "decision": "WARN", "reason": "current_step_missing"})
        print("⚠️ [plan-gate] 任务缺少 current_step 状态", file=sys.stderr, flush=True)
        return None
    return None


# ── Gate 5: Edit scope ──

def _check_edit_scope(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    if _ssot_err is not None:
        return f"edit-scope: task_ssot 导入失败({_ssot_err!r})——fail-closed 阻断"
    path = _extract_path(payload)
    if not path:
        return None
    if _is_governance(path):
        token = _active_token()
        task_dir = _task_dir(token) if token else None
        declared_scope = []
        if task_dir:
            plan_path = task_dir / "plan.md"
            try:
                if plan_path.exists():
                    declared_scope = _parse_scope(plan_path.read_text(encoding="utf-8"))
            except OSError:
                declared_scope = []
        if _goal_mode() and declared_scope and _in_scope(path, declared_scope):
            _append_audit({"event_type": "governance_scope_allow", "actor": "hook:pretool-gate",
                           "decision": "ALLOW", "reason": "human-approved-plan-scope", "path": path})
            return None
        _append_audit({"event_type": "governance_scope_ask_user", "actor": "hook:pretool-gate",
                        "decision": "ASK_USER", "reason": "governance_file_out_of_scope", "path": path})
        return "ASK_USER governance_path: 治理文件变更需要确认|请确认变更范围后继续。"
    # `.claude/` 下非治理文件（如 workflows/ references/ UI_README.md）是项目基建，
    # 不属于 scope 越界，放行。
    _p = path.replace("\\", "/")
    if _p.startswith(".claude/") or _p.startswith("./.claude/"):
        return None
    token = _active_token()
    if not token:
        return None

    goal_mode = _goal_mode()
    goal_text = str(token.get("goal", "") or token.get("goal", {}).get("description", ""))
    workflow_goal = goal_mode and "frontend-overnight" in goal_text
    local_goal_scope = [
        "src/", "public/", ".claude/workflows/", ".omc/ui-autopilot/"
    ] if workflow_goal else []

    def _scope_notice() -> str:
        _append_audit({"event_type": "scope_review_notice", "actor": "hook:pretool-gate",
                       "decision": "WARN", "path": path,
                       "reason": "plan_scope_is_mutable"})
        return "WARN edit-scope: 当前变更超出原 scope；plan 可合理更新，继续执行并记录原因。"

    _HARNESS_PATH = ROOT / "scripts" / "carroros-gates" / "harness.yaml"
    harness_scope = []
    try:
        if _HARNESS_PATH.exists():
            import yaml
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
        if _in_scope(path, harness_scope):
            return None
        _append_audit({"event_type": "scope_violation", "actor": "hook:pretool-gate",
                        "decision": "WARN", "reason": "harness_scope_violation",
                        "path": path, "scope": harness_scope[:10]})
        print(f"⚠️ [edit-scope] 路径不在 project scope 内: {path}", file=sys.stderr, flush=True)
        return _scope_notice()
    token_scope = token.get("implementation_scope") or token.get("scope") or []
    token_scope = [s for s in token_scope if not re.match(r"^[a-zA-Z]+://", str(s)) and not str(s).startswith("//")]
    if local_goal_scope and _in_scope(path, local_goal_scope):
        return None
    if token_scope:
        if _in_scope(path, token_scope):
            return None
        _append_audit({"event_type": "scope_violation", "actor": "hook:pretool-gate",
                        "decision": "WARN", "reason": "token_scope_violation",
                        "path": path, "scope": token_scope[:10]})
        print(f"⚠️ [edit-scope] 路径不在 token scope 内: {path}", file=sys.stderr, flush=True)
        return _scope_notice()
    _task_dir2 = _task_dir(token)
    if _task_dir2 and _task_dir2.exists():
        if not _in_scope(path, [str(_task_dir2)]):
            print(f"⚠️ [edit-scope] 路径不在默认 task scope 内: {path}", file=sys.stderr, flush=True)
            return _scope_notice()
    return None


# ── Gate 6: Verify gate ──

def _check_verify_gate(payload: dict) -> str | None:
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
        _append_audit({"event_type": "verifygate_preaction_block", "actor": "hook:pretool-gate",
                        "decision": "REDIRECT", "reason": "step_not_verified",
                        "path": path, "current_step": current_step})
        return f"REDIRECT step_{current_step}_not_VERIFIED|当前步骤 {current_step} 尚未通过验证。"
    return None


# ── Gate 7: Oracle gate ──

def _check_oracle_gate(payload: dict) -> str | None:
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
        if detail in ("gov_file_bypass",):
            _guidance = ""
            for _, _detail, _guide in _ORACLE_ANTI_PATTERN_RULES:
                if _detail == detail:
                    _guidance = _guide
                    break
            return f"REDIRECT oracle_redirect:{detail}|{_guidance}"
        _guidance = ""
        for _, _detail, _guide in _ORACLE_ANTI_PATTERN_RULES:
            if _detail == detail:
                _guidance = _guide
                break
        print(f"⚠️ [oracle-gate] 检测到反模式({detail})", file=sys.stderr, flush=True)
        return None
    if verdict == "BLOCK":
        return (f"BLOCK oracle_gate:{detail}|"
                f"⛔ 检测到高置信危险语义({detail})。\n"
                f"可选方案: 1. 移除绕过语义后重试  2. 确需绕过: 用户人工裁决")
    if verdict == "ESCALATE":
        return (f"ASK_USER oracle_gate:{detail}|"
                f"❓ 命令无法可靠解析且含高危信号,请人工判断。")
    if verdict in ("FORCE", "TRIGGER"):
        print(f"🔮 [oracle-gate] L2 {verdict} 触发检测", file=sys.stderr, flush=True)
    return None


# ── Document quality gate ──

def _check_document_quality(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path or not path.endswith(".md"):
        return None
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not content or len(content) < 50:
        return None
    warnings = []
    if re.search(r"(?i)\bTODO\b", content) and re.search(r"(?i)\bFIXME\b", content):
        warnings.append("含 TODO/FIXME 标记")
    if re.search(r"(?i)\b(TBD|to be determined|under construction)\b", content):
        warnings.append("含未完成标记")
    if warnings:
        msg = f"⚠️ [document-quality] {', '.join(warnings)} in {path}"
        _append_audit({"event_type": "document_quality_warn", "path": path, "warnings": warnings})
        print(msg, file=sys.stderr, flush=True)
    return None


# ── Context control gates ──

def _check_g2_large_file(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path:
        return None
    try:
        fpath = Path(path) if not Path(path).is_absolute() else Path(path)
        if not fpath.exists():
            return None
        size = fpath.stat().st_size
        if size > 500_000:
            return f"NARROW g2-large-file: {path} ({size/1024:.0f}KB) 建议分小文件写入"
    except Exception:
        pass
    return None


def _check_g3_reviews(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path:
        return None
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if len(content) > 2000 and any(kw in content.lower() for kw in ("review", "pr", "merge", "commit")):
        return f"CHECKPOINT_FIRST g3-review-large: 大段 review 内容,请先确认需要"
    return None


def _check_g5_wide_glob(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool != "bash":
        return None
    cmd = _extract_command(payload)
    if not cmd:
        return None
    if re.search(r"\*\*/\*\.\w+|find\s+.*-name\s+['\"]?\*", cmd) and not re.search(r"\|", cmd):
        return f"NARROW g5-wide-glob: 宽泛 glob 可能匹配大量文件,请确认范围"
    return None


def _check_g6_budget(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool != "bash":
        return None
    cmd = _extract_command(payload)
    if not cmd:
        return None
    if re.search(r"(pip|npm|brew|conda)\s+(install|update|upgrade)\s", cmd, re.IGNORECASE):
        return f"CHECKPOINT g6-dependency: 安装依赖,确认不影响项目"
    return None



# ── Secret scan ──

def _git_secret_candidates(command: str) -> list[str]:
    candidates = []
    patterns = [
        (r"\b[A-Za-z0-9+/=]{40,}\b", "base64_like"),
        (r"\bgh[ps]_[A-Za-z0-9]{36,}\b", "github_token"),
        (r"\bsk-[A-Za-z0-9]{20,}\b", "openai_key"),
        (r"\bAKIA[A-Z0-9]{16}\b", "aws_key"),
        (r"(?i)\bpassword\s*[=:]\s*['\"][^'\"]{6,}['\"]", "password_assignment"),
    ]
    for pat, label in patterns:
        if re.search(pat, command):
            candidates.append(label)
    return candidates


def _check_secret_scan(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    command = _extract_command(payload)
    if not command and tool in WRITE_TOOLS:
        ti = _extract_input(payload)
        command = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not command:
        return None
    # Git operations
    if tool == "bash" and re.search(r"\bgit\s+push\b", command, re.IGNORECASE):
        cands = _git_secret_candidates(command)
        if cands:
            _append_audit({"event_type": "secret_scan_warning", "actor": "hook:pretool-gate",
                            "decision": "WARN", "reason": f"git_push_secret_candidates:{cands}",
                            "command_preview": command[:160]})
            print(f"⚠️ [secret-scan] git push 含潜在密钥: {cands}", file=sys.stderr, flush=True)
    return None


# ── Watermark gate ──

def _check_source_marker(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path or not path.endswith((".py", ".sh", ".yaml", ".yml", ".json")):
        return None
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not content or len(content) < 200:
        return None
    # Goal mode bypass
    if _goal_mode():
        return None
    # Check marker: Python comment or shell/YAML comment
    lines = content.split("\n")
    first_line = lines[0].strip() if lines else ""
    second_line = lines[1].strip() if len(lines) > 1 else ""
    has_marker = False
    if path.endswith(".py"):
        has_marker = bool(re.search(r"CarrorOS|Auto-generated|DO NOT EDIT", first_line + second_line))
    elif path.endswith(".sh"):
        has_marker = bool(re.search(r"CarrorOS|Auto-generated|DO NOT EDIT", first_line + second_line))
    elif path.endswith((".yaml", ".yml", ".json")):
        for i, l in enumerate(lines[:5]):
            l = l.strip()
            if l.startswith("#") and re.search(r"CarrorOS|Auto-generated|DO NOT EDIT", l):
                has_marker = True
                break
    if not has_marker:
        _append_audit({"event_type": "source_marker_missing", "actor": "hook:pretool-gate",
                        "decision": "WARN", "reason": "no_source_marker", "path": path})
        print(f"⚠️ [source-marker] 新建文件 {path} 缺少 CarrorOS 标记", file=sys.stderr, flush=True)
    return None


# ── Numeric claim gate ──

def _check_numeric_claim(payload: dict) -> str | None:
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
    suspicious = []
    for m in re.finditer(r"(?<!\d)(\d{2,}(?:\.\d+)?%|\d+(?:x|倍|ms|s|gb|mb|kb))(?!\d)", content, re.IGNORECASE):
        line_num = content[:m.start()].count("\n") + 1
        suspicious.append(f"L{line_num}:{m.group()[:30]}")
    if suspicious:
        _append_audit({"event_type": "numeric_claim_detected", "actor": "hook:pretool-gate",
                        "decision": "WARN", "reason": "unattributed_numeric_claim",
                        "path": path, "claims": suspicious[:5]})
        print(f"⚠️ [numeric-claim] 无来源数值断言: {suspicious[:3]}", file=sys.stderr, flush=True)
    return None


# ── Claim source gate ──

def _check_claim_source(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in WRITE_TOOLS:
        return None
    path = _extract_path(payload)
    if not path or not path.endswith(".md"):
        return None
    ti = _extract_input(payload)
    content = str(ti.get("content", "") or ti.get("new_string", "") or "")
    if not content or len(content) < 100:
        return None
    lack_source = False
    for m in re.finditer(r"(?i)\b(file|path|directory|module|class|function|method)\s+(is|was|has|does)\b", content):
        snippet = content[max(0, m.start()-30):m.end()+30]
        if not re.search(r"\[.*\]\(.*\)|`[^`]+`|file:\w+|\bfound\b|\bseen\b|\bdetected\b", snippet):
            lack_source = True
            break
    if lack_source:
        _append_audit({"event_type": "claim_no_source", "actor": "hook:pretool-gate",
                        "decision": "WARN", "reason": "statement_without_source", "path": path})
        print(f"⚠️ [claim-source] 断言缺少来源引用: {path}", file=sys.stderr, flush=True)
    return None


# ── Action loop gate ──

def _check_action_loop(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool != "bash":
        return None
    command = _extract_command(payload)
    if not command or len(command) < 200:
        return None
    _loop_count_file = STATE_DIR / "action-loop-count.json"
    _loop_reset_s = 300  # 5 min
    _loop_threshold = 5
    try:
        if _loop_count_file.exists():
            raw = json.loads(_loop_count_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                last_ts = raw.get("ts", 0)
                count = raw.get("c", 0)
                if time.time() - last_ts > _loop_reset_s:
                    count = 0
                count += 1
                if count >= _loop_threshold:
                    _append_audit({"event_type": "action_loop_detected", "actor": "hook:pretool-gate",
                                    "decision": "BLOCK", "reason": f"action_loop_{count}_times"})
                    return (f"BLOCK action_loop: 已连续 {count} 次长命令执行,可能陷入循环。"
                            "请暂停当前方向,重新评估后重试。")
                _loop_count_file.write_text(json.dumps({"c": count, "ts": time.time()}))
    except Exception:
        pass
    return None


# ── Stall detection gate ──

def _check_stall(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool not in READ_TOOLS:
        return None
    path = _extract_path(payload)
    session_id_current = os.environ.get("HERMES_SESSION_ID") or ""
    if not session_id_current:
        return None
    _stall_file = OMC / "state" / "stall-count.json"
    _stall_reset_s = 120
    _stall_threshold = 8
    try:
        if path and _stall_file.exists():
            raw = json.loads(_stall_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and raw.get("path") == path and raw.get("session") == session_id_current:
                if time.time() - raw.get("ts", 0) < _stall_reset_s:
                    count = raw.get("c", 0) + 1
                    if count >= _stall_threshold:
                        _append_audit({"event_type": "stall_detected", "actor": "hook:pretool-gate",
                                        "decision": "REDIRECT", "reason": f"stall_{count}_reads",
                                        "path": path, "session_id": session_id_current[:16]})
                        return (f"REDIRECT stall_reads: 已重复读取 {path} {count} 次。"
                                "建议直接基于已读信息推进,不要反复确认。")
                    _stall_file.write_text(json.dumps({"c": count, "ts": time.time(),
                                                        "path": path, "session": session_id_current}))
                else:
                    _stall_file.write_text(json.dumps({"c": 1, "ts": time.time(),
                                                        "path": path, "session": session_id_current}))
    except Exception:
        pass
    return None


# ── Injection guard gate ──

def _check_injection(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    ti = _extract_input(payload)
    if tool not in WRITE_TOOLS:
        return None
    content = ""
    for key in ("content", "new_string", "file_content", "text", "data"):
        val = ti.get(key)
        if isinstance(val, str) and len(val) > 20:
            content = val
            break
    if not content:
        return None
    for pattern in _INJECTION_PATTERNS:
        m = pattern.search(content)
        if m:
            _append_audit({"event_type": "injection_detected", "actor": "hook:pretool-gate",
                            "decision": "BLOCK", "reason": f"prompt_injection_pattern:{pattern.pattern[:40]}",
                            "tool": tool, "match": m.group()[:80]})
            return (f"BLOCK injection_detected tool={tool}|"
                    f"⛔ 写入内容检测到提示注入模式: '{m.group()[:60]}'")
    if len(content) > _EXTERNAL_DATA_MAX_LEN:
        return (f"REDIRECT content_truncated tool={tool}|"
                f"内容长度 {len(content)} 字符超过 8000 限制。使用 Write 写入前 6000 字符+续写标记，再用 Edit 替换标记追加剩余内容")
    return None
