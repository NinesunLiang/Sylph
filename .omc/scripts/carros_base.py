#!/usr/bin/env python3
"""
carros_base.py — CarrorOS Base 核心状态系统

L1 Workflow: Plan → Step → Verify → Archive

Usage:
    python3 .claude/scripts/carros_base.py init --task-id TASK_ID [--step S1 [S2 ...]] [--level L1_BASE|L2_ENHANCE]
    python3 .claude/scripts/carros_base.py status
    python3 .claude/scripts/carros_base.py tick
    python3 .claude/scripts/carros_base.py verify [--step S1]
    python3 .claude/scripts/carros_base.py archive [--force]
    python3 .claude/scripts/carros_base.py bench [scene]
    python3 .claude/scripts/carros_base.py lint [path]
    python3 .claude/scripts/carros_base.py help

Exit codes: 0 = ok, 1 = warnings, 2 = errors
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── Dependencies: sibling modules ───
_hook_dir = Path(__file__).parent
_omc_scripts = str(_hook_dir)
if _omc_scripts not in sys.path:
    sys.path.insert(0, _omc_scripts)

try:
    import omc_lint
except ImportError:
    omc_lint = None

try:
    import carros_utils
except ImportError:
    carros_utils = None

try:
    import task_state_tracker as tst
except ImportError:
    tst = None

# ─── Paths (cross-platform: pathlib) ───
# .claude/        → 可复用资产（hooks, scripts, reference）
# .omc/tokens/    → 任务令牌（单 json 文件）
# .omc/tasks/     → 任务文档系统（research/plan/executor + sub_task/ + state/）
_SCRIPT_DIR = Path(__file__).resolve().parent
if (_SCRIPT_DIR / ".." / ".." / ".omc").resolve().exists():
    # Script is in .claude/scripts/ -> PROJECT_ROOT is grandparent
    PROJECT_ROOT = (_SCRIPT_DIR / ".." / "..").resolve()
elif (_SCRIPT_DIR / ".." / ".omc").resolve().exists():
    # Script is in .omc/scripts/ -> PROJECT_ROOT is parent
    PROJECT_ROOT = (_SCRIPT_DIR / "..").resolve()
else:
    PROJECT_ROOT = Path.cwd()
OMC_ROOT = PROJECT_ROOT / ".omc"
OMC_TOKENS = OMC_ROOT / "tokens"
OMC_TASKS = OMC_ROOT / "tasks"

# 这些在 init 时根据 task_id + date 动态计算
TOKEN_PATH = None  # .omc/tokens/{date}/{task_id}.json
TASK_DIR = None    # .omc/tasks/{date}/{task_id}/
PLAN_PATH = None
EXECUTOR_PATH = None
RESEARCH_PATH = None
SUB_TASK_DIR = None
STATE_DIR = None
HANDOFF_PATH = None
AUDIT_DIR = None

_SCHEMA_VERSION = "v1.0"


def _get_date_str():
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _init_task_paths(task_id=None, task_dir=None):
    """根据 task_id、日期和可选的自定义 task_dir 初始化所有路径"""
    date_str = _get_date_str()
    tid = task_id or "unnamed"
    global TOKEN_PATH, TASK_DIR, PLAN_PATH, EXECUTOR_PATH, RESEARCH_PATH
    global SUB_TASK_DIR, STATE_DIR, HANDOFF_PATH, AUDIT_DIR
    TOKEN_PATH = OMC_TOKENS / date_str / f"{tid}.json"
    if task_dir:
        TASK_DIR = Path(task_dir)
    else:
        TASK_DIR = OMC_TASKS / date_str / tid
    PLAN_PATH = TASK_DIR / "plan.md"
    EXECUTOR_PATH = TASK_DIR / "executor.md"
    RESEARCH_PATH = TASK_DIR / "research.md"
    SUB_TASK_DIR = TASK_DIR / "sub_task"
    STATE_DIR = TASK_DIR / "state"
    HANDOFF_PATH = Path(".claude/session-handoff.md")
    AUDIT_DIR = STATE_DIR / "audit"

# ─── ANSI helpers ───
def _green(s): return f"\033[32m{s}\033[0m"
def _yellow(s): return f"\033[33m{s}\033[0m"
def _red(s): return f"\033[31m{s}\033[0m"
def _bold(s): return f"\033[1m{s}\033[0m"

# ═══════════════════════════════════════════
# Token helpers
# ═══════════════════════════════════════════

def _default_token(task_id=None, level="L1_BASE", steps=None):
    now = datetime.now(timezone.utc)
    suffix = now.strftime("%Y%m%d")
    tid = task_id or f"sess_{suffix}_0000"
    if steps is None:
        steps = ["S1"]
    return {
        "schema_version": _SCHEMA_VERSION,
        "session": {
            "id": tid,
            "level": level,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
        "task_dir": str(TASK_DIR) if TASK_DIR else "",
        "status": "active",
        "stats": {
            "done": 0,
            "total": len(steps),
            "tick": 0,
        },
        "steps": [{"id": s, "status": "pending"} for s in steps],
    }


def _load_token(path=None):
    p = Path(path) if path else TOKEN_PATH
    if p and p.exists():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _save_token(token, path=None):
    p = Path(path) if path else TOKEN_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    token["session"]["updated_at"] = datetime.now(timezone.utc).isoformat()
    p.write_text(json.dumps(token, indent=2, ensure_ascii=False) + "\n")


def now_iso():
    return carros_utils.now_iso() if carros_utils else datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_handoff(token, plan_summary=None):
    """写入 session-handoff.md — 委托 carros_utils"""
    if carros_utils:
        # 兼容新版 token（task.current_step 替代 steps 数组）
        if "steps" not in token and "task" in token:
            tok_v2 = {
                "session": token.get("session", {}),
                "plan": {
                    "total": token.get("stats", {}).get("total", 0),
                    "done": token.get("stats", {}).get("done", 0),
                    "current_step": token.get("task", {}).get("current_step"),
                    "blocked": token.get("task", {}).get("blocked"),
                    "status": token.get("task", {}).get("status", "unknown"),
                },
            }
            carros_utils.write_handoff(tok_v2, PLAN_PATH, HANDOFF_PATH)
        else:
            carros_utils.write_handoff(token, PLAN_PATH, HANDOFF_PATH)
        return
    # fallback — inline
    HANDOFF_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if "steps" in token:
        done = token["stats"]["done"]
        total = token["stats"]["total"]
        steps_summary = "\n".join(
            f"  {'✅' if s['status'] == 'completed' else '⬜'} {s['id']}: {s['status']}"
            for s in token["steps"]
        )
    else:
        done = token.get("stats", {}).get("done", 0)
        total = token.get("stats", {}).get("total", 0)
        current = token.get("task", {}).get("current_step", "?")
        steps_summary = f"  current_step: {current} ({done}/{total})"
    plan = ""
    if PLAN_PATH.exists():
        plan = PLAN_PATH.read_text()[:300]
    content = (
        f"# Session Handoff: {token.get('session', {}).get('id', 'unknown')}\n"
        f"\n"
        f"**Updated:** {now}\n"
        f"**Level:** {token.get('session', {}).get('level', '?')}\n"
        f"**Progress:** {done}/{total} steps\n"
        f"\n"
        f"## Steps\n"
        f"{steps_summary}\n"
        f"\n"
        f"## Plan (condensed)\n"
        f"{plan}\n"
        f"\n"
        f"---\n"
        f"_Auto-generated by carros_base.py_\n"
    )
    HANDOFF_PATH.write_text(content)


# ═══════════════════════════════════════════
# Plan / Executor helpers
# ═══════════════════════════════════════════

def _write_default_plan(steps=None):
    """创建默认 plan.md 模板"""
    if steps is None:
        steps = ["S1"]
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Plan\n", "", "## Goal\n\n", "## Scope\n\n"]
    lines.append("## Steps\n")
    for s in steps:
        lines.append(f"- [ ] {s}: \n")
    lines.append("\n## Verify\n")
    for s in steps:
        lines.append(f"- {s}: \n")
    lines.append("\n---\n")
    lines.append("> 冻结规则：不改 scope、不改 step 顺序、不改 verify 条件。\n")
    PLAN_PATH.write_text("".join(lines))


def _write_default_executor():
    """创建空 executor.md 证据账簿"""
    EXECUTOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = """# Executor Evidence Ledger

