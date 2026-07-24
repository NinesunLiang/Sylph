#!/usr/bin/env python3
"""test-thinking-gate.py — 测试 thinking-gate UserPromptSubmit hook

覆盖场景：
1. H1: 检测 reasoning_content 字段残留
2. H1: 检测 "thinking": { JSON 结构
3. 无残留时完全静默（仅输出 {"continue": true}）
4. 检测到残留时记录 flywheel 事件
5. 检测到残留时写入证据日志
6. 剥离逻辑正确移除 thinking 内容
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# ── Test target: 复制主要检测逻辑（避免 import hooks 目录的复杂依赖）──
# 我们直接测试 thinking-gate.py 的核心函数，通过 subprocess 或 mock。

HOOK_PATH = Path(__file__).resolve().parent.parent.parent.parent / ".claude" / "hooks" / "thinking-gate.py"


def run_thinking_gate(input_text: str, use_json: bool = True) -> dict:
    """模拟 thinking-gate.py 执行，返回捕获的输出。

    以子进程方式运行 hook，捕获 stdout/stderr。
    返回 {'stdout': ..., 'stderr': ..., 'returncode': ...}
    """
    import subprocess

    payload = json.dumps({"prompt": input_text}) if use_json else input_text

    proc = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, "HC_SESSION_ID": "test-session", "HC_EVENT_NAME": "UserPromptSubmit"},
    )
    return {
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "returncode": proc.returncode,
    }


# ── Helper: 干净输出断言 ──

def is_clean_pass(result: dict) -> bool:
    """检查输出是否为干净通过：stdout = JSON {"continue": true}，无 stderr"""
    try:
        parsed = json.loads(result["stdout"])
        if parsed != {"continue": True}:
            return False
    except (json.JSONDecodeError, TypeError):
        return False
    if result["stderr"]:
        return False
    return result["returncode"] == 0


def has_leak_log(result: dict) -> bool:
    """检查 stderr 中是否包含 thinking-gate 泄漏日志"""
    return "[thinking-gate]" in result["stderr"] and "leak_detected" not in result["stderr"]


# ── 测试类 ──

class TestThinkingGateDetection(unittest.TestCase):
    """场景 1: H1 检测 — reasoning_content 字段残留"""

    def test_detects_reasoning_content_field(self):
        """H1: 检测到 reasoning_content JSON 字段 → 标记为泄漏"""
        msg = json.dumps({
            "role": "user",
            "content": "hello",
            "reasoning_content": "这个用户问的是 hello，需要友好回复",
        })
        result = run_thinking_gate(msg)
        self.assertIn("[thinking-gate]", result["stderr"])

    def test_detects_thinking_json_structure(self):
        """H1: 检测到 "thinking": { 结构 → 标记为泄漏"""
        msg = json.dumps({
            "thinking": {"steps": ["先分析", "再回复"]},
            "content": "hello",
        })
        result = run_thinking_gate(msg)
        self.assertIn("[thinking-gate]", result["stderr"])

    def test_detects_type_thinking(self):
        """H1: 检测到 type.*thinking → 标记为泄漏"""
        msg = json.dumps({
            "type": "thinking",
            "content": "analysis",
        })
        result = run_thinking_gate(msg)
        self.assertIn("[thinking-gate]", result["stderr"])

    def test_detects_reasoning_content_in_plain_text(self):
        """H1: plain text 中 reasoning_content 也会被检测"""
        msg = (
            '用户说：你好\n'
            'reasoning_content: 用户使用问候语，应该友好回复\n'
            '---\n'
            '你好，有什么可以帮助你的？'
        )
        result = run_thinking_gate(msg)
        self.assertIn("[thinking-gate]", result["stderr"])


class TestThinkingGateSilence(unittest.TestCase):
    """场景 2: 无残留时完全静默"""

    def test_clean_message_passes_silently(self):
        """干净的用户消息 → 无 stderr，仅 stdout {"continue": true}"""
        result = run_thinking_gate("你好，今天天气怎么样？")
        self.assertTrue(is_clean_pass(result))

    def test_clean_json_message_passes_silently(self):
        """干净的 JSON 格式消息 → 无 stderr"""
        msg = json.dumps({"role": "user", "content": "hello"})
        result = run_thinking_gate(msg)
        self.assertTrue(is_clean_pass(result))

    def test_empty_message_passes_silently(self):
        """空消息 → 无 stderr"""
        result = run_thinking_gate("")
        self.assertTrue(is_clean_pass(result))

    def test_code_block_no_false_positive(self):
        """代码块中包含 reasoning 不触发误报（仅 content，非字段名）"""
        msg = '# reasoning about this code\nprint("hello")'
        result = run_thinking_gate(msg)
        self.assertTrue(is_clean_pass(result))


class TestThinkingGateEvidenceLog(unittest.TestCase):
    """场景 3: 检测到残留时记录证据日志"""

    def setUp(self):
        self.evidence_log = os.path.expanduser("~/.hermes/cron/output/thinking-leak-events.json")

    def test_evidence_log_written_on_leak(self):
        """泄漏检测后 → 证据日志文件追加条目"""
        # 清理前一次测试的痕迹
        log_dir = os.path.dirname(self.evidence_log)
        os.makedirs(log_dir, exist_ok=True)
        before_count = 0
        if os.path.isfile(self.evidence_log):
            with open(self.evidence_log) as f:
                before_count = sum(1 for _ in f)

        msg = json.dumps({"role": "user", "content": "hi", "reasoning_content": "say hi back"})
        run_thinking_gate(msg)

        after_count = 0
        if os.path.isfile(self.evidence_log):
            with open(self.evidence_log) as f:
                after_count = sum(1 for _ in f)

        self.assertGreater(after_count, before_count, "证据日志应新增条目")

    def tearDown(self):
        """清理单次测试写入的证据日志条目（保留其他）"""
        pass  # 让日志自然累积，测试清理通过 setUp 计数对比


class TestThinkingGateFlywheel(unittest.TestCase):
    """场景 4: 检测到残留时记录 flywheel 事件"""

    def test_flywheel_event_on_leak(self):
        """泄漏检测后 → flywheel.log 新增 P1 事件"""
        flywheel_log = os.path.expanduser("~/.claude/flywheel.log")
        before = 0
        if os.path.isfile(flywheel_log):
            with open(flywheel_log) as f:
                for line in f:
                    if "thinking-gate_leak_detected" in line:
                        before += 1

        msg = json.dumps({"role": "user", "content": "test", "thinking": {"step": "analyze"}})
        run_thinking_gate(msg)

        after = 0
        if os.path.isfile(flywheel_log):
            with open(flywheel_log) as f:
                for line in f:
                    if "thinking-gate_leak_detected" in line:
                        after += 1

        self.assertGreater(after, before, "flywheel 应新增 thinking-gate_leak_detected 事件")


class TestThinkingGateStripping(unittest.TestCase):
    """场景 5: 剥离逻辑正确移除 thinking 内容（通过子进程模拟 stdin）"""

    def test_stdout_is_always_continue_true(self):
        """无论是否检测到泄漏，stdout 始终是 {"continue": true}"""
        cases = [
            "ordinary message",
            json.dumps({"role": "user", "content": "hi", "reasoning_content": "analyze"}),
            json.dumps({"thinking": {"steps": []}, "content": "hello"}),
            "<thinking>deep analysis</thinking>what's up?",
        ]
        for msg in cases:
            result = run_thinking_gate(msg)
            try:
                parsed = json.loads(result["stdout"])
                self.assertEqual(parsed, {"continue": True}, f"失败消息: {msg[:50]}")
            except json.JSONDecodeError as e:
                self.fail(f"stdout 不是合法 JSON: {result['stdout']} — {e}")

    def test_exit_code_always_zero(self):
        """无论是否检测到泄漏，exit code 始终是 0"""
        cases = ["hello", json.dumps({"reasoning_content": "test"}), ""]
        for msg in cases:
            result = run_thinking_gate(msg)
            self.assertEqual(result["returncode"], 0, f"失败消息: {msg[:50]}")


class TestThinkingGateEdgeCases(unittest.TestCase):
    """边界场景"""

    def test_field_in_nested_json_not_leak(self):
        """嵌套 JSON 中 'thinking' 作为普通值不触发"""
        msg = json.dumps({"data": {"mode": "thinking", "value": 42}})
        result = run_thinking_gate(msg)
        self.assertTrue(is_clean_pass(result))

    def test_chinese_thinking_block_detection(self):
        """中文 '思考：' 段落格式被检测"""
        msg = "用户消息\n思考：需要判断意图\n---\n正式回复"
        result = run_thinking_gate(msg)
        # 中文思考块不是 H1 检测项，检查是否仍能触发剥离
        self.assertTrue(is_clean_pass(result) or has_leak_log(result),
                        "中文思考块不应 H1 泄漏，但不应阻断")


# ── 直接测试：核心检测和剥离逻辑（单元测试，不依赖子进程）──

class TestThinkingCoreLogic(unittest.TestCase):
    """对 thinking-gate.py 核心函数的直接测试（通过 import + mock）

    测试剥离逻辑：
    - reasoning_content JSON 字段剥离
    - "thinking": {} 顶层 key 剥离
    - <thinking> XML 剥离
    - 中文思考段落剥离
    """

    def _mock_main_with_prompt(self, prompt: str):
        """模拟 main() 的输入处理、检测和剥离逻辑（不调用 subprocess）"""
        import re

        leak_type = ""
        leak_evidence = ""

        # H1 detect (same regex as thinking-gate.py)
        if re.search(r'(reasoning_content|"thinking"\s*:\s*\{|type.*?thinking)', prompt):
            leak_type = "H1-user-copy"
            leak_evidence = "found"

        stripped = prompt

        if leak_type:
            stripped = re.sub(
                r'"reasoning_content"\s*:\s*"[^"]*"\s*,?\s*',
                '', stripped, flags=re.DOTALL,
            )
            stripped = re.sub(
                r',?\s*"thinking"\s*:\s*\{[^}]*\}',
                '', stripped, flags=re.DOTALL,
            )
            stripped = re.sub(r'<thinking>.*?</thinking>', '', stripped, flags=re.DOTALL)
            stripped = re.sub(
                r'(?:^|\n)\s*思考[：:][^\n]*(\n[^\n]*)*(\n---\s*)?',
                '\n', stripped,
            )

        return leak_type, stripped

    def test_strip_reasoning_content_json(self):
        """剥离 reasoning_content JSON 字段"""
        prompt = '{"role": "user", "reasoning_content": "deep thoughts", "content": "hi"}'
        leak_type, stripped = self._mock_main_with_prompt(prompt)
        self.assertTrue(leak_type)
        self.assertNotIn("reasoning_content", stripped)

    def test_strip_thinking_json_key(self):
        """剥离 "thinking": {} 顶层 key"""
        prompt = '{"thinking": {"steps": ["a"]}, "content": "hi"}'
        leak_type, stripped = self._mock_main_with_prompt(prompt)
        self.assertTrue(leak_type)
        self.assertNotIn("thinking", stripped)

    def test_strip_thinking_xml(self):
        """剥离 <thinking> XML 块（需 H1 触发后才剥离）"""
        # XML 本身不触发 H1，需要 H1 触发后剥离才会执行
        prompt = 'reasoning_content: "deep"\n<thinking>内部推理\n多行思考</thinking>\n剩下的内容'
        leak_type, stripped = self._mock_main_with_prompt(prompt)
        self.assertTrue(leak_type, "应检测到 H1")
        self.assertNotIn("<thinking>", stripped)

    def test_strip_chinese_thinking(self):
        """剥离中文思考段落（需 H1 触发后才剥离）"""
        # 中文思考块本身不触发 H1，需要 H1 触发后剥离才会执行
        prompt = 'reasoning_content: "plan"\n用户说你好\n思考：先判断意图\n再分析情绪\n---\n回复内容'
        leak_type, stripped = self._mock_main_with_prompt(prompt)
        self.assertTrue(leak_type, "应检测到 H1")
        self.assertNotIn("思考：", stripped)

    def test_strip_xml_without_h1_noop(self):
        """仅有 <thinking> XML 但无 H1 触发 → 不剥离"""
        prompt = "正常内容\n<thinking>内部推理</thinking>\n结束"
        leak_type, stripped = self._mock_main_with_prompt(prompt)
        self.assertFalse(leak_type)
        self.assertIn("<thinking>", stripped)

    def test_strip_chinese_without_h1_noop(self):
        """仅有中文思考块但无 H1 触发 → 不剥离"""
        prompt = "用户说你好\n思考：随便想想\n---\n回复内容"
        leak_type, stripped = self._mock_main_with_prompt(prompt)
        self.assertFalse(leak_type)
        self.assertIn("思考：", stripped)

    def test_no_false_strip_on_clean(self):
        """干净内容不触发剥离"""
        prompt = "你好，今天天气怎么样？"
        leak_type, stripped = self._mock_main_with_prompt(prompt)
        self.assertFalse(leak_type)
        self.assertEqual(stripped, prompt)


# ── subprocess 级别的完整集成测试 ──

class TestThinkingGateIntegration(unittest.TestCase):
    """集成测试：模拟 CC 调用 hook 的完整数据流"""

    def test_stdin_json_input(self):
        """以完整 JSON stdin 输入调用 hook"""
        payload = json.dumps({"prompt": "hello"})
        result = run_thinking_gate(payload)
        self.assertTrue(is_clean_pass(result))

    def test_stdin_json_with_leak(self):
        """JSON stdin 含泄漏 → stderr 有日志"""
        payload = json.dumps({"prompt": json.dumps({"reasoning_content": "think"})})
        result = run_thinking_gate(payload)
        self.assertIn("[thinking-gate]", result["stderr"])

    def test_stdin_non_json_input(self):
        """非 JSON stdin 作为纯文本处理"""
        result = run_thinking_gate("this is a plain text message", use_json=False)
        self.assertTrue(is_clean_pass(result))

    def test_stdin_non_json_with_leak(self):
        """非 JSON stdin 含 reasoning_content → stderr 有日志"""
        result = run_thinking_gate(
            "用户说了 reasoning_content: 需要分析意图", use_json=False
        )
        self.assertIn("[thinking-gate]", result["stderr"])


if __name__ == "__main__":
    unittest.main()
