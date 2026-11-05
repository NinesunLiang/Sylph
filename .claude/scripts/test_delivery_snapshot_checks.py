"""Delivery checks must inspect the version actually committed or pushed."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
import subprocess

import pytest

SCRIPTS = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True).stdout


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "Delivery Test")
    (tmp_path / "app.py").write_text("value = 1\n")
    git(tmp_path, "add", "app.py")
    git(tmp_path, "commit", "-qm", "baseline")
    git(tmp_path, "branch", "delivery-baseline")
    return tmp_path


def test_staged_syntax_uses_index(repo, monkeypatch):
    pc = load("pre_commit_check")
    monkeypatch.setattr(pc, "ROOT", repo)
    (repo / "app.py").write_text("def broken(:\n")
    git(repo, "add", "app.py")
    (repo / "app.py").write_text("value = 2\n")
    assert pc.run(staged_only=True) == 1


def test_valid_index_ignores_broken_worktree(repo, monkeypatch):
    pc = load("pre_commit_check")
    monkeypatch.setattr(pc, "ROOT", repo)
    (repo / "app.py").write_text("value = 2\n")
    git(repo, "add", "app.py")
    (repo / "app.py").write_text("def broken(:\n")
    assert pc.run(staged_only=True) == 0


def test_deletion_only_is_a_real_commit(repo, monkeypatch):
    pc = load("pre_commit_check")
    monkeypatch.setattr(pc, "ROOT", repo)
    git(repo, "rm", "app.py")
    assert pc.run(staged_only=True) == 0


def test_staged_unicode_space_path(repo, monkeypatch):
    pc = load("pre_commit_check")
    monkeypatch.setattr(pc, "ROOT", repo)
    name = "含 空格.py"
    (repo / name).write_text("def broken(:\n")
    git(repo, "add", name)
    assert name in pc.changed_files(True)
    assert pc.run(staged_only=True) == 1


def test_git_failure_does_not_claim_no_changes(tmp_path, monkeypatch):
    pc = load("pre_commit_check")
    monkeypatch.setattr(pc, "ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="git"):
        pc.changed_files(True)


def test_push_scans_secret_removed_in_later_commit(repo, monkeypatch, capsys):
    pp = load("pre_push_check")
    monkeypatch.setattr(pp, "ROOT", repo)
    monkeypatch.setattr(pp, "_baseline", lambda: "delivery-baseline")
    monkeypatch.setattr(pp, "_secret_patterns", lambda: [re.compile("DEMO_CREDENTIAL")])
    (repo / "temporary.py").write_text('credential = "DEMO_CREDENTIAL"\n')
    git(repo, "add", "temporary.py")
    git(repo, "commit", "-qm", "add temporary fixture")
    git(repo, "rm", "temporary.py")
    git(repo, "commit", "-qm", "remove fixture")
    assert pp.run() == 1
    output = capsys.readouterr().out
    assert "temporary.py" in output
    assert "DEMO_CREDENTIAL" not in output


def test_push_does_not_ignore_committed_secret_hidden_by_worktree(repo, monkeypatch):
    pp = load("pre_push_check")
    monkeypatch.setattr(pp, "ROOT", repo)
    monkeypatch.setattr(pp, "_baseline", lambda: "delivery-baseline")
    monkeypatch.setattr(pp, "_secret_patterns", lambda: [re.compile("DEMO_CREDENTIAL")])
    (repo / "app.py").write_text('credential = "DEMO_CREDENTIAL"\n')
    git(repo, "add", "app.py")
    git(repo, "commit", "-qm", "change fixture")
    (repo / "app.py").write_text("value = 3\n")
    assert pp.run() == 1
