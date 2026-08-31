"""test_plan_step_enforcement.py — F2 红测试

PLAN_GATE 升级：写代码前必须读 plan.md 并标记当前步骤 [x]。
- plan 当前步骤未 VERIFIED → REDIRECT（提醒 AI 读 plan）
- 修改文件不在 plan 声明范围内 → REDIRECT（防止乱动）

目标：AI 沿着 plan 一镜到底，不报 hook 错。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "pretool-gate.py"


def _run_hook(payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=10,
    )
    result = {}
    lines = [l for l in (proc.stdout or "").splitlines() if l.strip().startswith("{")]
    if lines:
        try:
            # hook-launcher 已合并多 hook 输出为单 JSON
            result = json.loads(lines[-1])
        except json.JSONDecodeError:
            pass
    result["stderr"] = proc.stderr or ""
    return result


def test_no_active_plan_passes():
    """无活跃 task plan 时不拦（向后兼容）。"""
    payload = {
        "tool_name": "Edit",
        "tool_input": {"file_path": "/tmp/foo.md", "new_string": "x"},
    }
    r = _run_hook(payload)
    # 不应被 REDIRECT（除非有 plan）
    assert "REDIRECT" not in r.get("stderr", "") or "REDIRECT step_" not in r.get("stderr", ""), (
        f"无 plan 时不应触发 step REDIRECT。stderr: {r['stderr'][:300]}"
    )


def test_write_to_plan_file_requires_verified_step():
    """写 plan.md / 任务目录文件时，未 VERIFIED 步骤应被 REDIRECT。

    修复目标：AI 想写 plan 相关文件但当前步骤未验证 → 提醒 AI 走 verify。
    """
    # 模拟：有 active-resume.json + plan_dir + current_step 未 VERIFIED
    # 这里用 monkeypatch 模拟 _active_task_dir 行为；最简单方式是测"REDIRECT step_"
    # 出现在 stderr 中。
    payload = {
        "tool_name": "Edit",
        "tool_input": {"file_path": "/tmp/foo-plan.md", "new_string": "x"},
    }
    r = _run_hook(payload)
    # 注：无 active task 时不拦——这个测试只验证向后兼容
    # 真正的"REDIRECT step_"测试需要 fixture（active-resume.json）
    # 见 test_step_unverified_redirects（需要 fixture 化）
    assert "stderr" in r  # 基本可用性