#!/usr/bin/env python3
"""
token_writer.py — PostToolUse:.* / SessionStart — 写入 token 用量追踪索引供 context-guard 计算
Role: 写入 token 用量追踪索引供 context-guard 计算
对应 token_writer.sh 的 Python 移植
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, output_continue, read_input, hc_get, HOME_DIR


def auto_limit():
    """自动检测实际模型上下文限制"""
    try:
        settings_path = Path.home() / ".claude" / "settings.json"
        if settings_path.exists():
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            model = settings.get("env", {}).get("ANTHROPIC_MODEL", "")
            m = re.search(r"\[(\d+)([km])\]", model)
            if m:
                n = int(m.group(1))
                unit = m.group(2)
                return n * 1000 if unit == "k" else n * 1000000
    except Exception:
        pass
    return 200000


def detect_context_limit(state_dir):
    """自动检测实际模型上下文限制（优先级: 模型名后缀 > ecosystem-probe > harness config）"""
    # 1. 从 settings.json 解析模型名中的上下文后缀
    try:
        settings_path = Path.home() / ".claude" / "settings.json"
        if settings_path.exists():
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            model = settings.get("env", {}).get("ANTHROPIC_MODEL", "")
            m = re.search(r"\[(\d+)([km])\]", model)
            if m:
                n = int(m.group(1))
                unit = m.group(2)
                limit_val = n * 1000 if unit == "k" else n * 1000000
                if limit_val > 0:
                    return limit_val
    except Exception:
        pass

    # 2. 从 ecosystem-probe 缓存读取
    probe_cache = state_dir / ".ecosystem-probe-cache"
    if probe_cache.exists():
        try:
            content = probe_cache.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"context_limit:\s*(\d+)", content)
            if m:
                limit_val = int(m.group(1))
                if limit_val > 0:
                    return limit_val
        except Exception:
            pass

    # 3. 兜底
    return int(hc_get("token_tracking.limit", "200000"))


def get_increment(tool_name):
    """Map tool type to per-turn token increment"""
    mapping = {
        "read": 500,
        "grep": 1000,
        "bash": 2000,
        "write": 5000,
        "edit": 5000,
    }
    return mapping.get(tool_name.lower(), 3000)


def get_effective_incr(tool_name, input_stdin):
    """Get effective increment: actual response content bytes, or fallback to tool-type fixed value"""
    if not input_stdin:
        return get_increment(tool_name)

    try:
        d = json.loads(input_stdin)
    except (json.JSONDecodeError, ValueError):
        return get_increment(tool_name)

    tr = d.get("tool_response", {}) or {}
    total = 0

    # Sum all text from content blocks (Read, Grep, Edit results)
    content = tr.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                total += len(str(block.get("text", "") or ""))

    # Fall back to stdout (Bash results)
    if total == 0:
        total = len(tr.get("stdout", "") or "")

    # Fall back to stderr
    if total == 0:
        total = len(tr.get("stderr", "") or "")

    if total > 0:
        if total > 50000:
            total = 50000
        return total

    return get_increment(tool_name)


def main():
    # hc_enabled check
    if not hc_enabled("token_writer"):
        output_continue()
        return

    script_dir = Path(__file__).resolve().parent
    project_root = (script_dir / "../..").resolve()
    state_dir = project_root / ".omc" / "state"
    index_file = state_dir / "token-tracking-index.json"
    savings_file = state_dir / "token-savings.json"
    compact_state = state_dir / "token-compact-state.json"

    state_dir.mkdir(parents=True, exist_ok=True)

    # Read stdin for tool context (PostToolUse hook — extract tool_name)
    try:
        input_stdin = sys.stdin.read()
    except Exception:
        input_stdin = ""

    tool_name = ""
    if input_stdin:
        try:
            d = json.loads(input_stdin)
            tool_name = d.get("tool_name", d.get("tool", ""))
        except (json.JSONDecodeError, ValueError):
            m = re.search(r'"tool_name"\s*:\s*"([^"]+)"', input_stdin)
            if m:
                tool_name = m.group(1)
            else:
                m = re.search(r'"tool"\s*:\s*"([^"]+)"', input_stdin)
                if m:
                    tool_name = m.group(1)

    # --reset 模式
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_limit = auto_limit()
        index_data = {
            "usage": 0,
            "limit": reset_limit,
            "last_updated": "SESSION_START",
            "source": "token_writer.py --reset"
        }
        with open(str(index_file), "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2)
        session_log = state_dir / ".token-writer-session.log"
        with open(str(session_log), "a", encoding="utf-8") as f:
            f.write("[token_writer] reset\n")
        output_continue()
        return

    # Detect context limit
    limit = detect_context_limit(state_dir)

    # 读取当前值
    usage = 0
    if index_file.exists():
        try:
            with open(str(index_file), "r", encoding="utf-8") as f:
                idx_data = json.load(f)
            usage = int(idx_data.get("usage", 0))
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    # 读取 savings 当前值
    compact_saved = 0
    compact_events = 0
    if savings_file.exists():
        try:
            with open(str(savings_file), "r", encoding="utf-8") as f:
                sav_data = json.load(f)
            compact_saved = int(sav_data.get("compact", 0))
            compact_events = int(sav_data.get("compact_events", 0))
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    # --increment 模式
    if len(sys.argv) > 1 and sys.argv[1] == "--increment":
        # 检查是否有待处理的 compact
        if compact_state.exists():
            try:
                with open(str(compact_state), "r", encoding="utf-8") as f:
                    cs_data = json.load(f)
            except (json.JSONDecodeError, OSError):
                cs_data = {}

            pre_compact = int(cs_data.get("pre_compact_usage", 0))
            if pre_compact > 0:
                # 用户公式：savings = pre_compact_usage - post_compact_usage
                post_compact = pre_compact * 3 // 10
                compact_delta = pre_compact - post_compact

                # 累计 compact 节省
                compact_saved += compact_delta
                compact_events += 1

                # 更新 usage
                new_usage = post_compact + 3000
                if new_usage > limit:
                    new_usage = limit
                usage = new_usage

                # 清除 compact state
                with open(str(compact_state), "w", encoding="utf-8") as f:
                    json.dump({"pre_compact_usage": 0, "pending": False}, f, indent=2)
            else:
                # 无待处理 compact：正常递增
                incr = get_effective_incr(tool_name, input_stdin)
                usage += incr
                if usage > limit:
                    usage = limit
        else:
            # 无 compact state 文件：正常递增
            incr = get_effective_incr(tool_name, input_stdin)
            usage += incr
            if usage > limit:
                usage = limit

    # 写入 token-tracking-index.json
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    index_data = {
        "usage": usage,
        "limit": limit,
        "last_updated": now_str,
        "source": "token_writer.py"
    }
    with open(str(index_file), "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)

    # 写入 token-savings.json
    total = compact_saved
    savings_data = {
        "compact": compact_saved,
        "total": total,
        "compact_events": compact_events,
        "last_updated": now_str
    }
    with open(str(savings_file), "w", encoding="utf-8") as f:
        json.dump(savings_data, f, indent=2)

    # 只对 --reset / --increment 模式输出 continue
    if len(sys.argv) > 1 and sys.argv[1] in ("--reset", "--increment"):
        output_continue()

    flywheel_event("token_writer", "token_written", "P2", "written")
    sys.exit(0)


if __name__ == "__main__":
    main()
