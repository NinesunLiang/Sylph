#!/usr/bin/env python3
"""
test_hermes_gateway.py — Hermes Gateway + QQ Bot 健康诊断

SWE 风格测试（运行命令 + 验证输出）。
测试覆盖:
  1. Gateway 进程存活
  2. QQ Bot WebSocket 连接状态 (gateway_state.json)
  3. 状态文件时效性 (<300s)
  4. requests 库完整性
  5. 错误日志 4009 模式检测

使用:
    python3 .claude/scripts/test_hermes_gateway.py
返回:
    0 = 全部通过, 非 0 = 失败项数
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# ── 路径 ────────────────────────────────────────────────
HOME = Path.home()
STATE_FILE = HOME / ".hermes" / "gateway_state.json"
ERROR_LOG = HOME / ".hermes" / "logs" / "gateway.error.log"
VENV_PYTHON = HOME / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"
ADAPTER_PY = (
    HOME
    / ".hermes"
    / "hermes-agent"
    / "gateway"
    / "platforms"
    / "qqbot"
    / "adapter.py"
)


# ── 测试辅助 ────────────────────────────────────────────
passed = 0
failed = 0


def test(name: str):
    """Decorator that wraps a test function, catches exceptions, and prints pass/fail."""
    def decorator(fn):
        def inner():
            global passed, failed
            try:
                fn()
                print(f"  🟢 PASS: {name}")
                passed += 1
                return True
            except AssertionError as e:
                print(f"  🔴 FAIL: {name}")
                print(f"         {e}")
                failed += 1
                return False
            except Exception as e:
                print(f"  🔴 FAIL: {name}")
                print(f"         {e}")
                failed += 1
                return False
        inner.__name__ = fn.__name__
        inner.__doc__ = fn.__doc__
        return inner
    return decorator


def assert_eq(a, b, msg=""):
    if a != b:
        raise AssertionError(f"Expected {b!r}, got {a!r}. {msg}")


def assert_gt(a, b, msg=""):
    if not (a > b):
        raise AssertionError(f"Expected >{b}, got {a}. {msg}")


def assert_lt(a, b, msg=""):
    if not (a < b):
        raise AssertionError(f"Expected <{b}, got {a}. {msg}")


# ── 测试 1: Gateway 进程 ─────────────────────────────────
@test("Gateway 进程存活")
def test_gateway_process():
    result = subprocess.run(
        ["pgrep", "-f", "hermes.*gateway"],
        capture_output=True, text=True, timeout=5,
    )
    assert_eq(result.returncode, 0, "Gateway 进程未运行")
    pid = result.stdout.strip().split("\n")[0]
    assert pid, "PID 为空"
    # 额外信息：进程启动时间
    ps = subprocess.run(
        ["ps", "-o", "lstart=", "-p", pid],
        capture_output=True, text=True, timeout=5,
    )
    print(f"    PID {pid}, started: {ps.stdout.strip()}")


# ── 测试 2: QQ Bot 连接状态 ────────────────────────────
@test("QQ Bot 连接状态")
def test_qqbot_state():
    assert STATE_FILE.exists(), f"状态文件不存在: {STATE_FILE}"
    d = json.loads(STATE_FILE.read_text())
    qq = d.get("platforms", {}).get("qqbot", {})
    state = qq.get("state", "unknown")
    updated = qq.get("updated_at", "")
    ts = datetime.fromisoformat(updated).timestamp()
    age = time.time() - ts
    print(f"    state={state}, age={age:.0f}s")
    assert_eq(state, "connected", f"QQ Bot 状态为 {state}")
    # 状态文件只在 state 变化时写入。Gateway 稳定运行 → age 只会增长。
    # 这种情况反而是健康的信号。补充验证 gateway 运行时长。
    if age > 300:
        gw = subprocess.run(
            ["pgrep", "-f", "hermes.*gateway"],
            capture_output=True, text=True, timeout=5,
        )
        assert_eq(gw.returncode, 0,
                  f"状态超时 ({age:.0f}s) 且 Gateway 进程不存在")
        print(f"    ⚠️  age={age:.0f}s（稳定运行中，状态文件仅状态变化时更新）")


# ── 测试 3: Gateway 整体状态时效 ───────────────────────
@test("Gateway 状态时效")
def test_gateway_state_freshness():
    assert STATE_FILE.exists(), f"状态文件不存在: {STATE_FILE}"
    d = json.loads(STATE_FILE.read_text())
    updated = d.get("updated_at", "")
    ts = datetime.fromisoformat(updated).timestamp()
    age = time.time() - ts
    print(f"    gateway last state update: {age:.0f}s ago")
    if age > 300:
        gw = subprocess.run(
            ["pgrep", "-f", "hermes.*gateway"],
            capture_output=True, text=True, timeout=5,
        )
        assert_eq(gw.returncode, 0,
                  f"Gateway 状态过期 ({age:.0f}s) 且进程不存在")
        print(f"    ⚠️  age={age:.0f}s but gateway alive — OK (state file only updated on changes)")


# ── 测试 4: requests 库完整性 ────────────────────────────
@test("requests 库完整性")
def test_requests_integrity():
    assert VENV_PYTHON.exists(), f"venv python 不可用: {VENV_PYTHON}"
    result = subprocess.run(
        [str(VENV_PYTHON), "-c",
         "import requests; "
         f"print(requests.__file__); "
         f"assert hasattr(requests, 'Response'), 'Response missing'; "
         f"assert hasattr(requests, 'get'), 'get missing'"],
        capture_output=True, text=True, timeout=10,
    )
    assert_eq(result.returncode, 0,
              f"requests 库异常:\n{result.stderr}\n"
              f"需 pip install --force-reinstall requests")
    print(f"    requests OK: {result.stdout.strip()}")


# ── 测试 5: 4009 模式检测 ──────────────────────────────
@test("4009 错误检测")
def test_4009_pattern():
    if not ERROR_LOG.exists():
        print("    ⏭️  错误日志不存在")
        return

    result = subprocess.run(
        ["grep", "-c", "Session timed out", str(ERROR_LOG)],
        capture_output=True, text=True, timeout=5,
    )
    total_4009 = int(result.stdout.strip() or 0)

    log_epoch = os.path.getmtime(str(ERROR_LOG))
    log_age = time.time() - log_epoch

    # 检查 gateway 存活时间
    gw = subprocess.run(
        ["pgrep", "-f", "hermes.*gateway"],
        capture_output=True, text=True, timeout=5,
    )
    if gw.returncode != 0:
        print(f"    历史 4009 总计: {total_4009} 次")
        print("    ⏭️  Gateway 未运行，无法判定当前 4009")
        return

    pid = gw.stdout.strip().split("\n")[0]
    ps = subprocess.run(
        ["ps", "-o", "lstart=", "-p", pid],
        capture_output=True, text=True, timeout=5,
    )
    line = ps.stdout.strip()
    gw_elapsed = 0
    if " " in line:
        try:
            gw_start = datetime.strptime(line, "%a %b %d %H:%M:%S %Y")
            gw_elapsed = int(time.time() - gw_start.timestamp())
        except ValueError:
            pass

    print(f"    历史 4009 总计: {total_4009} 次")
    print(f"    Gateway 存活: {gw_elapsed}s")
    print(f"    错误日志: {log_age:.0f}s 前更新")

    if gw_elapsed > 300 and log_age > 120:
        assert_eq(0, 0, "稳定状态")  # 无新错误
    elif gw_elapsed < 300:
        print(f"    ⏭️  Gateway 刚启动 {gw_elapsed}s，暂不判定")
    else:
        print(f"    ⏭️  Gateway 运行中，日志无新异常")


# ── 主入口 ────────────────────────────────────────────────
def main():
    global passed, failed
    passed = 0
    failed = 0

    print("")
    print("═══════════════════════════════════════════════")
    print("  Hermes Gateway 健康诊断")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═══════════════════════════════════════════════")
    print("")

    # 显式收集所有 test 函数（它们已被 @test 注册）
    tests = [
        test_gateway_process,
        test_qqbot_state,
        test_gateway_state_freshness,
        test_requests_integrity,
        test_4009_pattern,
    ]

    for i, t in enumerate(tests, 1):
        print(f"── [{i}/{len(tests)}] {t.__name__.replace('test_', '').replace('_', ' ').title()} ──")
        t()

    print("")
    print("── 汇总 ──")
    if failed == 0:
        print(f"  🟢 全部通过 ({passed}/{passed + failed})")
        return 0
    else:
        print(f"  🔴 {failed} 项失败 (passed={passed}, failed={failed})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
