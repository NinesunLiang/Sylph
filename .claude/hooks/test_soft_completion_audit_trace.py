"""test_soft_completion_audit_trace.py — 软完成语 warn 落项目审计链（index33 电池实证修复）

观测性缺口（index33 双法官共识#5）：soft_completion_detected 仅写宿主机 ~/.claude/flywheel.log，
项目 .omc/state/ 审计链不可见。修复：posttool-claim-audit 检测到时追加 .omc/state/soft-completion.jsonl。
index34 验收修复：用 CARROROS_STATE_DIR 环境变量隔离到 tmp（避免污染真实审计链）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent
HOOK = _HOOKS / "posttool-claim-audit.py"


def _run_hook(payload: dict, state_dir: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "CARROROS_STATE_DIR": str(state_dir)}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


def _payload(content: str, file_path: str = "/tmp/test-doc.md") -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": content}}


def _log_lines(state_dir: Path) -> list[str]:
    log = state_dir / "soft-completion.jsonl"
    if not log.exists():
        return []
    return [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_soft_completion_writes_project_audit_trace(tmp_path):
    """含"基本完成"的 Write → soft-completion.jsonl（tmp 隔离）新增一条记录。"""
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    before = len(_log_lines(state_dir))
    proc = _run_hook(_payload("## 修复报告\n\n基本完成，可以发布。\n", "/tmp/foo-doc.md"), state_dir)
    assert "soft_completion" in (proc.stderr or "").lower() or "软完成" in (proc.stderr or "")
    after = len(_log_lines(state_dir))
    assert after > before, f"soft-completion.jsonl 未新增记录 (before={before} after={after})"
    last = json.loads(_log_lines(state_dir)[-1])
    assert last.get("pattern") == "基本完成", f"pattern 不符: {last}"
    assert last.get("severity") == "warn", f"severity 不符: {last}"
    assert "foo-doc.md" in last.get("file_path", ""), f"file_path 不符: {last}"


def test_no_soft_completion_no_audit_entry(tmp_path):
    """不含软完成语 → 不新增审计记录。"""
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    before = len(_log_lines(state_dir))
    proc = _run_hook(_payload(
        "## 修复报告\n\n已修复：认证 token 过期 → 加 refresh 逻辑。\nVERIFIED: pytest 3 passed\n",
        "/tmp/foo-clean.md",
    ), state_dir)
    assert "soft_completion" not in (proc.stderr or "").lower()
    after = len(_log_lines(state_dir))
    assert after == before, f"正常内容不应新增审计记录 (before={before} after={after})"


def test_gate_bypassed_isolated_state_dir(tmp_path):
    """CARROROS_STATE_DIR 隔离生效：真实仓库审计链不被测试污染。"""
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    _run_hook(_payload("## x\n\n基本完成。\n", "/tmp/iso-doc.md"), state_dir)
    # 真实仓库 state 不应新增该条目（隔离验证）
    real_log = _HOOKS.parent.parent / ".omc" / "state" / "soft-completion.jsonl"
    if real_log.exists():
        content = real_log.read_text(encoding="utf-8")
        assert "iso-doc.md" not in content, "真实审计链不应被测试污染"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
