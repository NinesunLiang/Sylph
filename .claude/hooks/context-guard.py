#!/usr/bin/env python3
"""context-guard.py — PreToolUse:Edit|Write — 基于真实 token 百分比阻断写操作，防止上下文溢出
Role: 基于真实 token 百分比阻断写操作，防止上下文溢出

等效移植自 context-guard.sh:
- 读取 token_writer 状态文件，检查使用率
- 三个阈值: warn(50%), danger(80%), critical(90%)
- 只封锁 Edit/Write，保留 Read/Grep/Bash 诊断通道
- 有 context-force-override 逃生门
- Ghost/Goal 模式不阻断写操作，仅记录 flywheel
- 原则: "读是诊断, 写是破坏"

集成关系 (pre-exec + completion-gate):
- hermes-pre-exec → 前置执行门禁，context-guard 与 pre-exec 共同构成写操作的双重防护
- completion-gate → 任务完成门禁，context-guard 阻断防止溢出导致 completion-gate 误判
- context-guard 的阻断决策可被 pre-exec 逻辑覆盖（force-override 逃生门）
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── 导入共享库 ───

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, hc_get, hc_emit_hook_json, flywheel_event, is_mode_active

# ─── 路径解析 ───

_PROJECT_ROOT = (_HOOKS_DIR / "../..").resolve()
_STATE_DIR = _PROJECT_ROOT / ".omc" / "state"
_OVERRIDE_FILE = _STATE_DIR / "context-force-override"

# ─── 阈值 (可配置) ───

WARN_PCT = int(hc_get("context_guard.warn_threshold", "50"))
DANGER_PCT = int(hc_get("context_guard.danger_threshold", "80"))
CRITICAL_PCT = int(hc_get("context_guard.critical_threshold", "90"))


# ─── agentic_status block 等效 ───

def _agentic_status_block(title: str, message: str, detail: str = ""):
    """输出阻断 UI 到 stderr（等效 sh 的 agentic_status block）。"""
    sep = "═" * 55
    lines = [
        "",
        f"⛔ [{title}]",
        sep,
        message,
        f"     {detail}" if detail else "",
        "",
    ]
    print("\n".join(lines), file=sys.stderr, flush=True)


# ─── 上下文监控读取 ───

def _read_context_monitor() -> dict:
    """尝试执行 context_monitor.py（如果存在且可执行），返回其 JSON 输出。

    等效 sh 中:
        RESULT=$(CONTEXT_*_THRESHOLD=... context_monitor.py 2>/dev/null)

    Returns:
        dict with keys: percentage, source, is_danger, is_critical, sweet_spot_warning
        如果无法执行则返回空 dict。
    """
    scripts_dir = (_HOOKS_DIR / ".." / "scripts").resolve()
    monitor_script = scripts_dir / "context_monitor.py"

    if not monitor_script.exists() or not os.access(str(monitor_script), os.X_OK):
        return {}

    import subprocess

    env = os.environ.copy()
    env["CONTEXT_WARN_THRESHOLD"] = str(WARN_PCT)
    env["CONTEXT_DANGER_THRESHOLD"] = str(DANGER_PCT)
    env["CONTEXT_CRITICAL_THRESHOLD"] = str(CRITICAL_PCT)

    try:
        result = subprocess.run(
            [sys.executable, str(monitor_script)],
            capture_output=True, text=True, timeout=10, env=env,
        )
        output = result.stdout.strip()
        if not output:
            return {}
        return json.loads(output)
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
        return {}
    except Exception:
        return {}


# ─── 主逻辑 ───

def main():
    # ── 门禁检查 ──
    if not hc_enabled("context_guard"):
        print('{"continue": true}')
        sys.exit(0)

    # ── 读取 stdin ──
    stdin_data = sys.stdin.read()
    try:
        payload = json.loads(stdin_data)
    except json.JSONDecodeError:
        print('{"continue": true}')
        sys.exit(0)

    # ── 逃生舱盖: 标记文件存在时跳过阻断 ──
    if _OVERRIDE_FILE.exists():
        _OVERRIDE_FILE.unlink(missing_ok=True)
        print('{"continue": true}')
        sys.exit(0)

    # ── 统一模式检测 ──
    mode = is_mode_active(str(_STATE_DIR))
    mode_label = f"[{mode} mode]" if mode != "normal" else ""

    # ── 提取 tool_name ──
    tool_name = (payload.get("tool_name") or payload.get("tool") or "")

    block_writes = tool_name in ("Edit", "Write")

    # ── 运行上下文监控 ──
    monitor_data = _read_context_monitor()
    if not monitor_data:
        # No monitor available, just pass through
        print('{"continue": true}')
        sys.exit(0)

    source = monitor_data.get("source", "")
    pct = monitor_data.get("percentage", 0)
    is_danger = monitor_data.get("is_danger", False)
    is_critical = monitor_data.get("is_critical", False)
    sweet_spot_warning = monitor_data.get("sweet_spot_warning", "")

    # ── CRITICAL threshold (90%): hard-block in normal mode, log+pass in autonomous ──
    if is_critical and source == "transcript (real)":
        if mode != "normal":
            # 自主模式: 仅记录，不阻断
            _log_skipped(mode, pct, "critical context but autonomous mode")
            msg = f"⚠️ [{mode} mode] 上下文占比 {pct}%。超出紧急阈值但自主模式不阻断。请考虑 /compact。"
            print(hc_emit_hook_json(msg, event="PreToolUse", continue_val=True))
            sys.exit(0)

        flywheel_event("context_guard", "critical", "P0")
        _agentic_status_block(
            "Context Guard 紧急阻断 — 90% 临界",
            f"会话上下文占比已达 {pct}%（紧急阈值: {CRITICAL_PCT}%）。"
            f"AI 记忆已不可靠，继续操作将导致数据损毁。务必立即运行 /compact 压缩会话。"
            f"所有写操作已被物理阻断。{mode_label}",
        )
        sys.exit(2)

    # ── DANGER threshold (80%): block writes in normal mode ──
    if is_danger and source == "transcript (real)":
        flywheel_event("context_guard", "triggered", "P2")

        if block_writes:
            if mode != "normal":
                # 自主模式: 不阻断
                _log_skipped(mode, pct, "context exceeds danger but autonomous mode")
                msg = f"⚠️ [{mode} mode] 上下文占比 {pct}%。超出危险阈值但自主模式不阻断。请考虑 /compact。"
                print(hc_emit_hook_json(msg, event="PreToolUse", continue_val=True))
                sys.exit(0)

            _agentic_status_block(
                "Context Guard 硬阻断",
                f"当前会话上下文占比已达 {pct}%（危险阈值: {DANGER_PCT}%，警告阈值: {WARN_PCT}%）！",
                "为防止灾难性幻觉、指令遗忘或代码损毁，已强制拦截写入操作。"
                "诊断工具 (Read/Grep/Bash) 可正常使用。请运行 '/compact' 压缩会话或手动重置 token 追踪。"
                f"{mode_label}",
            )
            sys.exit(2)
        else:
            # 非写工具: 告警到 stderr + 不阻断
            print(f"⚠️ [Context Guard] 上下文占比 {pct}%{mode_label} — heuristic 源不触发硬阻断，已告警记录",
                  file=sys.stderr, flush=True)
            msg = f"⚠️ 上下文占比 {pct}%。超出危险阈值。请考虑 /compact。诊断操作未阻断。"
            print(hc_emit_hook_json(msg, event="PreToolUse", continue_val=True))
            sys.exit(0)

    # ── Heuristic danger warning: transcript unavailable but context estimated high ──
    if is_danger and source != "transcript (real)":
        print(f"⚠️ [Context Guard] 上下文占比 {pct}% ({source}) — heuristic 源告警不阻断",
              file=sys.stderr, flush=True)
        ml = f" [{mode} mode]" if mode != "normal" else ""
        msg = f"⚠️ 上下文估算占比 {pct}%。来源: {source}。无法读取 transcript，阻断已跳过。请检查 transcript 目录或手动 /compact。{ml}"
        print(hc_emit_hook_json(msg, event="PreToolUse", continue_val=True))
        sys.exit(0)

    # ── Sweet-spot / Hand-off Alert: inject into AI context via additionalContext ──
    if sweet_spot_warning:
        sweet_json = json.dumps(json.dumps(sweet_spot_warning))
        result = json.dumps({
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": sweet_spot_warning,
            }
        })
        print(result)
        sys.exit(0)

    # ── 放行 ──
    print('{"continue": true}')
    sys.exit(0)


# ─── 辅助函数 ───

def _log_skipped(mode: str, pct, reason: str):
    """将自主模式跳过的阻断记录到 skipped-errors.md。"""
    log_path = _STATE_DIR / "skipped-errors.md"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{timestamp} | {mode} | context_guard | {pct}% | {reason}\n"
    try:
        _STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(str(log_path), "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


if __name__ == "__main__":
    main()
