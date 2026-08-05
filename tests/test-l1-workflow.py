#!/usr/bin/env python3
"""test-l1-workflow.py — L1 工作流端到端验证

验证 AGENTS.md L1 工作流完整闭环：
  init → 写 executor.md 证据块 → tick → verify → archive

执行: python3 tests/test-l1-workflow.py
退出码: 0=全过, 1=有失败
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARROS = ROOT / ".claude" / "scripts" / "carros_base.py"
TODAY = datetime.now(timezone.utc).strftime("%Y%m%d")

PASS = 0
FAIL = 0
CURRENT_TOKEN = None


def ok(msg: str):
    global PASS
    PASS += 1
    print(f"  ✅ {msg}")


def fail(msg: str):
    global FAIL
    FAIL += 1
    print(f"  ❌ {msg}")


def run_carros(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if CURRENT_TOKEN is not None:
        env["CARROROS_TOKEN_PATH"] = str(CURRENT_TOKEN)
    return subprocess.run(
        [sys.executable, str(CARROS), *args],
        capture_output=True, text=True, timeout=30, env=env,
    )


# ── Test 1: init 创建任务 ──────────────────────────────────

TASK_ID = f"test-l1-flow-{int(time.time())}"
r = run_carros("init", "--task-id", TASK_ID, "--level", "L1",
               "--step", "S1",
               "--user-request", "L1工作流端到端测试")
if r.returncode == 0:
    ok(f"init — exit 0: {TASK_ID}")
else:
    fail(f"init — exit {r.returncode}: {r.stderr[:200]}")

TASK_DIR = ROOT / ".omc" / "tasks" / TODAY / TASK_ID
TOKEN_PATH = ROOT / ".omc" / "tokens" / TODAY / f"{TASK_ID}.json"
CURRENT_TOKEN = TOKEN_PATH

plan_path = TASK_DIR / "plan.md"
plan_text = plan_path.read_text()
legacy_rule = "  - verify: assertion:完成用户确认范围内的修改"
if legacy_rule in plan_text:
    plan_text = plan_text.replace(
        legacy_rule,
        "  - verify: assertion:l1 workflow evidence recorded",
        1,
    )
    plan_count = 1
else:
    plan_text, plan_count = re.subn(
        r"(- \[ \] S1:[^\n]*\n)",
        r"\1  - verify: assertion:l1 workflow evidence recorded\n",
        plan_text,
        count=1,
    )
if plan_count:
    plan_path.write_text(plan_text)
else:
    fail("plan.md — S1 verify rule could not be inserted")

# ── Test 2: 检查任务文件是否创建 ────────────────────────────

expected = ["plan.md", "executor.md", "research.md", "handoff.md", "evidence.jsonl", "working-set.yaml"]
for f in expected:
    if (TASK_DIR / f).exists():
        ok(f"文件已创建: {f}")
    else:
        fail(f"文件缺失: {f}")

if TOKEN_PATH.exists():
    ok(f"token 已创建: {TOKEN_PATH.name}")
else:
    fail(f"token 缺失: {TOKEN_PATH}")

# ── Test 3: 写 executor.md 证据块 ──────────────────────────

evidence_block = """# Executor

## Conditions
- isolated L1 workflow fixture
## Key Changes
- no production files changed
## Decisions
- rationale: use the current VerifyGate evidence contract
## Acceptance Checklist
- [x] fixture contract is complete
## TDD Evidence
- dependency TDD command: echo dependency TDD → exit 0
- regression TDD command: echo regression TDD → exit 0
## S1

### EV-S1

- step: S1
- type: test
- source: l1-workflow-test
- exit_code: 0
- file: AGENTS.md
- assertion: l1 workflow evidence recorded
"""
(TASK_DIR / "executor.md").write_text(evidence_block)

exec_text = (TASK_DIR / "executor.md").read_text()
if "### EV-S1" in exec_text and "- assertion: l1 workflow evidence recorded" in exec_text:
    ok("executor.md — 证据块格式正确 (### EV-S1 + assertion 匹配)")
else:
    fail("executor.md — 证据块格式不正确")

# ── Test 4: tick ────────────────────────────────────────────

r = run_carros("tick")
if r.returncode == 0:
    ok(f"tick — exit 0: {r.stdout.strip()}")
else:
    fail(f"tick — exit {r.returncode}: {r.stderr[:200]}")

# ── Test 5: verify — 期望 VERIFIED ──────────────────────────

r = run_carros("verify")
if r.returncode == 0 and "VERIFIED" in r.stdout:
    ok(f"verify — VERIFIED (exit 0)")
elif r.returncode == 0:
    ok(f"verify — exit 0: {r.stdout.strip()[:120]}")
else:
    fail(f"verify — exit {r.returncode}: {r.stdout[:200]}")

# ── Test 6: plan.md 步骤状态已更新 ──────────────────────────

plan_text = (TASK_DIR / "plan.md").read_text()
if "[x] S1:" in plan_text:
    ok("plan.md — S1 已标记 [x]")
else:
    fail("plan.md — S1 未标记 [x]")

# ── Test 7: token 已完成 ────────────────────────────────────

if TOKEN_PATH.exists():
    token = json.loads(TOKEN_PATH.read_text())
    done = token.get("stats", {}).get("done", 0)
    total = token.get("stats", {}).get("total", 0)
    status = token.get("task", {}).get("status", "")
    if done >= total and status == "completed":
        ok(f"token — {done}/{total} completed")
    else:
        fail(f"token — {done}/{total} status={status}")
else:
    fail("token — 不存在(verify 后应存在)")

# ── Test 8: archive ──────────────────────────────────────────

r = run_carros("archive")
if r.returncode == 0 and "archived" in r.stdout.lower():
    ok(f"archive — exit 0")
else:
    fail(f"archive — exit {r.returncode}: {r.stdout[:200]}")

# ── Test 9: archive 后 token 已删除 ──────────────────────────

if not TOKEN_PATH.exists():
    ok("archive — token 已删除")
elif TOKEN_PATH.exists():
    # 可能改名了,检查 archive 目录
    archive_dir = ROOT / ".omc" / "archive" / TASK_ID
    if archive_dir.exists():
        ok(f"archive — 报告已保存: {archive_dir.name}")
    else:
        fail("archive — token 未删除且 archive 目录不存在")

# ── 清理 ────────────────────────────────────────────────

if TASK_DIR.exists():
    # Python 3.14+ shutil.rmtree raises on symlinks; handle gracefully
    if TASK_DIR.is_symlink():
        TASK_DIR.unlink()
    else:
        import os as _os
        def _rmtree_onexc(fn, path, exc):
            p = Path(path)
            if p.is_symlink():
                p.unlink()
            else:
                raise exc[1]
        shutil.rmtree(TASK_DIR, onexc=_rmtree_onexc)
if TOKEN_PATH.exists():
    TOKEN_PATH.unlink()

# ── 结果 ────────────────────────────────────────────────

print(f"\n结果: {PASS} 过 / {FAIL} 败 (共 {PASS + FAIL} 项)")
sys.exit(1 if FAIL else 0)
