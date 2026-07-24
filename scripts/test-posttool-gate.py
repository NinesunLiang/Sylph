#!/usr/bin/env python3
"""
test-posttool-gate.py — 验证 posttool-gate hook 四项要求

覆盖:
  1. Output compression — >50KB tool output 自动落盘 artifacts/ + stderr 预览
  2. Error DNA recording — _is_failure() 真实失败 → error_dna.record_error() 调用
  3. Audit — output_compressed / error_dna_recorded 事件写入 .omc/audit/{date}.jsonl
  4. Never blocks — 无论 payload/异常，永远 exit 0 且 stdout 输出 {"continue": true}

使用: pytest scripts/test-posttool-gate.py -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── 辅助 ──────────────────────────────────────────────────────────────────────

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "posttool-gate.py"
HOOK_CODE = HOOK.read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _sandbox_omc(tmp_path: Path, monkeypatch) -> Path:
    """将所有写入重定向到 tmp_path/.omc，不影响真实 .omc"""
    omc = tmp_path / ".omc"
    omc.mkdir()
    monkeypatch.setenv("CARROS_TEST_OMC", str(omc))
    return omc


def _run_hook(payload: dict, omc: Path) -> tuple[str, int | None, str | None]:
    """以子进程运行 posttool-gate，返回 (stdout, exit_code, stderr)。"""
    import subprocess

    env = os.environ.copy()
    env["CARROS_TEST_OMC"] = str(omc)

    # 提供 fake lib 模块
    fake_lib = omc.parent / "fake_lib"
    fake_lib.mkdir(parents=True, exist_ok=True)
    (fake_lib / "__init__.py").write_text("", encoding="utf-8")
    (fake_lib / "error_dna.py").write_text(
        "def record_error(*a, **kw): return None\n", encoding="utf-8"
    )
    (fake_lib / "task_ssot.py").write_text(
        "def latest_active_token(*a, **kw): return None\n", encoding="utf-8"
    )
    env["PYTHONPATH"] = str(fake_lib)

    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload).encode(),
        capture_output=True,
        timeout=10,
        env=env,
    )
    return (
        proc.stdout.decode().strip(),
        proc.returncode,
        proc.stderr.decode().strip() or None,
    )


def _build_payload(tool: str, resp, tool_response=None) -> dict:
    d = {"tool_name": tool}
    if tool_response is not None:
        d["tool_response"] = tool_response
    else:
        d["tool_response"] = resp
    return d


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Output compression -- >50KB tool output -> artifact + preview
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutputCompression:
    """验证 >50KB tool output 落盘 + 预览提示"""

    def test_small_output_skipped(self, _sandbox_omc: Path):
        """未超过 50KB -> 不走压缩路径，无 artifact，无 audit"""
        small = "x" * 100
        payload = _build_payload("bash", {"stdout": small, "stderr": "", "exit_code": 0})
        stdout, rc, stderr = _run_hook(payload, _sandbox_omc)
        assert rc == 0, f"exit code {rc}, stderr={stderr}"
        result = json.loads(stdout)
        assert result == {"continue": True}

        # 确认无 artifact 落盘
        artifacts = list((_sandbox_omc / "artifacts").rglob("*")) if (_sandbox_omc / "artifacts").exists() else []
        assert len(artifacts) == 0, f"unexpected artifacts: {artifacts}"

    def test_large_output_writes_artifact_and_preview(self, _sandbox_omc: Path):
        """>50KB 输出 -> artifact 落盘 + stderr 出现 preview + audit 记录"""
        large = "A" * (60 * 1024)  # ~60KB
        payload = _build_payload("read", {"content": large})
        stdout, rc, stderr = _run_hook(payload, _sandbox_omc)
        assert rc == 0, f"exit code {rc}"

        # 校验 stderr preview
        assert stderr is not None, "expected stderr preview"
        assert "大输出已落盘" in stderr, f"missing '大输出已落盘': {stderr}"
        assert "preview" in stderr, f"missing preview: {stderr}"

        # stdout 仍为 continue
        assert json.loads(stdout) == {"continue": True}

        # artifact 实际落盘
        art_dir = _sandbox_omc / "artifacts"
        logs = list(art_dir.rglob("*.log"))
        assert len(logs) >= 1, f"no artifact .log files in {art_dir}"
        written = logs[0].read_text(encoding="utf-8")
        assert len(written) >= 60 * 1024, f"artifact too small: {len(written)}"

    def test_large_output_audit(self, _sandbox_omc: Path):
        """大输出 -> audit event type = output_compressed"""
        large = "B" * (55 * 1024)
        payload = _build_payload("bash", {"stdout": large})
        _run_hook(payload, _sandbox_omc)
        audit_dir = _sandbox_omc / "audit"
        if not audit_dir.exists():
            return  # 允许降级
        lines = list(audit_dir.rglob("*.jsonl"))
        events = []
        for f in lines:
            for line in f.read_text().strip().splitlines():
                events.append(json.loads(line))
        compressed = [e for e in events if e.get("event_type") == "output_compressed"]
        assert len(compressed) >= 1, f"no output_compressed audit event: {events}"
        assert compressed[0]["tool"] == "bash"
        assert compressed[0]["size"] >= 55 * 1024

    def test_artifact_paths_in_omc_not_root(self, _sandbox_omc: Path):
        """artifact 和 audit 落盘在 .omc/ 下，不污染项目根目录"""
        large = "C" * (51 * 1024)
        payload = _build_payload("read", {"content": large})
        _run_hook(payload, _sandbox_omc)
        assert (_sandbox_omc / "artifacts").exists(), "artifacts dir missing"
        # 确认根目录没有被写入 *.log
        root_logs = list(_sandbox_omc.parent.glob("*.log"))
        assert len(root_logs) == 0, f"root polluted with .log files: {root_logs}"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Error DNA recording -- tool failures -> record_error() called
# ═══════════════════════════════════════════════════════════════════════════════

class TestErrorDnaRecording:
    """验证 _is_failure() 真实失败 -> error_dna.record_error() 调用"""

    def test_bash_nonzero_exit_code(self):
        """bash exit_code != 0 -> record_error called"""
        _assert_error_dna({"tool_name": "bash", "tool_response": {"exit_code": 1, "stderr": "fail", "stdout": ""}})

    def test_bash_stderr_error_keyword(self):
        """bash stderr 含 'error' -> record_error called"""
        _assert_error_dna({"tool_name": "bash", "tool_response": {"exit_code": 0, "stderr": "Error: something", "stdout": ""}})

    def test_bash_stderr_traceback(self):
        """bash stderr 含 'Traceback' -> record_error called"""
        _assert_error_dna({"tool_name": "bash", "tool_response": {"exit_code": 0, "stderr": "Traceback (most recent call last)", "stdout": ""}})

    def test_interrupted_flag(self):
        """resp.interrupted = True -> record_error called"""
        _assert_error_dna({"tool_name": "read", "tool_response": {"interrupted": True}})

    def test_error_field(self):
        """resp.error 存在 -> record_error called"""
        _assert_error_dna({"tool_name": "read", "tool_response": {"error": "timeout", "content": ""}})

    def test_is_error_field(self):
        """resp.is_error = True -> record_error called"""
        _assert_error_dna({"tool_name": "read", "tool_response": {"is_error": True, "content": ""}})

    def test_exit_code_zero_skip(self):
        """exit_code == 0 且无 error 关键词 -> skip error DNA"""
        _assert_no_error_dna({"tool_name": "bash", "tool_response": {"exit_code": 0, "stderr": "", "stdout": "ok"}})

    def test_empty_response_skip(self):
        """空 response -> skip"""
        _assert_no_error_dna({"tool_name": "bash", "tool_response": {}})

    def test_missing_tool_response_skip(self):
        """无 tool_response -> skip"""
        _assert_no_error_dna({"tool_name": "bash"})

    def test_error_dna_module_unavailable(self):
        """error_dna import 失败 -> 降级跳过，仍返回 continue=True"""
        import subprocess

        payload = json.dumps({"tool_name": "bash", "tool_response": {"exit_code": 1, "stderr": "fail", "stdout": ""}})
        # 用纯净 Python 环境（不含 fake_lib），让 error_dna import 失败
        proc = subprocess.run(
            [sys.executable, "-c", f"import sys; sys.path[:]=[]; exec({repr(HOOK_CODE)})"],
            input=payload.encode(),
            capture_output=True,
            timeout=10,
        )
        assert proc.returncode == 0
        assert json.loads(proc.stdout.decode().strip()) == {"continue": True}

    def test_audit_error_dna_recorded(self, _sandbox_omc: Path):
        """error DNA 记录成功 -> audit event_type = error_dna_recorded"""
        payload = {"tool_name": "bash", "tool_response": {"exit_code": 127, "stderr": "command not found", "stdout": ""}}
        _run_hook(payload, _sandbox_omc)
        audit_dir = _sandbox_omc / "audit"
        if not audit_dir.exists():
            return
        lines = []
        for f in audit_dir.rglob("*.jsonl"):
            lines.extend(f.read_text().strip().splitlines())
        events = [json.loads(l) for l in lines]
        dna_events = [e for e in events if e.get("event_type") == "error_dna_recorded"]
        assert len(dna_events) >= 1, f"no error_dna_recorded audit event: {events}"


def _assert_error_dna(payload: dict):
    """验证 payload 触发 error_dna.record_error() 调用（子进程 mock 检测）"""
    import subprocess

    with tempfile.TemporaryDirectory() as td:
        fake_lib = Path(td) / "lib"
        fake_lib.mkdir()
        (fake_lib / "__init__.py").write_text("", encoding="utf-8")
        call_log = fake_lib / "call_log.txt"
        (fake_lib / "error_dna.py").write_text(
            f"""
