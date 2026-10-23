"""governance_ticket.py — 人类审批票校验（P0 治理加固）。

设计约束（用户 2026-10-18 裁决）：
  治理文件不是「永不可改」，而是「AI 不能擅自改」。
  人类在终端签发一次性审批票 → AI 只能消费，不能创建。

票的绑定：
  - 文件路径（仓库相对路径，posix）
  - 内容哈希（首次使用时校验一次，防止「批的是 A、改的是 B」）
  - TTL（最长 24 小时，防止永久授权）
  - 首次通过后条目标记 used=True；同一票内后续写入仅受 TTL 约束
    （支持一个文件多次 Edit，不必每次重签）
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .constants import ROOT, STATE_DIR

MAX_TTL_HOURS = 24
_ENV_TICKET = "CARROROS_GOV_TICKET"


def ticket_path() -> Path:
    override = os.environ.get(_ENV_TICKET, "").strip()
    if override:
        return Path(override)
    return STATE_DIR / "governance-approval.json"


def rel_path(path: str) -> str:
    """把任意路径规范成仓库相对 posix 路径；仓库外路径保留绝对形式。"""
    p = Path(str(path).strip().strip("'\""))
    if not p.is_absolute():
        p = ROOT / p
    try:
        resolved = p.resolve()
    except OSError:
        resolved = p
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def sha256_file(path: str | Path) -> str:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return ""


def _parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _load() -> dict | None:
    try:
        return json.loads(ticket_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _save(data: dict) -> None:
    target = ticket_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".gov-ticket-", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def check(path: str) -> tuple[bool, str]:
    """返回 (是否放行, 原因)。放行时会把该条目标记为已使用。"""
    data = _load()
    if not isinstance(data, dict):
        return (False, "no_ticket")
    if not str(data.get("approved_by") or "").strip():
        return (False, "missing_approver")

    created = _parse_ts(data.get("created_at", ""))
    expires = _parse_ts(data.get("expires_at", ""))
    if created is None or expires is None:
        return (False, "invalid_time")
    now = datetime.now(timezone.utc)
    if expires <= now:
        return (False, "expired")
    if expires <= created:
        return (False, "invalid_time")
    if (expires - created).total_seconds() > MAX_TTL_HOURS * 3600:
        return (False, "ttl_too_long")

    files = data.get("files")
    if not isinstance(files, dict):
        return (False, "invalid_files")

    key = rel_path(path)
    entry = files.get(key)
    if entry is None:
        return (False, "file_not_listed")

    if isinstance(entry, str):
        entry = {"sha256": entry, "used": False}
        files[key] = entry

    if not entry.get("used"):
        expected = str(entry.get("sha256") or "")
        if not expected:
            return (False, "missing_hash")
        actual = sha256_file(key)
        if not actual or actual != expected:
            return (False, "content_changed")
        entry["used"] = True
        try:
            _save(data)
        except OSError:
            # 票没能落盘不构成放行理由：宁可拒绝
            return (False, "ticket_write_failed")

    return (True, "approved")
