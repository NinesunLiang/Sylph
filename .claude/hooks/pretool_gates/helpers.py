"""
helpers.py — Helper functions extracted from pretool-gate.py.
"""
from __future__ import annotations
import json
import os
import re
import secrets
import shlex
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constants import (
    ROOT, OMC, STATE_DIR, TOKENS, AUDIT,
    CRITICAL_STATE, FALLBACK_REQUIRED, FALLBACK_APPROVED,
    TEMP_BYPASS, REDIRECT_STREAK, TRUST_BREACH,
    SENSITIVE_PATTERNS, STALE_LOCK_THRESHOLD,
    READ_TOOLS, WRITE_TOOLS, PLAN_FILE_PATTERNS,
    STATE_TOKEN,
)

# ── GateKeeper 分层裁决链 ──
sys.path.insert(0, str(ROOT / ".claude" / "scripts"))
from gatekeeper import GateKeeper, GateContext, make_context  # noqa: E402

# ── Round7 PKG-1: SSOT ──
sys.path.insert(0, str(ROOT / ".claude" / "scripts" / "lib"))
try:
    from task_ssot import latest_terminal_token as _ssot_latest_terminal_token
    _SSOT_ERR: Exception | None = None
except Exception as exc:
    _ssot_latest_terminal_token = None
    _SSOT_ERR = exc

# Export for checks.py
_ssot_err = _SSOT_ERR


# ═══════════════════════════════════
# Goal mode
# ═══════════════════════════════════

def _goal_mode() -> bool:
    token = _active_token()
    if not token or token.get("mode") != "goal" or token.get("status") != "active":
        return False
    expires = token.get("goal", {}).get("expires_at")
    if expires:
        try:
            if datetime.now(timezone.utc) >= datetime.fromisoformat(expires):
                return False
        except ValueError:
            return False
    return True


# ═══════════════════════════════════
# Governance
# ═══════════════════════════════════

def _is_governance(path: str) -> bool:
    p = path.replace("\\", "/")
    gov_patterns = [
        r"(^|/)\.claude/hooks/",
        r"(^|/)\.claude/scripts/",
        r"(^|/)\.claude/settings\.json",
        r"(^|/)scripts/carroros-gates/",
        r"(^|/)\.claude/kernel\.md$",
        r"(^|/)AGENTS\.md$",
    ]
    return any(re.search(pat, p, re.IGNORECASE) for pat in gov_patterns)


def _is_sensitive(path: str) -> bool:
    p = path.replace("\\", "/")
    return bool(re.search("|".join(SENSITIVE_PATTERNS), p, re.IGNORECASE))


# ═══════════════════════════════════
# Extraction helpers
# ═══════════════════════════════════

def _read_stdin() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _check_temp_bypass() -> bool:
    if not TEMP_BYPASS.exists():
        return False
    try:
        data = json.loads(TEMP_BYPASS.read_text(encoding="utf-8"))
        expires = data.get("expires_at", "")
        if not expires:
            # No expires_at — fail closed, delete and return False
            TEMP_BYPASS.unlink(missing_ok=True)
            return False
        try:
            from datetime import datetime, timezone
            exp = datetime.fromisoformat(expires)
            now = datetime.now(timezone.utc)
            if now >= exp:
                TEMP_BYPASS.unlink(missing_ok=True)
                return False
            # Enforce max 24h validity
            max_valid = now.timestamp() + 86400
            if exp.timestamp() > max_valid:
                TEMP_BYPASS.unlink(missing_ok=True)
                return False
        except Exception:
            TEMP_BYPASS.unlink(missing_ok=True)
            return False
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


# ═══════════════════════════════════
# Output helpers
# ═══════════════════════════════════

def _ok(msg: str = "OK") -> int:
    print(json.dumps({"continue": True, "message": f"PreToolGate: {msg}"}, ensure_ascii=False))
    return 0


