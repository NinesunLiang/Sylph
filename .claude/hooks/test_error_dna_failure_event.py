"""TDD 回归: error-dna 在 PostToolUseFailure 事件下不崩溃(is_escape 修复)。

缺陷: is_escape 在 line 413 才赋值, 但 line 380 的 level 计算先使用
→ UnboundLocalError。之前 error-dna 只在 PostToolUse(成功)跑, 该分支
从没走到; 降级为 PostToolUseFailure(仅失败)后首次暴露。

修复: is_escape 判定前置到 level 计算前, 移除重复赋值。
"""
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "error-dna.py"
LAUNCHER = Path(__file__).resolve().parent / "hook-launcher.py"

# 失败事件 payload(模拟 PostToolUseFailure: Bash 失败)
FAILURE_PAYLOAD = json.dumps({
    "tool_name": "Bash",
    "tool_input": {"command": "ls /nonexistent"},
    "tool_response": {"exit_code": 2, "stderr": "ls: /nonexistent: No such file or directory"},
    "hook_event_name": "PostToolUseFailure",
})


def _run_hook():
    return subprocess.run(
        [sys.executable, str(LAUNCHER), "error-dna.py"],
        input=FAILURE_PAYLOAD, capture_output=True, text=True, timeout=30,
    )


def test_failure_event_no_crash():
    """PostToolUseFailure 事件下 error-dna 不崩溃, 正常 continue。"""
    r = _run_hook()
    assert r.returncode == 0, f"error-dna 应正常退出, 实际 exit={r.returncode}: {r.stderr}"
    assert '"continue": true' in r.stdout, "应输出 continue:true"


def test_failure_event_writes_record():
    """失败事件应写入 error-dna.jsonl 记录(含 level=error)。"""
    r = _run_hook()
    assert r.returncode == 0
    log = Path(__file__).resolve().parents[2] / ".omc" / "state" / "error-dna.jsonl"
    assert log.exists(), "error-dna.jsonl 应存在"
    lines = [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    last = json.loads(lines[-1])
    assert "error" in (last.get("level") or "").lower() or last.get("level") in ("error", "warn"), \
        f"失败记录 level 应为 error/warn, 实际: {last.get('level')}"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
