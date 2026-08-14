"""
checks.py — All _check_* gate functions extracted from pretool-gate.py.
"""
from __future__ import annotations
import json
import os
import re
import sys
import time
from pathlib import Path

from .constants import (
    OMC, STATE_DIR,
    DANGEROUS_COMMANDS, WARN_ONLY_COMMANDS, ASK_USER_COMMANDS,
    READ_TOOLS, WRITE_TOOLS, PLAN_FILE_PATTERNS,
    _INJECTION_PATTERNS, _EXTERNAL_DATA_MAX_LEN,
    BASH_READ_TOKEN_RE, BASH_WRITE_TOKEN_RE,
    SECRET_CONTENT_COMPILED, PRIVACY_SCAN_SIZE_CAP,
    READ_SENSITIVE_PATTERNS,
)
from .helpers import (
    _goal_mode, _is_governance, _is_sensitive,
    _extract_tool, _extract_input, _extract_path, _extract_command,
    _match_any, _append_audit,
    _active_token, _task_dir, _check_verified,
)
from .oracle import _oracle_classify, _ORACLE_ANTI_PATTERN_RULES


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


# ── Gate 1b (index25): sensitive read — 读取侧隐私门禁 ──
# 动机: posttool-sensitive-filter 是提示型掩码（hook stderr 输出掩码版，不剥离模型可见的
# 原始工具结果）→ 密钥仍会进入模型上下文（index24 P1 双法官确认）。本门在读取前拦截:
# 路径命中敏感模式 → 直接拦；内容命中密钥模式（<1MB 文本）→ 拦。
def _candidate_read_paths(payload: dict) -> list[str]:
    tool = _extract_tool(payload).lower()
    inp = _extract_input(payload)
    paths: list[str] = []
    if tool in ("read", "grep", "search_files"):
        p = str(inp.get("file_path") or inp.get("path") or "")
        if p:
            paths.append(p)
    elif tool == "bash":
        cmd = _extract_command(payload) or ""
        for m in BASH_READ_TOKEN_RE.finditer(cmd):
            g = m.group(1) or m.group(2)
            if g:
                paths.append(g)
    return paths


def _resolve_read_path(p: str) -> Path:
    q = Path(p.strip().strip("'\""))
    if not q.is_absolute():
        q = Path(os.getcwd()) / q
    return q


_READ_SENSITIVE_RE = re.compile("|".join(READ_SENSITIVE_PATTERNS), re.IGNORECASE)


def _is_read_sensitive(path: str) -> bool:
    """读取侧敏感判定：仅凭据/密钥类路径；治理文件域（AGENTS.md/.claude/hooks）可读。"""
    return bool(_READ_SENSITIVE_RE.search(path.replace("\\", "/")))


def _check_sensitive_read(payload: dict) -> str | None:
    """读取敏感文件（路径模式或内容含密钥模式）→ ASK_USER(deny)，阻止密钥进入上下文。"""
    for raw in _candidate_read_paths(payload):
        q = _resolve_read_path(raw)
        if not q.exists():
            continue
        s = str(q)
        if _is_read_sensitive(s):
            _append_audit({"event_type": "privacy_read_block", "actor": "hook:pretool-gate",
                           "path": s, "reason": "sensitive_path"})
            return (f"ASK_USER sensitive_read|"
                    f"⛔ 读取被隐私门禁拦截：{q.name} 命中敏感路径模式（凭据/密钥）。\n"
                    f"确需读取请人工授权；或先脱敏导出。")
        if q.is_file() and q.stat().st_size <= PRIVACY_SCAN_SIZE_CAP:
            try:
                data = q.read_bytes()
            except OSError:
                continue
            if b"\x00" in data[:8192]:
                continue  # 二进制文件不扫描
            text = data.decode("utf-8", errors="ignore")
            if any(pat.search(text) for pat in SECRET_CONTENT_COMPILED):
                _append_audit({"event_type": "privacy_read_block", "actor": "hook:pretool-gate",
                               "path": s, "reason": "secret_content"})
                return (f"ASK_USER sensitive_read|"
                        f"⛔ 读取被隐私门禁拦截：{q.name} 内容含密钥/凭据模式"
                        f"（sk-*/私钥/令牌）。\n"
                        f"确需读取请人工授权；或使用脱敏导出通道。")
    return None


