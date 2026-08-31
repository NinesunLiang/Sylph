"""test_index37_fixes.py — index37 双法官盲评机制修复 TDD（先红后绿）。

P0 test-verification 门禁死锁（index37 电池 8/17 ON 探针 exit=1 根因）：
  - 门禁要求"本日 audit 有测试记录"，但没有任何机制把测试运行写进 audit → 永远无法满足
  - 同一良性 .py 编辑被 REDIRECT 2 次 → 升级 hard stop → max_turns 卡死
  - 修复：① Bash 跑测试 → 记录 test_run 到 audit（门禁自清）② 同一文件已引导过 → 放行（良性不卡死）

P1 删除保护引号 bug（rm-dot ON 删光 AGENTS.md/CLAUDE.md 根因）：
  - _extract_delete_targets 从 `rm -rf "AGENTS.md"` 提取的目标带引号 → 与 _GOVERNANCE_DELETE_BASENAMES 不匹配
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from pretool_gates import checks  # noqa: E402
from pretool_gates import helpers  # noqa: E402


def _payload(tool: str, **kw) -> dict:
    return {"tool_name": tool, "tool_input": kw}


def _mk_project(tmp: Path, with_test: bool = True) -> Path:
    """临时项目：app.py + (可选) test_app.py + 空 state。"""
    (tmp / "app.py").write_text("x = 1\n", encoding="utf-8")
    if with_test:
        (tmp / "test_app.py").write_text("def test_x(): pass\n", encoding="utf-8")
    (tmp / ".omc" / "state" / "audit").mkdir(parents=True, exist_ok=True)
    return tmp


# ── P1 删除保护引号 bug ────────────────────────────────────────────────

def test_rm_quoted_governance_file_blocked():
    """rm -rf 带引号删除 AGENTS.md 应被保护拦截（引号剥离后匹配）。"""
    cmd = 'rm -rf "/tmp/x/.git" "/tmp/x/.omc" "/tmp/x/AGENTS.md" "/tmp/x/CLAUDE.md"'
    targets = checks._extract_delete_targets(_payload("Bash", command=cmd))
    assert any(t.rstrip("/").split("/")[-1] == "AGENTS.md" for t in targets), f"目标应含 AGENTS.md: {targets}"
    r = checks._check_governance_delete_protection(_payload("Bash", command=cmd))
    assert r and r.startswith("REDIRECT"), f"带引号删除 AGENTS.md 应被拦截, 实际: {r!r}"


def test_rm_quoted_kernel_index_blocked():
    """rm 带引号删除 .claude/kernel.md / index.md 应被拦截。"""
    for f in (".claude/kernel.md", ".claude/index.md"):
        cmd = f'rm -rf "/tmp/x/{f}"'
        r = checks._check_governance_delete_protection(_payload("Bash", command=cmd))
        assert r and r.startswith("REDIRECT"), f"{f} 带引号删除应被拦截: {r!r}"


# ── P0 test-verification 死锁 ──────────────────────────────────────────

def test_implement_stub_py_allowed_without_redirect():
    """index40 F1：编辑 stub（空实现）py 文件应放行——实现新函数不该被 test-verification 拦。"""
    with tempfile.TemporaryDirectory() as td:
        proj = _mk_project(Path(td))
        (proj / "app.py").write_text("def double(x):\n    pass\n", encoding="utf-8")
        old_state = checks.STATE_DIR
        old_audit = helpers.AUDIT
        old_cwd = os.getcwd()
        try:
            os.chdir(proj)
            checks.STATE_DIR = proj / ".omc" / "state"
            helpers.AUDIT = proj / ".omc" / "state" / "audit"
            r = checks._check_test_verification(
                _payload("Edit", file_path="app.py", old_string="pass", new_string="return x * 2"))
            assert r is None, f"实现 stub 应放行: {r!r}"
        finally:
            checks.STATE_DIR = old_state
            helpers.AUDIT = old_audit
            os.chdir(old_cwd)


def test_bash_test_run_records_test_run():
    """Bash 跑测试（pytest）应记录 test_run 到 audit 并放行（门禁自清）。"""
    with tempfile.TemporaryDirectory() as td:
        proj = _mk_project(Path(td))
        old_state = checks.STATE_DIR
        old_audit = helpers.AUDIT
        old_cwd = os.getcwd()
        try:
            os.chdir(proj)
            checks.STATE_DIR = proj / ".omc" / "state"
            helpers.AUDIT = proj / ".omc" / "state" / "audit"
            r = checks._check_test_verification(_payload("Bash", command="python3 -m pytest -q"))
            assert r is None, f"跑 pytest 应放行: {r!r}"
            today = datetime.now().strftime("%Y-%m-%d")
            audit_file = helpers.AUDIT / f"{today}.jsonl"
            assert audit_file.exists(), "test_run 应落盘 audit"
            content = audit_file.read_text(encoding="utf-8")
            assert "test_run" in content, f"audit 应含 test_run: {content[:200]}"
        finally:
            checks.STATE_DIR = old_state
            helpers.AUDIT = old_audit
            os.chdir(old_cwd)


def test_retry_edit_without_test_run_still_redirects():
    """index40 F2：同一文件重试编辑但没跑测试 → 仍 REDIRECT（堵重试绕过）。"""
    with tempfile.TemporaryDirectory() as td:
        proj = _mk_project(Path(td))
        old_state = checks.STATE_DIR
        old_audit = helpers.AUDIT
        old_cwd = os.getcwd()
        try:
            os.chdir(proj)
            checks.STATE_DIR = proj / ".omc" / "state"
            helpers.AUDIT = proj / ".omc" / "state" / "audit"
            r1 = checks._check_test_verification(
                _payload("Edit", file_path="app.py", old_string="1", new_string="2"))
            assert r1 and r1.startswith("REDIRECT"), f"首次编辑应 REDIRECT: {r1!r}"
            r2 = checks._check_test_verification(
                _payload("Edit", file_path="app.py", old_string="2", new_string="3"))
            assert r2 and r2.startswith("REDIRECT"), f"未跑测试重试仍应 REDIRECT: {r2!r}"
        finally:
            checks.STATE_DIR = old_state
            helpers.AUDIT = old_audit
            os.chdir(old_cwd)


def test_edit_allowed_after_recent_test_run():
    """index40 F2：跑过测试(test_run 近期)后同一文件编辑 → 放行。"""
    with tempfile.TemporaryDirectory() as td:
        proj = _mk_project(Path(td))
        old_state = checks.STATE_DIR
        old_audit = helpers.AUDIT
        old_cwd = os.getcwd()
        try:
            os.chdir(proj)
            checks.STATE_DIR = proj / ".omc" / "state"
            helpers.AUDIT = proj / ".omc" / "state" / "audit"
            # 先跑测试（记录 test_run）
            r0 = checks._check_test_verification(_payload("Bash", command="python3 -m pytest -q"))
            assert r0 is None
            # 再编辑同一文件 → 放行
            r1 = checks._check_test_verification(
                _payload("Edit", file_path="app.py", old_string="1", new_string="2"))
            assert r1 is None, f"近期跑过测试应放行: {r1!r}"
        finally:
            checks.STATE_DIR = old_state
            helpers.AUDIT = old_audit
            os.chdir(old_cwd)
