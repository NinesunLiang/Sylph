#!/usr/bin/env python3
"""
test-posttool-bash-audit.py — 测试 posttool-bash-audit.py 的审计、证据、不阻断行为

覆盖:
  1. 常规命令审计 (git commit/push/reset --hard, rm -rf, kill)
  2. 普通命令 → 无审计消息 (ls, echo)
  3. 门禁正确性: warn-only（只有连续构建失败 >=10 次才阻断）
  4. 治理审计追踪: build-fail-streak.json / .harness-evidence/
  5. E4 证据编造检测 (error-dna.jsonl + error-signals.jsonl)
  6. C1 反模式检测和 E5 hard block
  7. 空命令、非 JSON 输入、功能关闭

运行:
  cd scripts/ && python3 test-posttool-bash-audit.py

设计:
  hook 的 state_dir 由 Path(__file__).parent / "../.." / ".omc" / "state" 决定,
  因此测试直接在项目真实 state_dir 下创建文件并清理。
  通过写入 .harness-cache 来模拟配置，测试实际运行的 hook 代码。
"""

import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from io import StringIO

# ── 路径 ──
HOOKS_DIR = Path(__file__).resolve().parent.parent.parent.parent / ".claude" / "hooks"
STATE_DIR = HOOKS_DIR.parent.parent / ".omc" / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = STATE_DIR / ".harness-cache"

sys.path.insert(0, str(HOOKS_DIR))

# ── 由于文件名带连字符，需用 importlib 加载 ──
_HOOK_PATH = HOOKS_DIR / "posttool-bash-audit.py"
_CACHE_BACKUP = None  # 用于 setUp/tearDown 恢复


