#!/usr/bin/env python3
"""
posttool-gate.py — CarrorOS Unified PostToolUse Gate

Multiplexes (Base lightweight philosophy, replaces 4 deleted posttool hooks):
  1. Output compression — tool output >50KB → artifact 落盘 + 预览提示（context_boom 防线）
  2. Error DNA — 工具真实失败自动记录（生产路径接入，此前只有测试调用）
  3. Audit — 落盘 .omc/audit/

Constraints:
  - Never blocks: always exit 0
  - Fast: small successful outputs return immediately
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
ROOT = HOOK_DIR.parents[1]
os.chdir(str(ROOT))

OMC = ROOT / ".omc"
ARTIFACTS = OMC / "artifacts"
AUDIT = OMC / "audit"
TOKENS_DIR = OMC / "tokens"
SCRIPTS = ROOT / ".claude" / "scripts"
sys.path.insert(0, str(SCRIPTS))

# Round7 PKG-2: token 读取委托 SSOT + error_dna 死导入修复
# 直插 lib 目录按顶层模块导入——hooks/lib 正规包(含 __init__.py)会遮蔽
# lib.* 包路径,使旧 `from lib.error_dna import` 解析到 hooks/lib(无此模块)
# → ImportError 被 :158 except 吞掉 → error DNA 自接入之日起静默死
# (文件头 docstring 宣称"生产路径接入"=虚假接线,2026-07-20 实证)
sys.path.insert(0, str(SCRIPTS / "lib"))
try:
    from task_ssot import latest_active_token as _ssot_latest_active_token
except Exception:  # SSOT 不可用 → error DNA 跳过归属(永不阻断工具响应)
    _ssot_latest_active_token = None
try:
    from error_dna import record_error as _record_error
except Exception:  # error_dna 不可用 → 降级跳过(永不阻断)
    _record_error = None

SIZE_THRESHOLD = 50 * 1024  # 50KB
PREVIEW_LEN = 1300


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _append_audit(event: dict) -> None:
    try:
        AUDIT.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        event.setdefault("timestamp", _now_iso())
        with (AUDIT / f"{day}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        pass


def _active_task() -> tuple[Path | None, str]:
    """Returns (task_dir, current_step) of latest ACTIVE carros token — 委托 task_ssot。

    根因(2026-07-20 幻影 token 事件):旧实现按 mtime 取前 5 无终态过滤,
    archived token 经水位回写刷新 mtime → error DNA 记录到已终态的旧任务目录。
    """
    if _ssot_latest_active_token is None:
        return None, "unknown"
    path = _ssot_latest_active_token(TOKENS_DIR)
    if path is None:
        return None, "unknown"
    data = _read_json(path, {})
    task = data.get("task")
    if not isinstance(task, dict):
        return None, "unknown"
    task_dir = data.get("task_dir")
    step = str(task.get("current_step") or "unknown")
    if task_dir and (ROOT / task_dir).exists():
        return ROOT / task_dir, step
    return None, "unknown"


def _serialize_response(resp) -> str:
    if isinstance(resp, str):
        return resp
    try:
        return json.dumps(resp, ensure_ascii=False)
    except Exception:
        return str(resp)


def _is_failure(tool: str, resp) -> bool:
    if isinstance(resp, dict):
        if resp.get("interrupted"):
            return True
        code = resp.get("exit_code") or resp.get("exitCode") or resp.get("returncode")
        if isinstance(code, int) and code != 0:
            return True
        stderr = str(resp.get("stderr") or "")
        if resp.get("error") or resp.get("is_error"):
            return True
        if tool == "bash" and stderr and ("error" in stderr.lower() or "traceback" in stderr.lower()):
            return True
    return False


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}

    tool = str(payload.get("tool_name") or payload.get("tool") or "unknown")
    resp = payload.get("tool_response") or payload.get("tool_result") or payload.get("response") or {}
    text = _serialize_response(resp)

    # ─── 1. Output compression: large output → artifact ───
    if len(text) > SIZE_THRESHOLD:
        try:
            day = datetime.now(timezone.utc).strftime("%Y%m%d")
            out_dir = ARTIFACTS / day
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%H%M%S")
            artifact = out_dir / f"{tool}-{ts}.log"
            artifact.write_text(text, encoding="utf-8")
            preview = text[:PREVIEW_LEN]
            _append_audit({
                "event_type": "output_compressed",
                "actor": "hook:posttool-gate",
                "tool": tool,
                "size": len(text),
                "artifact": str(artifact.relative_to(ROOT)),
            })
            print(
                f"📦 [posttool-gate] 大输出已落盘（{len(text)//1024}KB）: "
                f"{artifact.relative_to(ROOT)}\n--- preview ---\n{preview}\n--- "
                f"完整内容请 Read 该文件，勿重复执行命令 ---",
                file=sys.stderr, flush=True,
            )
        except Exception:
            pass

    # ─── 2. Error DNA: real tool failure → record ───
    if _is_failure(tool, resp) and _record_error is not None:
        try:
            task_dir, step = _active_task()
            if task_dir:
                _record_error(
                    task_dir=task_dir,
                    step_id=step,
                    error_text=f"[{tool}] {text[:400]}",
                    artifact_path=None,
                    retry_count=0,
                )
                _append_audit({
                    "event_type": "error_dna_recorded",
                    "actor": "hook:posttool-gate",
                    "tool": tool,
                    "step": step,
                })
        except Exception:
            pass

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