> schema_version: v1.0
> 每步必须包含标准 evidence block。

## S1

**证据块：**
```
- action:
- file:
- command:
- output:
- status: [PASS/FAIL]
```

---
"""
    EXECUTOR_PATH.write_text(content)


def _write_default_research():
    """创建 research.md — 子任务也可引用 src.md"""
    RESEARCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = """# Research

> 事实层：技术决策、架构边界、参考来源

## 背景

## 约束

## 已知信息
"""
    RESEARCH_PATH.write_text(content)


def _init_task_dirs():
    """初始化任务子目录：sub_task/ + state/ + state/audit"""
    for d in [SUB_TASK_DIR, STATE_DIR, AUDIT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _inject_plan_step(step_id):
    """为 plan.md 补充 step，当 step 不在已有列表时追加"""
    if not PLAN_PATH.exists():
        _write_default_plan([step_id])
        return
    plan = PLAN_PATH.read_text()
    pattern = r"- \[ \] " + re.escape(step_id) + r":"
    if re.search(pattern, plan):
        return  # already exists
    # append before the last line (freeze note)
    lines = plan.rstrip().split("\n")
    insert_idx = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("## Verify"):
            insert_idx = i
            break
    lines.insert(insert_idx, f"- [ ] {step_id}: ")
    lines.insert(insert_idx + 1, "")
    PLAN_PATH.write_text("\n".join(lines))


# ═══════════════════════════════════════════
# Audit helpers
# ═══════════════════════════════════════════

def _write_audit(event_type, data, fallback=False):
    """追加审计事件到当天 JSONL — 委托 carros_utils"""
    if carros_utils:
        # 如果 AUDIT_DIR 是 None 但 fallback=True，直接写本地
        ad = AUDIT_DIR
        if ad is None and fallback:
            ad = OMC_ROOT / "state" / "audit"
        if ad is not None:
            carros_utils.write_audit(ad, event_type, data, _SCHEMA_VERSION)
            return
    # fallback — inline
    if AUDIT_DIR is None and fallback:
        ad = OMC_ROOT / "state" / "audit"
    else:
        ad = AUDIT_DIR
    if ad is None:
        return  # 无法写 audit
    ad.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    audit_file = ad / f"{date_str}.jsonl"
    record = {
        "schema_version": _SCHEMA_VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "data": data,
    }
    with open(audit_file, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════
# Commands
# ═══════════════════════════════════════════

def _run_plan_builder(intake_decision, user_request, task_id, feature=None):
    """调用 PlanBuilder 生成 plan.md + 更新 token.json + 写 audit"""
    import subprocess as sb
    import tempfile

    # 暂存 IntakeDecision JSON
    intake_json = json.dumps(intake_decision, ensure_ascii=False)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(intake_json)
        intake_path = f.name

    try:
        plan_builder = _hook_dir / "plan_builder.py"
        if not plan_builder.exists():
            return None, "plan_builder.py not found"

        # 将 token_path 作为环境变量传给 plan_builder
        env = os.environ.copy()
        env["CARROROS_TOKEN_PATH"] = str(TOKEN_PATH) if TOKEN_PATH else ""

        cmd = [sys.executable, str(plan_builder), intake_path, user_request, task_id]
        if feature:
            cmd.append(feature)

        result = sb.run(cmd, capture_output=True, text=True, timeout=15, env=env)
        if result.returncode != 0:
            return None, result.stderr or "plan_builder failed"

        # PlanBuilder 已写入 plan.md + token.json + audit
        return result.stdout, None
    finally:
        os.unlink(intake_path)


def cmd_init(task_id, level="L1_BASE", steps=None, user_request=None, task_dir=None, feature=None):
    """初始化任务 — IntakeGate 分级 → PlanBuilder 生成冻结计划"""
    _init_task_paths(task_id=task_id, task_dir=task_dir)

    intake_decision_data = None

    # IntakeGate 前置分级（如有 user_request）
    if user_request:
        try:
            import subprocess
            intake_script = _hook_dir / "intake_gate.py"
            if intake_script.exists():
                cmd = [sys.executable, str(intake_script), user_request]
                if level == "L2_ENHANCE":
                    cmd.append("--enhance-available")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode in (0, 1):
                    try:
                        intake = json.loads(result.stdout)
                        decision = intake["decision"]
                        print(f"   IntakeGate: {decision} (risk={intake['risk_level']})")
                        for r in intake.get("reasons", []):
                            print(f"     reason: {r}")

                        if decision == "BLOCKED":
                            print(_red(f"❌ BLOCKED: {intake['next_action']}"))
                            return 2
                        elif decision == "ASK_USER":
                            print(_yellow(f"⚠  ASK_USER: {intake['next_action']}"))
                            for c in intake.get("required_confirmations", []):
                                print(f"     ⚠ 确认: {c}")
                            print(_yellow("等待用户补充信息后重新执行 init"))
                            # 仍然生成 plan draft 供参考
                            intake_decision_data = intake
                        else:
                            # L1 / L2 — 正常走 PlanBuilder
                            intake_decision_data = intake
                    except (json.JSONDecodeError, KeyError) as e:
                        print(_yellow(f"   ⚠ IntakeGate parse warning: {e}"))
        except subprocess.TimeoutExpired:
            print(_yellow("   ⚠ IntakeGate timed out (10s), continuing with default level"))
        except Exception:
            pass

    # 将其他 active token 标记为 archived（避免多 token 冲突）
    archived_count = 0
    for f in sorted(OMC_TOKENS.rglob("*.json")):
        try:
            t = json.loads(f.read_text())
            if t.get("status") == "active":
                t["status"] = "archived"
                f.write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n")
                archived_count += 1
        except (json.JSONDecodeError, OSError):
            continue
    if archived_count > 0:
        print(f"   Archived previous tokens: {archived_count} total")

    # ── PlanBuilder 生成冻结计划 ──
    if intake_decision_data:
        plan_md_output, pb_err = _run_plan_builder(intake_decision_data, user_request, task_id, feature)
        if pb_err:
            print(_yellow(f"   ⚠ PlanBuilder warning: {pb_err}"))
            # fallback — 使用旧方式
            token = _default_token(task_id=task_id, level=level, steps=steps)
            _save_token(token)
            _write_default_plan(steps=steps)
            _write_default_executor()
            _write_default_research()
        else:
            print(_green(f"   PlanBuilder: plan.md + token generated"))
            # plan_builder.py 已写入 plan.md + .omc/state/token.json + audit
            # 但还需要创建 task dirs 和 executor.md/research.md/handoff
            _write_default_executor()
            _write_default_research()
    else:
        # 无 user_request 或 intake 失败 — 使用旧方式
        token = _default_token(task_id=task_id, level=level, steps=steps)
        _save_token(token)
        _write_default_plan(steps=steps)
        _write_default_executor()
        _write_default_research()

    _init_task_dirs()
    _write_handoff(_load_token() or _default_token(task_id=task_id, level=level, steps=steps))
    print(_green(f"✅ Initialized: {task_id}"))
    # 从 token 读取最终信息
    loaded = _load_token()
    if loaded:
        total = loaded.get("stats", {}).get("total", 0)
        task_blocked = loaded.get("task", {}).get("blocked")
        if task_blocked:
            print(f"   Status: {loaded.get('task', {}).get('status', 'unknown')}")
        print(f"   Steps: {total} total")
    print(f"   Token: {TOKEN_PATH}")
    print(f"   Task:  {TASK_DIR}")
    print(f"   Plan:  {PLAN_PATH}")
    print(f"   Exec:  {EXECUTOR_PATH}")
    return 0


def _find_latest_token(require_active=True):
    """扫描 tokens 目录，找到日期最新且活跃的 token

    require_active=True: 只返回 status=active 的 token（首选）
    require_active=False: 返回任何一个有效的 token（作为回退）

    排序规则：按文件 mtime 倒序（最新写的优先），而非文件名排序
    """
    OMC_TOKENS.mkdir(parents=True, exist_ok=True)
    if not OMC_TOKENS.exists():
        return None, None

    # 收集所有 token 文件，按 mtime 排序
    candidates = []
    for dd in sorted(OMC_TOKENS.iterdir(), reverse=True):
        if dd.is_dir():
            for jf in dd.glob("*.json"):
                try:
                    candidates.append((jf.stat().st_mtime, jf))
                except OSError:
                    continue

    # 按 mtime 倒序
    candidates.sort(key=lambda x: x[0], reverse=True)

    fallback = None
    for _, jf in candidates:
        try:
            token = json.loads(jf.read_text())
            if token.get("status") == "active":
                return token, jf
            if fallback is None:
                fallback = (token, jf)
        except (json.JSONDecodeError, OSError):
            continue

    if fallback and not require_active:
        return fallback
    return None, None


def cmd_status():
    """展示当前任务状态"""
    if not TOKEN_PATH or not TOKEN_PATH.exists():
        token, found_path = _find_latest_token()
        if token and found_path:
            _init_task_paths(task_id=token.get("session", {}).get("id", "unknown"))
        else:
            print(_yellow("⚠  No active task"))
            return 0
    token = _load_token()
    if not token:
        print(_yellow("⚠  No active task (token.json not found)"))
        return 0
    s = token.get("stats", {})
    status_top = token.get("status", "?")
    status_icon = _green("●") if status_top == "active" else _red("●")
    print(f"{status_icon} Task: {token.get('session', {}).get('id', '?')} [{token.get('session', {}).get('level', '?')}]")
    print(f"   Status: {status_top}")
    print(f"   Progress: {s.get('done', 0)}/{s.get('total', 0)} steps completed")
    # 兼容新旧 token 格式
    if "steps" in token:
        print(f"   Ticks: {s.get('tick', 0)}")
        for step in token["steps"]:
            icon = _green("✔") if step["status"] == "completed" else (_yellow("◷") if step["status"] == "running" else "○")
            print(f"   {icon} {step['id']}: {step['status']}")
    else:
        current_step = token.get("task", {}).get("current_step")
        task_status = token.get("task", {}).get("status")
        blocked = token.get("task", {}).get("blocked")
        current = current_step or "?"
        print(f"   Current Step: {current}")
        print(f"   Task Status: {task_status}")
        if blocked:
            print(f"   Blocked: {blocked}")
    # task-state 追踪展示
    if tst:
        state_info = tst.format_status(token, TOKEN_PATH)
        if state_info:
            print(state_info)
    return 0


def cmd_tick():
    """递增 tick 计数器 + 自动追踪当前步骤状态"""
    if not TOKEN_PATH or not TOKEN_PATH.exists():
        token, _ = _find_latest_token()
        if token:
            _init_task_paths(task_id=token.get("session", {}).get("id", "unknown"))
        else:
            print(_red("❌ No active task"))
            return 2
    token = _load_token()
    if not token:
        print(_red("❌ No active task"))
        return 2

    # 找当前 pending 步骤 — 记录追踪起点
    current_step = None
    if "steps" in token:
        for s in token["steps"]:
            if s["status"] == "pending":
                current_step = s["id"]
                break

    if "tick" in token.get("stats", {}):
        token["stats"]["tick"] += 1
        print(f"   Tick: {token['stats']['tick']}")
    else:
        token["stats"]["turns"] = token["stats"].get("turns", 0) + 1
        print(f"   Turn: {token['stats']['turns']}")
    _save_token(token)

    # task-state: 记录步骤开始追踪
    if current_step and tst:
        tst.mark_step_started(TOKEN_PATH, current_step)
        print(f"   ◷ Tracking {current_step} (use 'verify' to complete)")
    return 0


def cmd_verify(step_id=None):
    """验证 step 完成 — 标记 plan.md [x] + 写 audit"""
    if not TOKEN_PATH or not TOKEN_PATH.exists():
        token, _ = _find_latest_token()
        if token:
            _init_task_paths(task_id=token.get("session", {}).get("id", "unknown"))
        else:
            print(_red("❌ No active task"))
            return 2
    token = _load_token()
    if not token:
        print(_red("❌ No active task"))
        return 2

    if not PLAN_PATH.exists():
        print(_red("❌ plan.md not found"))
        return 2

    plan = PLAN_PATH.read_text()
    lines = plan.split("\n")

    if step_id:
        targets = [step_id]
    else:
        # 找第一个 pending 的 step — 兼容新旧格式
        targets = []
        if "steps" in token:
            for step in token["steps"]:
                if step["status"] == "pending":
                    targets.append(step["id"])
                    break
        else:
            current = token.get("task", {}).get("current_step")
            if current:
                targets.append(current)
        if not targets:
            print(_yellow("⚠  All steps already completed"))
            return 0

    verified_any = False
    for target in targets:
        pattern = re.compile(r"^- \[ \] " + re.escape(target) + r":", re.MULTILINE)
        replacement = f"- [x] {target}:"
        new_plan, count = pattern.subn(replacement, plan)
        if count > 0:
            plan = new_plan
            # 更新 token — 兼容新旧格式
            if "steps" in token:
                found = False
                for step in token["steps"]:
                    if step["id"].split(":")[0].strip() == target:
                        step["status"] = "completed"
                        found = True
                        break
                if not found:
                    token["steps"].append({"id": target, "status": "completed"})
                token["stats"]["done"] = sum(1 for s in token["steps"] if s["status"] == "completed")
            else:
                # 新 token 格式 — 递增 done 计数器
                token["stats"]["done"] = token["stats"].get("done", 0) + 1
                if token["stats"]["done"] >= token["stats"]["total"]:
                    token["task"]["status"] = "completed"
            _write_audit("verify", {"step": target, "result": "VERIFIED"})
            print(_green(f"✅ {target}: VERIFIED"))
            # task-state: 标记完成
            if tst:
                tst.mark_step_completed(TOKEN_PATH, target)
                verdict = tst.format_tick_verdict(TOKEN_PATH, target)
                if verdict:
                    print(verdict)
            verified_any = True
        else:
            print(_yellow(f"⚠  {target}: not found in plan.md"))

    if verified_any:
        PLAN_PATH.write_text(plan)
        _save_token(token)
        _write_handoff(token)
    return 0


def cmd_archive(force=False):
    """归档任务 — archive = lint + verify-summary + final-report + tombstone"""
    if not TOKEN_PATH or not TOKEN_PATH.exists():
        token, _ = _find_latest_token()
        if token:
            _init_task_paths(task_id=token.get("session", {}).get("id", "unknown"))
        else:
            print(_red("❌ No active task"))
            return 2
    print(_bold("Archiving task..."))

    # Step 1: run lint
    if not force:
        lint_ok = cmd_lint()
        if lint_ok != 0:
            print(_red("❌ Lint failed. Use --force to archive anyway."))
            return 2
    else:
        print(_yellow("⚠  --force: skipping lint"))

    token = _load_token()
    if not token:
        print(_red("❌ No active task"))
        return 2

    # Step 2: check all steps completed — 兼容新旧格式
    if not force:
        if "steps" in token:
            pending = [s for s in token["steps"] if s["status"] != "completed"]
        else:
            pending = []
            # 新 token 格式没有 steps 数组，基于 stats 判断
            if token.get("stats", {}).get("done", 0) < token.get("stats", {}).get("total", 0):
                pending = ["current_step not completed"]
        if pending:
            if "steps" in token:
                print(_red(f"❌ Steps not completed: {[s['id'] for s in pending]}"))
            else:
                print(_red(f"❌ Steps not completed: {pending}"))
            return 2
    else:
        print(_yellow("⚠  --force: skipping step completion check"))

    # Step 3: generate final report
    task_sid = token.get("session", {}).get("id", "unknown")
    archive_dir = OMC_ROOT / "archive" / task_sid
    archive_dir.mkdir(parents=True, exist_ok=True)
    final_report = _generate_final_report(token)
    report_path = archive_dir / "final-report.md"
    report_path.write_text(final_report)
    print(_green(f"✅ Final report: {report_path}"))

    # Step 4: tombstone — 复制 token 到 archive 目录作为墓碑
    token["status"] = "archived"
    token["archived_at"] = datetime.now(timezone.utc).isoformat()
    _save_token(token)

    # 按方案 10.md L987-1000 写 token.final.json + token.tombstone.json
    import shutil
    write_json_atomic = lambda p, d: (p.parent.mkdir(parents=True, exist_ok=True), p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n"))
    write_json_atomic(archive_dir / "token.final.json", token)
    write_json_atomic(
        archive_dir / "token.tombstone.json",
        {
            "task_id": token["session"]["id"],
            "previous_token": str(TOKEN_PATH),
            "status": "archived",
            "archived_at": now_iso(),
            "final_report": str(archive_dir / "final-report.md"),
            "final_verdict": "ARCHIVED",
            "level": token.get("session", {}).get("level", "unknown_level"),
        },
    )
    for optional in ["plan.md", "executor.md"]:
        src = TASK_DIR / optional if TASK_DIR else None
        if src and src.exists():
            shutil.copy2(src, archive_dir / optional)
    handoff_src = HANDOFF_PATH if HANDOFF_PATH else Path(".claude/session-handoff.md")
    if handoff_src.exists():
        shutil.copy2(handoff_src, archive_dir / "session-handoff.md")

    _write_audit("archive", {"task_id": token["session"]["id"], "result": "ARCHIVED"})
    _write_handoff(token)

    # Step 5: 删除 active token — 方案 10.md L1012: token_path.unlink(missing_ok=True)
    token_path_str = str(TOKEN_PATH)
    TOKEN_PATH.unlink(missing_ok=True)
    print(_green(f"✅ Token 已删除: {token_path_str}"))

    # Step 6: 输出 {"continue": false} — 给 main agent 正式结束通知
    print(json.dumps({"continue": False}))
    print(_green("✅ Task archived"))
    return 0


def _generate_final_report(token):
    """生成归档报告 — 委托 carros_utils"""
    if carros_utils:
        return carros_utils.generate_final_report(token)
    # fallback — inline
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sid = token.get("session", {}).get("id", "unknown")
    level = token.get("session", {}).get("level", "?")
    status = token.get("status", "?")
    stats = token.get("stats", {})

    if "steps" in token:
        done = token["stats"]["done"]
        total = token["stats"]["total"]
        tick = token.get("stats", {}).get("tick", 0)
        step_lines = []
        for step in token["steps"]:
            icon = "✅" if step["status"] == "completed" else "⬜"
            step_lines.append(f"{icon} {step['id']}: {step['status']}")
    else:
        done = stats.get("done", 0)
        total = stats.get("total", 0)
        tick = stats.get("turns", 0)
        current = token.get("task", {}).get("current_step", "?")
        task_status = token.get("task", {}).get("status", "?")
        step_lines = [f"  current_step: {current} ({task_status})"]

    lines = [
        f"# Final Report: {sid}",
        "",
        f"**Archived at:** {now}",
        f"**Level:** {level}",
        f"**Status:** {status}",
        "",
        "## Summary",
        "",
        f"Completed {done}/{total} steps in {tick} ticks.",
        "",
        "## Steps",
        "",
    ]
    lines.extend(step_lines)
    lines.append("")
    lines.append("## Audit Trail")
    lines.append("")
    lines.append("See `.omc/state/audit/` for full event log.")
    lines.append("")
    lines.append("---")
    lines.append("_Generated by carros_base.py archive_")
    return "\n".join(lines)


def cmd_lint(path=None):
    """统一 lint — 委托 omc_lint 模块"""
    if omc_lint is None:
        print(_red("❌ omc_lint module not available"))
        return 2

    target = path or str(PROJECT_ROOT)
    try:
        result = omc_lint.run_lint(target)
        print(result["output"])
        return result["exit_code"]
    except Exception as e:
        print(_red(f"❌ Lint error: {e}"))
        return 2


BENCH_SCENES = {
    "01_doc_update": {
        "description": "纯文档更新",
        "steps": ["S1"],
    },
    "02_single_file_fix": {
        "description": "单文件修复",
        "steps": ["S1"],
    },
    "03_multi_file_test": {
        "description": "多文件协同修改",
        "steps": ["S1", "S2"],
    },
    "04_failure_then_repair": {
        "description": "失败后修复",
        "steps": ["S1", "S2"],
    },
    "05_compact_resume": {
        "description": "compact/resume 恢复",
        "steps": ["S1", "S2", "S3"],
    },
    "06_fallback_downgrade": {
        "description": "降级场景",
        "steps": ["S1"],
    },
    "07_archive": {
        "description": "归档闭环",
        "steps": ["S1", "S2", "S3", "S4", "S5"],
    },
}


def cmd_bench(scene=None):
    """运行 bench 基准测试—验证治理系统基本链路"""
    import subprocess

    scenes = BENCH_SCENES
    if scene:
        if scene not in scenes:
            print(_red(f"❌ Unknown bench scene: {scene}"))
            print(f"   Available: {', '.join(scenes.keys())}")
            return 2
        scenes = {scene: scenes[scene]}

    results = []
    for scene_id, cfg in scenes.items():
        print(_bold(f"\n{'='*60}"))
        print(_bold(f"▶ Bench: {scene_id} — {cfg['description']}"))
        print(f"{'='*60}")

        task_id = f"bench-{scene_id[:2]}"
        steps = cfg["steps"]

        # 1. init
        step_args = " ".join(f"--step {s}" for s in steps)
        cmd = f"python3 .claude/scripts/carros_base.py init --task-id {task_id} {step_args} --force"
        print(_yellow(f"    init..."))
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if r.returncode != 0:
            print(_red(f"    ❌ init failed: {r.stderr[:200]}"))
            results.append((scene_id, "FAIL_INIT"))
            continue

        # 2. status
        r = subprocess.run("python3 .claude/scripts/carros_base.py status", shell=True,
                          capture_output=True, text=True, cwd=PROJECT_ROOT)
        if r.returncode != 0:
            print(_red(f"    ❌ status failed"))
            results.append((scene_id, "FAIL_STATUS"))
            continue
        print(f"    {r.stdout.strip().split(chr(10))[0]}")

        # 3. tick
        r = subprocess.run("python3 .claude/scripts/carros_base.py tick", shell=True,
                          capture_output=True, text=True, cwd=PROJECT_ROOT)
        if r.returncode != 0:
            print(_yellow(f"    ⚠ tick failed"))

        # 4. verify each step
        all_verified = True
        for s in steps:
            r = subprocess.run(f"python3 .claude/scripts/carros_base.py verify --step {s}",
                              shell=True, capture_output=True, text=True, cwd=PROJECT_ROOT)
            if r.returncode == 0:
                print(f"    ✅ {s}: VERIFIED")
            else:
                print(_red(f"    ❌ {s}: {r.stdout[:100]}"))
                all_verified = False

        if not all_verified:
            results.append((scene_id, "FAIL_VERIFY"))
            continue

        # 5. lint
        r = subprocess.run("python3 .claude/scripts/carros_base.py lint", shell=True,
                          capture_output=True, text=True, cwd=PROJECT_ROOT)
        lint_ok = r.returncode == 0
        if lint_ok:
            print(f"    ✅ lint: PASS")
        else:
            print(_yellow(f"    ⚠ lint: {r.stdout.strip()[:100]}"))

        # 6. archive
        r = subprocess.run("python3 .claude/scripts/carros_base.py archive --force", shell=True,
                          capture_output=True, text=True, cwd=PROJECT_ROOT)
        if r.returncode == 0:
            print(_green(f"    ✅ archive: OK"))
            results.append((scene_id, "PASS"))
        else:
            print(_red(f"    ❌ archive: {r.stdout[:200]}"))
            results.append((scene_id, "FAIL_ARCHIVE"))

    # Summary
    print(_bold(f"\n{'='*60}"))
    print(_bold("Bench Results"))
    print(f"{'='*60}")
    passed = sum(1 for _, s in results if s == "PASS")
    failed = sum(1 for _, s in results if s != "PASS")
    for scene_id, status in results:
        icon = _green("✅") if status == "PASS" else _red("❌")
        print(f"  {icon} {scene_id}: {status}")
    print(f"\n  {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


def cmd_gate():
    """PreActionGate - 对 action_spec 做执行前安全裁决

    读取当前 active token，创建临时 action_spec 文件，
    调用 pre_action_gate.py 做裁决。

    用法:
        python3 .omc/scripts/carros_base.py gate --action-type write_file --paths README.md --step S1 --intent "update docs"
    """
    import subprocess
    import tempfile

    argv = sys.argv[sys.argv.index("gate") + 1:]
    p = {}
    i = 0
    while i < len(argv):
        if argv[i] == "--action-type" and i + 1 < len(argv):
            p["action_type"] = argv[i + 1]; i += 2
        elif argv[i] == "--command" and i + 1 < len(argv):
            p["command"] = argv[i + 1]; i += 2
        elif argv[i] == "--paths" and i + 1 < len(argv):
            p["paths"] = argv[i + 1].split(","); i += 2
        elif argv[i] == "--step" and i + 1 < len(argv):
            p["current_step"] = argv[i + 1]; i += 2
        elif argv[i] == "--intent" and i + 1 < len(argv):
            p["intent"] = argv[i + 1]; i += 2
        elif argv[i] == "--risk-hint" and i + 1 < len(argv):
            p["risk_hint"] = argv[i + 1]; i += 2
        elif argv[i] == "--network" and i + 1 < len(argv):
            p["requires_network"] = argv[i + 1].lower() in ("true", "1", "yes"); i += 2
        elif argv[i] == "--production" and i + 1 < len(argv):
            p["requires_production"] = argv[i + 1].lower() in ("true", "1", "yes"); i += 2
        elif argv[i] == "--database" and i + 1 < len(argv):
            p["requires_database"] = argv[i + 1].lower() in ("true", "1", "yes"); i += 2
        else:
            i += 1

    if "action_type" not in p:
        print(_red("Missing --action-type"))
        return 2

    p.setdefault("paths", [])
    p.setdefault("intent", "")
    p.setdefault("current_step", "S1")

    spec_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="preaction-"
    )
    json.dump(p, spec_file, ensure_ascii=False, indent=2)
    spec_path = spec_file.name
    spec_file.close()

    # 找到当前 active token
    _token_data, token_path = _find_latest_token()
    if token_path is None:
        print(_yellow("No active token found — running without token context"))
        token_arg = []
    else:
        token_arg = ["--token", str(token_path)]

    try:
        gate_script = _hook_dir / "pre_action_gate.py"
        cmd = [sys.executable, str(gate_script), spec_path] + token_arg
        r = subprocess.run(cmd, capture_output=True, text=True)
        output = r.stdout.strip() if r.stdout else r.stderr.strip()
        if output:
            print(output)
        return r.returncode
    finally:
        Path(spec_path).unlink(missing_ok=True)


def _sub_token(task_dir: str, parent_id: str, step_id: str, plan_text: str = "") -> dict:
    """生成 subagent token.json — 子代理的启动契约

    subagent 读这个文件知道：为谁工作（parent_id）、
    要做什么（subtask.plan）、被允许做什么（session.level）
    """
    now = datetime.now(timezone.utc)
    return {
        "schema_version": _SCHEMA_VERSION,
        "session": {
            "id": f"{parent_id}-{step_id}",
            "level": "L1_SUB",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
        "parent": {
            "task_dir": task_dir,
            "task_id": parent_id,
            "step_id": step_id,
        },
        "subtask": {
            "plan": plan_text,
        },
        "status": "active",
        "stats": {"done": 0, "total": 1, "tick": 0},
    }


def _result_template() -> dict:
    """result.json 模板 — subagent 完成工作后写"""
    return {
        "status": "running",
        "summary": "",
        "evidence": [],
        "files_changed": [],
        "failure": None,
        "completed_at": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def cmd_dispatch():
    """分发子任务到 subagent — 创建 sub_task/{step} 目录 + token + plan

    用法:
        python3 .claude/scripts/carros_base.py dispatch --step S1 [--text \"要做什么\"]

    产生文件:
        .omc/tasks/{date}/{task}/sub_task/sub-{step}/
            token.json     — subagent 契约（parent/plan/约束）
            result.json    — subagent 汇报模板
            executor.md    — 空证据账本

    subagent 启动后工作:
        1. 读 token.json（知道 parent_task 和 plan）
        2. 按 plan 执行
        3. 写 executor.md（证据）
        4. 更新 result.json（status=completed + summary + evidence）
        5. 更新 token.json（status=completed）
    """
    global TASK_DIR, TOKEN_PATH, SUB_TASK_DIR

    # 确保有 active token
    if not TOKEN_PATH or not TOKEN_PATH.exists():
        token, tp = _find_latest_token()
        if not token:
            print(_red("❌ No active main task. Run 'init' first."))
            return 2
        _init_task_paths(task_id=token.get("session", {}).get("id", "unknown"))

    # 解析参数
    argv = sys.argv[sys.argv.index("dispatch") + 1:]
    step_id = "S1"
    plan_text = ""
    i = 0
    while i < len(argv):
        if argv[i] == "--step" and i + 1 < len(argv):
            step_id = argv[i + 1]; i += 2
        elif argv[i] == "--text" and i + 1 < len(argv):
            plan_text = argv[i + 1]; i += 2
        else:
            i += 1

    # 创建 sub_task 目录
    sub_dir = SUB_TASK_DIR / f"sub-{step_id}"
    sub_dir.mkdir(parents=True, exist_ok=True)

    # 生成 subagent token
    token_data = _sub_token(
        task_dir=str(TASK_DIR),
        parent_id=token.get("session", {}).get("id", "unknown"),
        step_id=step_id,
        plan_text=plan_text,
    )

    # 写入 token.json
    token_path = sub_dir / "token.json"
    token_path.write_text(json.dumps(token_data, ensure_ascii=False, indent=2))

    # 写入 result.json（模板）
    result_data = _result_template()
    result_data["parent"] = {
        "task_dir": str(TASK_DIR),
        "token_path": str(TOKEN_PATH),
    }
    result_path = sub_dir / "result.json"
    result_path.write_text(json.dumps(result_data, ensure_ascii=False, indent=2))

    # 写入 executor.md（空账本）
    exec_path = sub_dir / "executor.md"
    if not exec_path.exists():
        exec_path.write_text(
            f"# Executor: {token_data['session']['id']}\n"
            f"## Parent: {token_data['parent']['task_id']}\n\n"
        )

    # 更新 main token：记录该 step 已分配 subagent
    main_token = _load_token()
    if main_token and "steps" in main_token:
        for s in main_token["steps"]:
            if s["id"] == step_id:
                s["status"] = "running"
                s["subagent_path"] = str(sub_dir)
                break
        _save_token(main_token)

    print(_green(f"✅ Dispatched {step_id} → {sub_dir}"))
    print(f"   token:  {token_path}")
    print(f"   result: {result_path}")
    print(f"   Subagent reads token.json for task, writes result.json on completion")
    return 0


def cmd_poll():
    """轮询所有 subagent 状态 — main agent 追踪 subagent 进度

    读每个 sub_task/sub-*/result.json，展示汇总状态。
    支持 --verbose 展示每个 subagent 的关键证据。

    用法:
        python3 .claude/scripts/carros_base.py poll [--verbose]
    """
    global SUB_TASK_DIR, TASK_DIR

    if not SUB_TASK_DIR or not SUB_TASK_DIR.exists():
        # 尝试从当前 token 获取
        tok, _ = _find_latest_token()
        if tok:
            td = tok.get("task_dir")
            if td:
                SUB_TASK_DIR = Path(td) / "sub_task"
        if not SUB_TASK_DIR or not SUB_TASK_DIR.exists():
            print(_yellow("⚠  No sub tasks found"))
            return 0

    verbose = "--verbose" in sys.argv

    sub_dirs = sorted([d for d in SUB_TASK_DIR.iterdir() if d.is_dir()])
    if not sub_dirs:
        print(_yellow("⚠  No sub tasks found"))
        return 0

    print(_bold(f"SubAgent Status: {len(sub_dirs)} task(s)"))
    print(f"{'─' * 50}")

    total_done = 0
    total_failed = 0
    for sd in sub_dirs:
        name = sd.name
        result_path = sd / "result.json"
        token_path = sd / "token.json"

        if not result_path.exists():
            print(f"   ○ {name}: no result yet")
            continue

        try:
            result = json.loads(result_path.read_text())
            status = result.get("status", "unknown")

            if status == "completed":
                icon = _green("✔")
                total_done += 1
            elif status == "failed":
                icon = _red("✘")
                total_failed += 1
            elif status == "running":
                icon = _yellow("◷")
            else:
                icon = "○"

            summary = result.get("summary", "")
            parts = [f"   {icon} {name}: {status}"]
            if summary:
                parts.append(f"→ {summary[:60]}")
            if verbose and result.get("files_changed"):
                parts.append(f"files: {', '.join(result['files_changed'][:3])}")
            if result.get("failure"):
                parts.append(_red(f"FAIL: {result['failure'][:80]}"))

            print("  ".join(parts))

        except (json.JSONDecodeError, OSError) as e:
            print(f"   ⚠ {name}: read error ({e})")

    print(f"{'─' * 50}")
    print(f"   {total_done} completed, {total_failed} failed, "
          f"{len(sub_dirs) - total_done - total_failed} running/pending")

    # 更新 main token 的 step 状态
    main_token = _load_token()
    if main_token and "steps" in main_token:
        updated = False
        for s in main_token["steps"]:
            sp = s.get("subagent_path")
            if sp and s["status"] == "running":
                rp = Path(sp) / "result.json"
                if rp.exists():
                    try:
                        r = json.loads(rp.read_text())
                        if r.get("status") == "completed":
                            s["status"] = "completed"
                            updated = True
                        elif r.get("status") == "failed":
                            s["status"] = "failed"
                            updated = True
                    except Exception:
                        pass
        if updated:
            _save_token(main_token)

    return 0


def cmd_collect():
    """回收 subagent 完成结果 — 把 result.json 汇入 main task executor.md

    用法:
        python3 .claude/scripts/carros_base.py collect --step S1

    执行:
        1. 读 sub_task/sub-{step}/result.json
        2. 验证 status=completed
        3. 证据追加到 main executor.md
        4. 文件变更记录到 audit
        5. 标记 main token step 完成
    """
    global SUB_TASK_DIR, TASK_DIR, TOKEN_PATH, EXECUTOR_PATH

    argv = sys.argv[sys.argv.index("collect") + 1:]
    step_id = None
    i = 0
    while i < len(argv):
        if argv[i] == "--step" and i + 1 < len(argv):
            step_id = argv[i + 1]; i += 2
        else:
            i += 1

    if not step_id:
        print(_red("❌ Usage: collect --step S1"))
        return 2

    # 找 sub task 目录
    if not SUB_TASK_DIR or not SUB_TASK_DIR.exists():
        tok, tp = _find_latest_token()
        if tok:
            td = tok.get("task_dir")
            if td:
                SUB_TASK_DIR = Path(td) / "sub_task"
                _init_task_paths(task_id=tok.get("session", {}).get("id", "unknown"))
    sub_dir = SUB_TASK_DIR / f"sub-{step_id}"

    if not sub_dir.exists():
        print(_red(f"❌ Sub task not found: {sub_dir}"))
        return 2

    result_path = sub_dir / "result.json"
    if not result_path.exists():
        print(_red(f"❌ No result.json — subagent hasn't reported"))
        return 2

    try:
        result = json.loads(result_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(_red(f"❌ Failed to read result.json: {e}"))
        return 2

    status = result.get("status", "unknown")
    if status == "failed":
        print(_yellow(f"⚠  {step_id} result=failed"))
        print(f"   failure: {result.get('failure', 'unknown')}")
        return 2 if "--force" not in sys.argv else 0
    elif status != "completed":
        print(_yellow(f"⚠  {step_id} is still {status}"))

    # 证据追加到 main executor.md
    if EXECUTOR_PATH:
        ev_lines = [
            f"\n### SubAgent {step_id} — collected at {datetime.now(timezone.utc).isoformat()}",
            f"- source: sub_task/sub-{step_id}",
        ]
        if result.get("summary"):
            ev_lines.append(f"- summary: {result['summary']}")
        if result.get("evidence"):
            for ev in result["evidence"][:5]:
                ev_lines.append(f"- evidence: {ev[:100]}")
        if result.get("files_changed"):
            for f in result["files_changed"][:10]:
                ev_lines.append(f"- file: {f}")
        if result.get("failure"):
            ev_lines.append(f"- failure: {result['failure'][:100]}")

        exec_path = Path(EXECUTOR_PATH) if isinstance(EXECUTOR_PATH, (str, Path)) else EXECUTOR_PATH
        if isinstance(exec_path, Path) and exec_path.exists():
            with exec_path.open("a") as f:
                f.write("\n".join(ev_lines) + "\n")
        else:
            # 可能还没创建 executor.md
            pass

    # 标记 main token 完成
    main_token = _load_token()
    if main_token and "steps" in main_token:
        for s in main_token["steps"]:
            if s["id"] == step_id:
                s["status"] = "completed"
                break
        main_token["stats"]["done"] = sum(
            1 for s in main_token["steps"] if s["status"] == "completed"
        )
        _save_token(main_token)

    _write_audit("collect", {
        "step": step_id,
        "status": status,
        "evidence_count": len(result.get("evidence", [])),
        "files_changed": len(result.get("files_changed", [])),
    }, fallback=True)

    print(_green(f"✅ {step_id}: collected and verified"))
    summary = result.get("summary", "")
    if summary:
        print(f"   {summary}")
    return 0


def cmd_cancel():
    """中止 subagent 任务

    用法:
        python3 .claude/scripts/carros_base.py cancel --step S1 [--reason \"changes not needed\"]

    将 sub_task/sub-{step}/result.json status 设为 cancelled，
    标记 main token 对应 step 为 cancelled。
    """
    global SUB_TASK_DIR

    argv = sys.argv[sys.argv.index("cancel") + 1:]
    step_id = None
    reason = "cancelled by main agent"
    i = 0
    while i < len(argv):
        if argv[i] == "--step" and i + 1 < len(argv):
            step_id = argv[i + 1]; i += 2
        elif argv[i] == "--reason" and i + 1 < len(argv):
            reason = argv[i + 1]; i += 2
        else:
            i += 1

    if not step_id:
        print(_red("❌ Usage: cancel --step S1"))
        return 2

    tok, tp = _find_latest_token()
    if tok:
        td = tok.get("task_dir")
        if td:
            SUB_TASK_DIR = Path(td) / "sub_task"
            _init_task_paths(task_id=tok.get("session", {}).get("id", "unknown"))

    sub_dir = SUB_TASK_DIR / f"sub-{step_id}" if SUB_TASK_DIR else None
    if not sub_dir or not sub_dir.exists():
        print(_yellow(f"⚠  No sub task: sub-{step_id}"))
        return 0

    result_path = sub_dir / "result.json"
    if result_path.exists():
        try:
            result = json.loads(result_path.read_text())
            result["status"] = "cancelled"
            result["failure"] = reason
            result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception:
            result_path.write_text(json.dumps({
                "status": "cancelled",
                "failure": reason,
                "started_at": "",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }))

    # 更新 main token
    main_token = _load_token()
    if main_token and "steps" in main_token:
        for s in main_token["steps"]:
            if s["id"] == step_id:
                s["status"] = "cancelled"
                break
        _save_token(main_token)

    _write_audit("cancel", {"step": step_id, "reason": reason})
    print(_yellow(f"⚠  {step_id}: cancelled ({reason})"))
    return 0



def cmd_help():
    """打印帮助信息"""
    print(__doc__.strip())
    return 0


# ═══════════════════════════════════════════
# CLI entrypoint
# ═══════════════════════════════════════════

COMMANDS = {
    "init": cmd_init,
    "status": cmd_status,
    "tick": cmd_tick,
    "verify": cmd_verify,
    "archive": cmd_archive,
    "lint": cmd_lint,
    "bench": cmd_bench,
    "gate": cmd_gate,
    "dispatch": cmd_dispatch,
    "poll": cmd_poll,
    "collect": cmd_collect,
    "cancel": cmd_cancel,
    "oracle": cmd_oracle,
    "fallback": cmd_fallback,
    "help": cmd_help,
}


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if not argv or argv[0] in ("-h", "--help", "help"):
        return cmd_help()

    command = argv[0]
    if command not in COMMANDS:
        print(_red(f"Unknown command: {command}"))
        print(f"Available: {', '.join(COMMANDS.keys())}")
        return 2

    args = argv[1:]

    if command == "init":
        task_id = None
        level = "L1_BASE"
        steps = None
        task_dir = None
        user_request = None
        feature = None
        i = 0
        while i < len(args):
            if args[i] == "--task-id" and i + 1 < len(args):
                task_id = args[i + 1]
                i += 2
            elif args[i] == "--level" and i + 1 < len(args):
                level = args[i + 1]
                i += 2
            elif args[i] == "--task-dir" and i + 1 < len(args):
                task_dir = args[i + 1]
                i += 2
            elif args[i] == "--step":
                if steps is None:
                    steps = []
                i += 1
                while i < len(args) and not args[i].startswith("--"):
                    steps.append(args[i])
                    i += 1
            elif args[i] == "--user-request" and i + 1 < len(args):
                user_request = args[i + 1]
                i += 2
            elif args[i] == "--feature" and i + 1 < len(args):
                feature = args[i + 1]
                i += 2
            else:
                i += 1
        return cmd_init(task_id=task_id, level=level, steps=steps, user_request=user_request, task_dir=task_dir, feature=feature)

    elif command == "verify":
        step_id = None
        if args and args[0] == "--step" and len(args) >= 2:
            step_id = args[1]
        return cmd_verify(step_id=step_id)

    elif command == "archive":
        force = "--force" in args or "-f" in args
        return cmd_archive(force=force)

    elif command == "lint":
        path = args[0] if args else None
        return cmd_lint(path=path)

    else:
        return COMMANDS[command]()


if __name__ == "__main__":
    sys.exit(main())