_REASON_TO_HAZARD = {
    "destructive": ("destructive", "irreversible"),
    "irreversible": ("irreversible",),
    "privilege": ("privilege_escalation",),
    "architecture": ("architecture_change",),
    "production": ("production",),
    "production_op": ("production",),
    "env_bypass": ("privilege_escalation",),
    "trust_broken": ("privilege_escalation", "irreversible"),
    "governance": ("governance_violation",),
}


def _block(reason: str, suggestion: str = "") -> int:
    safe_reason = reason[:300]
    unattended = _goal_mode()
    is_high_risk = any(k in safe_reason.lower() for k in _REASON_TO_HAZARD)

    ask_user = safe_reason.startswith("ASK_USER ")
    display_reason = safe_reason.removeprefix("ASK_USER ") if ask_user else safe_reason
    hs: dict[str, Any] = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": display_reason,
    }

    if ask_user:
        hs["additionalContext"] = (
            f"ASK_USER: {display_reason}\n\n"
            f"{suggestion or '请确认是否继续，或调整当前计划。'}"
        )
        print(json.dumps({"continue": True, "hookSpecificOutput": hs}, ensure_ascii=False))
        sys.stderr.write(f"PreToolGate: ASK_USER - {display_reason}\n")
        return 0

    if is_high_risk:
        hazard_flags = []
        for key, flags in _REASON_TO_HAZARD.items():
            if key in safe_reason.lower():
                hazard_flags.extend(flags)
        ctx = make_context(
            action=safe_reason, target="",
            destructive="destructive" in hazard_flags,
            irreversible="irreversible" in hazard_flags,
            privilege_escalation="privilege_escalation" in hazard_flags,
            architecture_change="architecture_change" in hazard_flags,
            production="production" in hazard_flags,
            risk="high", unattended=unattended,
        )
        result = GateKeeper.evaluate(ctx)
        full_msg = GateKeeper.format_output(result)
        if result.decision.value == "skip":
            hs["additionalContext"] = (
                f"blocked-human: {safe_reason}\n\n"
                f"原因: 高风险操作在goal模式下被跳过。\n"
                f"建议: continue other work, skip this risk.\n"
                f"详情已记录至 skipped-risks.jsonl, 退出报告将汇总。"
            )
            print(json.dumps({
                "continue": True,
                "hookSpecificOutput": hs,
            }, ensure_ascii=False))
            sys.stderr.write(f"PreToolGate: SKIPPED (goal) - {safe_reason}\n")
            return 0
        # Interactive high-risk: use GateKeeper output + AskUserQuestion instruction
        hs["additionalContext"] = (
            f"{full_msg}\n\n"
            f"---\n"
            f"请使用 AskUserQuestion 与用户交互，提供选项供用户选择。"
        )
        print(json.dumps({
            "continue": True,
            "hookSpecificOutput": hs,
        }, ensure_ascii=False))
        sys.stderr.write(f"PreToolGate: BLOCKED (ask_user) - {safe_reason}\n")
        return 0

    # Non-high-risk: recoverable denial
    hs["additionalContext"] = (
        f"🔄 {safe_reason}\n\n可选方案:\n  {suggestion}"
        if suggestion else f"🔄 {safe_reason}"
    )
    print(json.dumps({
        "continue": True,
        "hookSpecificOutput": hs,
    }, ensure_ascii=False))
    sys.stderr.write(f"PreToolGate: DENIED - {safe_reason}\n")
    return 0


def _redirect(reason: str, guidance: str = "") -> int:
    ctx = make_context(
        action=reason, target="",
        risk="medium", unattended=_goal_mode(),
        fixable_issue=True,
    )
    result = GateKeeper.evaluate(ctx, gate_type="pretool")
    full_output = GateKeeper.format_output(result)
    print(json.dumps({
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
            "additionalContext": f"REDIRECT: {reason}\n\n{guidance}\n\n{full_output}",
        }
    }, ensure_ascii=False))
    sys.stderr.write(f"PreToolGate: REDIRECT - {reason}\n")
    if guidance:
        sys.stderr.write(f"  {guidance}\n")
    return 0


