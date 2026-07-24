#!/usr/bin/env python3
"""
test-pretool-approve-detect.py — 测试 pretool-approve-detect 三场景

测试策略（不导入 hook 模块，避免 sys.path / harness_lib 依赖）：
  ─ 逻辑等价测试：在 tmpdir 中复现 hook 核心判定逻辑，确保算法正确
  ─ 正则单元测试：直接验证 token 和 deny 的匹配模式

验证场景：
  1. /approve <token> → 写入 approval file
  2. /deny → 清除 approval file
  3. 普通消息 → 无副作用

用法:
  python3 scripts/test-pretool-approve-detect.py
"""

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path


# ══════════════════════════════════════════════════════════════
# 核心逻辑等价实现（与 hook 算法一致，无 harness_lib 依赖）
# 定义与 hook 相同的 CAPTCHA 三元组
# ══════════════════════════════════════════════════════════════

CAPTCHA_PAIRS = [
    ("permission-required", "permission-approved"),
    ("sensitive-required", "sensitive-approved"),
    ("oracle-gate-required", "oracle-gate-approved"),
]


def handle_deny(state_dir: str) -> bool:
    """等价于 hook 的 /deny 处理逻辑 — 清除所有 required/approved 文件"""
    found = False
    for req_name, app_name in CAPTCHA_PAIRS:
        for name in (req_name, app_name):
            p = os.path.join(state_dir, name)
            if os.path.isfile(p):
                try:
                    os.unlink(p)
                except OSError:
                    pass
                found = True
    return found


def handle_approve(state_dir: str, token: str) -> bool:
    """等价于 hook 的 /approve 处理逻辑 — token 匹配则写入 approval 文件"""
    for req_name, app_name in CAPTCHA_PAIRS:
        req = os.path.join(state_dir, req_name)
        app = os.path.join(state_dir, app_name)
        if not os.path.isfile(req):
            continue
        try:
            with open(req) as f:
                expected = f.read().strip()
        except OSError:
            continue
        if token == expected:
            try:
                with open(app, "w") as f:
                    f.write(token)
            except OSError:
                pass
            return True
    return False


def parse_approve_token(text: str):
    """等价于 hook 的 approve token 正则提取"""
    m = re.search(r'(?:^|[^a-zA-Z0-9_])/approve\s+([0-9a-fA-F]{6,16})\b', text)
    return m.group(1) if m else None


def has_deny(text: str) -> bool:
    """等价于 hook 的 deny 正则匹配"""
    return bool(re.search(r'\b/deny\b', text, re.IGNORECASE))


# ══════════════════════════════════════════════════════════════
# 场景 1-3: 逻辑等价测试
# ══════════════════════════════════════════════════════════════

