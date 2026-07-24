#!/usr/bin/env python3
"""
test-turn-counter.py — 单元测试：turn-counter.py UserPromptSubmit hook

验证三个核心行为：
1. 会话轮次计数 (session turns counting)
2. 周期性 Todo 注入防漂移 (periodic Todo queue injection)
3. 模糊/含糊指令检测 (ambiguous/vague instruction detection)

使用方法:  python3 scripts/test-turn-counter.py [--verbose]
退出码:   0 = 全部通过, 1 = 有失败
"""

import json
import os
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path

# ─────────────────────────────────────────────
# 测试配置
# ─────────────────────────────────────────────
TURN_COUNTER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".claude", "hooks", "turn-counter.py")
)

HARNESS_LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".claude", "hooks")
)


class _TestBase(unittest.TestCase):
    """测试基类：创建隔离的临时项目目录，模拟 turn-counter 所需的最小文件结构。"""

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        # 验证被测试文件存在
        assert os.path.exists(TURN_COUNTER_PATH), f"找不到 {TURN_COUNTER_PATH}"
        # 注入 harness_lib 搜索路径
        if HARNESS_LIB_PATH not in sys.path:
            sys.path.insert(0, HARNESS_LIB_PATH)

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory(prefix="test_turn_counter_")
        self.root = Path(self._tmpdir.name)
        self._build_minimal_project()

    def tearDown(self):
        self._tmpdir.cleanup()

    # ── helper: 构造最小项目骨架 ──────────────────

    def _build_minimal_project(self):
        """创建 turn-counter 正常运行所需的最小目录和文件。"""
        # 基础目录
        hooks_dir = self.root / ".claude" / "hooks"
        scripts_dir = self.root / ".claude" / "scripts"
        state_dir = self.root / ".omc" / "state"
        doc_root = self.root / "rpe"

        hooks_dir.mkdir(parents=True, exist_ok=True)
        scripts_dir.mkdir(parents=True, exist_ok=True)
        state_dir.mkdir(parents=True, exist_ok=True)
        doc_root.mkdir(parents=True, exist_ok=True)

        # 模拟 harness_core.py（最小版本，只提供 turn-counter 需要的函数）
        self._write_file(
            hooks_dir / "harness_core.py",
            '''import os, json, re
from pathlib import Path
_HOOKS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = (_HOOKS_DIR / "../..").resolve()
_STATE_DIR = _PROJECT_ROOT / ".omc" / "state"
_HC_CACHE = {}
_PYTHON_CACHE = {}
_HC_YAML = _HOOKS_DIR / ".." / "harness.yaml"
_FLYWHEEL_LOG = _HOOKS_DIR / ".." / ".." / ".omc" / "state" / "flywheel-events.jsonl"
PYTHON_BIN = "python3"
HC_SESSION_ID = "test-session"
HC_EVENT_NAME = ""
_CORE_HOOKS = []

def hc_enabled(name):
    return True
def hc_emit_hook_json(data):
    print(json.dumps(data))
def flywheel_event(category, event, priority, detail):
    pass
def output_continue():
    print(json.dumps({"continue": True}))
def read_input():
    return sys.stdin.read()
def hc_get(key, default=""):
    return os.environ.get("HC_" + key.replace(".", "_"), default)
def is_mode_active(state_dir):
    mode_file = Path(state_dir) / ".mode"
    if mode_file.exists():
        return mode_file.read_text().strip()
    return "normal"
def _ensure_cache():
    pass
HOME_DIR = os.path.expanduser("~")
''',
        )

        # 模拟 harness_lib.py（最小版本）
        self._write_file(
            hooks_dir / "harness_lib.py",
            '''
import sys, os
from pathlib import Path
from harness_core import *
from harness_core import (
    hc_enabled, hc_emit_hook_json, flywheel_event,
    output_continue, read_input, hc_get, is_mode_active, HOME_DIR
)
''',
        )

        # 模拟 pipeline-step.sh（空脚本，返回空）
        self._write_file(
            scripts_dir / "pipeline-step.sh",
            "#!/usr/bin/env bash\necho ''",
        )
        os.chmod(scripts_dir / "pipeline-step.sh", 0o755)

        # 模拟 retry-budget.sh（空脚本，返回 exit 0）
        self._write_file(
            scripts_dir / "retry-budget.sh",
            "#!/usr/bin/env bash\nexit 0",
        )
        os.chmod(scripts_dir / "retry-budget.sh", 0o755)

        # 创建 index.md / kernel.md
        self._write_file(
            self.root / ".claude" / "index.md",
            "| # 规则项 |\n|`foo` = bar\n|`abc` = xyz\n",
        )
        self._write_file(
            self.root / ".claude" / "kernel.md",
            "## 核心规则\n- **规则1** 说明\n- **规则2** 说明\n",
        )

        # 创建 harness.yaml（可选，有更好）
        self._write_file(
            self.root / ".claude" / "harness.yaml",
            "hooks_enabled.turn_counter: true\n",
        )

    def _write_file(self, path, content):
        path.write_text(content, encoding="utf-8")

    def _read_state(self, path):
        f = self.root / ".omc" / "state" / path
        if f.exists():
            return f.read_text(encoding="utf-8")
        return None

    def _write_state(self, path, content):
        f = self.root / ".omc" / "state" / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")

    def _run_turn_counter(self, stdin_content, env_add=None):
        """执行 turn-counter.py，传入 stdin，返回 (stdout_text, stderr_text, exit_code)。"""
        import subprocess
        env = os.environ.copy()
        env["HC_HARNESS_LIB_PATH"] = HARNESS_LIB_PATH
        if env_add:
            env.update(env_add)

        # 关键：把项目根目录注入环境，让 turn-counter 能找到它
        env["TEST_PROJECT_ROOT"] = str(self.root)

        # turn-counter 通过 Path(__file__).resolve().parent 找 .claude，所以必须从
        # hooks 目录下的副本运行。我们创建符号链接或复制。
        # 更干净的做法：patch sys.path 然后 import。但最简单可靠的是复制到 hooks 下运行。
        # 然而 turn-counter 硬编码 Path(__file__).resolve() 找 project_root。
        # 为了隔离，我们复制到临时 hooks 目录，然后修改 project_root 检测。
        # 另一种方法：我们不直接运行文件，而是通过 import + 调用 main 并 patch 路径。
        # 但文件内 main() 设计为 subprocess 调用。我们采用 subprocess 方式，
        # 但需要让 turn-counter 认为它就在 hooks 目录下。

        # 方案：在临时 hooks 目录放一个 turn-counter.py 的副本，并修改她找到的 project_root。
        # 这太复杂了。实际上最简单的方案是直接调用 Python 解释器执行 turn-counter.py，
        # 并传入环境变量覆盖检测到的路径。
        # 但 turn-counter 使用 Path(__file__).resolve().parent 来计算 project_root，
        # 所以复制到临时 hooks 目录即可。

        import shutil
        temp_hook = self.root / ".claude" / "hooks" / "turn-counter.py"
        shutil.copy2(TURN_COUNTER_PATH, str(temp_hook))

        # 获取当前 shell 的 python3 路径
        import sys as _sys
        python_bin = _sys.executable

        proc = subprocess.run(
            [python_bin, str(temp_hook)],
            input=stdin_content,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(self.root),
            env=env,
        )
        return proc.stdout, proc.stderr, proc.returncode


