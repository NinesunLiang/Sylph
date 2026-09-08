from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from pretool_gates import checks  # noqa: E402
from pretool_gates import helpers  # noqa: E402


def _payload(tool: str, **kw) -> dict:
    return {"tool_name": tool, "tool_input": kw}


def _mk_project(tmp: Path) -> Path:
    """临时项目：app.py + test_app.py(断言) + 空 state。"""
    (tmp / "app.py").write_text("TIMEOUT = 30\n", encoding="utf-8")
    (tmp / "test_app.py").write_text(
        "from app import TIMEOUT\nassert TIMEOUT == 30\n", encoding="utf-8")
    (tmp / ".omc" / "state" / "audit").mkdir(parents=True, exist_ok=True)
    return tmp


# ── index44 S5 G1：堵「改测试凑绿」——修改已存在测试文件也需先跑测试 ──

def test_modify_existing_test_file_without_test_run_redirects():
    """修改已存在的 test 文件（改断言对齐代码）而无近期 test_run → 应 REDIRECT。

    index44 skip-tests 实证：模型把 test_config.py 断言 ==30 改成 ==99 绕过 F2。
    """
    with tempfile.TemporaryDirectory() as td:
        proj = _mk_project(Path(td))
        old_state = checks.STATE_DIR
        old_audit = helpers.AUDIT
        old_cwd = os.getcwd()
        try:
            os.chdir(proj)
            checks.STATE_DIR = proj / ".omc" / "state"
            helpers.AUDIT = proj / ".omc" / "state" / "audit"
            r = checks._check_test_verification(
                _payload("Edit", file_path="test_app.py", old_string="== 30", new_string="== 99"))
            assert r and r.startswith("REDIRECT"), f"改已有测试无 test_run 应 REDIRECT: {r!r}"
        finally:
            checks.STATE_DIR = old_state
            helpers.AUDIT = old_audit
            os.chdir(old_cwd)


def test_edit_test_allowed_after_recent_test_run():
    """已存在的测试文件，跑过 pytest 后再改 → 放行（不破坏合法 red/green 维护）。"""
    with tempfile.TemporaryDirectory() as td:
        proj = _mk_project(Path(td))
        old_state = checks.STATE_DIR
        old_audit = helpers.AUDIT
        old_cwd = os.getcwd()
        try:
            os.chdir(proj)
            checks.STATE_DIR = proj / ".omc" / "state"
            helpers.AUDIT = proj / ".omc" / "state" / "audit"
            r0 = checks._check_test_verification(_payload("Bash", command="python3 -m pytest -q"))
            assert r0 is None, "跑 pytest 应放行并记录"
            r1 = checks._check_test_verification(
                _payload("Edit", file_path="test_app.py", old_string="== 30", new_string="== 99"))
            assert r1 is None, f"近期跑过测试后改测试应放行: {r1!r}"
        finally:
            checks.STATE_DIR = old_state
            helpers.AUDIT = old_audit
            os.chdir(old_cwd)


def test_create_new_test_file_allowed_red_first():
    """新建测试文件（red-first 编写，此前不存在）→ 放行，不破坏 TDD 红灯流程。"""
    with tempfile.TemporaryDirectory() as td:
        proj = _mk_project(Path(td))
        (proj / "new_test.py").unlink(missing_ok=True)
        old_state = checks.STATE_DIR
        old_audit = helpers.AUDIT
        old_cwd = os.getcwd()
        try:
            os.chdir(proj)
            checks.STATE_DIR = proj / ".omc" / "state"
            helpers.AUDIT = proj / ".omc" / "state" / "audit"
            r = checks._check_test_verification(
                _payload("Write", file_path="test_new.py", content="def test_y(): assert True\n"))
            assert r is None, f"新建测试文件(red-first)应放行: {r!r}"
        finally:
            checks.STATE_DIR = old_state
            helpers.AUDIT = old_audit
            os.chdir(old_cwd)


# ── index44 S5 G2：堵「python 通道绕过删除保护」──

def test_python_rmtree_governance_file_blocked():
    """python shutil.rmtree 删除 AGENTS.md 应被治理删除保护拦截（此前仅拦 rm）。"""
    cmd = "python3 -c \"import shutil; shutil.rmtree('/tmp/x/AGENTS.md')\""
    targets = checks._extract_delete_targets(_payload("Bash", command=cmd))
    assert any(t.rstrip("/").split("/")[-1] == "AGENTS.md" for t in targets), f"目标应含 AGENTS.md: {targets}"
    r = checks._check_governance_delete_protection(_payload("Bash", command=cmd))
    assert r and r.startswith("REDIRECT"), f"python rmtree 删 AGENTS.md 应被拦: {r!r}"


def test_python_osremove_referenced_style_blocked_by_doc_gate_targets():
    """python os.remove 目标应能被抽取（供 F3 doc-reference 门使用）。"""
    cmd = "python3 delete.py  # os.remove('scripts/api_helper.py')"
    # 仅字面删除调用应被识别，注释不触发
    cmd2 = "python3 -c \"import os; os.remove('/tmp/x/scripts/api_helper.py')\""
    targets = checks._extract_delete_targets(_payload("Bash", command=cmd2))
    assert "api_helper.py" in str(targets), f"python os.remove 目标应被抽取: {targets}"
    # 纯注释/普通 python 脚本不带字面删除 → 不误伤
    assert checks._extract_delete_targets(_payload("Bash", command=cmd)) == []
