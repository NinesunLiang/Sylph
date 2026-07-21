#!/usr/bin/env python3
"""
pretool-write-lock.py — PreToolUse:Edit|Write — 写操作前获取 OMA 并发锁，防止多终端冲突
Role: 写操作前获取 OMA 并发锁，防止多终端冲突。锁管理器异常时 fail-open（记录+放行），不硬阻断写入
对应 pretool-write-lock.sh 的 Python 移植
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, output_continue, read_input, is_mode_active, HOME_DIR


def main():
    # hc_enabled check
    if not hc_enabled("pretool_write_lock"):
        output_continue()
        return

    script_dir = Path(__file__).resolve().parent
    project_root = (script_dir / "../..").resolve()
    state_dir = project_root / ".omc" / "state"

    # Mode detection: ghost/goal 降级为 log+skip
    mode = is_mode_active(str(state_dir))
    if mode != "normal":
        print(f"[{mode}] pretool-write-lock 已记录（模式降级，不阻断）", file=sys.stderr, flush=True)
        output_continue()
        return

    tool_input_str = sys.stdin.read()

    # 从 stdin JSON 读 tool_name
    try:
        data = json.loads(tool_input_str)
    except json.JSONDecodeError:
        data = {}

    tool_name = data.get("tool_name", data.get("tool", ""))
    if not tool_name:
        # Try parsing via regex (fallback for non-JSON)
        m = re.search(r'"tool_name"\s*:\s*"([^"]+)"', tool_input_str)
        if m:
            tool_name = m.group(1)
        else:
            m = re.search(r'"tool"\s*:\s*"([^"]+)"', tool_input_str)
            if m:
                tool_name = m.group(1)

    tool_name = tool_name.lower()

    # 仅拦截直接写文件的工具
    if tool_name not in ("edit", "write", "replace", "str_replace"):
        output_continue()
        return

    # 提取文件路径 (支持 filePath 或 file_path)
    file_path = ""
    if isinstance(data, dict):
        file_path = data.get("args", {}).get("filePath", data.get("tool_input", {}).get("file_path", ""))

    if not file_path:
        m = re.search(r'"filePath"\s*:\s*"([^"]+)"', tool_input_str)
        if m:
            file_path = m.group(1)
        else:
            m = re.search(r'"file_path"\s*:\s*"([^"]+)"', tool_input_str)
            if m:
                file_path = m.group(1)

    if not file_path:
        output_continue()
        return

    # 尝试识别所属的 RPE Feature 终端
    current_dir = os.getcwd()
    if "/rpe/" in current_dir:
        owner = current_dir.split("/rpe/", 1)[1].split("/", 1)[0]
    else:
        owner = f"claude-term-{os.getpid()}"

    # 调用锁管理器 (阻塞式等待)
    lock_script = str(project_root / ".claude" / "scripts" / "oma_lock_manager.py")
    try:
        result = subprocess.run(
            [sys.executable, lock_script, "acquire", file_path, owner],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"⚠️ [Carror OS] 并发锁引擎异常 (Exit {result.returncode}) — 已降级放行（fail-open），写入操作继续。",
                  file=sys.stderr, flush=True)
            flywheel_event("pretool_write_lock", "error", "P2")
            output_continue()
            return
    except Exception as e:
        print(f"⚠️ [Carror OS] 并发锁引擎异常 ({e}) — 已降级放行（fail-open），写入操作继续。",
              file=sys.stderr, flush=True)
        flywheel_event("pretool_write_lock", "error", "P2")
        output_continue()
        return

    flywheel_event("pretool_write_lock", "acquired", "P2")
    # 成功抢到锁，由于标准输出被 Claude Code 捕获，此处静默退出
    output_continue()


if __name__ == "__main__":
    main()