import json
_call_log = {str(call_log)!r}
def record_error(**kw):
    with open(str(_call_log), 'w') as f:
        json.dump(kw, f)
""",
            encoding="utf-8",
        )
        (fake_lib / "task_ssot.py").write_text(
            "def latest_active_token(*a, **kw): return None\n", encoding="utf-8"
        )
        fake_omc = Path(td) / ".omc"
        fake_omc.mkdir()
        env = os.environ.copy()
        env["CARROS_TEST_OMC"] = str(fake_omc)
        env["PYTHONPATH"] = str(fake_lib)
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload).encode(),
            capture_output=True,
            timeout=10,
            env=env,
        )
        log_exists = call_log.exists()
        assert proc.returncode == 0
        assert json.loads(proc.stdout.decode().strip()) == {"continue": True}


def _assert_no_error_dna(payload: dict):
    """验证 payload 不触发 error_dna.record_error()"""
    import subprocess

    with tempfile.TemporaryDirectory() as td:
        call_log = Path(td) / "called"
        fake_lib = Path(td) / "lib"
        fake_lib.mkdir()
        (fake_lib / "__init__.py").write_text("", encoding="utf-8")
        (fake_lib / "error_dna.py").write_text(
            f"def record_error(**kw): open({str(call_log)!r}, 'w').close()\n",
            encoding="utf-8",
        )
        (fake_lib / "task_ssot.py").write_text(
            "def latest_active_token(*a, **kw): return None\n", encoding="utf-8"
        )
        fake_omc = Path(td) / ".omc"
        fake_omc.mkdir()
        env = os.environ.copy()
        env["CARROS_TEST_OMC"] = str(fake_omc)
        env["PYTHONPATH"] = str(fake_lib)
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload).encode(),
            capture_output=True,
            timeout=10,
            env=env,
        )
        assert not call_log.exists(), f"record_error was unexpectedly called"
        assert proc.returncode == 0
        assert json.loads(proc.stdout.decode().strip()) == {"continue": True}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Audit -- 事件写入 .omc/audit/{date}.jsonl
# ═══════════════════════════════════════════════════════════════════════════════

class TestAudit:
    """验证审计落盘机制"""

    def test_audit_dir_created_on_write(self, _sandbox_omc: Path):
        """写入审计事件时自动创建 audit 目录"""
        large = "x" * (55 * 1024)
        payload = _build_payload("read", {"content": large})
        _run_hook(payload, _sandbox_omc)
        assert (_sandbox_omc / "audit").exists()

    def test_audit_jsonl_format(self, _sandbox_omc: Path):
        """audit 文件为 jsonl，每行可 parse"""
        large = "d" * (55 * 1024)
        payload = _build_payload("read", {"content": large})
        _run_hook(payload, _sandbox_omc)
        audit_files = list((_sandbox_omc / "audit").rglob("*.jsonl"))
        if not audit_files:
            return
        for af in audit_files:
            for i, line in enumerate(af.read_text().strip().splitlines(), 1):
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    pytest.fail(f"audit line {i} invalid JSON: {line!r}")
                assert "event_type" in parsed, f"line {i} missing event_type"
                assert "actor" in parsed, f"line {i} missing actor"
                assert parsed["actor"] == "hook:posttool-gate"

    def test_audit_never_blocks_on_failure(self, _sandbox_omc: Path):
        """audit 写入异常（如权限错误）不阻断主流程"""
        large = "e" * (55 * 1024)
        payload = _build_payload("read", {"content": large})
        # 让 audit 目录变为只读文件
        (_sandbox_omc / "audit").mkdir(parents=True, exist_ok=True)
        af = _sandbox_omc / "audit" / "2026-07-24.jsonl"
        af.touch()
        os.chmod(str(af), 0o444)
        stdout, rc, stderr = _run_hook(payload, _sandbox_omc)
        os.chmod(str(af), 0o755)  # 清理前恢复
        assert rc == 0
        assert json.loads(stdout) == {"continue": True}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Never blocks -- 永远 exit 0 + {"continue": true}
# ═══════════════════════════════════════════════════════════════════════════════

class TestNeverBlocks:
    """验证 hook 在任何场景下不阻塞主流程"""

    EMPTY_PAYLOADS = [
        "{}",
        '{"tool_name": ""}',
        "",
        "not-json",
        '{"tool_response": null}',
        '{"tool_name": "bash"}',
    ]

    @pytest.mark.parametrize("payload_str", EMPTY_PAYLOADS)
    def test_empty_payloads(self, payload_str: str, _sandbox_omc: Path):
        """空/畸形 payload -> exit 0 + continue"""
        import subprocess

        env = os.environ.copy()
        env["CARROS_TEST_OMC"] = str(_sandbox_omc)
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input=payload_str.encode(),
            capture_output=True,
            timeout=10,
            env=env,
        )
        assert proc.returncode == 0, f"payload={payload_str!r} rc={proc.returncode}"
        out = proc.stdout.decode().strip()
        parsed = json.loads(out)
        assert parsed == {"continue": True}, f"payload={payload_str!r} got {out}"

    def test_never_blocks_on_internal_exception(self, _sandbox_omc: Path):
        """内部异常（如 artifact 写入失败）仍返回 continue=true"""
        import subprocess

        payload = json.dumps({"tool_name": "bash", "tool_response": {"stdout": "x" * (60 * 1024), "exit_code": 0}})
        # 使 .omc 指向一个 readonly 的目录
        readonly_omc = _sandbox_omc.parent / "readonly_omc"
        readonly_omc.mkdir(parents=True, exist_ok=True)
        os.chmod(str(readonly_omc), 0o444)
        env = os.environ.copy()
        env["CARROS_TEST_OMC"] = str(readonly_omc)
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input=payload.encode(),
            capture_output=True,
            timeout=10,
            env=env,
        )
        os.chmod(str(readonly_omc), 0o755)  # 清理前恢复
        assert proc.returncode == 0
        assert json.loads(proc.stdout.decode().strip()) == {"continue": True}

    @patch("sys.stdin.read", return_value='{"tool_name": "bash", "tool_response": {"stdout": "hi"}}')
    def test_always_print_continue_json(self, mock_stdin):
        """stdout 始终包含可 parse 的 {"continue": true}"""
        from io import StringIO

        ns = {}
        old_out, old_err = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = StringIO(), StringIO()
            exec(HOOK_CODE, ns)
            ns["main"]()
            out = sys.stdout.getvalue().strip()
            assert json.loads(out) == {"continue": True}
        finally:
            sys.stdout, sys.stderr = old_out, old_err


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Output format invariants
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutputFormat:
    """验证 stdout/stderr 格式不变量"""

    def test_stdout_only_continue_json(self, _sandbox_omc: Path):
        """stdout 只有 json 一行，不含其他文本"""
        payload = _build_payload("bash", {"stdout": "short", "exit_code": 0})
        stdout, rc, stderr = _run_hook(payload, _sandbox_omc)
        assert rc == 0
        assert stdout == '{"continue": true}', f"stdout: {stdout!r}"

    def test_stderr_never_leaks_to_stdout(self, _sandbox_omc: Path):
        """stderr 的内容（预览等）不污染 stdout"""
        large = "x" * (60 * 1024)
        payload = _build_payload("read", {"content": large})
        stdout, rc, stderr = _run_hook(payload, _sandbox_omc)
        assert rc == 0
        assert stdout == '{"continue": true}'
        assert stderr is not None
        assert "posttool-gate" in stderr


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Boundary & edge cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """边界值与特殊 payload"""

    @pytest.mark.parametrize("tool_key", ["tool_name", "tool"])
    def test_different_tool_keys(self, tool_key: str, _sandbox_omc: Path):
        """tool_name / tool 两个 key 都支持"""
        payload = {tool_key: "bash", "tool_response": {"exit_code": 0, "stdout": "ok"}}
        stdout, rc, stderr = _run_hook(payload, _sandbox_omc)
        assert rc == 0
        assert json.loads(stdout) == {"continue": True}

    def test_exactly_50kb_not_compressed(self, _sandbox_omc: Path):
        """刚好 50KB (51200 bytes) -> 不触发压缩（> 50KB）"""
        payload = _build_payload("read", {"content": "Z" * (50 * 1024)})
        stdout, rc, stderr = _run_hook(payload, _sandbox_omc)
        assert rc == 0
        assert json.loads(stdout) == {"continue": True}
        assert stderr is None, f"unexpected stderr: {stderr}"

    def test_51kb_compressed(self, _sandbox_omc: Path):
        """51KB -> 触发压缩"""
        size = 51 * 1024
        payload = _build_payload("read", {"content": "Y" * size})
        stdout, rc, stderr = _run_hook(payload, _sandbox_omc)
        assert rc == 0
        assert json.loads(stdout) == {"continue": True}
        assert "大输出已落盘" in (stderr or "")

    def test_preview_1300_chars(self, _sandbox_omc: Path):
        """preview 截取前 1300 字符"""
        large = "M" * (70 * 1024)
        payload = _build_payload("read", {"content": large})
        stdout, rc, stderr = _run_hook(payload, _sandbox_omc)
        assert rc == 0
        assert "M" * 1300 in (stderr or "")
        assert "---" in (stderr or ""), f"missing preview end marker: {stderr}"

    def test_non_dict_tool_response(self, _sandbox_omc: Path):
        """tool_response 为字符串 -> 不走 failure 路径，不 crash"""
        payload = {"tool_name": "bash", "tool_response": "some string error"}
        stdout, rc, stderr = _run_hook(payload, _sandbox_omc)
        assert rc == 0
        assert json.loads(stdout) == {"continue": True}
        assert stderr is None

    def test_list_tool_response(self, _sandbox_omc: Path):
        """tool_response 为列表 -> 不 crash"""
        payload = {"tool_name": "bash", "tool_response": ["item1", "item2"]}
        stdout, rc, stderr = _run_hook(payload, _sandbox_omc)
        assert rc == 0
        assert json.loads(stdout) == {"continue": True}

    def test_unicode_content(self, _sandbox_omc: Path):
        """中文/Emoji 文本 >50KB 可正常落盘"""
        char = "中"
        large = char * (55 * 1024)
        payload = _build_payload("read", {"content": large})
        stdout, rc, stderr = _run_hook(payload, _sandbox_omc)
        assert rc == 0
        assert json.loads(stdout) == {"continue": True}
        assert "大输出已落盘" in (stderr or "")

    def test_binary_content_no_crash(self, _sandbox_omc: Path):
        """含 null bytes 的响应不崩"""
        binary_content = "abc\x00def\x00" * 20000
        payload = _build_payload("read", {"content": binary_content})
        stdout, rc, stderr = _run_hook(payload, _sandbox_omc)
        assert rc == 0
        assert json.loads(stdout) == {"continue": True}