# ── Gate 1c (index25): sensitive write via Bash — 补 sensitive-edit 的 Bash 通道 ──
# 动机: sensitive-edit 只覆盖 WRITE_TOOLS（Edit/Write），模型经 Bash 写敏感/治理路径
# （sed -i / tee / 重定向 / python open(w|a) / touch）可绕过（index24 P6 双法官确认）。
def _check_sensitive_write_bash(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool != "bash":
        return None
    cmd = _extract_command(payload) or ""
    candidates: list[str] = []
    for rx in BASH_WRITE_TOKEN_RE:
        for m in rx.finditer(cmd):
            g = m.group(1)
            if g:
                candidates.append(g.strip().strip("'\""))
    for raw in candidates:
        if not raw:
            continue
        if _is_sensitive(raw) or _is_governance(raw):
            _append_audit({"event_type": "privacy_write_block", "actor": "hook:pretool-gate",
                           "path": raw, "reason": "sensitive_or_governance"})
            return (f"ASK_USER sensitive_write|"
                    f"⛔ Bash 写入被门禁拦截：{raw} 命中敏感/治理路径（凭据/密钥/治理文件）。\n"
                    f"确需修改请改用 Edit 工具走敏感编辑流程，或人工授权。")
    return None


# ── governance_bypass 软门禁（ADR 0015 二期）：Bash 写敏感治理文件 → REDIRECT ──
# 路径找补：echo/cat >> CLAUDE.md 等绕过 Write 门禁直写治理文件 → 软门禁
# REDIRECT 回正确路径，不 BLOCK（对齐 agentic-ui 软锁哲学：REDIRECT/ASK_USER）。

# 治理文件判定在 _is_governance 基础上补充顶层 CLAUDE.md 与 .claude/harness.yaml
# （_is_governance 的 patterns 未覆盖这两处）。
_GOV_BYPASS_EXTRA = ("CLAUDE.md", ".claude/harness.yaml")


def _check_governance_bypass(payload: dict) -> str | None:
    tool = _extract_tool(payload).lower()
    if tool != "bash":
        return None
    command = _extract_command(payload)
    if not command:
        return None
    for m in re.finditer(r"[>]{1,2}\s+([^\s;>|&]+)", command):
        target = m.group(1).strip("'\"")
        if not target:
            continue
        if not (_is_governance(target) or target in _GOV_BYPASS_EXTRA):
            continue
        _append_audit({
            "event_type": "governance_bypass_redirect",
            "actor": "hook:pretool-gate",
            "decision": "REDIRECT",
            "reason": f"governance_bypass: bash write to {target}",
            "tool": tool,
            "command": command[:120],
        })
        return (
            f"REDIRECT governance_bypass tool={tool} target={target}|"
            f"⚠️ Bash 重定向写治理文件 {target}，绕过 Write 门禁。"
            f"治理文件变更须走受控决策流程（铁律/审批）；请勿用 echo/cat >> 直写。"
            f"若确需变更，通过正确路径申请后再写。"
        )
    return None


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


# ──────────────────────────────────────────────
# omc-skeleton-readonly gate（worktree 隔离用）
# .omc/**/*.md 骨架文件在 worktree 内只读——多智能体并发时, worktree 隔离
# 任务不得改写 .omc/ 骨架索引(会与主树/其他 worktree merge 冲突)。
# 必须进 _GATE_CORE(守护级, 不因 L1/L2 跳过)。
# ──────────────────────────────────────────────
_SKELETON_MD_RE = re.compile(r"(^|[/\\])\.omc[/\\].*\.md$", re.IGNORECASE)


def _check_omc_skeleton_readonly(payload: dict) -> str | None:
    """拦截对 .omc/**/*.md 骨架的 Write/Edit/MultiEdit。

    gate 契约: 返回 None=放行, 返回 "BLOCK <reason>"=阻断。
    只拦 .md 骨架(状态写入走 carros_base.py 接口), 放行 .json 等其他文件。
    """
    tool = _extract_tool(payload).lower()
    if tool not in ("write", "edit", "multiedit"):
        return None
    ti = _extract_input(payload) or {}
    path = str(ti.get("file_path", "") or "").replace("\\", "/")
    if _SKELETON_MD_RE.search(path):
        _append_audit({
            "event_type": "omc_skeleton_write_blocked",
            "actor": "hook:pretool-gate",
            "gate": "omc-skeleton-readonly",
            "decision": "BLOCK",
            "reason": f"skeleton_md_write:{path[:120]}",
            "tool": tool,
        })
        return (f"BLOCK omc-skeleton-readonly|"
                f"直接修改骨架文件 {path!r} 被禁止(worktree 隔离下 .omc/**/*.md 只读)。"
                f"如需更新任务状态, 使用 carros_base.py 的状态写入接口。")
    return None