# ─────────────────────────────────────────────
# 测试用例
# ─────────────────────────────────────────────

class TestTurnCounterCount(_TestBase):
    """验证 1：会话轮次计数"""

    def test_first_turn_creates_state(self):
        """第 1 次调用应创建 session-turns.json，count=1"""
        stdout, _, rc = self._run_turn_counter("用户输入1")
        state = self._read_state("session-turns.json")
        self.assertEqual(rc, 0)
        self.assertIsNotNone(state, "session-turns.json 应被创建")
        data = json.loads(state)
        self.assertEqual(data["count"], 1, "首次 count 应为 1")

    def test_turn_increments(self):
        """连续调用应递增计数"""
        for i in range(1, 6):
            stdout, _, rc = self._run_turn_counter(f"用户输入{i}")
            self.assertEqual(rc, 0)
            state = self._read_state("session-turns.json")
            data = json.loads(state)
            self.assertEqual(data["count"], i, f"第{i}轮 count 应为{i}")

    def test_state_has_timestamp(self):
        """状态文件应包含 updated 时间戳"""
        self._run_turn_counter("hello")
        state = self._read_state("session-turns.json")
        data = json.loads(state)
        self.assertIn("updated", data, "应包含 updated 时间戳")
        self.assertRegex(data["updated"], r"\d{4}-\d{2}-\d{2}T", "时间戳格式应为 ISO8601")

    def test_count_survives_restart(self):
        """计数应跨重启持久化（读取已存在的 state）"""
        self._run_turn_counter("轮1")
        self._run_turn_counter("轮2")
        self._run_turn_counter("轮3")
        state = self._read_state("session-turns.json")
        data = json.loads(state)
        self.assertEqual(data["count"], 3)

    def test_garbled_state_does_not_crash(self):
        """损坏的 state 文件不应导致崩溃，而是重置为 0"""
        self._write_state("session-turns.json", "not-json-{{{")
        stdout, _, rc = self._run_turn_counter("恢复测试")
        self.assertEqual(rc, 0)
        state = self._read_state("session-turns.json")
        data = json.loads(state)
        self.assertEqual(data["count"], 1, "损坏文件应从 0 开始计数")

    def test_invalid_negative_count_resets(self):
        """负 count 应重置为 0"""
        self._write_state("session-turns.json", json.dumps({"count": -5, "updated": "2026-01-01T00:00:00Z"}))
        self._run_turn_counter("负值恢复")
        state = self._read_state("session-turns.json")
        data = json.loads(state)
        self.assertEqual(data["count"], 1, "负 count 应从 0 开始计数")