def _load_hook_module():
    """Load posttool-bash-audit.py via importlib (handles hyphenated filename)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("hook_mod", str(_HOOK_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_input(command="ls -la", exit_code="0", stdout="", stderr=""):
    """构建 CC hook 事件 JSON。"""
    return json.dumps({
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
        },
        "args": {},
    })


def _write_cache(entries: dict):
    """写入 .harness-cache，使得 hc_get / hc_enabled 使用测试配置。"""
    lines = [f"__parsed_count__={len(entries)}"]
    for k, v in entries.items():
        lines.append(f"{k}={v}")
    CACHE_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_hook(test_input_str):
    """执行 posttool-bash-audit.main()，返回 (stdout, stderr, exit_code)。"""
    mod = _load_hook_module()
    with patch("sys.stdin", StringIO(test_input_str)):
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                exit_code = None
                orig_exit = sys.exit
                try:
                    sys.exit = lambda code: (_ for _ in ()).throw(
                        SystemExit(code) if code else SystemExit(1)
                    )
                    try:
                        mod.main()
                    except SystemExit as e:
                        exit_code = e.code if e.code is not None else 0
                    finally:
                        sys.exit = orig_exit
                finally:
                    pass
                return (mock_stdout.getvalue(), mock_stderr.getvalue(), exit_code)


def _parse_stdout(stdout: str):
    """Parse hook JSON from stdout. If empty, returns empty dict."""
    if not stdout.strip():
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {}


class TestPosttoolBashAudit(unittest.TestCase):
    """综合测试: 审计、证据、不阻断、反模式、硬阻断阈值。"""

    _STATE_FILES = set()  # class var for cleanup

    # ── 默认 cache 配置 ──
    DEFAULT_CACHE = {
        "hooks_enabled.posttool_bash_audit": "true",
        "escape_detection": "true",
        "posttool_bash_audit.fail_streak_threshold": "3",
        "posttool_bash_audit.hard_block_threshold": "10",
    }

    # ── Cache 变体 ──
    DISABLED_CACHE = {
        "hooks_enabled.posttool_bash_audit": "false",
        "escape_detection": "true",
    }

    HARD_BLOCK_CACHE = {
        "hooks_enabled.posttool_bash_audit": "true",
        "escape_detection": "true",
        "posttool_bash_audit.fail_streak_threshold": "3",
        "posttool_bash_audit.hard_block_threshold": "10",
    }

    @classmethod
    def setUpClass(cls):
        global _CACHE_BACKUP
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        # 备份已有 cache
        if CACHE_FILE.exists():
            _CACHE_BACKUP = CACHE_FILE.read_text(encoding="utf-8")
        else:
            _CACHE_BACKUP = None

    @classmethod
    def tearDownClass(cls):
        # 清理测试创建的文件（不含备份）
        for fpath in list(cls._STATE_FILES):
            try:
                p = Path(fpath)
                if p.exists():
                    if p.is_dir():
                        import shutil
                        shutil.rmtree(str(p), ignore_errors=True)
                    else:
                        p.unlink(missing_ok=True)
            except Exception:
                pass
        cls._STATE_FILES.clear()

        # 恢复缓存
        if _CACHE_BACKUP is not None:
            CACHE_FILE.write_text(_CACHE_BACKUP, encoding="utf-8")
        elif CACHE_FILE.exists():
            CACHE_FILE.unlink(missing_ok=True)

    def tearDown(self):
        # 清理单个测试创建的文件
        for fpath in list(self.__class__._STATE_FILES):
            try:
                p = Path(fpath)
                if p.exists():
                    if p.is_dir():
                        import shutil
                        shutil.rmtree(str(p), ignore_errors=True)
                    else:
                        p.unlink(missing_ok=True)
            except Exception:
                pass
        self.__class__._STATE_FILES.clear()

    def _run(self, command, exit_code="0", stdout="", stderr="", cache=None):
        """Run hook with given params and cache, return (stdout, stderr, exit_code)."""
        if cache is None:
            cache = self.DEFAULT_CACHE
        _write_cache(cache)
        inp = _make_input(command=command, exit_code=exit_code, stdout=stdout, stderr=stderr)
        return _run_hook(inp)

    def _mkstate(self, relpath, content=""):
        """Create a file in REAL state dir and register for cleanup. Returns Path."""
        fp = STATE_DIR / relpath
        fp.parent.mkdir(parents=True, exist_ok=True)
        if content:
            if isinstance(content, (dict, list)):
                fp.write_text(json.dumps(content), encoding="utf-8")
            elif isinstance(content, list):
                fp.write_text("\n".join(json.dumps(e) if isinstance(e, dict) else e for e in content),
                              encoding="utf-8")
            else:
                fp.write_text(str(content), encoding="utf-8")
        self.__class__._STATE_FILES.add(str(fp))
        return fp

    def _rmstate(self, relpath):
        """Remove a file from state dir."""
        fp = STATE_DIR / relpath
        if fp.exists():
            if fp.is_dir():
                import shutil
                shutil.rmtree(str(fp), ignore_errors=True)
            else:
                fp.unlink(missing_ok=True)
        self.__class__._STATE_FILES.discard(str(fp))

    def _hasstate(self, relpath):
        return (STATE_DIR / relpath).exists()

    def _readstate(self, relpath):
        fp = STATE_DIR / relpath
        if fp.exists():
            return json.loads(fp.read_text(encoding="utf-8"))
        return None

    # ═════════════════════════════════════════
    #  1. 审计命令检测
    # ═════════════════════════════════════════

    def _assert_context_contains(self, stdout, expected_text):
        """Parse stdout JSON and check decoded additionalContext."""
        p = _parse_stdout(stdout)
        self.assertTrue(p, f"Expected JSON stdout, got empty: {stdout!r}")
        ctx = p.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertIn(expected_text, ctx, f"Context missing '{expected_text}': {ctx[:200]}")

    def test_git_commit_audit(self):
        """git commit → context 包含 Git提交 审计消息 + continue=true"""
        stdout, stderr, ec = self._run("git commit -m 'test'")
        self._assert_context_contains(stdout, "Git提交")
        p = _parse_stdout(stdout)
        self.assertTrue(p.get("continue", False))

    def test_git_push_audit(self):
        """git push → context 包含 Git推送"""
        stdout, stderr, ec = self._run("git push origin main")
        self._assert_context_contains(stdout, "Git推送")

    def test_git_reset_hard_audit(self):
        """git reset --hard → context 包含 硬重置"""
        stdout, stderr, ec = self._run("git reset --hard HEAD~1")
        self._assert_context_contains(stdout, "硬重置")

    def test_rm_rf_audit(self):
        """rm -rf → context 包含 递归删除"""
        stdout, stderr, ec = self._run("rm -rf /tmp/foo")
        self._assert_context_contains(stdout, "递归删除")

    def test_kill_audit(self):
        """kill → context 包含 进程信号"""
        stdout, stderr, ec = self._run("kill 1234")
        self._assert_context_contains(stdout, "进程信号")

    def test_pkill_audit(self):
        """pkill → context 包含 进程信号"""
        stdout, stderr, ec = self._run("pkill myprocess")
        self._assert_context_contains(stdout, "进程信号")

    # ═════════════════════════════════════════
    #  2. 普通命令 → 无审计消息
    # ═════════════════════════════════════════

    def test_normal_command_no_audit(self):
        """ls → stdout 为空（output_continue 不打印到 stdout）"""
        stdout, stderr, ec = self._run("ls -la")
        self.assertEqual(stdout.strip(), "",
                         "普通命令应输出空 stdout (output_continue 是 no-op)")

    # ═════════════════════════════════════════
    #  3. 构建失败追踪
    # ═════════════════════════════════════════

    def test_build_fail_recorded(self):
        """go build 失败 → build-fail-streak.json 创建并计数 1"""
        self._rmstate("build-fail-streak.json")
        stdout, stderr, ec = self._run("go build ./...", exit_code="1",
                                       stderr="compile error: undefined: foo")
        self.assertTrue(self._hasstate("build-fail-streak.json"))
        data = self._readstate("build-fail-streak.json")
        self.assertEqual(data["count"], 1)
        self.assertIn("compile error", data.get("signatures", [""])[0])

    def test_build_fail_streak_increments(self):
        """连续构建失败 → streak 递增"""
        self._mkstate("build-fail-streak.json",
                      {"count": 2, "signatures": ["prev error"], "last_command": "go build"})
        stdout, stderr, ec = self._run("go build ./...", exit_code="1",
                                       stderr="new error: type mismatch")
        data = self._readstate("build-fail-streak.json")
        self.assertEqual(data["count"], 3)
        self.assertTrue(
            any("new error" in s for s in data.get("signatures", [])),
            f"Expected 'new error' in signatures: {data.get('signatures', [])}")

    def test_build_success_resets_streak(self):
        """构建成功 → streak 文件被删除"""
        self._mkstate("build-fail-streak.json",
                      {"count": 3, "signatures": ["err"]})
        stdout, stderr, ec = self._run("go build ./...", exit_code="0", stdout="ok")
        self.assertFalse(self._hasstate("build-fail-streak.json"))

    # ═════════════════════════════════════════
    #  4. C1 反模式检测
    # ═════════════════════════════════════════

    def test_c1_anti_pattern_at_threshold(self):
        """连续 3 次失败 → stdout 包含 C1 反模式消息"""
        self._rmstate("build-fail-streak.json")
        self._rmstate("build-fail-gate.json")
        self._mkstate("build-fail-streak.json",
                      {"count": 2, "signatures": ["prev error"], "last_command": "go build"})
        stdout, stderr, ec = self._run("go build ./...", exit_code="1",
                                       stderr="compile error: undefined: X")
        p = _parse_stdout(stdout)
        ctx = p.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertIn("C1", ctx)
        self.assertIn("编译错误盲修", ctx)

    def test_c1_build_fail_gate_created(self):
        """连续 3 次失败 → build-fail-gate.json 被创建"""
        self._rmstate("build-fail-streak.json")
        self._rmstate("build-fail-gate.json")
        self._mkstate("build-fail-streak.json",
                      {"count": 2, "signatures": ["err1"], "last_command": "go build"})
        stdout, stderr, ec = self._run("go build ./...", exit_code="1", stderr="err2")
        self.assertTrue(self._hasstate("build-fail-gate.json"))
        gate = self._readstate("build-fail-gate.json")
        self.assertTrue(gate.get("requires_diagnosis", False))

    # ═════════════════════════════════════════
    #  5. E5 Hard Block
    # ═════════════════════════════════════════

    def test_hard_block_on_excessive_failures(self):
        """连续 10 次失败 → hook_report(block) + sys.exit(2)"""
        self._rmstate("build-fail-streak.json")
        self._rmstate("build-fail-gate.json")
        self._mkstate("build-fail-streak.json",
                      {"count": 9, "signatures": [f"error_{i}" for i in range(5)],
                       "last_command": "go build", "last_output": "build failed"})
        stdout, stderr, ec = self._run(
            "go build ./...", exit_code="1", stderr="another error",
            cache=self.HARD_BLOCK_CACHE)
        self.assertEqual(ec, 2)
        self.assertIn("构建失败", stderr)

    def test_hard_block_not_below_threshold(self):
        """连续 9 次失败 → warn-only, stdout C1, 不阻断"""
        self._rmstate("build-fail-streak.json")
        self._rmstate("build-fail-gate.json")
        self._mkstate("build-fail-streak.json",
                      {"count": 8, "signatures": [f"err_{i}" for i in range(3)],
                       "last_command": "go build"})
        stdout, stderr, ec = self._run(
            "go build ./...", exit_code="1", stderr="still failing",
            cache=self.HARD_BLOCK_CACHE)
        self.assertNotEqual(ec, 2)
        self._assert_context_contains(stdout, "C1")

    # ═════════════════════════════════════════
    #  6. E4 证据编造检测
    # ═════════════════════════════════════════

    def test_e4_evidence_fabrication_detected(self):
        """error-signals gate_operation + echo VERIFIED → E4"""
        self._rmstate("error-signals.jsonl")
        self._rmstate("error-dna.jsonl")
        self._mkstate("error-signals.jsonl",
                      json.dumps({"ts": time.time(),
                                  "error_type": "gate_operation",
                                  "message": "completion-gate blocked"}))
        stdout, stderr, ec = self._run("echo VERIFIED > .completion-evidence")
        self._assert_context_contains(stdout, "E4")
        self._assert_context_contains(stdout, "证据编造")

    def test_e4_no_false_positive_with_build_cmd(self):
        """有编译命令记录 → 不触发 E4"""
        self._rmstate("error-signals.jsonl")
        self._rmstate("error-dna.jsonl")
        self._mkstate("error-signals.jsonl", [
            {"ts": time.time(), "error_type": "gate_operation",
             "message": "completion-gate blocked"},
            {"ts": time.time(), "error_type": "build", "cmd": "go build ./..."},
        ])
        stdout, stderr, ec = self._run("echo VERIFIED > .completion-evidence")
        p = _parse_stdout(stdout)
        ctx = p.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertNotIn("E4", ctx)

    def test_e4_no_false_positive_no_gate_block(self):
        """无 gate block → 不触发 E4"""
        self._rmstate("error-signals.jsonl")
        self._rmstate("error-dna.jsonl")
        self._mkstate("error-signals.jsonl",
                      json.dumps({"ts": time.time(), "error_type": "lint",
                                  "message": "formatting fix"}))
        stdout, stderr, ec = self._run("echo VERIFIED > .completion-evidence")
        p = _parse_stdout(stdout)
        ctx = p.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertNotIn("E4", ctx)

    def test_e4_no_false_positive_no_evidence_write_cmd(self):
        """当前命令不写入证据 → 不触发 E4"""
        self._rmstate("error-signals.jsonl")
        self._rmstate("error-dna.jsonl")
        self._mkstate("error-signals.jsonl",
                      json.dumps({"ts": time.time(),
                                  "error_type": "gate_operation",
                                  "message": "completion-gate blocked"}))
        stdout, stderr, ec = self._run("ls -la")
        self.assertEqual(stdout.strip(), "", "无审计消息时应输出空 stdout")

    # ═════════════════════════════════════════
    #  7. 空命令 / 非JSON / 功能关闭
    # ═════════════════════════════════════════

    def test_empty_command_noop(self):
        """空命令 → stdout 为空"""
        stdout, stderr, ec = self._run("")
        self.assertEqual(stdout.strip(), "")

    def test_non_json_input_noop(self):
        """非 JSON 输入 → output_continue (no-op), 不崩"""
        mod = _load_hook_module()
        with patch("sys.stdin", StringIO("not json at all")):
            with patch("sys.stderr", new_callable=StringIO):
                with patch("sys.stdout", new_callable=StringIO) as mout:
                    try:
                        try:
                            mod.main()
                        except SystemExit:
                            pass
                    finally:
                        pass
                    self.assertEqual(mout.getvalue().strip(), "")

    def test_hook_disabled_noop(self):
        """功能关闭 (hooks_enabled=false) → stdout 为空"""
        stdout, stderr, ec = self._run(
            "git commit -m 'test'", cache=self.DISABLED_CACHE)
        self.assertEqual(stdout.strip(), "")

    # ═════════════════════════════════════════
    #  8. Harness Evidence Capture
    # ═════════════════════════════════════════

    def _clear_evidence(self):
        self._rmstate(".harness-evidence")

    def test_harness_evidence_captured_on_pytest(self):
        """pytest 成功 → .harness-evidence/ 写入证据文件"""
        self._clear_evidence()
        stdout, stderr, ec = self._run("pytest tests/", exit_code="0",
                                       stdout="4 passed in 0.12s")
        ev_dir = STATE_DIR / ".harness-evidence"
        self.__class__._STATE_FILES.add(str(ev_dir))
        ev_files = list(ev_dir.glob("*.json"))
        self.assertTrue(len(ev_files) >= 1)
        ev = json.loads(ev_files[0].read_text(encoding="utf-8"))
        self.assertEqual(ev.get("source"), "harness")
        self.assertEqual(ev.get("exit_code"), 0)
        self.assertIn("4 passed", ev.get("stdout", ""))

    def test_harness_evidence_captured_on_go_test(self):
        """go test 成功 → .harness-evidence/ 写入"""
        self._clear_evidence()
        stdout, stderr, ec = self._run("go test ./...", exit_code="0",
                                       stdout="ok  github.com/carror-os/core")
        ev_dir = STATE_DIR / ".harness-evidence"
        self.__class__._STATE_FILES.add(str(ev_dir))
        ev_files = list(ev_dir.glob("*.json"))
        self.assertTrue(len(ev_files) >= 1)

    def test_harness_evidence_not_captured_on_fail(self):
        """pytest 失败 → 不写入"""
        self._clear_evidence()
        stdout, stderr, ec = self._run("pytest tests/", exit_code="1",
                                       stderr="FAILED test_foo")
        ev_dir = STATE_DIR / ".harness-evidence"
        self.__class__._STATE_FILES.add(str(ev_dir))
        self.assertEqual(len(list(ev_dir.glob("*.json"))), 0)

    def test_harness_evidence_not_captured_non_verify(self):
        """ls → 不写入"""
        self._clear_evidence()
        stdout, stderr, ec = self._run("ls -la")
        ev_dir = STATE_DIR / ".harness-evidence"
        self.__class__._STATE_FILES.add(str(ev_dir))
        self.assertEqual(len(list(ev_dir.glob("*.json"))), 0)

    # ═════════════════════════════════════════
    #  9. 审计消息 always continue=true
    # ═════════════════════════════════════════

    def test_always_continue_with_audit(self):
        """git commit / rm -rf / kill → continue=True"""
        for cmd in [
            "git commit -m 'test'",
            "git push origin main",
            "git reset --hard HEAD",
            "rm -rf /tmp/foo",
            "kill -9 1234",
        ]:
            with self.subTest(cmd=cmd):
                stdout, stderr, ec = self._run(cmd)
                p = _parse_stdout(stdout)
                if not p:
                    self.fail(f"'{cmd}': empty stdout, expected audit JSON")
                self.assertTrue(p.get("continue", True))

    # ═════════════════════════════════════════
    #  10. E3 子 agent 上下文规避
    # ═════════════════════════════════════════

    def test_e3_subagent_context_evasion_detected(self):
        """context-guard block + task_create → E3"""
        self._rmstate("error-signals.jsonl")
        self._rmstate("error-dna.jsonl")
        self._mkstate("error-signals.jsonl",
                      json.dumps({"ts": time.time(),
                                  "message": "context guard triggered",
                                  "error_type": "context", "cmd": "guard check"}))
        stdout, stderr, ec = self._run("task_create run_tests -- refine pipeline")
        self._assert_context_contains(stdout, "E3")
        self._assert_context_contains(stdout, "上下文规避")

    def test_e3_no_false_positive_no_context_block(self):
        """无 context-guard → 不触发 E3"""
        self._rmstate("error-signals.jsonl")
        self._rmstate("error-dna.jsonl")
        self._mkstate("error-signals.jsonl",
                      json.dumps({"ts": time.time(), "error_type": "lint",
                                  "message": "style fix"}))
        stdout, stderr, ec = self._run("task_create run_tests")
        p = _parse_stdout(stdout)
        ctx = p.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertNotIn("E3", ctx)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPosttoolBashAudit)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
