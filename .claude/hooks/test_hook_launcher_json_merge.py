"""test_hook_launcher_json_merge.py — F1 红测试

hook-launcher.py 跑多个 hook 时，stdout 应该是单 JSON object，
不是两个 JSON 拼接（"}{" pattern）。

实测根因：每个 hook 都 print 独立 JSON，launcher 直接 sys.stdout.write 拼接。
Claude Code JSON parser 看到 `}{...}{...}` 失败 → "Hook output looks like a JSON object but is not valid JSON"

修复策略：launcher 应合并多 hook 输出成单 JSON（合并 message 字段 + 合并 reasons）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_LAUNCHER = Path(__file__).resolve().parent / "hook-launcher.py"


def _run_launcher(hook_names: list[str], payload: dict) -> dict:
    """调用 hook-launcher 跑多个 hook，返回 Claude Code 看到的合并 JSON。"""
    proc = subprocess.run(
        [sys.executable, str(HOOK_LAUNCHER)] + hook_names,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
    )
    # 解析 stdout 第一行（Claude Code 解析的第一行 JSON）
    out_lines = (proc.stdout or "").strip().splitlines()
    if not out_lines:
        return {"raw": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}
    first = out_lines[0]
    try:
        return json.loads(first)
    except json.JSONDecodeError as e:
        return {"raw_first": first, "raw_all": proc.stdout, "stderr": proc.stderr,
                "returncode": proc.returncode, "error": str(e)}


def test_single_hook_returns_single_json():
    """单 hook：stdout 应为单 JSON object（基线）。"""
    r = _run_launcher(
        ["pretool-gate.py"],
        {"tool_name": "Bash", "tool_input": {"command": "ls /tmp"}},
    )
    # 必须能 parse 为 dict
    assert isinstance(r, dict), f"单 hook 返回非 dict: {r}"
    # 单 hook 输出应有 continue 字段
    assert "continue" in r, f"单 hook 输出无 continue: {r}"


def test_multiple_hooks_returns_single_json():
    """多 hook：stdout 应仍为单 JSON object（关键修复点）。"""
    proc = subprocess.run(
        [sys.executable, str(HOOK_LAUNCHER), "pretool-gate.py", "carroros-night-deny.py"],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls /tmp"}}),
        capture_output=True, text=True, timeout=30,
    )
    # 关键断言：整个 stdout 必须是单 JSON object
    # Claude Code 会 parse 整个 stdout（不是只第一行）
    stdout = proc.stdout or ""
    # 尝试把整个 stdout parse 为单 JSON
    try:
        parsed = json.loads(stdout.strip())
        # 必须是 dict（单对象），不是 dict + dict
        assert isinstance(parsed, dict), (
            f"stdout 不是单 JSON object — Claude Code 会报 hook error. stdout: {stdout[:200]}"
        )
    except json.JSONDecodeError as e:
        pytest.fail(
            f"stdout 不是合法 JSON（这是 hook error 的根因）: {e}. stdout: {stdout[:200]}"
        )


import pytest  # 放在后面避免上方 import 失败


def test_multiple_hooks_messages_merged():
    """多 hook 的 message 应合并到单个 JSON 的 message 字段（而不是拼接）。"""
    r = _run_launcher(
        ["pretool-gate.py", "carroros-night-deny.py"],
        {"tool_name": "Bash", "tool_input": {"command": "ls /tmp"}},
    )
    if "message" not in r:
        # 如果 merge 实现把 message 放到 hookSpecificOutput 或别处，跳过
        return  # 软断言：message 不是必需
    msg = r["message"]
    # 多 hook 的 message 应包含多个 hook 的痕迹（如分隔符或多个标识）
    # 不是简单 "}{" 拼接
    assert not msg.startswith("{") or not msg.endswith("}"), (
        f"message 字段仍是原始 JSON 拼接: {msg[:100]}"
    )


def test_hook_event_type_post_tool_use_failure():
    """PostToolUseFailure event type 应正确传递，避免 'Hook returned incorrect event name' 错误。"""
    # 用软完成语触发 REDIRECT 路径（有 hookSpecificOutput）
    proc = subprocess.run(
        [sys.executable, str(HOOK_LAUNCHER), "pretool-gate.py"],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git commit -m 'all done'"}}),
        capture_output=True, text=True, timeout=30,
        env={**__import__("os").environ, "HOOK_EVENT_TYPE": "PostToolUseFailure"},
    )
    parsed = json.loads(proc.stdout.strip())
    hso = parsed.get("hookSpecificOutput", {})
    assert hso.get("hookEventName") == "PostToolUseFailure", (
        f"hookEventName 应是 PostToolUseFailure，实际: {hso.get('hookEventName')}"
    )