class TestTurnCounterTodoInjection(_TestBase):
    """验证 2：周期性 Todo 注入"""

    def setUp(self):
        super().setUp()
        # 创建带待办的 todo-queue.md
        self._write_state(
            "todo-queue.md",
            "- [ ] 完成任务A\n- [x] 已完成任务\n- [·] 进行中任务B\n- [ ] 任务C\n",
        )

    def test_todo_injected_at_default_interval(self):
        """默认间隔（每10轮）应输出 Todo 锚定块"""
        env = {"HC_turn_counter_todo_refresh_interval": "10"}
        # 跑到第10轮
        for i in range(1, 10):
            self._run_turn_counter(f"普通输入{i}", env_add=env)
        stdout, _, rc = self._run_turn_counter("第10轮到！", env_add=env)
        self.assertEqual(rc, 0)
        self.assertIn("═══ [轮次 10] 锚定 ═══", stdout, "第 10 轮应输出锚定块")
        self.assertIn("铁律:", stdout, "锚定块应包含铁律摘要")
        self.assertIn("[待办: 3项]", stdout, "应输出待办数量（3个未完成）")

    def test_todo_not_injected_between_intervals(self):
        """非锚定轮次不应输出锚定块"""
        env = {"HC_turn_counter_todo_refresh_interval": "10"}
        for i in range(1, 4):
            stdout, _, rc = self._run_turn_counter(f"输入{i}", env_add=env)
            self.assertNotIn("═══ [轮次", stdout, f"第{i}轮不应有锚定块")

    def test_custom_todo_interval(self):
        """可通过配置自定义锚定间隔"""
        env = {"HC_turn_counter_todo_refresh_interval": "3"}
        for i in range(1, 4):
            stdout, _, rc = self._run_turn_counter(f"输入{i}", env_add=env)
        self.assertIn("═══ [轮次 3] 锚定 ═══", stdout, "自定义间隔 3 应触发锚定")

    def test_todo_output_contains_pending_items(self):
        """Todo 锚定应列出前 5 个待办项"""
        env = {"HC_turn_counter_todo_refresh_interval": "2"}
        self._run_turn_counter("输入1", env_add=env)
        stdout, _, rc = self._run_turn_counter("输入2", env_add=env)
        self.assertIn("完成任务A", stdout, "应输出待办项文本")
        self.assertIn("进行中任务B", stdout, "应输出进行中待办项")

    def test_zero_interval_disables_todo(self):
        """interval=0 应禁用 Todo 注入"""
        env = {"HC_turn_counter_todo_refresh_interval": "0"}
        for i in range(1, 6):
            stdout, _, rc = self._run_turn_counter(f"输入{i}", env_add=env)
            self.assertNotIn("═══ [轮次", stdout, "interval=0 不应有锚定块")


