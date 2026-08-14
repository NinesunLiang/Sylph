"""test_privacy_gates.py — index25 隐私门禁依赖 TDD（先红后绿）。

覆盖 4 类：
- 读取拦截：Read/Bash-cat/Grep 命中敏感路径或敏感内容 → ASK_USER
- 写入覆盖：Bash sed/tee/redirect/python-open 写敏感/治理路径 → ASK_USER
- 免误伤：普通文件读取/普通写入不拦截
- 护栏：>1MB 文件不做内容扫描
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .checks import _check_sensitive_read, _check_sensitive_write_bash

_SK = "sk-AbCdEf1234567890XyZqwertyuiop"


def _payload(tool: str, **input_kwargs) -> dict:
    return {"tool_name": tool, "tool_input": input_kwargs}


def _write(tmp: Path, name: str, content: str) -> Path:
    p = tmp / name
    p.write_text(content, encoding="utf-8")
    return p


# ── 读取拦截 ───────────────────────────────────────────────────────────

def test_read_tool_blocks_secret_content():
    tmp = Path(tempfile.mkdtemp())
    f = _write(tmp, "api_config.json", json.dumps({"api_key": _SK}))
    r = _check_sensitive_read(_payload("Read", file_path=str(f)))
    assert r and r.startswith("ASK_USER"), r


def test_read_tool_blocks_sensitive_path_no_scan():
    tmp = Path(tempfile.mkdtemp())
    f = _write(tmp, ".env", "EMPTY=1\n")  # 路径命中敏感模式，内容无密钥也应拦
    r = _check_sensitive_read(_payload("Read", file_path=str(f)))
    assert r and r.startswith("ASK_USER"), r


def test_read_tool_allows_clean_file():
    tmp = Path(tempfile.mkdtemp())
    f = _write(tmp, "notes.md", "普通内容，无密钥。\n")
    assert _check_sensitive_read(_payload("Read", file_path=str(f))) is None


def test_read_tool_allows_governance_instructions():
    """index26 修复: 治理文件域（AGENTS.md）是代理指令来源，读取不得拦截（只禁写）。"""
    tmp = Path(tempfile.mkdtemp())
    f = _write(tmp, "AGENTS.md", "治理指令，非凭据。\n")
    assert _check_sensitive_read(_payload("Read", file_path=str(f))) is None


def test_read_tool_allows_hooks_source():
    """index26 修复: .claude/hooks 源码可读（只禁写）。"""
    tmp = Path(tempfile.mkdtemp())
    d = tmp / ".claude" / "hooks"
    d.mkdir(parents=True)
    f = d / "pretool-gate.py"
    f.write_text("print('ok')\n", encoding="utf-8")
    assert _check_sensitive_read(_payload("Read", file_path=str(f))) is None


def test_bash_cat_blocks_secret_content():
    tmp = Path(tempfile.mkdtemp())
    f = _write(tmp, "api_config.json", json.dumps({"api_key": _SK}))
    r = _check_sensitive_read(_payload("Bash", command=f"cat {f}"))
    assert r and r.startswith("ASK_USER"), r


def test_bash_read_allows_clean_file():
    tmp = Path(tempfile.mkdtemp())
    f = _write(tmp, "README.md", "hello\n")
    assert _check_sensitive_read(_payload("Bash", command=f"cat {f}")) is None


def test_read_large_file_skipped_by_size_cap():
    tmp = Path(tempfile.mkdtemp())
    f = tmp / "big.bin"
    f.write_bytes(b"\x00" * (2 * 1024 * 1024) + _SK.encode())  # 2MB，含密钥但超护栏
    assert _check_sensitive_read(_payload("Read", file_path=str(f))) is None


def test_grep_tool_sensitive_path_blocks():
    tmp = Path(tempfile.mkdtemp())
    _write(tmp, "credentials.json", json.dumps({"api_key": _SK}))
    r = _check_sensitive_read(_payload("Grep", pattern="key", path=str(tmp / "credentials.json")))
    assert r and r.startswith("ASK_USER"), r


# ── 写入覆盖（Bash 通道） ──────────────────────────────────────────────

def test_bash_write_sed_sensitive_path():
    r = _check_sensitive_write_bash(_payload("Bash", command="sed -i 's/a/b/' credentials.json"))
    assert r and r.startswith("ASK_USER"), r


def test_bash_write_redirect_sensitive_path():
    r = _check_sensitive_write_bash(_payload("Bash", command="echo new > credentials.json"))
    assert r and r.startswith("ASK_USER"), r


def test_bash_write_python_open_write_mode():
    r = _check_sensitive_write_bash(
        _payload("Bash", command="python3 -c \"open('credentials.json','w').write('x')\""))
    assert r and r.startswith("ASK_USER"), r


def test_bash_write_governance_path():
    r = _check_sensitive_write_bash(
        _payload("Bash", command="sed -i 's/x/y/' .claude/hooks/pretool-gate.py"))
    assert r and r.startswith("ASK_USER"), r


def test_bash_write_clean_target_allowed():
    r = _check_sensitive_write_bash(_payload("Bash", command="cat notes.md > out.txt"))
    assert r is None, r


def test_non_bash_tool_passes_write_gate():
    assert _check_sensitive_write_bash(_payload("Edit", file_path="credentials.json")) is None


def test_rooot_resolution_is_cwd_independent():
    """index27 修复: constants.ROOT 必须解析到仓库根（含 .claude/.git 的祖先），
    与调用 cwd 无关——gate_cli 在任意目录调用时审计仍落盘正确仓库。"""
    import os
    from . import constants as _c
    assert (_c.ROOT / ".claude").is_dir(), f"ROOT 不是仓库根: {_c.ROOT}"
    assert (_c.ROOT / ".git").is_dir() or (_c.ROOT / "AGENTS.md").is_file(), \
        f"ROOT 缺仓库根标志: {_c.ROOT}"
    assert _c.AUDIT == _c.ROOT / ".omc" / "state" / "audit", f"AUDIT 偏离仓库: {_c.AUDIT}"
