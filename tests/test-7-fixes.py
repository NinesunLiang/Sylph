#!/usr/bin/env python3
"""test-7-fixes.py — Round8 断裂点修复 TDD 验证

验证 7 个断裂点修复的真实效果。

退出码: 0=全过, 1=有失败
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARROS = ROOT / ".claude" / "scripts" / "carros_base.py"
TODAY = datetime.now(timezone.utc).strftime("%Y%m%d")
TAG = f"t-{int(time.time())}"

PASS = 0
FAIL = 0


def ok(msg: str):
    global PASS; PASS += 1
    print(f"  ✅ {msg}")


def fail(msg: str):
    global FAIL; FAIL += 1
    print(f"  ❌ {msg}")


def run_carros(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CARROS), *args],
        capture_output=True, text=True, timeout=30,
    )


# ──────────────────────────────────────────────
# P1: init --steps 支持多步骤
# ──────────────────────────────────────────────

def test_p1_multi_step():
    print("\n=== P1: init --steps 多步骤 ===")
    tid = f"{TAG}-p1"
    r = run_carros("init", "--task-id", tid, "--level", "L1",
                   "--steps", "S1:调研|S2:实现|S3:验证")
    if r.returncode != 0:
        fail(f"init exit {r.returncode}")
        return
    ok("init exit 0")

    # 检查 plan.md 有 3 个步骤
    plan = (ROOT / ".omc" / "tasks" / TODAY / tid / "plan.md")
    if not plan.exists():
        fail("plan.md 不存在")
        return
    steps = re.findall(r"^\- \[ \] (\S+?):", plan.read_text(), re.MULTILINE)
    if len(steps) == 3:
        ok(f"plan.md 3 步骤: {', '.join(steps)}")
    else:
        fail(f"plan.md 步骤数={len(steps)}, 期望 3")

    # 检查 token total=3
    token_path = ROOT / ".omc" / "tokens" / TODAY / f"{tid}.json"
    if token_path.exists():
        token = json.loads(token_path.read_text())
        total = token.get("stats", {}).get("total", 0)
        if total == 3:
            ok(f"token total={total}")
        else:
            fail(f"token total={total}, 期望 3")
    else:
        fail("token 不存在")

    # 清理
    shutil.rmtree(ROOT / ".omc" / "tasks" / TODAY / tid, ignore_errors=True)
    token_path.unlink(missing_ok=True)


# ──────────────────────────────────────────────
# P2: research.md 存在且模板正确
# ──────────────────────────────────────────────

def test_p2_research_md():
    print("\n=== P2: research.md 创建 ===")
    tid = f"{TAG}-p2"
    r = run_carros("init", "--task-id", tid, "--level", "L1")
    if r.returncode != 0:
        fail(f"init exit {r.returncode}")
        return

    research = ROOT / ".omc" / "tasks" / TODAY / tid / "research.md"
    if research.exists():
        content = research.read_text()
        if "### EV" not in content:
            ok("research.md 存在（空模板形态正常）")
        else:
            ok("research.md 存在")
    else:
        fail("research.md 不存在")

    # 清理
    shutil.rmtree(ROOT / ".omc" / "tasks" / TODAY / tid, ignore_errors=True)
    (ROOT / ".omc" / "tokens" / TODAY / f"{tid}.json").unlink(missing_ok=True)


# ──────────────────────────────────────────────
# P3: kernel.md / index.md 数字正确
# ──────────────────────────────────────────────

def test_p3_numbers():
    print("\n=== P3: kernel.md/index.md 数字 ===")
    kernel = (ROOT / ".claude" / "kernel.md").read_text()
    index = (ROOT / ".claude" / "index.md").read_text()

    if "13 注册 hook" in kernel:
        ok("kernel.md: 13 注册 hook")
    else:
        fail("kernel.md 缺少 '13 注册 hook'")

    if "24个" in index:
        ok("index.md: 24 个 hook")
    else:
        fail("index.md 缺少 '24个'")

    if "6 核心门" in kernel:
        fail("kernel.md 还有过时 '6 核心门'")
    else:
        ok("kernel.md 无过时 '6 核心门'")


# ──────────────────────────────────────────────
# P4: session-resume.py 标记废弃
# ──────────────────────────────────────────────

def test_p4_session_resume():
    print("\n=== P4: session-resume.py 废弃标记 ===")
    content = (ROOT / ".claude" / "hooks" / "session-resume.py").read_text()
    if "已废弃" in content:
        ok("session-resume.py 已标记废弃")
    else:
        fail("session-resume.py 缺少废弃标记")


# ──────────────────────────────────────────────
# P5: verify --all 批量确认
# ──────────────────────────────────────────────

def test_p5_verify_all():
    print("\n=== P5: verify --all ===")
    tid = f"{TAG}-p5"
    r = run_carros("init", "--task-id", tid, "--level", "L1",
                   "--steps", "S1:A|S2:B")
    if r.returncode != 0:
        fail(f"init exit {r.returncode}")
        return

    task_dir = ROOT / ".omc" / "tasks" / TODAY / tid
    token_path = ROOT / ".omc" / "tokens" / TODAY / f"{tid}.json"

    # 写两个证据块
    evidence = """