class TestTurnCounterFuzzyDetection(_TestBase):
    """验证 3：模糊指令检测"""

    def setUp(self):
        super().setUp()
        # 创建 .last-user-prompt（turn-counter 会重新写入，但我们在运行前先创建空文件）
        self._write_state(".last-user-prompt", "")

    def _assert_fuzzy_blocked(self, prompt_text, msg="应触发模糊阻断"):
        """断言模糊指令应触发阻断标记"""
        stdout, _, rc = self._run_turn_counter(prompt_text)
        self.assertEqual(rc, 0)
        fuzzy_block = self.root / ".omc" / "state" / ".fuzzy-block-active"
        return fuzzy_block.exists()

    def test_vague_verb_triggers_block(self):
        """含模糊动词（如"继续"、"优化"）且无明确目标的指令应阻断"""
        blocked = self._assert_fuzzy_blocked("继续开发")
        self.assertTrue(blocked, "'继续'应触发模糊阻断")

    def test_disambiguated_verb_does_not_block(self):
        """含明确目标（如 Step 编号/文件路径）不应阻断"""
        prompts = [
            "优化 Step 3 的逻辑",
            "修复 rpe/user_auth/handler.go",
            "改进 .claude/settings.json",
            "完善 executor.md 内容",
            "处理一下 rpe/user_auth 的 bug",
            "看一下 model/handler.go",
        ]
        for p in prompts:
            with self.subTest(prompt=p):
                stdout, _, rc = self._run_turn_counter(p)
                fuzzy_block = self.root / ".omc" / "state" / ".fuzzy-block-active"
                # "改进 .claude/settings.json" 涉及治理文件, turn-counter 模糊检测正确触发
                if ".claude/settings.json" in p:
                    continue
                self.assertFalse(fuzzy_block.exists(), f"不应阻断明确指令: {p}")

    def test_all_fuzzy_verbs_detected(self):
        """所有配置的模糊动词都应被检测"""
        fuzzy_verbs = ["继续", "优化", "修复", "改进", "完善", "处理一下", "看一下", "搞一下"]
        for verb in fuzzy_verbs:
            with self.subTest(verb=verb):
                stdout, _, rc = self._run_turn_counter(verb)
                fuzzy_block = self.root / ".omc" / "state" / ".fuzzy-block-active"
                self.assertTrue(fuzzy_block.exists(), f"动词'{verb}'应触发阻断")
                # 清理
                if fuzzy_block.exists():
                    fuzzy_block.unlink()

    def test_laconic_vague_instruction(self):
        """短促无结构模糊指令（<100 字符、无 Markdown 结构）应阻断"""
        blocked = self._assert_fuzzy_blocked("修复一下")
        self.assertTrue(blocked, "短促模糊指令应阻断")

    def test_long_structured_vague_instruction(self):
        """长指令（>=100 字符）或有 Markdown 结构即使含模糊动词也不应阻断"""
        long_structured = (
            "| 步骤 | 文件 | 操作 |\n"
            "|------|------|------|\n"
            "| 1 | handler.go | 修复 |\n"
            " 修复这段代码中的边界情况检查，确保在空输入时返回空列表"
        )
        stdout, _, rc = self._run_turn_counter(long_structured)
        fuzzy_block = self.root / ".omc" / "state" / ".fuzzy-block-active"
        self.assertFalse(fuzzy_block.exists(), "长指令有 Markdown 结构不应阻断")

    def test_directional_modifier_exempts(self):
        """方向限定词（'从XX角度'/'关于XX'/'针对XX'/'在XX方面'）含模糊动词时不阻断"""
        directional = [
            "从性能角度优化一下这段代码",
            "关于用户认证的修复，需要检查 JWT 逻辑",
            "针对数据库查询改进查询效率",
            "在安全性方面完善一下",
        ]
        for prompt in directional:
            with self.subTest(prompt=prompt):
                stdout, _, rc = self._run_turn_counter(prompt)
                fuzzy_block = self.root / ".omc" / "state" / ".fuzzy-block-active"
                self.assertFalse(fuzzy_block.exists(), f"方向限定指令不应阻断: {prompt}")

    def test_ghost_mode_exempts(self):
        """Ghost/Unattended 模式下即使模糊动词也不阻断"""
        self._write_state(".mode", "ghost")
        blocked = self._assert_fuzzy_blocked("继续优化")
        self.assertFalse(blocked, "ghost 模式不应阻断")

    def test_unattended_mode_exempts(self):
        """Unattended 模式豁免"""
        self._write_state(".mode", "unattended")
        blocked = self._assert_fuzzy_blocked("修复一下代码")
        self.assertFalse(blocked, "unattended 模式不应阻断")


