#!/usr/bin/env python3
"""
tool_store.py — CarrorOS 工具结果落盘 + 稳定预览

工具长输出 → artifacts/tool_<seq>.log（无损）
模型只见 ≤ 2K chars 的稳定预览（字节级固定）
"""

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

TOOL_PREVIEW_CHARS = 2000


def task_artifacts_dir(task_id: str, omc_root: Optional[Path] = None) -> Path:
    """Locate/create .omc/tasks/<date>/<task_id>/artifacts/"""
    if omc_root is None:
        omc_root = Path.cwd() / ".omc"
    # task_id might be date/task format
    if "/" in task_id:
        parts = task_id.split("/", 1)
        return omc_root / "tasks" / parts[0] / parts[1] / "artifacts"
    # Use today
    today = datetime.now().strftime("%Y%m%d")
    return omc_root / "tasks" / today / task_id / "artifacts"


def next_artifact_name(artifacts_dir: Path) -> str:
    """tool_<seq>.log 单调序号"""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    existing = list(artifacts_dir.glob("tool_*.log"))
    seq = len(existing) + 1
    return "tool_{:04d}.log".format(seq)


def _utf8_slice(text: bytes, max_bytes: int) -> str:
    """Safely slice UTF-8 bytes to avoid splitting multi-byte chars."""
    return text[:max_bytes].decode("utf-8", errors="replace")


def _tail_lines(text: str, n: int = 5, max_chars: int = 600) -> str:
    """Last N lines focusing on error/exit info."""
    lines = text.splitlines()
    tail = lines[-n:]
    result = "\n".join(tail)
    if len(result) > max_chars:
        result = result[:max_chars] + "..."
    return result


def build_preview(content: bytes, exit_code: int) -> dict:
    """
    内容寻址 preview — 同一 content → 相同 body 前缀。
    路径不进入 cache-sensitive 前缀。
    """
    digest = hashlib.sha256(content).hexdigest()

    head = _utf8_slice(content, 1200)
    tail = ""
    if len(content) > 1800:
        tail_text = content.decode("utf-8", errors="replace")
        tail = _tail_lines(tail_text, n=5)

    preview = "[tool_result stored]\n"
    preview += "digest: {}\n".format(digest[:12])
    preview += "exit_code: {}\n".format(exit_code)
    preview += "bytes: {}\n".format(len(content))
    preview += "preview:\n"
    preview += head
    if tail:
        preview += "\n...tail:\n" + tail
    if len(content) > TOOL_PREVIEW_CHARS:
        preview += "\n...[TRUNCATED]"

    if len(preview) > TOOL_PREVIEW_CHARS + 200:
        preview = preview[:TOOL_PREVIEW_CHARS] + "\n...[TRUNCATED]"

    return {
        "artifact_path": ".omc/artifacts/sha256/{}/{}".format(digest[:2], digest),
        "exit_code": exit_code,
        "bytes": len(content),
        "preview": preview,
    }


def store_tool_result(
    task_id: str,
    content: bytes,
    meta: Optional[dict] = None,
) -> dict:
    """
    全文写入 artifact（无损可回滚）；返回 preview。
    meta 建议: {"exit_code": int, "command": str}
    """
    if meta is None:
        meta = {"exit_code": 0}
    exit_code = meta.get("exit_code", 0)

    artifacts_dir = task_artifacts_dir(task_id)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    name = next_artifact_name(artifacts_dir)
    artifact_path = artifacts_dir / name
    artifact_path.write_bytes(content)

    return build_preview(content, exit_code)