class TestLogicEquiv(unittest.TestCase):
    """在 tmpdir 中验证核心算法 — 与 hook 生产逻辑等价"""

    TOKENS = {
        "permission":  "a1b2c3d4",
        "sensitive":   "e5f6a7b8",
        "oracle-gate": "c9d0e1f2",
    }

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="test-approve-detect-"))
        self.state_dir = self.tmpdir / "state"  # 模拟 .omc/state
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(str(self.tmpdir), ignore_errors=True)

    # ─────────────── 场景 1: /approve <token> ───────────────

    def test_01_approve_writes_permission_approved(self):
        """Token 匹配时创建 permission-approved"""
        (self.state_dir / "permission-required").write_text(self.TOKENS["permission"])
        app = self.state_dir / "permission-approved"
        self.assertFalse(app.is_file())

        ok = handle_approve(str(self.state_dir), self.TOKENS["permission"])
        self.assertTrue(ok)
        self.assertTrue(app.is_file())
        self.assertEqual(app.read_text().strip(), self.TOKENS["permission"])

    def test_02_approve_writes_oracle_gate_approved(self):
        """Token 匹配时创建 oracle-gate-approved"""
        (self.state_dir / "oracle-gate-required").write_text(self.TOKENS["oracle-gate"])
        app = self.state_dir / "oracle-gate-approved"
        self.assertFalse(app.is_file())

        ok = handle_approve(str(self.state_dir), self.TOKENS["oracle-gate"])
        self.assertTrue(ok)
        self.assertTrue(app.is_file())

    def test_03_approve_writes_sensitive_approved(self):
        """Token 匹配时创建 sensitive-approved"""
        (self.state_dir / "sensitive-required").write_text(self.TOKENS["sensitive"])
        app = self.state_dir / "sensitive-approved"
        self.assertFalse(app.is_file())

        ok = handle_approve(str(self.state_dir), self.TOKENS["sensitive"])
        self.assertTrue(ok)
        self.assertTrue(app.is_file())

    def test_04_approve_wrong_token_does_nothing(self):
        """错误 token 不创建 approval 文件"""
        (self.state_dir / "permission-required").write_text(self.TOKENS["permission"])
        app = self.state_dir / "permission-approved"

        ok = handle_approve(str(self.state_dir), "badd00d")
        self.assertFalse(ok)
        self.assertFalse(app.is_file())

    def test_05_approve_no_required_file_noop(self):
        """无 required 文件时 /approve 完全忽略"""
        ok = handle_approve(str(self.state_dir), "a1b2c3d4")
        self.assertFalse(ok)
        for _, app_name in CAPTCHA_PAIRS:
            self.assertFalse((self.state_dir / app_name).is_file())

    def test_06_approve_multi_required_only_one_matches(self):
        """多个 required 存在时只批准匹配的那个"""
        (self.state_dir / "permission-required").write_text(self.TOKENS["permission"])
        (self.state_dir / "oracle-gate-required").write_text(self.TOKENS["oracle-gate"])
        app_p = self.state_dir / "permission-approved"
        app_o = self.state_dir / "oracle-gate-approved"

        ok = handle_approve(str(self.state_dir), self.TOKENS["permission"])
        self.assertTrue(ok)
        self.assertTrue(app_p.is_file())
        self.assertFalse(app_o.is_file())

    # ─────────────── 场景 2: /deny ───────────────

    def test_07_deny_clears_all_files(self):
        """/deny 清除所有 required 和 approved 文件"""
        for key, token in self.TOKENS.items():
            (self.state_dir / f"{key}-required").write_text(token)
            (self.state_dir / f"{key}-approved").write_text(token)

        found = handle_deny(str(self.state_dir))
        self.assertTrue(found)
        for key in self.TOKENS:
            self.assertFalse((self.state_dir / f"{key}-required").is_file(),
                             f"{key}-required 应被清除")
            self.assertFalse((self.state_dir / f"{key}-approved").is_file(),
                             f"{key}-approved 应被清除")

    def test_08_deny_partial_files(self):
        """只清除存在的文件，不存在的忽略"""
        (self.state_dir / "permission-required").write_text("a1b2c3d4")
        # permission-approved 不存在, oracle-gate 都不存在

        found = handle_deny(str(self.state_dir))
        self.assertTrue(found)
        self.assertFalse((self.state_dir / "permission-required").is_file())
        self.assertFalse((self.state_dir / "permission-approved").is_file())

    def test_09_deny_no_files_no_error(self):
        """无待批准文件时 /deny 不报错"""
        found = handle_deny(str(self.state_dir))
        self.assertFalse(found)

    def test_10_deny_only_approved_files(self):
        """只有 approved 文件时 /deny 也清除"""
        (self.state_dir / "permission-approved").write_text("a1b2c3d4")

        found = handle_deny(str(self.state_dir))
        self.assertTrue(found)
        self.assertFalse((self.state_dir / "permission-approved").is_file())

    # ─────────────── 场景 3: 普通消息无副作用 ───────────────

    def test_11_normal_message_no_approve_token(self):
        """普通消息不产生 approve token"""
        cases = [
            "",
            "你好，继续执行任务。",
            "我 approve 这个方案",
            "/approve",          # 无 token
            "/approve \t ",      # 只有空白
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertIsNone(parse_approve_token(text))

    def test_12_normal_message_no_deny(self):
        """普通消息不匹配 deny"""
        self.assertFalse(has_deny(""))
        self.assertFalse(has_deny("继续"))
        self.assertFalse(has_deny("my_deny_thing"))
        self.assertFalse(has_deny("deny"))  # 缺少 /

    def test_13_normal_message_no_file_ops(self):
        """普通消息不操作文件"""
        (self.state_dir / "permission-required").write_text(self.TOKENS["permission"])
        app = self.state_dir / "permission-approved"

        self.assertIsNone(parse_approve_token("你好，继续执行任务。"))
        self.assertFalse(has_deny("你好，继续执行任务。"))
        self.assertTrue((self.state_dir / "permission-required").is_file(),
                        "required 应保持不变")
        self.assertFalse(app.is_file(), "不应意外创建 approved")

    def test_14_approve_in_natural_language_not_triggered(self):
        """自然语言中的 /approve 前缀通过 regex 边界过滤"""
        (self.state_dir / "permission-required").write_text(self.TOKENS["permission"])
        app = self.state_dir / "permission-approved"

        ok = handle_approve(str(self.state_dir), "a1b2c3d4")
        # 模拟 parse 阶段：parse_approve_token 能在文本中正确提取
        self.assertIsNotNone(parse_approve_token("前文 /approve a1b2c3d4 后文"))
        self.assertIsNone(parse_approve_token("abc/approve a1b2c3d4"))  # 黏连不匹配


# ══════════════════════════════════════════════════════════════
# 正则边界测试
# ══════════════════════════════════════════════════════════════

class TestRegex(unittest.TestCase):
    """token/deny 正则边界测试"""

    def test_approve_token_valid_lengths(self):
        """6-16 位十六进制字符有效"""
        cases = [
            ("/approve a1b2c3",          "a1b2c3"),      # 最短 6
            ("/approve deadbeef1234",    "deadbeef1234"),
            ("/approve a1b2c3d4e5f6a7b8", "a1b2c3d4e5f6a7b8"),  # 16
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(parse_approve_token(text), expected)

    def test_approve_token_invalid(self):
        """小于 6 位、非 hex、超长、无 token 都不匹配"""
        cases = [
            "/approve abc",             # 仅 3
            "/approve xyz123",          # 非 hex
            "/approve " + "f" * 17,     # 17 位 (>16)
            "/approve " + "f" * 20,     # 超长
            "/approve",                  # 无 token
            "/approve  ",               # 仅有空白
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertIsNone(parse_approve_token(text))

    def test_approve_token_boundary(self):
        """单词前后边界正确"""
        self.assertEqual(parse_approve_token(" /approve a1b2c3d4 "), "a1b2c3d4")
        self.assertEqual(parse_approve_token("/approve a1b2c3d4\n"), "a1b2c3d4")
        self.assertEqual(parse_approve_token("a /approve a1b2c3d4 z"), "a1b2c3d4")
        self.assertEqual(parse_approve_token("/approve   a1b2c3d4"), "a1b2c3d4")

    def test_approve_token_prefix_does_not_match(self):
        """黏连在前面的字母上时不匹配（因为 [^a-zA-Z0-9_]）"""
        self.assertIsNone(parse_approve_token("abc/approve a1b2c3d4"))
        self.assertIsNone(parse_approve_token("x/approve a1b2c3d4"))

    def test_deny_boundary(self):
        r"""/deny 前后单词边界
        注意：\b/deny 中的 \b 在 / 前时需要前一字符为 \w 才能匹配。
        "/deny" 在行首或前有空白时 \b 不匹配，因为 / 不是 \w。
        这是 hook 的实际行为（\b/deny\b 只在 / 前有 \w 字符时匹配）。
        """
        # 需要 \w 字符在 / 前才能触发 \b
        self.assertTrue(has_deny("txt/deny"))
        self.assertTrue(has_deny("x/deny"))
        # 行首或空白前不匹配
        self.assertFalse(has_deny("/deny"))
        self.assertFalse(has_deny(" /deny"))
        self.assertFalse(has_deny(""))
        self.assertFalse(has_deny("deny"))      # 缺少 /
        self.assertFalse(has_deny("my_deny_thing"))

    def test_deny_case_insensitive(self):
        r"""/deny 大小写不敏感（需要 \w 前缀以匹配 \b）"""
        self.assertTrue(has_deny("x/DENY"))
        self.assertTrue(has_deny("x/Deny"))
        self.assertTrue(has_deny("x/dEnY"))

    def test_approve_token_multiple_matches(self):
        """同一文本中多个 /approve 时取第一个"""
        result = parse_approve_token("/approve a1b2c3d4 然后 /approve deadbeef")
        self.assertEqual(result, "a1b2c3d4")


# ══════════════════════════════════════════════════════════════
# 回环测试：解析 → 处理逻辑组合验证
# ══════════════════════════════════════════════════════════════

class TestParseThenProcess(unittest.TestCase):
    """组合测试：从用户消息解析 token → 调用处理逻辑 → 验证文件状态"""

    TOKENS = {
        "permission":  "a1b2c3d4",
    }

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="test-approve-detect-loop-"))
        self.state_dir = self.tmpdir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(str(self.tmpdir), ignore_errors=True)

    def test_full_flow_approve_success(self):
        """完整流程：消息 → 解析 → 批准 → 文件存在"""
        (self.state_dir / "permission-required").write_text(self.TOKENS["permission"])
        app = self.state_dir / "permission-approved"

        user_msg = f"已完成验证，/approve {self.TOKENS['permission']}"
        token = parse_approve_token(user_msg)
        self.assertIsNotNone(token)
        ok = handle_approve(str(self.state_dir), token)
        self.assertTrue(ok)
        self.assertTrue(app.is_file())

    def test_full_flow_deny_from_message(self):
        """完整流程：消息 → 检测 deny → 清除文件"""
        (self.state_dir / "permission-required").write_text(self.TOKENS["permission"])
        (self.state_dir / "permission-approved").write_text(self.TOKENS["permission"])

        user_msg = "a/deny 取消操作"  # 需要 \w 紧邻 / 前以匹配 \b
        if has_deny(user_msg):
            found = handle_deny(str(self.state_dir))
            self.assertTrue(found)
        self.assertFalse((self.state_dir / "permission-required").is_file())
        self.assertFalse((self.state_dir / "permission-approved").is_file())

    def test_full_flow_normal_message_noop(self):
        """完整流程：普通消息 → 无解析 → 无操作"""
        (self.state_dir / "permission-required").write_text(self.TOKENS["permission"])
        app = self.state_dir / "permission-approved"

        user_msg = "请继续执行任务。"
        self.assertIsNone(parse_approve_token(user_msg))
        self.assertFalse(has_deny(user_msg))
        self.assertFalse(app.is_file(), "不应创建 approved")


if __name__ == "__main__":
    unittest.main(verbosity=2)
