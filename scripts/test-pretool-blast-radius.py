#!/usr/bin/env python3
"""
test-pretool-blast-radius.py — 单元测试套件

测试范围：pretool-blast-radius.py（DG-100 破坏性命令拦截 hook）
测试策略：通过 mock 替换 harness_lib，直接调用 main() 检查 stdout/stderr/exit_code

用法：
    python3 scripts/test-pretool-blast-radius.py

    # 在 Carror OS 内：
    bash source/harness/python-path.sh scripts/test-pretool-blast-radius.py
"""

import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# ─── 路径 ─────────────────────────────────────────────────────────────────────
HOOK_PATH = (
    Path(__file__).resolve().parent.parent
    / ".claude" / "hooks" / "pretool-blast-radius.py"
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestBlastRadius(unittest.TestCase):
    """pretool-blast-radius.py 拦截逻辑验证。

    覆盖三类判定：
      - P0 硬阻断（exit 2, continue=False）
      - P3 警告  （exit 0, continue=True, stderr 含 ⚠️）
      - 放行    （exit 0, continue=True, 无 stderr）
    """

    maxDiff = None

    # ── Helper ────────────────────────────────────────────────────────────

    def _run(self, command):
        """静默运行被测试 hook，返回 (exit_code, stdout_json, stderr_text)。"""
        # 通过子进程调用，真实 import harness_lib。
        # Mock 通过环境变量控制 hook 行为（我们只在需要时设变量）。
        env = {**os.environ, "HC_BLAST_RADIUS_ENABLED": "true"}
        payload = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": command},
        })
        proc = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr

    # ── P0 硬阻断判定 ─────────────────────────────────────────────────────

    def test_hard_block_git_checkout_dot(self):
        """git checkout . → hard block, continue=False"""
        rc, out, err = self._run("git checkout .")
        self.assertEqual(rc, 2, f"expected exit 2, got {rc}")
        data = json.loads(out)
        self.assertFalse(data["continue"])
        self.assertIn("DG-100", data["reason"])
        self.assertIn("硬阻断", err)

    def test_hard_block_git_checkout_double_dash_dot(self):
        """git checkout -- . → hard block"""
        rc, out, err = self._run("git checkout -- .")
        self.assertEqual(rc, 2)
        data = json.loads(out)
        self.assertFalse(data["continue"])
        self.assertIn("DG-100", data["reason"])

    def test_hard_block_git_checkout_head_dot(self):
        """git checkout HEAD . → hard block"""
        rc, out, err = self._run("git checkout HEAD .")
        self.assertEqual(rc, 2)
        data = json.loads(out)
        self.assertFalse(data["continue"])
        self.assertIn("DG-100", data["reason"])

    def test_hard_block_git_checkout_head_double_dash_dot(self):
        """git checkout HEAD -- . → hard block"""
        rc, out, err = self._run("git checkout HEAD -- .")
        self.assertEqual(rc, 2)
        data = json.loads(out)
        self.assertFalse(data["continue"])
        self.assertIn("DG-100", data["reason"])

    def test_hard_block_checkout_dot_with_pipe(self):
        """git checkout -- . | something → hard block"""
        rc, out, err = self._run("git checkout -- . | head")
        self.assertEqual(rc, 2)
        data = json.loads(out)
        self.assertFalse(data["continue"])
        self.assertIn("DG-100", data["reason"])

    def test_hard_block_checkout_dot_with_semicolon(self):
        """git checkout .; echo done → hard block"""
        rc, out, err = self._run("git checkout .; echo done")
        self.assertEqual(rc, 2)
        data = json.loads(out)
        self.assertFalse(data["continue"])
        self.assertIn("DG-100", data["reason"])

    def test_hard_block_checkout_dot_with_and(self):
        """git checkout . && echo done → hard block"""
        rc, out, err = self._run("git checkout . && echo done")
        self.assertEqual(rc, 2)
        data = json.loads(out)
        self.assertFalse(data["continue"])

    def test_hard_block_reset_hard(self):
        """git reset --hard → exit 2, continue=True (design: signals block but doesn't halt)"""
        rc, out, err = self._run("git reset --hard")
        self.assertEqual(rc, 2)
        data = json.loads(out)
        self.assertTrue(data["continue"], "git reset --hard continue=True per hook design")
        self.assertIn("git reset", data["reason"])

    def test_hard_block_reset_hard_head(self):
        """git reset --hard HEAD → exit 2, continue=True"""
        rc, out, err = self._run("git reset --hard HEAD")
        self.assertEqual(rc, 2)
        data = json.loads(out)
        self.assertTrue(data["continue"], "git reset --hard continue=True per hook design")
        self.assertIn("git reset", data["reason"])

    # ── P3 警告判定 ───────────────────────────────────────────────────────

    def test_warn_git_checkout_double_dash_no_file(self):
        """git checkout -- (no path) → warn only"""
        rc, out, err = self._run("git checkout --")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertIn("⚠️", err)
        self.assertIn("未指定具体文件", err)

    def test_warn_git_checkout_double_dash_space_only(self):
        """git checkout --  (trailing space) → warn"""
        rc, out, err = self._run("git checkout -- ")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertIn("⚠️", err)

    def test_warn_git_add_all(self):
        """git add -A → warn"""
        rc, out, err = self._run("git add -A")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertIn("⚠️", err)
        self.assertIn("暂存所有文件", err)

    def test_warn_git_add_dot(self):
        """git add . → warn"""
        rc, out, err = self._run("git add .")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertIn("⚠️", err)

    def test_warn_package_release_sh(self):
        """package-release.sh → 打包提醒"""
        rc, out, err = self._run("bash scripts/package-release.sh")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertIn("📦", err)
        self.assertIn("audit-hooks", err)

    # ── 放行判定（安全命令）───────────────────────────────────────────────

    def test_safe_ls(self):
        """ls → pass"""
        rc, out, err = self._run("ls -la")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertEqual(err.strip(), "")

    def test_safe_git_status(self):
        """git status → pass"""
        rc, out, err = self._run("git status")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertEqual(err.strip(), "")

    def test_safe_git_checkout_specific_file(self):
        """git checkout -- src/main.py → pass (specific path)"""
        rc, out, err = self._run("git checkout -- src/main.py")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertEqual(err.strip(), "")

    def test_safe_git_checkout_head_specific_file(self):
        """git checkout HEAD -- README.md → pass"""
        rc, out, err = self._run("git checkout HEAD -- README.md")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertEqual(err.strip(), "")

    def test_safe_rm_specific_file(self):
        """rm file.txt → pass"""
        rc, out, err = self._run("rm file.txt")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertEqual(err.strip(), "")

    def test_safe_python_script(self):
        """python3 script.py → pass"""
        rc, out, err = self._run("python3 scripts/build.py")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertEqual(err.strip(), "")

    def test_safe_git_add_specific_file(self):
        """git add src/main.py → pass (not bulk)"""
        rc, out, err = self._run("git add src/main.py")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertEqual(err.strip(), "")

    def test_safe_git_diff(self):
        """git diff → pass"""
        rc, out, err = self._run("git diff")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertEqual(err.strip(), "")

    def test_safe_empty_command(self):
        """空/缺失命令 → pass"""
        rc, out, err = self._run("")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])

    # ── 边界值 & 正则绕过 ────────────────────────────────────────────────

    def test_hard_block_checkout_dot_subdir(self):
        """git checkout . 即使在子目录中也要阻断"""
        rc, out, err = self._run("cd src && git checkout .")
        self.assertEqual(rc, 2)
        data = json.loads(out)
        self.assertFalse(data["continue"])

    def test_safe_git_checkout_not_dot(self):
        """git checkout (no dot, no --) → pass"""
        rc, out, err = self._run("git checkout feature-branch")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertEqual(err.strip(), "")

    def test_warn_git_add_all_long(self):
        """git add --all → warn"""
        rc, out, err = self._run("git add --all")
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertTrue(data["continue"])
        self.assertIn("⚠️", err)


# ─── 入口：支持 unittest 和直接运行 ──────────────────────────────────────────

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBlastRadius)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
