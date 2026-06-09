#!/usr/bin/env python3
"""
posttool-subagent-audit.py — PostToolUse:Task — 子 agent 执行后审计 content 用量，超限告警
"""

import json
import os
import sys
import time
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, hc_get, flywheel_event, hc_emit_hook_json


def main():
    if not hc_enabled("posttool_subagent_audit"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    try:
        input_data = sys.stdin.read()
    except Exception:
        input_data = ""

    tool_name = ""
    agent_type = ""
    content_len = 0

    if input_data.strip():
        try:
            parsed = json.loads(input_data)
            tool_name = parsed.get("tool_name", "") or ""
            agent_type = parsed.get("tool_input", {}).get("subagent_type", "") or ""
            content = parsed.get("tool_response", {}).get("content", "") or ""
            content_len = len(content.encode("utf-8"))
        except (json.JSONDecodeError, Exception):
            pass

    # 只处理 Task / Agent 工具
    if tool_name not in ("Task", "Agent"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # 判断是否为危险类型
    dangerous_types_str = hc_get("subagent_guard.dangerous_types", "executor designer scientist")
    dangerous_types = dangerous_types_str.split()
    is_dangerous = any(dt in agent_type for dt in dangerous_types)

    project_root = (_HOOKS_DIR / "../..").resolve()
    state_dir = project_root / ".omc" / "state"
    usage_log = state_dir / "subagent-usage.jsonl"
    state_dir.mkdir(parents=True, exist_ok=True)

    # 高用量阈值
    try:
        high_threshold = int(hc_get("subagent_guard.high_usage_threshold_bytes", "51200"))
    except (ValueError, TypeError):
        high_threshold = 51200

    is_high = content_len > high_threshold

    ts = int(time.time())

    # 记录到 subagent-usage.jsonl
    log_entry = json.dumps({
        "ts": ts,
        "agent": agent_type,
        "content_bytes": content_len,
        "high_usage": is_high
    }, ensure_ascii=True)
    try:
        with open(str(usage_log), "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception:
        pass

    # 日志轮转（>512KB 切档）
    if usage_log.exists():
        try:
            size = usage_log.stat().st_size
            if size > 524288:
                usage_log.rename(str(usage_log) + ".1")
                usage_log.touch()
        except Exception:
            pass

    # K1 跨Agent数据链: 子Agent输出 >=10KB → 注入验证提醒
    try:
        verify_threshold = int(hc_get("subagent_guard.verify_reminder_threshold_bytes", "10240"))
    except (ValueError, TypeError):
        verify_threshold = 10240

    if content_len > verify_threshold:
        flywheel_event("posttool_subagent_audit", "verify_reminder", "P2")
        verify_msg = (
            f"[K1 跨Agent数据链提醒] {agent_type} 返回 {content_len} 字节内容。\n"
            f"⚠️ 子Agent输出默认视为 [推断, 待确认] — 任何数值/统计/路径在写入输出文件前必须独立验证（wc -l / ls / diff 物理确认）。\n"
            f"DG-44/DG-63: 未验证的子Agent数据曾导致 34x 幻读偏差。"
        )
        print(hc_emit_hook_json(verify_msg, "PostToolUse", True))

    # 高用量 → 写 flywheel P0 事件
    if is_high:
        home = Path.home()
        flywheel_buf = home / ".claude" / "flywheel-buffer.jsonl"
        flywheel_buf.parent.mkdir(parents=True, exist_ok=True)
        buf_entry = json.dumps({
            "ts": ts,
            "event": "subagent_high_usage",
            "level": "P0",
            "project": project_root.name,
            "agent": agent_type,
            "content_bytes": content_len
        }, ensure_ascii=True)
        try:
            with open(str(flywheel_buf), "a", encoding="utf-8") as f:
                f.write(buf_entry + "\n")
        except Exception:
            pass

        msg = (
            f"[Subagent Audit] {agent_type} 返回 {content_len} 字节"
            f"（>{high_threshold} 高用量阈值）。已记入 flywheel P0 事件，"
            f"下次 SessionStart 会告警。"
            f"如需调整阈值改 harness.yaml subagent_guard.high_usage_threshold_bytes"
        )
        print(hc_emit_hook_json(msg, "PostToolUse", True))
        sys.exit(0)

    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
