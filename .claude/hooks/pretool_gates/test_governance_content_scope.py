"""test_governance_content_scope.py — F1 红测试

scorecard-gate 应区分：
- 治理基础设施文件（豁免：scorecard.md / .omc/ / settings.json 等）→ 放行
- 治理内容文件（SKILLS.md / references/ 等）→ 走 working-set 检查

当前问题：所有 .claude/ 都视为治理文件被豁免，AI 可随便改 SKILLS.md / references/ 等。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "pretool-scorecard-gate.py"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
ACTIVE_RESUME = STATE_DIR / "active-resume.json"
TASK_WORKING_SET = PROJECT_ROOT / ".omc/tasks/20260830/vibecoding-min-changes-3fix/working-set.yaml"


def _setup_active_task(tmp_path: Path | None = None) -> None:
    """写 active-resume.json 指向 vibecoding-min-changes-3fix 任务（含 .claude/skills）。"""
    ACTIVE_RESUME.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_RESUME.write_text(json.dumps({
        "task_dir": str(TASK_WORKING_SET.parent),
        "plan_dir": str(TASK_WORKING_SET.parent),
    }))


def _teardown_active_task() -> None:
    if ACTIVE_RESUME.exists():
        ACTIVE_RESUME.unlink()


def _run_hook(file_path: str) -> dict:
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "test"},
    }
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
    )
    result = {}
    lines = [l for l in (proc.stdout or "").splitlines() if l.strip().startswith("{")]
    if lines:
        try:
            result = json.loads(lines[-1])
        except json.JSONDecodeError:
            pass
    result["stderr"] = proc.stderr or ""
    return result


def setup_module(_):
    _setup_active_task()


def teardown_module(_):
    _teardown_active_task()


def test_content_file_outside_working_set_redirects():
    """SKILLS.md 是治理内容文件，工作集未声明时应被 REDIRECT。"""
    # F1 修复前：scorecard-gate 把 .claude/skills/ 视为治理文件，跳过检查
    # F1 修复后：SKILLS.md 应走 working-set 检查
    r = _run_hook(str(PROJECT_ROOT / ".claude/skills/SKILLS.md"))
    decision = r.get("hookSpecificOutput", {}).get("permissionDecision", "")
    # F1 修复前 decision = "" (被豁免)
    # F1 修复后若 working-set 未声明，应 ASK
    # 当前测试工作集已声明 skills/，所以应放行
    assert decision != "ask", (
        f"working-set 已声明 skills/，不应 ASK。decision: {decision!r}, stderr: {r['stderr']!r}"
    )


def test_infrastructure_file_exempted():
    """scorecard.md 是治理基础设施文件，应被豁免（无论 working-set 是否声明）。"""
    r = _run_hook(str(PROJECT_ROOT / ".claude/references/scorecard.md"))
    decision = r.get("hookSpecificOutput", {}).get("permissionDecision", "")
    # 豁免：decision = "" (放行)
    assert decision == "", (
        f"scorecard.md 应被豁免。decision: {decision!r}, stderr: {r['stderr']!r}"
    )


def test_settings_json_exempted():
    """settings.json 是治理基础设施文件，应被豁免。"""
    r = _run_hook(str(PROJECT_ROOT / ".claude/settings.json"))
    decision = r.get("hookSpecificOutput", {}).get("permissionDecision", "")
    assert decision == "", (
        f"settings.json 应被豁免。decision: {decision!r}, stderr: {r['stderr']!r}"
    )


def test_orphan_content_file_redirected():
    """工作集未声明的 .claude/workflows/foo.md 应被 REDIRECT（内容文件不受 .claude/ 整目录豁免）。"""
    # 当前 working-set 没声明 .claude/workflows/
    r = _run_hook(str(PROJECT_ROOT / ".claude/workflows/orphan-test-file.md"))
    decision = r.get("hookSpecificOutput", {}).get("permissionDecision", "")
    # F1 修复前：被 .claude/ 整目录豁免 → decision="" (放行)
    # F1 修复后：未声明 → 应 ASK
    assert decision == "ask", (
        f".claude/workflows/ 未声明应被 ASK。decision: {decision!r}, stderr: {r['stderr']!r}"
    )