def _hard_stop(reason: str) -> int:
    """Hard stop: exit the tool with continue:false + stopReason, return 0."""
    print(json.dumps({
        "continue": False,
        "stopReason": f"HARD_BLOCK: {reason[:300]}",
    }, ensure_ascii=False))
    sys.stderr.write(f"PreToolGate: HARD_STOP - {reason}\n")
    return 0


def _increment_streak(key: str, path: Path | None = None) -> int:
    """Atomic increment for redirect streak with 6h TTL.

    Reads existing streak data, cleans expired entries (6h TTL),
    increments count for *key*, writes back, returns new count.
    """
    _TTL = 21600  # 6 hours
    now_s = int(time.time())
    store: dict[str, dict] = {}
    p = path or REDIRECT_STREAK
    try:
        if p.is_file():
            raw = json.loads(p.read_text(encoding="utf-8"))
            for k, v in raw.items():
                if isinstance(v, dict) and "c" in v and "t" in v:
                    if now_s - v["t"] < _TTL:
                        store[k] = v
    except Exception:
        store = {}
    prev = store.get(key, {}).get("c", 0)
    store[key] = {"c": prev + 1, "t": now_s}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(store), encoding="utf-8")
    except Exception:
        pass
    return prev + 1


# ═══════════════════════════════════
# Trust breach
# ═══════════════════════════════════

def _check_trust_breach() -> str | None:
    if not TRUST_BREACH.exists():
        return None
    try:
        data = json.loads(TRUST_BREACH.read_text(encoding="utf-8", errors="replace"))
        return data.get("reason", "unknown")
    except Exception:
        return "unknown"


