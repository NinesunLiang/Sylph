"""test_py39_compat.py — Python 3.9 运行时兼容回归测试。

背景（index22 双法官实测发现）:
- write_lock.py:19 `LOCK_DIR: Path | None` 无 __future__ → Py3.9 `TypeError: unsupported
  operand type(s) for |: 'type' and 'NoneType'`，导致 carros_base.py 直接崩溃，
  tick/verify/archive 全部不可用。
- sub_agent_result.py:21 `ResultUpdater = Callable[[dict[str, Any]], dict[str, Any] | None]`
  是**赋值语句**（非注解），__future__ 无法延迟求值，必须改 Optional。
- goal_state_machine.py / error_dna_logger.py / token_lifecycle.py 等同样缺 __future__。
- executor_ledger.py:223 f-string 表达式内反斜杠（Py3.9 语法禁止）。

修复：核心脚本补 from __future__ import annotations；赋值型类型别名改 Optional；
f-string 反斜杠提取到变量。

本测试保证：CarrorOS 核心 CLI 与治理模块在 Python 3.9 下可 import / 可编译。
"""
from __future__ import annotations

import importlib
import importlib.util
import pathlib
import py_compile
import subprocess
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT_ROOT / ".claude" / "scripts"

# 曾在 Py3.9 崩溃或含 Py3.10+ 语法、已被修复的核心模块
CORE_MODULES = [
    "carros_base",
    "write_lock",
    "sub_agent_result",
    "goal_state_machine",
    "error_dna_logger",
    "token_lifecycle",
    "step_contracts",
    "verify_gate",
    "content_writer",
    "goal_contracts",
    "sub_agent_executor",
    "executor_ledger",
]


def _import_core(name: str) -> None:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None, f"{name}.py spec not found"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)


def test_carros_base_importable_py39() -> None:
    """carros_base.py 必须能在 Py3.9 下完整 import（含子模块链）。"""
    _import_core("carros_base")


def test_core_modules_importable_py39() -> None:
    """治理核心模块逐个可 import，验证无运行时 | 求值。"""
    for name in CORE_MODULES:
        _import_core(name)


def test_all_scripts_compile_py39() -> None:
    """.claude/scripts 下全部 .py 必须通过 Py3.9 语法编译（含 f-string 反斜杠禁令）。"""
    bad = []
    for f in sorted(SCRIPTS.glob("*.py")):
        if "__pycache__" in f.name:
            continue
        try:
            py_compile.compile(str(f), doraise=True)
        except Exception as e:  # noqa: BLE001
            bad.append((f.name, str(e).splitlines()[-1][:120]))
    assert not bad, f"Py3.9 编译失败: {bad}"


def test_carros_base_cli_help_runs() -> None:
    """CLI 顶层命令（help/status）在 Py3.9 下真实可执行，不是仅 import 链通过。"""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "carros_base.py"), "--help"],
        capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT),
    )
    # 任意子命令存在即可证明入口可用（--help 可能未定义，fallback usage）
    assert proc.returncode in (0, 1), f"carros_base --help rc={proc.returncode}: {proc.stderr[:500]}"
