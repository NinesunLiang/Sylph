"""VerifyGate file: 规则真实读文件验证（还债升级）。

旧行为：验证 executor.md 里 AI 自述的 file/assertion 字段（可文字造假）。
新行为：真实读仓库内文件，检查内容包含目标字符串；路径越界即拒。
"""
from pathlib import Path

import verify_gate as vg


def _run(monkeypatch, tmp_path, rule, extra_files=None):
    vg.VERIFY_ROOT = Path(tmp_path)
    for name, content in (extra_files or {}).items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return vg.match_verify_rule(rule, [])  # 无 EV 证据：纯真实文件验证


def test_file_rule_real_read_matches(monkeypatch, tmp_path):
    ok, reason, _ = _run(monkeypatch, tmp_path,
                         "file: src/mod.py contains def handle_request",
                         {"src/mod.py": "def handle_request(x):\n    pass\n"})
    assert ok, reason
    assert "real file match" in reason


def test_file_rule_real_read_case_insensitive(monkeypatch, tmp_path):
    ok, reason, _ = _run(monkeypatch, tmp_path,
                         "file: src/mod.py contains DEF HANDLE_REQUEST",
                         {"src/mod.py": "def handle_request(x):\n"})
    assert ok, reason


def test_file_rule_real_read_missing_file_rejected(monkeypatch, tmp_path):
    ok, reason, _ = _run(monkeypatch, tmp_path,
                         "file: src/notexist.py contains foo")
    assert not ok
    assert "verified file missing" in reason


def test_file_rule_real_read_content_missing_rejected(monkeypatch, tmp_path):
    ok, reason, _ = _run(monkeypatch, tmp_path,
                         "file: src/mod.py contains bar",
                         {"src/mod.py": "only foo here\n"})
    assert not ok
    assert "does not contain" in reason


def test_file_rule_path_escape_rejected(monkeypatch, tmp_path):
    ok, reason, _ = _run(monkeypatch, tmp_path,
                         "file: ../../etc/passwd contains root")
    assert not ok
    assert "outside repo" in reason


def test_file_rule_absolute_path_outside_repo_rejected(monkeypatch, tmp_path):
    ok, reason, _ = _run(monkeypatch, tmp_path,
                         "file: /etc/hostname contains localhost")
    assert not ok
    assert "outside repo" in reason


def test_file_rule_absolute_path_inside_repo_allowed(monkeypatch, tmp_path):
    inside = tmp_path / "src"
    inside.mkdir()
    target = inside / "mod.py"
    target.write_text("def handle_request(x):\n", encoding="utf-8")
    ok, reason, _ = _run(monkeypatch, tmp_path,
                         f"file: {target} contains def handle_request")
    assert ok, reason


def test_file_rule_with_ev_evidence_ignored_for_real_match(monkeypatch, tmp_path):
    """防造假核心：即使 EV 自述写对了，真实文件不含也拒绝。"""
    ok, reason, _ = _run(monkeypatch, tmp_path,
                         "file: src/mod.py contains target_never_there",
                         {"src/mod.py": "unrelated content\n"})
    assert not ok, "EV 自述不能通过真实文件不匹配的验证"


def test_file_rule_real_read_ignores_soft_completion_in_content(monkeypatch, tmp_path):
    """真实文件内容含软完成短语不误判（软完成检测只防 AI 自述，不套真实文件）。"""
    ok, reason, _ = _run(monkeypatch, tmp_path,
                         "file: src/mod.py contains def handle_request",
                         {"src/mod.py": "def handle_request(x):\n    # should be ok\n    pass\n"})
    assert ok, reason


# ── index19 F1: task-dir relative path (artifacts/) should resolve ──

def test_file_rule_resolves_task_dir_relative_path(monkeypatch, tmp_path):
    """plan.md 的 file: 规则常用任务目录相对路径（如 artifacts/xxx）——
    应从 executor.md 所在任务目录解析，而非仅 repo 根。"""
    vg.VERIFY_ROOT = Path(tmp_path)
    task_dir = tmp_path / ".omc" / "tasks" / "20260813" / "probe-task"
    task_dir.mkdir(parents=True)
    artifact = task_dir / "artifacts" / "scorecard.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("C 加权 = 8.90\n", encoding="utf-8")
    ok, reason, _ = vg.match_verify_rule(
        "file: artifacts/scorecard.md contains C 加权", [], base_dir=task_dir)
    assert ok, reason


def test_file_rule_repo_root_still_works_with_base_dir(monkeypatch, tmp_path):
    """提供 base_dir 不破坏 repo 根解析（向后兼容）。"""
    vg.VERIFY_ROOT = Path(tmp_path)
    p = tmp_path / "src" / "mod.py"
    p.parent.mkdir(parents=True)
    p.write_text("def handle_request(x):\n", encoding="utf-8")
    ok, reason, _ = vg.match_verify_rule(
        "file: src/mod.py contains def handle_request", [], base_dir=tmp_path / "task")
    assert ok, reason


def test_file_rule_base_dir_missing_falls_back_to_repo_root(monkeypatch, tmp_path):
    """base_dir 不存在时回退 repo 根，行为同当前。"""
    vg.VERIFY_ROOT = Path(tmp_path)
    p = tmp_path / "mod.py"
    p.write_text("top level\n", encoding="utf-8")
    ok, reason, _ = vg.match_verify_rule(
        "file: mod.py contains top level", [], base_dir=tmp_path / "nonexistent-dir")
    assert ok, reason


def test_file_rule_base_dir_missing_but_repo_root_exists(monkeypatch, tmp_path):
    """base_dir 下该路径不存在但 repo 根存在：应命中 repo 根（不误报 missing）。"""
    vg.VERIFY_ROOT = Path(tmp_path)
    task_dir = tmp_path / "task"
    task_dir.mkdir()  # base_dir 存在，但 task_dir/Benchmarking/x 不存在
    p = tmp_path / "Benchmarking" / "index19.md"
    p.parent.mkdir()
    p.write_text("index19 report\n", encoding="utf-8")
    ok, reason, _ = vg.match_verify_rule(
        "file: Benchmarking/index19.md contains index19", [], base_dir=task_dir)
    assert ok, reason


def test_file_rule_base_dir_missing_returns_missing_not_outside(monkeypatch, tmp_path):
    """base_dir 下缺失且 repo 根也缺失：报 verified file missing（非 outside repo）。"""
    vg.VERIFY_ROOT = Path(tmp_path)
    task_dir = tmp_path / "task"
    task_dir.mkdir()
    ok, reason, _ = vg.match_verify_rule(
        "file: artifacts/ghost.md contains foo", [], base_dir=task_dir)
    assert not ok
    assert "verified file missing" in reason


def test_file_rule_strips_wrapping_quotes(monkeypatch, tmp_path):
    """plan.md `contains \"index19\"` 引号是书写习惯，不应按字面量含引号比较。"""
    vg.VERIFY_ROOT = Path(tmp_path)
    p = tmp_path / "report.md"
    p.write_text("index19 report\n", encoding="utf-8")
    ok, reason, _ = vg.match_verify_rule(
        'file: report.md contains "index19"', [])
    assert ok, reason
