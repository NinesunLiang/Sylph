"""stop-user-command-gate 契约测试。

人类裁决 2026-10-24：给用户的命令必须单行、不折行、只调用 .omc/scripts。
先红后绿：这些用例在门禁实现前应全部失败。
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parent / "stop-user-command-gate.py"


def _load():
    spec = importlib.util.spec_from_file_location("stop_user_command_gate", GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def gate():
    return _load()


def _kinds(gate, text):
    return [v["kind"] for v in gate.find_violations(text)]


# ── 应拦截 ──

def test_multiline_bash_block_is_blocked(gate):
    text = "跑这个：\n```bash\nmv a b\nmv c d\n```\n"
    assert "multi_line" in _kinds(gate, text)


def test_absolute_path_is_blocked(gate):
    text = "```bash\nmv /Users/lucas.liang/Desktop/x/.git /Users/lucas.liang/Desktop/x/.git-disabled\n```"
    assert "absolute_path" in _kinds(gate, text)


def test_long_single_command_is_blocked(gate):
    cmd = 'git commit -m "a very long commit message that surely wraps the terminal line"'
    text = f"```bash\n{cmd}\n```"
    assert "too_long" in _kinds(gate, text)


def test_long_inline_command_is_blocked(gate):
    text = "运行 `python3 .claude/scripts/carros_base.py init --task-id demo --steps aaa`"
    assert "too_long" in _kinds(gate, text)


def test_bare_bang_command_is_blocked(gate):
    text = "! mv /Users/lucas.liang/Desktop/a /Users/lucas.liang/Desktop/b"
    assert "absolute_path" in _kinds(gate, text)


# ── 应放行 ──

def test_allowed_script_invocation_passes(gate):
    text = "```bash\nbash .omc/scripts/fix_git.sh\n```"
    assert gate.find_violations(text) == []


def test_allowed_inline_invocation_passes(gate):
    text = "执行 `bash .omc/scripts/fix_git.sh` 即可。"
    assert gate.find_violations(text) == []


def test_short_command_passes(gate):
    text = "```bash\ngit status\n```"
    assert gate.find_violations(text) == []


def test_python_block_is_ignored(gate):
    text = "```python\nimport os\nprint(os.getcwd())\n```"
    assert gate.find_violations(text) == []


def test_plain_text_block_is_ignored(gate):
    text = "```\nsrc/\n  main.py\n```"
    assert gate.find_violations(text) == []


def test_empty_message_passes(gate):
    assert gate.find_violations("") == []


# ── 循环保护与主线 ──

def test_stop_hook_active_never_blocks(gate, monkeypatch, capsys):
    payload = {"stop_hook_active": True,
               "last_assistant_message": "```bash\nmv a b\nmv c d\n```"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    assert gate.main() == 0
    assert capsys.readouterr().out.strip() == ""


def test_main_emits_block_decision(gate, monkeypatch, capsys):
    payload = {"stop_hook_active": False,
               "last_assistant_message": "```bash\nmv a b\nmv c d\n```"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setenv("CARROROS_AUDIT_DIR", "/tmp/carroros-test-audit")
    assert gate.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["decision"] == "block"
    assert ".omc/scripts" in out["reason"]