def _record_trust_breach(reason: str) -> None:
    try:
        TRUST_BREACH.parent.mkdir(parents=True, exist_ok=True)
        TRUST_BREACH.write_text(json.dumps({
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _is_trust_breach_reason(detail: str) -> bool:
    # Only env_bypass / bypass_attempt / trust_broken trigger permanent trust breach.
    # Normal governance_path deny does NOT write permanent trust breach.
    return any(kw in detail.lower() for kw in ["env_bypass", "bypass_attempt", "trust_broken"])


def _clear_trust_breach() -> bool:
    try:
        if TRUST_BREACH.exists():
            TRUST_BREACH.unlink()
            return True
    except OSError:
        pass
    return False


def _match_any(text: str, patterns: list[str]) -> str | None:
    for p in patterns:
        if re.search(p, text):
            return p
    return None


def _append_audit(event: dict) -> None:
    try:
        AUDIT.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        event.setdefault("timestamp", datetime.now(timezone.utc).replace(microsecond=0).isoformat())
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


# ═══════════════════════════════════
# Token helpers
# ═══════════════════════════════════

def _latest_token() -> Path | None:
    raw_token = os.environ.get("CARROROS_TOKEN_PATH", "").strip()
    if raw_token:
        path = Path(raw_token).expanduser().resolve()
        return path if path.is_file() else None
    raw_task = os.environ.get("CARROROS_TASK_DIR", "").strip()
    if not raw_task:
        return None
    task_dir = Path(raw_task).expanduser().resolve()
    path = TOKENS / task_dir.parent.name / f"{task_dir.name}.json"
    return path if path.is_file() else None


def _active_token() -> dict[str, Any] | None:
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
        task = {}
    explicit = (
        task.get("dir")
        or token.get("task_dir")
        or token.get("plan_dir")
    )
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
    return s[2:] if s.startswith("./") else s


def _in_scope(path: str, scope: list[str]) -> bool:
    try:
        p_real = os.path.realpath(path)
    except Exception:
        p_real = path.replace("\\\\", "/")
    p = _strip_dot_slash(p_real)
    for item in scope:
        s_orig = item.replace("\\\\", "/")
        try:
            s_abs = os.path.realpath(s_orig)
        except Exception:
            s_abs = s_orig
        s = _strip_dot_slash(s_abs)
        if "*" in s or "?" in s:
            import fnmatch
            if fnmatch.fnmatch(p, s) or fnmatch.fnmatch(os.path.basename(p), s):
                return True
            parts = p.split("/")
            for i in range(len(parts)):
                if fnmatch.fnmatch("/".join(parts[i:]), s):
                    return True
            continue
        s_dir = s.rstrip("/")
        if p == s_dir or p == "/" + s_dir:
            return True
        prefix = s_dir + "/"
        if p.startswith(prefix) or p.startswith("/" + prefix):
            return True
        if p.endswith("/" + s_dir):
            return True
    return False


def _check_verified(step_id: str | None, task_id: str | None = None,
                    task_dir: Path | None = None) -> bool:
    if not step_id or not task_id:
        return False
    dirs = [AUDIT, OMC / "state" / "audit"]
    if task_dir:
        dirs.append(task_dir / "state" / "audit")
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
                    if e.get("event") == "verify":
                        data = e.get("data", {})
                        if (isinstance(data, dict)
                                and data.get("result") == "VERIFIED"
                                and data.get("step") == step_id
                                and data.get("task_id") == task_id):
                            return True
                    if (e.get("event_type") == "verify_decision"
                            and e.get("decision") == "VERIFIED"
                            and e.get("step") == step_id
                            and e.get("task_id") == task_id):
                        return True
    return False


def _auto_init(target_path: str | None = None) -> None:
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


def _safe_unlink(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _auto_archive_token(token_path: Path, token_data: dict, reason: str) -> None:
    try:
        archive_dir = OMC / "archive" / "tokens" / token_path.parent.name
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / token_path.name
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


def _failure_escalate(signature: str, *, window: int = 20, threshold: int = 3) -> bool:
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


def _clean_stale_state_token() -> None:
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
    if age >= STALE_LOCK_THRESHOLD:
        try:
            STATE_TOKEN.unlink()
        except OSError:
            pass


# ═══════════════════════════════════
# Gate mode & misc
# ═══════════════════════════════════

def _get_gate_mode() -> str:
    env_mode = os.environ.get("CARROROS_GATE_MODE", "").lower()
    if env_mode in ("l1", "l2"):
        return env_mode
    harness_mode = ""
    try:
        _HARNESS_PATH = ROOT / "scripts" / "carroros-gates" / "harness.yaml"
        if _HARNESS_PATH.exists():
            import yaml
            with open(_HARNESS_PATH, "r") as _fh:
                _hdata = yaml.safe_load(_fh) or {}
            harness_mode = (_hdata.get("project", {}) or {}).get("gate_mode", "").lower()
    except Exception:
        pass
    if not sys.stdin.isatty() or os.environ.get("CI") == "true" or os.environ.get("CARROROS_CI_MODE") == "1":
        return harness_mode if harness_mode else "l2"
    return harness_mode if harness_mode else "l1"


def _is_ci_environment() -> bool:
    return (
        not sys.stdin.isatty() or
        os.environ.get("CI") == "true" or
        os.environ.get("CARROROS_CI_MODE") == "1"
    )


def _validate_bypass_token(token: str) -> bool:
    if not token or len(token) < 8:
        return False
    try:
        _SECRET_FILE = Path(__file__).resolve().parent.parent / ".bypass_secret"
        if not _SECRET_FILE.exists():
            return False
        secret = _SECRET_FILE.read_text(encoding="utf-8").strip()
        if not secret:
            return False
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


def _record_gate_decision(gate_name: str, result: str | None, mode: str) -> None:
    now = datetime.now(timezone.utc)
    _append_audit({
        "event_type": "gate_decision",
        "gate": gate_name,
        "mode": mode,
        "decision": result[:50] if result else "PASS",
        "timestamp": now.isoformat(),
    })


def _verify_contract_compliance(mode: str, executed_gates: set[str]) -> str | None:
    try:
        _CONTRACT_PATH = ROOT / "scripts" / "carroros-gates" / "gate-contract.yaml"
        if not _CONTRACT_PATH.exists():
            return None
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