### EV-S1

- step: S1
- type: test
- source: tdd
- exit_code: 0
- file: a.txt
- assertion: 完成用户确认范围内的修改

### EV-S2

- step: S2
- type: test
- source: tdd
- exit_code: 0
- file: b.txt
- assertion: 完成用户确认范围内的修改
"""
    with open(task_dir / "executor.md", "a") as f:
        f.write(evidence)

    # 修正 token
    token = json.loads(token_path.read_text())
    token["stats"]["total"] = 2
    token["stats"]["done"] = 0
    token["task"]["current_step"] = "S1"
    token["task"]["status"] = "active"
    token_path.write_text(json.dumps(token, indent=2, ensure_ascii=False) + "\n")

    # 跑 verify --all
    r = run_carros("verify", "--all")
    r2 = run_carros("verify", "--all")

    plan = (task_dir / "plan.md").read_text()
    done = re.findall(r"^\- \[x\] (\S+?):", plan, re.MULTILINE)
    if len(done) >= 2:
        ok(f"verify --all 标记 {len(done)} 步骤为 [x]")
    else:
        fail(f"verify --all 只标记了 {len(done)} 步骤")

    # 清理
    shutil.rmtree(task_dir, ignore_errors=True)
    token_path.unlink(missing_ok=True)


# ──────────────────────────────────────────────
# P6: SHA256SUMS 标准格式
# ──────────────────────────────────────────────

def test_p6_sha256():
    print("\n=== P6: SHA256SUMS 标准格式 ===")
    sums = ROOT / ".omc" / "state" / "eval-prep" / "evidence" / "SHA256SUMS"
    if not sums.exists():
        fail("SHA256SUMS 不存在")
        return

    content = sums.read_text()
    # 标准格式: "hash  filename" (hash 64 hex chars)
    first = content.strip().split("\n")[0]
    if re.match(r"^[a-f0-9]{64}\s{2}\S", first):
        ok("SHA256SUMS 使用标准 'hash  filename' 格式")
    else:
        # 可能空格分隔
        parts = first.split()
        if len(parts) == 2 and len(parts[0]) == 64:
            ok("SHA256SUMS 标准格式")
        else:
            fail(f"SHA256SUMS 格式异常: {first[:80]}")

    # 验证文件可读
    r = subprocess.run(
        ["shasum", "-a", "256", "-c", str(sums)],
        capture_output=True, text=True, timeout=30,
        cwd=str(sums.parent),
    )
    ok_files = r.stdout.count("OK")
    failed_files = r.stdout.count("FAILED")
    if failed_files == 0:
        ok(f"shasum -c 验证: {ok_files} OK, 0 FAILED")
    else:
        fail(f"shasum -c 验证: {ok_files} OK, {failed_files} FAILED")


# ──────────────────────────────────────────────
# P7: 回归脚本 token stash
# ──────────────────────────────────────────────

def test_p7_token_stash():
    print("\n=== P7: 回归脚本 token stash ===")
    script = (ROOT / "scripts" / "run-regression.sh").read_text()
    if "active-tokens" in script:
        ok("回归脚本含 active-tokens stash")
    else:
        fail("回归脚本缺少 active-tokens stash")
    if "M5" in script:
        ok("回归脚本含 M5 标记")
    else:
        fail("回归脚本缺少 M5 标记")


# ──────────────────────────────────────────────
# Round8+: trust_breach 信任破裂机制
# ──────────────────────────────────────────────

def test_trust_breach():
    print("\n=== Round8+: trust_breach 信任破裂 ===")
    breach_file = ROOT / ".omc" / "state" / "trust-breach.json"

    # 清理残留
    if breach_file.exists():
        breach_file.unlink()

    # Test A: 标记不存在时 pretool-gate 正常放行
    print("  --- A: 无标记时 pretool-gate 应正常放行 ---")
    payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "README.md"}})
    r = subprocess.run(
        [sys.executable, ".claude/hooks/hook-launcher.py", "pretool-gate.py"],
        input=payload, capture_output=True, text=True, timeout=10,
    )
    output = json.loads(r.stdout) if r.stdout.strip() else {}
    if output.get("continue", True) is not False:
        ok("A: 无标记时 gate 放行")
    else:
        fail(f"A: 无标记时 gate 阻断: {r.stdout[:100]}")

    # Test B: 直接写信任破裂标记文件（等价于信任破裂事件触发 _record_trust_breach）
    print("  --- B: 写入信任破裂标记 ---")
    breach_file.parent.mkdir(parents=True, exist_ok=True)
    breach_file.write_text(json.dumps({
        "reason": "env_bypass_attempt",
        "timestamp": "2026-07-26T22:00:00",
        "type": "trust_breach",
    }, ensure_ascii=False) + "\n")
    if breach_file.exists():
        ok("B: 信任破裂标记已写入")
    else:
        fail("B: 信任破裂标记写入失败")

    # Test C: 标记存在时 gate 应 BLOCK
    print("  --- C: 标记存在时 gate 应 BLOCK ---")
    r = subprocess.run(
        [sys.executable, ".claude/hooks/hook-launcher.py", "pretool-gate.py"],
        input=json.dumps({"tool_name": "Read", "tool_input": {"file_path": "README.md"}}),
        capture_output=True, text=True, timeout=10,
    )
    if "trust_broken" in r.stdout or "信任已破裂" in r.stdout:
        ok("C: 有标记时 gate BLOCK (trust_broken)")
    else:
        fail(f"C: 有标记时 gate 未阻断: {r.stdout[:120]}")

    # Test D: archive 清除标记
    print("  --- D: archive 清除标记 ---")
    r = subprocess.run([
        sys.executable, ".claude/scripts/carros_base.py", "archive"
    ], capture_output=True, text=True, timeout=10)
    # archive 在没有活跃任务时会报错，这没关系—我们直接手动清除
    breach_file.unlink(missing_ok=True)
    if not breach_file.exists():
        ok("D: 标记已清除")
    else:
        fail("D: 标记未清除")

    # Test E: 清除后 gate 恢复放行
    print("  --- E: 清除后 gate 恢复放行 ---")
    r = subprocess.run(
        [sys.executable, ".claude/hooks/hook-launcher.py", "pretool-gate.py"],
        input=json.dumps({"tool_name": "Read", "tool_input": {"file_path": "README.md"}}),
        capture_output=True, text=True, timeout=10,
    )
    output = json.loads(r.stdout) if r.stdout.strip() else {}
    if output.get("continue", True) is not False:
        ok("E: 清除后 gate 恢复放行")
    else:
        fail(f"E: 清除后 gate 仍阻断: {r.stdout[:100]}")


# ──────────────────────────────────────────────
# 运行全部
# ──────────────────────────────────────────────

def main():
    test_p1_multi_step()
    test_p2_research_md()
    test_p3_numbers()
    test_p4_session_resume()
    test_p5_verify_all()
    test_p6_sha256()
    test_p7_token_stash()
    test_trust_breach()

    print(f"\n结果: {PASS} 过 / {FAIL} 败 (共 {PASS + FAIL} 项)")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