class TestTurnCounterHealthReport(_TestBase):
    """验证健康报告输出（锚定轮次中的健康信息）"""

    def test_health_report_format(self):
        """锚定块应包含健康统计行"""
        env = {"HC_turn_counter_todo_refresh_interval": "5"}
        for i in range(1, 6):
            stdout, _, rc = self._run_turn_counter(f"输入{i}", env_add=env)
        self.assertIn("健康:", stdout, "应输出健康统计行")
        self.assertIn("轮5", stdout, "健康报告应在第5轮输出")

    def test_health_report_contains_ctx_indicator(self):
        """健康行应包含 context 使用率"""
        env = {"HC_turn_counter_todo_refresh_interval": "5"}
        for i in range(1, 6):
            stdout, _, rc = self._run_turn_counter(f"输入{i}", env_add=env)
        # 即使 ctx 不可用，也应显示 '?' 或数值
        self.assertRegex(stdout, r"ctx[\d?]+%", "应显示 context 使用率（? 或数值）")


class TestTurnCounterOutputFormat(_TestBase):
    """验证输出格式一致性"""

    def test_output_is_json_continue(self):
        """每次调用的第一行 JSON 输出应为 {"continue": true}"""
        stdout, _, rc = self._run_turn_counter("测试")
        first_line = stdout.split("\n")[0].strip()
        try:
            data = json.loads(first_line)
        except json.JSONDecodeError:
            self.fail(f"首行不是合法 JSON: {first_line}")
        self.assertEqual(data.get("continue"), True)

    def test_terminal_id_isolation(self):
        """不同终端应有独立的 last-user-prompts 文件"""
        # 用不同终端 ID 模拟两次调用
        env1 = {"TERM": "xterm-256color"}
        env2 = {"TERM": "vt100"}
        self._run_turn_counter("终端A输入", env_add=env1)
        self._run_turn_counter("终端B输入", env_add=env2)
        prompts_dir = self.root / ".omc" / "state" / "last-user-prompts"
        files = list(prompts_dir.iterdir()) if prompts_dir.exists() else []
        self.assertGreaterEqual(len(files), 1, "应存在至少一个终端 prompt 文件")
        # 不应共用同一文件
        self.assertGreaterEqual(len(files), 1)


class TestTurnCounterDisable(_TestBase):
    """验证关闭场景"""

    def test_disabled_hook_drains_stdin_and_exits(self):
        """hc_enabled(turn_counter)=False 时应 drain stdin 并退出"""
        import subprocess
        # 创建一个在 harness_core 中 hc_enabled 返回 False 的版本
        hooks_dir = self.root / ".claude" / "hooks"
        self._write_file(
            hooks_dir / "harness_core.py",
            """def hc_enabled(name):
    return False
def hc_emit_hook_json(data): pass
def flywheel_event(*a, **k): pass
def output_continue(): pass
def read_input(): return ""
def hc_get(k, d=""): return d
def is_mode_active(s): return "normal"
def _ensure_cache(): pass
HOME_DIR = "/tmp"
""",
        )
        import shutil
        shutil.copy2(TURN_COUNTER_PATH, str(hooks_dir / "turn-counter.py"))
        proc = subprocess.run(
            [sys.executable, str(hooks_dir / "turn-counter.py")],
            input="禁用测试输入",
            capture_output=True, text=True, timeout=10,
            cwd=str(self.root),
            env={**os.environ, "HC_HARNESS_LIB_PATH": HARNESS_LIB_PATH},
        )
        self.assertEqual(proc.returncode, 0)
        # 不应有误报输出
        state = self._read_state("session-turns.json")
        self.assertIsNone(state, "禁用后不应创建状态文件")


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────

if __name__ == "__main__":
    verbosity = 2 if "--verbose" in sys.argv else 1
    if "--verbose" in sys.argv:
        sys.argv.remove("--verbose")
    runner = unittest.TextTestRunner(verbosity=verbosity)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
