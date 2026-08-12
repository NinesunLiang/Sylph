#!/usr/bin/env python3
"""
lx-goal.py — 目标模式（目标驱动自主执行）
跨平台（macOS/Linux/Windows）

用法: lx-goal <目标描述> [小时]  或  lx-goal 子命令 [参数]

与 lx-ghost 的区别: goal = 目标驱动（具体任务），ghost = 方向驱动（开放探索）
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ============================================================
# 路径定位 — 跨平台 PROJECT_ROOT 计算
# ============================================================
# 脚本所在目录深度决定向上层数：
#   .claude/skills/lx-goal/scripts/lx-goal.py → ../../../../.. = 5 layers up
#   packages/carroros-gov/src/scripts/lx-goal.py → ../../.. = 3 layers up
#   template/skills/lx-goal/scripts/lx-goal.py → ../../../../.. = 5 layers up
# 通过检测目标目录文件名自适应
SCRIPT_DIR = Path(__file__).resolve().parent

# 从脚本目录向上查找，找到包含 AGENTS.md 或 .claude/ 的目录
def _find_project_root(start: Path) -> Path:
    """向上查找 CarrorOS 项目根目录（含非空 AGENTS.md 或 .claude/ 的目录）"""
    d = start
    for _ in range(10):  # 最多向上 10 层
        agents_md = d / "AGENTS.md"
        has_valid_agents = agents_md.exists() and agents_md.stat().st_size > 0
        has_dot_claude = (d / ".claude").is_dir()
        if has_valid_agents or has_dot_claude:
            return d
        parent = d.parent
        if parent == d:
            break
        d = parent
    raise RuntimeError(f"Cannot find project root from {start}")

PROJECT_ROOT = _find_project_root(SCRIPT_DIR)
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
TASKS_DIR = PROJECT_ROOT / ".omc" / "tasks"   # 文档系统 — "房间"
TOKENS_DIR = PROJECT_ROOT / ".omc" / "tokens"  # 令牌系统 — "钥匙" (独立于 tasks，compact 恢复入口)
PLANS_DIR = TASKS_DIR                           # 向后兼容: plan/research/executor 写入 tasks
CURRENT_PLAN_DIR: Path | None = None
get_now = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _goal_slug(goal: str) -> str:
    """Create a bounded activation slug that cannot collide across tasks."""
    base = "".join(c if c.isalnum() or c in "-_" else "" for c in goal.replace(" ", "-")[:44])
    base = base.strip("-_") or "goal"
    suffix = uuid.uuid4().hex[:8]
    return f"{base[: max(1, 64 - len(suffix) - 1)].rstrip('-_')}-{suffix}"


_GOAL_RUNTIME_KEYS = (
    "activated_at", "expires_at", "retry_count", "skipped_risks",
    "completed_tasks", "hard_boundary_hits", "blocked_human",
    "phase0_passed_at", "plan_passed_at",
)


def _merge_goal_runtime(token: dict) -> dict:
    goal = token.setdefault("goal", {})
    if not isinstance(goal, dict):
        raise ValueError("token.goal must be an object")
    list_keys = {"skipped_risks", "completed_tasks", "hard_boundary_hits", "blocked_human"}
    for key in _GOAL_RUNTIME_KEYS:
        default = [] if key in list_keys else 0 if key == "retry_count" else None
        token.setdefault(key, goal.get(key, default))
    return token


# Goal 状态机 + Step 合约（fail-closed: 导入失败时赋 None，调用方必须检查）
sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "scripts"))
from carros_base import _save_token as _save_task_token
_lc_set_mode = None
try:
    from goal_state_machine import GoalMachine as _GSM, ALL_STATES as _GSM_ALL_STATES, GoalError as _GSM_Error
except Exception:
    _GSM = None
    _GSM_ALL_STATES = []
    _GSM_Error = Exception
try:
    from goal_contracts import ResearchGate as _ResearchGate, ResearchGateError as _RGError, PlanGate as _PlanGate, PlanGateError as _PGError
except Exception:
    _ResearchGate = None
    _RGError = Exception
    _PlanGate = None
    _PGError = Exception
try:
    from executor_ledger import append_evidence_block as _ledger_append_block
except Exception:
    def _ledger_append_block(*args, **kwargs):
        pass
try:
    from phase_contracts import start_phase as _start_phase, complete_phase as _complete_phase
except Exception:
    _start_phase = None
    _complete_phase = None

from token_lifecycle import finalize_token, lock_path_for


# ============================================================
# 工具函数
# ============================================================
def _sanitize(text: str) -> str:
    """清除控制字符和代理对"""
    result = []
    for c in text:
        if 0xD800 <= ord(c) <= 0xDFFF:
            continue
        if ord(c) < 0x20 and c not in ("\n", "\t", "\r"):
            continue
        result.append(c)
    return "".join(result)


def _resolve_plan_dir(plan_dir: Path | str | None = None) -> Path:
    global CURRENT_PLAN_DIR
    candidate = plan_dir or CURRENT_PLAN_DIR or os.environ.get("CARROROS_TASK_DIR")
    if not candidate:
        print("❌ 必须提供 --task-dir；不会猜测其它终端任务", file=sys.stderr)
        raise SystemExit(2)
    resolved = Path(candidate).expanduser().resolve()
    required = ("plan.md", "research.md", "executor.md")
    if not resolved.is_dir() or any(not (resolved / name).is_file() for name in required):
        print(f"❌ task_dir 不完整: {resolved}", file=sys.stderr)
        raise SystemExit(2)
    CURRENT_PLAN_DIR = resolved
    return resolved


def _read_mode_file(plan_dir: Path | str | None = None) -> tuple[dict, str]:
    """Read the selected task token; never consult shared Goal state."""
    resolved = _resolve_plan_dir(plan_dir)
    token_path = _token_path_for_plan(resolved)
    if not token_path.exists():
        print(f"❌ Goal token 不存在: {token_path}", file=sys.stderr)
        raise SystemExit(2)
    try:
        data = json.loads(token_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"❌ Goal token 不可读: {token_path}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if data.get("mode") != "goal":
        print(f"❌ token 不是 Goal 任务: {token_path}", file=sys.stderr)
        raise SystemExit(2)
    return _merge_goal_runtime(data), str(token_path)


def _write_mode_file(data: dict, path: str):
    goal = data.setdefault("goal", {})
    for key in _GOAL_RUNTIME_KEYS:
        if key in data:
            goal[key] = data[key]
    _save_task_token(data, Path(path))


def is_mode_active(plan_dir: Path | str | None = None) -> bool:
    try:
        data, _ = _read_mode_file(plan_dir)
    except SystemExit:
        return False
    if data.get("status") != "active" or data.get("mode") != "goal":
        return False
    expires = data.get("goal", {}).get("expires_at")
    if expires:
        try:
            if datetime.now(timezone.utc) >= datetime.fromisoformat(expires):
                return False
        except ValueError:
            return False
    return True


def cmd_is_active(plan_dir: Path | str | None = None):
    """Check the explicitly selected Goal task."""
    if is_mode_active(plan_dir):
        print("✅ goal 模式激活中")
        return 0
    print("⭕ goal 模式未激活")
    return 1


def _get_plan_dir(token: dict):
    p = token.get("task_dir", "")
    if not p:
        return None
    plan_dir = Path(p).expanduser().resolve()
    required = ("plan.md", "research.md", "executor.md")
    if not plan_dir.is_dir() or any(not (plan_dir / name).is_file() for name in required):
        return None
    return plan_dir


def _rollback_activation() -> None:
    return None


def cmd_assert_plan_dir(plan_dir: Path | str | None = None):
    """assert-plan-dir 子命令: 输出 plan_dir 路径给 AI 捕获, 验证目录存在。

    goal 模式激活后,AI 必须调用此命令获取唯一计划目录路径,不得自行创建或猜测。

    成功 → 输出 plan_dir 绝对路径到 stdout, exit 0
    失败(未激活/目录不存在) → exit 2
    """
    if not is_mode_active():
        print("❌ 目标模式未激活,无法获取 plan_dir", file=sys.stderr)
        sys.exit(2)
    mode_data, _ = _read_mode_file()
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir or not plan_dir.exists():
        print("❌ plan_dir 不存在或已被删除, 请重新激活目标模式", file=sys.stderr)
        sys.exit(2)
    # 输出 plan_dir 绝对路径（AI 在 Phase 1 捕获此输出作为 I/O 锚定）
    print(str(plan_dir.resolve()))
    sys.exit(0)


def _token_path_for_plan(plan_dir: Path) -> Path:
    resolved = Path(plan_dir).resolve()
    return TOKENS_DIR / resolved.parent.name / f"{resolved.name}.json"


def _update_lock_counter(plan_dir: Path, field: str, inc: int = 1):
    """更新物理锁内的计数器字段"""
    lock_file = _token_path_for_plan(plan_dir)
    if not lock_file.exists():
        return  # 锁不存在时静默跳过
    with open(lock_file, encoding="utf-8") as f:
        lock = json.load(f)
    lock[field] = lock.get(field, 0) + inc
    lock["updated_at"] = get_now()
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump(lock, f, indent=2, ensure_ascii=False)


# ============================================================
# 跨会话恢复工具
# ============================================================

def find_first_incomplete_step(plan_dir: Path) -> str | None:
    """扫描 plan.md,返回第一个 [ ] 的 step ID(跨会话恢复用)"""
    plan_md = plan_dir / "plan.md"
    if not plan_md.exists():
        return None
    for line in plan_md.read_text(encoding="utf-8").splitlines():
        m = re.match(r"- \[(?: |a|A)\] (\S+?):", line.strip())
        if m:
            return m.group(1)
    return None


def plan_step_count(plan_dir: Path) -> int:
    """Count parsed plan steps, including checked and active states."""
    plan_md = plan_dir / "plan.md"
    if not plan_md.exists():
        return 0
    return sum(
        bool(re.match(r"- \[[ xXaA]\] (\S+?):", line.strip()))
        for line in plan_md.read_text(encoding="utf-8").splitlines()
    )


def completed_plan_steps(plan_dir: Path) -> list[str]:
    """Return every checked plan step."""
    plan_md = plan_dir / "plan.md"
    if not plan_md.exists():
        return []
    return [
        match.group(1)
        for line in plan_md.read_text(encoding="utf-8").splitlines()
        if (match := re.match(r"- \[[xX]\] (\S+?):", line.strip()))
    ]


def incomplete_plan_steps(plan_dir: Path) -> list[str]:
    """Return every unchecked plan step so phase results cannot masquerade as completion."""
    plan_md = plan_dir / "plan.md"
    if not plan_md.exists():
        return []
    steps = []
    for line in plan_md.read_text(encoding="utf-8").splitlines():
        m = re.match(r"- \[(?: |a|A)\] (\S+?):", line.strip())
        if m:
            steps.append(m.group(1))
    return steps


def missing_verified_evidence(plan_dir: Path) -> list[str]:
    """Return checked steps without a successful EV block."""
    executor = plan_dir / "executor.md"
    if not executor.exists():
        return completed_plan_steps(plan_dir)
    text = executor.read_text(encoding="utf-8")
    missing = []
    for step in completed_plan_steps(plan_dir):
        match = re.search(
            rf"^### EV-{re.escape(step)}\s*$([\s\S]*?)(?=^### |^## |\Z)",
            text,
            flags=re.MULTILINE,
        )
        if not match or not re.search(r"- exit_code:\s*0\b", match.group(1)):
            missing.append(step)
    return missing


# ============================================================
# 子命令
# ============================================================

def cmd_on(goal: str, expiry_hours: int = 6, task_id: str | None = None):
    """激活目标模式 — 创建 mode file + 计划目录 + 物理锁"""
    goal = goal or "目标任务未指定"
    if not 1 <= expiry_hours <= 168:
        raise ValueError("expiry hours must be between 1 and 168")
    if task_id is not None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", task_id):
            raise ValueError("task_id must contain only letters, digits, '.', '_' or '-'")
        slug = task_id
    else:
        slug = _goal_slug(goal)
    expires = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat()
    now = get_now()

    # ── 委托 carros_base.py 创建任务目录 + 结构化模板 ──
    # 不再自建 research/plan/executor 骨架模板
    carros_base = PROJECT_ROOT / ".claude" / "scripts" / "carros_base.py"
    user_request = f"goal: {goal}"
    plan_dir = None
    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, str(carros_base), "init",
             "--task-id", slug,
             "--level", "L2",
             "--user-request", user_request,
             "--task-mode", "goal"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            print(f"❌ carros_base.py init 失败 (exit={result.returncode})", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            _rollback_activation()
            sys.exit(2)

        # 解析最后一行 CARROROS_TASK_DIR=xxx
        task_dir_line = ""
        for line in reversed(result.stdout.splitlines()):
            if line.startswith("CARROROS_TASK_DIR="):
                task_dir_line = line
                break
        if not task_dir_line:
            print("❌ 未找到 CARROROS_TASK_DIR= 输出", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            _rollback_activation()
            sys.exit(2)
        plan_dir_str = task_dir_line.split("=", 1)[1].strip()
        plan_dir = Path(plan_dir_str)
        required = ("plan.md", "research.md", "executor.md")
        if not plan_dir.is_dir() or any(not (plan_dir / name).is_file() for name in required):
            print(f"❌ carros_base 创建的 task dir 不完整: {plan_dir}", file=sys.stderr)
            _rollback_activation()
            sys.exit(2)

        # 输出 carros_base 的 stdout（过滤掉 CARROROS_TASK_DIR 行）
        for line in result.stdout.splitlines():
            if not line.startswith("CARROROS_TASK_DIR="):
                print(line)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    except FileNotFoundError:
        print(f"❌ carros_base.py 脚本不存在: {carros_base}", file=sys.stderr)
        _rollback_activation()
        sys.exit(2)
    except subprocess.TimeoutExpired:
        print("❌ carros_base.py init 超时 (15s)", file=sys.stderr)
        _rollback_activation()
        sys.exit(2)

    # ── 读取已有 token（由 carros_base.py 创建），合并 goal 字段 ──
    lock_file = _token_path_for_plan(plan_dir)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if lock_file.exists():
        try:
            existing = json.loads(lock_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    goal_state = existing.setdefault("goal", {})
    existing["task_dir"] = str(plan_dir.resolve())
    goal_state["state"] = "CLARIFY"
    goal_state["description"] = goal[:200]
    goal_state["activated_at"] = now
    goal_state["expires_at"] = expires
    goal_state["retry_count"] = 0
    goal_state["skipped_risks"] = []
    goal_state["completed_tasks"] = []
    goal_state["hard_boundary_hits"] = []
    goal_state["blocked_human"] = []
    if "frontend-overnight" in goal:
        task = existing.setdefault("task", {})
        prototype_scope = task.get("scope", []) or []
        task["prototype_scope"] = prototype_scope
        task["implementation_scope"] = [
            "src/", "public/", ".claude/workflows/", ".omc/ui-autopilot/"
        ]
        task["scope"] = task["implementation_scope"]
    _write_mode_file(existing, str(lock_file))

    print(f"🔒 物理锁: {lock_file}")
    print(f"✅ 目标任务已开启 — 目标: {goal}, {expiry_hours}h 过期")
    print(f"   后续命令必须绑定: --task-dir {plan_dir.resolve()}")
    print('   任务逐项标记: lx-goal.py task-done "完成项描述" --task-dir <path>')
    print("   完成后输出报告: lx-goal.py report --task-dir <path>")
    # 无人模式轮询指引（跨会话/compact 恢复硬化）
    print("   ── 无人模式硬化 ──")
    print("   状态探测: lx-goal.py is-active --task-dir <path>")
    print("   轮询注册: lx-goal.py status --task-dir <path> && lx-goal.py poll --task-dir <path>")
    print("   会话内:   ScheduleWakeup delaySeconds=1200（长任务心跳）")
    print("   跨会话恢复: compact handoff → task_dir → token 续跑")

    # Scope-from-Goal
    auto_scope = PROJECT_ROOT / ".claude" / "scripts" / "auto-scope.sh"
    if auto_scope.exists():
        os.system(f"bash {auto_scope} 2>/dev/null")

    # 决策链注入（skill 自带 references，原 .claude/reference/ 路径不存在为死代码）
    decision_chain = SCRIPT_DIR.parent / "references" / "autonomous-execution.md"
    if decision_chain.exists():
        try:
            label = decision_chain.relative_to(PROJECT_ROOT)
        except ValueError:
            label = decision_chain
        print(f"\n[{label}]")
        print(decision_chain.read_text(encoding="utf-8"))


def cmd_off(plan_dir: Path | str | None = None):
    """Finalize only the explicitly selected Goal task."""
    mode_data, _ = _read_mode_file(plan_dir)
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir:
        print("❌ task_dir 不完整，无法关闭 Goal", file=sys.stderr)
        raise SystemExit(2)

    step_count = plan_step_count(plan_dir)
    incomplete_steps = incomplete_plan_steps(plan_dir)
    missing_evidence = missing_verified_evidence(plan_dir)
    if step_count == 0 or incomplete_steps or missing_evidence:
        cmd_report()
        print("❌ Goal 仍有未完成步骤或缺少 EV evidence，保留运行态", file=sys.stderr)
        raise SystemExit(1)

    lock_file = _token_path_for_plan(plan_dir)
    if not lock_file.exists():
        print(f"❌ Goal token 不存在: {lock_file}", file=sys.stderr)
        raise SystemExit(2)
    token = json.loads(lock_file.read_text(encoding="utf-8"))
    status = token.get("status")
    state = token.get("goal", {}).get("state")
    if status == "active" and state not in {"VERIFYING", "ARCHIVING", "ARCHIVED"}:
        print(f"❌ Goal 当前阶段为 {state or 'UNKNOWN'}，先完成验证再关闭", file=sys.stderr)
        raise SystemExit(1)
    if status not in {"archived", "completed"}:
        token["phase"] = "off"
        token["updated_at"] = get_now()
        _write_mode_file(token, str(lock_file))

    runtime = _merge_goal_runtime(token)
    checklist = plan_dir / "state" / "checklist.md"
    checklist.parent.mkdir(parents=True, exist_ok=True)
    checklist.write_text(
        "# Checklist\n\n## 验收清单\n"
        "- [x] 目标任务已关闭\n"
        f"- [x] 完成任务: {len(runtime.get('completed_tasks', []))} 项\n"
        f"- [x] 跳过风险: {len(runtime.get('skipped_risks', []))} 项\n"
        f"- [x] 硬边界拦截: {len(runtime.get('hard_boundary_hits', []))} 项\n"
        f"- [x] 推迟决策: {len(runtime.get('blocked_human', []))} 项\n"
        f"\n> 自动生成 @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        encoding="utf-8",
    )
    final_status = "archived" if status == "archived" else "completed"
    finalize_token(lock_file, status=final_status, reason="goal off")
    cmd_report()
    print(f"🔓 终态锁已删除，token 保留: {lock_file}")
    print(f"RPE退出报告: {checklist}")


def cmd_status(plan_dir: Path | str | None = None):
    """Show only the explicitly selected Goal task."""
    mode_data, _ = _read_mode_file(plan_dir)
    runtime = _merge_goal_runtime(mode_data)
    plan_dir = _get_plan_dir(mode_data)
    goal = mode_data.get("goal", {}).get("description", "?")
    print(f"📋 目标任务: {goal}")
    print(f"   状态: {mode_data.get('status', '?')}  阶段: {mode_data.get('goal', {}).get('state', '?')}")
    print(f"   过期: {mode_data.get('goal', {}).get('expires_at', '无')}")
    print(f"   已完成: {len(runtime.get('completed_tasks', []))}  跳过风险: {len(runtime.get('skipped_risks', []))} ")
    print(f"   硬边界: {len(runtime.get('hard_boundary_hits', []))}  推迟决策: {len(runtime.get('blocked_human', []))}  重试: {runtime.get('retry_count', 0)}")
    if plan_dir:
        lock_file = _token_path_for_plan(plan_dir)
        print(f"   token: {lock_file}")
        print(f"   lock: {'present' if lock_path_for(lock_file).exists() else 'absent'}")


def cmd_set(key: str, value_str: str):
    """Reject arbitrary token mutation; lifecycle commands own state changes."""
    print(f"❌ 禁止直接修改 Goal token 字段: {key}；请使用专用生命周期命令", file=sys.stderr)
    raise SystemExit(2)


def cmd_phase0_done():
    """Complete research only; plan completion is a separate hard transition."""
    mode_data, path = _read_mode_file()
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir:
        print("❌ 计划目录不存在，请重新激活目标模式")
        sys.exit(1)

    research_md = plan_dir / "research.md"
    if _ResearchGate is None:
        print("❌ ResearchGate 不可用，拒绝推进 Goal", file=sys.stderr)
        sys.exit(2)
    try:
        _ResearchGate.validate(str(research_md))
    except _RGError as e:
        errors = "；".join(e.errors[:5])
        print(f"❌ Phase 0 未完成: research.md 未通过结构验证: {errors}")
        if len(e.errors) > 5:
            print(f"   (共 {len(e.errors)} 项失败)")
        sys.exit(1)

    slug = plan_dir.name
    date_dir = plan_dir.parent.name
    lock_file = TOKENS_DIR / date_dir / f"{slug}.json"
    if _GSM is None:
        print("❌ GoalMachine 不可用，拒绝推进 Goal", file=sys.stderr)
        sys.exit(2)

    mode_snapshot = _snapshot_file(path)
    token_snapshot = _snapshot_file(lock_file)
    lock_snapshot = token_snapshot
    try:
        token_data = json.loads(lock_file.read_text(encoding="utf-8"))
        if not token_data.get("task_dir"):
            token_data["task_dir"] = str(plan_dir.resolve())
            lock_file.write_text(json.dumps(token_data, indent=2, ensure_ascii=False), encoding="utf-8")
        if _start_phase is not None:
            handoff = plan_dir / "state" / "phase-handoff-CLARIFY.json"
            if not handoff.exists():
                _start_phase(plan_dir, "CLARIFY")
            _complete_phase(plan_dir, "CLARIFY", {
                "research.sections": "ResearchGate passed",
                "research.dependency_tree": "ResearchGate passed",
            })
        gsm = _GSM(str(lock_file))
        if gsm.current_state == "CLARIFY":
            gsm.transition(
                "PLANNING",
                research_path=str(research_md),
                reason="phase0-done: research.md validated",
            )
        elif gsm.current_state != "PLANNING":
            raise _GSM_Error(
                f"Phase 0 requires CLARIFY or PLANNING, current={gsm.current_state}"
            )

        mode_data = json.loads(lock_file.read_text(encoding="utf-8"))
        mode_data["phase0_passed_at"] = get_now()
        _write_mode_file(mode_data, str(lock_file))
        if lock_file.exists():
            lock = json.loads(lock_file.read_text(encoding="utf-8"))
            lock["phase"] = "planning"
            lock["updated_at"] = get_now()
            lock_file.write_text(json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")
    except (_GSM_Error, OSError, json.JSONDecodeError) as e:
        _restore_file(lock_file, lock_snapshot)
        _restore_file(path, mode_snapshot)
        print(f"❌ Phase 0 状态提交失败，已回滚: {e}", file=sys.stderr)
        sys.exit(2)

    if _start_phase is not None:
        try:
            handoff = plan_dir / "state" / "phase-handoff-CLARIFY.json"
            if not handoff.exists():
                _start_phase(plan_dir, "CLARIFY")
            _complete_phase(plan_dir, "CLARIFY", {
                "research.sections": "ResearchGate passed",
                "research.dependency_tree": "ResearchGate passed",
            })
            _start_phase(plan_dir, "PLANNING")
        except ValueError as exc:
            print(f"❌ 阶段交接 schema 未就绪，不能进入 PLANNING: {exc}", file=sys.stderr)
            sys.exit(1)
    print("✅ Phase 0 完成 → PLANNING 已解锁")
    print("   ResearchGate 内容结构验证通过")
    print("   已提交 PLANNING 入参 schema：research.md / ResearchGate 结果")
    print("   现在填写并审查 plan.md")
    print("   完成后运行: lx-goal.py plan-done")


def cmd_plan_done():
    """Validate the plan after research and unlock execution."""
    mode_data, path = _read_mode_file()
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir:
        print("❌ 计划目录不存在，请重新激活目标模式")
        sys.exit(1)
    if _ResearchGate is None or _PlanGate is None:
        print("❌ ResearchGate/PlanGate 不可用，拒绝进入执行态", file=sys.stderr)
        sys.exit(2)

    research_md = plan_dir / "research.md"
    plan_md = plan_dir / "plan.md"
    try:
        _ResearchGate.validate(str(research_md))
        _PlanGate.validate(str(plan_md))
    except (_RGError, _PGError) as e:
        print(f"❌ PlanGate 未通过，不能进入执行态: {e}", file=sys.stderr)
        sys.exit(1)

    slug = plan_dir.name
    date_dir = plan_dir.parent.name
    lock_file = TOKENS_DIR / date_dir / f"{slug}.json"
    if _GSM is None:
        print("❌ GoalMachine 不可用，拒绝推进 Goal", file=sys.stderr)
        sys.exit(2)

    mode_snapshot = _snapshot_file(path)
    token_snapshot = _snapshot_file(lock_file)
    physical_lock = lock_file.with_suffix(lock_file.suffix + ".lock")
    physical_lock_snapshot = _snapshot_file(physical_lock)
    try:
        token_data = json.loads(lock_file.read_text(encoding="utf-8"))
        if not token_data.get("task_dir"):
            token_data["task_dir"] = str(plan_dir.resolve())
            lock_file.write_text(json.dumps(token_data, indent=2, ensure_ascii=False), encoding="utf-8")
        if _start_phase is not None:
            handoff = plan_dir / "state" / "phase-handoff-PLANNING.json"
            if not handoff.exists():
                _start_phase(plan_dir, "PLANNING")
            _complete_phase(plan_dir, "PLANNING", {
                "plan.phases": "PlanGate passed",
                "plan.steps": "PlanGate passed",
                "step.acceptance": "PlanGate passed",
                "step.verify": "PlanGate passed",
            })
        gsm = _GSM(str(lock_file))
        if gsm.current_state != "PLANNING":
            raise _GSM_Error(
                f"Plan completion requires PLANNING, current={gsm.current_state}"
            )
        gsm.transition(
            "EXECUTING",
            research_path=str(research_md),
            plan_path=str(plan_md),
            reason="plan-done: plan.md validated",
        )
        mode_data = json.loads(lock_file.read_text(encoding="utf-8"))
        mode_data["plan_passed_at"] = get_now()
        _write_mode_file(mode_data, str(lock_file))
        if lock_file.exists():
            lock = json.loads(lock_file.read_text(encoding="utf-8"))
            lock["phase"] = "executing"
            lock["updated_at"] = get_now()
            lock_file.write_text(json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")
    except (_GSM_Error, OSError, json.JSONDecodeError) as e:
        _restore_file(lock_file, token_snapshot)
        _restore_file(path, mode_snapshot)
        _restore_file(physical_lock, physical_lock_snapshot)
        print(f"❌ PlanGate 状态提交失败，已回滚执行解锁: {e}", file=sys.stderr)
        sys.exit(2)

    if _start_phase is not None:
        try:
            handoff = plan_dir / "state" / "phase-handoff-PLANNING.json"
            if not handoff.exists():
                _start_phase(plan_dir, "PLANNING")
            _complete_phase(plan_dir, "PLANNING", {
                "plan.phases": "PlanGate passed",
                "plan.steps": "PlanGate passed",
                "step.acceptance": "PlanGate passed",
                "step.verify": "PlanGate passed",
            })
            _start_phase(plan_dir, "EXECUTING")
        except ValueError as exc:
            print(f"❌ 阶段交接 schema 未就绪，不能进入 EXECUTING: {exc}", file=sys.stderr)
            sys.exit(1)
    print("✅ PlanGate 通过 → EXECUTING 已解锁")
    print("   已提交 EXECUTING 入参 schema：plan.md / current_step.schema / executor sections")
    print("   现在才允许 tick、subagent-log 和 executor 证据写入")


def cmd_report(plan_dir: Path | str | None = None):
    """Generate a report inside the selected task directory."""
    mode_data, path = _read_mode_file(plan_dir)
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir:
        print("❌ task_dir 不完整，无法生成报告", file=sys.stderr)
        raise SystemExit(2)
    report_file = plan_dir / "state" / "goal-report.md"
    runtime = _merge_goal_runtime(mode_data)
    step_count = plan_step_count(plan_dir) if plan_dir else 0
    completed_steps = completed_plan_steps(plan_dir) if plan_dir else []
    incomplete_steps = incomplete_plan_steps(plan_dir) if plan_dir else []
    missing_evidence = missing_verified_evidence(plan_dir) if plan_dir else []
    uncertified_items = []
    if not plan_dir:
        uncertified_items.append("goal.plan_dir.missing: plan/research/executor context is unavailable")
    elif step_count == 0:
        uncertified_items.append("plan.steps.missing: no parsed plan steps")
    uncertified_items.extend(f"plan.step.{step}.incomplete" for step in incomplete_steps)
    uncertified_items.extend(f"plan.step.{step}.verified_evidence_missing" for step in missing_evidence)
    uncertified_items.extend(
        f"skip-risk.{item.get('risk_level', 'low')}: {item.get('description', '?')}"
        for item in mode_data.get("skipped_risks", [])
        if isinstance(item, dict) and item.get("risk_level") in ("medium", "high", "critical")
    )
    uncertified_items.extend(f"blocked-human: {item.get('description', '?')}" for item in mode_data.get("blocked_human", []))

    goal = mode_data.get("goal", {}).get("description", "?")
    done = len(completed_steps)
    skip = len(runtime.get("skipped_risks", []))
    hard = len(runtime.get("hard_boundary_hits", []))
    blocked = len(runtime.get("blocked_human", []))
    retry = runtime.get("retry_count", 0)
    activated = mode_data.get("goal", {}).get("activated_at", "?")
    expires = mode_data.get("goal", {}).get("expires_at", "?")

    # build lists
    def _skip_line(r):
        if isinstance(r, dict):
            lvl = r.get("risk_level", "low")
            line = f"- [{lvl}] {r.get('description', '?')}"
            if r.get("reason"):
                line += f" — 理由: {r['reason']}"
            if r.get("impact"):
                line += f" / 影响: {r['impact']}"
            return line
        return f"- {r}"

    skip_list = "\n".join(_skip_line(r) for r in mode_data.get("skipped_risks", [])) or "无"
    hard_list = ""
    for h in mode_data.get("hard_boundary_hits", []):
        hard_list += f"- **操作**: {h.get('description', '?')}\n  **原因**: {h.get('reason', '?')}\n  **需人类执行**: {h.get('human_action', '?')}\n\n"
    hard_list = hard_list or "无"
    blocked_list = ""
    for b in mode_data.get("blocked_human", []):
        blocked_list += f"- **决策**: {b.get('description', '?')}\n  **AI 推荐**: {b.get('ai_recommendation', '?')}\n  **依据**: {b.get('rationale', '?')}\n\n"
    blocked_list = blocked_list or "无"
    task_list = (
        "\n".join(f"- [x] {step}" for step in completed_steps)
        if plan_dir
        else "\n".join(
            f"- [x] {t.get('description', t) if isinstance(t, dict) else t}  ({t.get('timestamp', '') if isinstance(t, dict) else ''})"
            for t in mode_data.get("completed_tasks", [])
        )
    ) or "无"

    # 人为决策汇总表
    decision_rows = []
    idx = 0
    for h in mode_data.get("hard_boundary_hits", []):
        idx += 1
        decision_rows.append(f"| {idx} | 硬边界 | {h.get('description', '?')} | {h.get('human_action', '?')} | {h.get('reason', '?')} |")
    for b in mode_data.get("blocked_human", []):
        idx += 1
        decision_rows.append(f"| {idx} | 推迟决策 | {b.get('description', '?')} | {b.get('ai_recommendation', '?')} | {b.get('rationale', '?')} |")
    # 中高风险跳过项 — 只跳过不执行，必须反馈人类干预（goal 模式核心安全阀）
    for r in mode_data.get("skipped_risks", []):
        if isinstance(r, dict) and r.get("risk_level") in ("medium", "high", "critical"):
            idx += 1
            basis = r.get("reason") or "风险规避"
            if r.get("impact"):
                basis += f" / 影响: {r['impact']}"
            decision_rows.append(
                f"| {idx} | 中高风险跳过[{r['risk_level']}] | {r.get('description', '?')} "
                f"| 建议人类评估后手动执行或明确放弃 | {basis} |"
            )
    if not decision_rows:
        decision_rows.append("| - | - | 无需人类介入的项 | - | - |")

    # GateKeeper 事件摘要（从 gatekeeper_digest 消费）
    _gk_digest = ""
    try:
        _gk_result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "gatekeeper_digest.py"), "--alert"],
            capture_output=True, text=True, timeout=10,
        )
        _gk_digest = _gk_result.stdout.strip()
    except Exception:
        pass
    _gk_section = f"\n## GateKeeper 事件摘要\n\n```\n{_gk_digest}\n```\n\n" if _gk_digest else ""

    report_content = f"""# 目标模式执行报告

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 目标

{_sanitize(goal)}

## 基本信息

- 激活时间: {activated}
- 过期时间: {expires}

## 执行摘要

- 已完成任务数: {done}
- 跳过风险数: {skip}
- 硬边界拦截数: {hard}
- 推迟决策数: {blocked}
- 重试次数: {retry}

## 已完成任务

{task_list}

## 跳过的风险

{skip_list}

## ⚠️ 需人为决策汇总

| # | 类型 | 描述 | AI 推荐 | 依据 |
|---|------|------|---------|------|
{chr(10).join(decision_rows)}

## ⚠️ 需人类介入项（硬边界）

{hard_list}

## 推迟决策项（裁决链 Level 3 — 需人类裁决）

{blocked_list}

## 未认证项（自动派生）

{chr(10).join(f"- `{item}`" for item in uncertified_items) or "- 无"}

{_gk_section}## 验证状态

{f"BLOCKED: 当前 Goal plan_dir 不完整，不能生成 VERIFIED 报告。" if not plan_dir else f"BLOCKED: plan.md 未解析出任何步骤，不能生成 VERIFIED 报告。" if step_count == 0 else f"IN_PROGRESS: 未完成计划步骤 {', '.join(incomplete_steps)}；goal 保持执行态，不得视为验收完成。" if incomplete_steps else f"BLOCKED: 缺少成功的 EV evidence，不能生成 VERIFIED 报告（{', '.join(missing_evidence)}）。" if missing_evidence else f"IN_PROGRESS: 存在未认证项（{', '.join(uncertified_items)}）。" if uncertified_items else f"VERIFIED: 所有计划步骤已完成（{done} 项完成，{skip} 项风险跳过，{hard} 项硬边界拦截，{blocked} 项推迟决策，{retry} 次重试）"}
"""
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report_content, encoding="utf-8")
    print(f"✅ 报告已生成: {report_file}")
    print(report_content)


def cmd_poll(plan_dir: Path | str | None = None):
    """Poll only the explicitly selected Goal task."""
    data, token_path_str = _read_mode_file(plan_dir)
    token_path = Path(token_path_str)
    plan_dir = _get_plan_dir(data)
    if not plan_dir:
        print("❌ task_dir 不完整，停止轮询", file=sys.stderr)
        return 2

    expires_str = data.get("goal", {}).get("expires_at", "")
    if expires_str:
        try:
            exp = datetime.fromisoformat(expires_str)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                print(f"⏰ 目标任务已过期（{expires_str}），自动关闭")
                cmd_report()
                finalize_token(token_path, status="expired", reason="goal expired")
                print(f"🔓 过期终态锁已删除，token 保留: {token_path}")
                return 0
        except ValueError:
            pass

    runtime = _merge_goal_runtime(data)
    goal = data.get("goal", {}).get("description", "?")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"🔄 目标轮询 {now}")
    print(f"   目标: {_sanitize(goal)}")
    print(f"   已完成: {len(runtime.get('completed_tasks', []))}  已跳过风险: {len(runtime.get('skipped_risks', []))}  ")
    print(f"   硬边界: {len(runtime.get('hard_boundary_hits', []))}  重试次数: {runtime.get('retry_count', 0)}")
    print("   后续命令必须带 --task-dir")
    next_step = find_first_incomplete_step(plan_dir)
    if next_step:
        print(f"   下一步: {next_step}")
    return 0


def _goal_context(plan_dir: Path) -> tuple[Path, dict[str, str]]:
    token_path = TOKENS_DIR / plan_dir.parent.name / f"{plan_dir.name}.json"
    if not token_path.is_file():
        raise RuntimeError(f"goal token missing for task_id={plan_dir.name}: {token_path}")
    try:
        token = json.loads(token_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"goal token unreadable: {token_path}") from exc
    task_id = token.get("session", {}).get("id")
    if task_id != plan_dir.name:
        raise RuntimeError(f"goal token task_id mismatch: expected={plan_dir.name}, actual={task_id}")
    token_dir = token.get("task_dir")
    if token_dir and Path(token_dir).expanduser().resolve() != plan_dir.resolve():
        raise RuntimeError(f"goal token task_dir mismatch: {token_dir}")
    env = os.environ.copy()
    env["CARROROS_TOKEN_PATH"] = str(token_path)
    env["CARROROS_TASK_ID"] = plan_dir.name
    env["CARROROS_TASK_DIR"] = str(plan_dir.resolve())
    return token_path, env


def _goal_state(plan_dir: Path) -> str | None:
    """Read the canonical Goal state for a bound task directory."""
    token_path = TOKENS_DIR / plan_dir.parent.name / f"{plan_dir.name}.json"
    try:
        token = json.loads(token_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return token.get("goal", {}).get("state")


def _require_execution_phase(plan_dir: Path, action: str) -> bool:
    """Reject executor mutations until plan-done has opened EXECUTING."""
    state = _goal_state(plan_dir)
    if state in {"EXECUTING", "VERIFYING"}:
        return True
    print(
        f"❌ {action} 被阻断：Goal 当前状态为 {state or 'UNKNOWN'}；"
        "必须先完成 research → plan-done → EXECUTING",
        file=sys.stderr,
    )
    return False


def _snapshot_file(path: str | Path) -> bytes | None:
    file_path = Path(path)
    return file_path.read_bytes() if file_path.exists() else None


def _restore_file(path: str | Path, original: bytes | None) -> None:
    file_path = Path(path)
    if original is None:
        file_path.unlink(missing_ok=True)
        return
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(original)


def _verify_goal_step(step_id: str) -> int:
    """Activate the goal step through tick, then run canonical verification."""
    script = PROJECT_ROOT / ".claude" / "scripts" / "carros_base.py"
    if not script.exists():
        print("❌ VerifyGate runner missing: .claude/scripts/carros_base.py", file=sys.stderr)
        return 2
    plan_dir = _get_plan_dir(_read_mode_file()[0])
    if not plan_dir:
        print("❌ 当前 goal 的 plan_dir 不存在或不完整", file=sys.stderr)
        return 2
    try:
        _, goal_env = _goal_context(plan_dir)
    except RuntimeError as exc:
        print(f"❌ 当前 goal 上下文无效: {exc}", file=sys.stderr)
        return 2

    state = _goal_state(plan_dir)
    if state == "EXECUTING":
        activate = subprocess.run(
            [sys.executable, str(script), "tick", "--step", step_id],
            cwd=PROJECT_ROOT,
            env=goal_env,
            capture_output=True,
            text=True,
        )
        if activate.returncode != 0:
            print((activate.stdout or "") + (activate.stderr or ""), file=sys.stderr)
            return activate.returncode
    elif state != "VERIFYING":
        print(
            f"❌ verify blocked: Goal state={state or 'UNKNOWN'}; "
            "必须先完成 plan-done → EXECUTING",
            file=sys.stderr,
        )
        return 2
    result = subprocess.run(
        [sys.executable, str(script), "verify", "--step", step_id],
        cwd=PROJECT_ROOT,
        env=goal_env,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    if output:
        print(output.rstrip())
    return result.returncode


def _resolve_current_step(plan_dir: Path) -> str | None:
    """Resolve the active step or first dependency-ready pending step."""
    plan_md = plan_dir / "plan.md"
    if not plan_md.exists():
        return None
    try:
        import step_contracts
        steps = step_contracts.parse_plan_steps(plan_md.read_text(encoding="utf-8"))
        for step in steps:
            if step["status"] == "active":
                return step["id"]
        return step_contracts.find_first_activatable_step(steps)
    except Exception:
        return find_first_incomplete_step(plan_dir)


def cmd_verify_step(step_id: str = ""):
    """Verify one goal step; only canonical VerifyGate may mark plan.md [x]."""
    mode_data, _ = _read_mode_file()
    plan_dir = _get_plan_dir(mode_data)
    if not step_id or not plan_dir:
        print("❌ 用法: lx-goal.py verify-step <step_id>", file=sys.stderr)
        return 2
    return _verify_goal_step(step_id)


def cmd_task_done(description: str = "未知任务"):
    """Verify the current step before recording a goal task completion."""
    mode_data, path = _read_mode_file()
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir:
        print("❌ 未记录完成：当前 goal 的 plan_dir 不存在或不完整", file=sys.stderr)
        return 2
    if mode_data.get("mode") == "goal" and not _require_execution_phase(plan_dir, "task-done"):
        return 2
    step_id = _resolve_current_step(plan_dir)
    if plan_dir and step_id:
        rc = _verify_goal_step(step_id)
        if rc != 0:
            print(f"❌ 未记录完成：{step_id} 未通过 VerifyGate", file=sys.stderr)
            return rc
    elif plan_dir:
        plan_path = plan_dir / "plan.md"
        if not plan_path.exists() or incomplete_plan_steps(plan_dir):
            print("❌ 未记录完成：当前 goal 没有可验证的 current_step", file=sys.stderr)
            return 2

    ts = datetime.now().isoformat()
    completed = mode_data.setdefault("completed_tasks", [])
    already_recorded = any(
        isinstance(item, dict) and item.get("description") == description
        for item in completed
    )
    if not already_recorded:
        completed.append({"description": description, "timestamp": ts})
        _write_mode_file(mode_data, path)
        if plan_dir:
            _ledger_append_block(plan_dir / "executor.md", "Completed Tasks", {"task": description, "timestamp": ts})
            _update_lock_counter(plan_dir, "completed_tasks")
    print(f"✅ 已验证并标记任务完成: {_sanitize(description)}")
    return 0


def cmd_skip_risk(description: str = "未知风险", risk_level: str = "low", reason: str = "", impact: str = ""):
    """记录跳过的风险。

    risk_level: low/medium/high/critical。
    中高风险（medium+）只跳过不执行，会自动进入退出报告的「需人为决策汇总」表，
    反馈给人类干预 — 这是 goal 模式的核心安全阀。
    """
    risk_level = (risk_level or "low").lower()
    if risk_level not in ("low", "medium", "high", "critical"):
        risk_level = "low"
    mode_data, path = _read_mode_file()
    mode_data.setdefault("skipped_risks", []).append({
        "description": description,
        "risk_level": risk_level,
        "reason": reason,
        "impact": impact,
        "timestamp": get_now(),
    })
    _write_mode_file(mode_data, path)

    plan_dir = _get_plan_dir(mode_data)
    if plan_dir:
        plan_md = plan_dir / "plan.md"
        if plan_md.exists():
            with open(plan_md, "a", encoding="utf-8") as f:
                f.write(f"\n- [skip-risk/{risk_level}] {description} — {reason or '未填理由'}  ({get_now()})\n")
        _update_lock_counter(plan_dir, "skipped_risks")

    marker = "⚠️" if risk_level in ("medium", "high", "critical") else "📝"
    print(f"{marker} 已记录跳过的风险[{risk_level}]: {_sanitize(description)}")
    if risk_level in ("medium", "high", "critical"):
        print("   中高风险项：仅跳过不执行，将出现在退出报告「需人为决策汇总」")


def cmd_hard_boundary_hit(description: str = "未知硬边界", reason: str = "未知原因", human_action: str = "请人工审阅并决定是否执行"):
    """记录硬边界拦截项"""
    mode_data, path = _read_mode_file()
    mode_data.setdefault("hard_boundary_hits", []).append({
        "description": description,
        "reason": reason,
        "human_action": human_action,
        "timestamp": get_now(),
    })
    _write_mode_file(mode_data, path)

    plan_dir = _get_plan_dir(mode_data)
    if plan_dir:
        plan_md = plan_dir / "plan.md"
        if plan_md.exists():
            with open(plan_md, "a", encoding="utf-8") as f:
                f.write(f"\n- [hard-boundary] {description} — {reason}  ({get_now()})\n")
        _update_lock_counter(plan_dir, "hard_boundary_hits")

    print(f"🛑 硬边界拦截已记录: {_sanitize(description)} (原因: {_sanitize(reason)})")


def cmd_blocked_human(description: str = "未知决策", ai_recommendation: str = "AI 推荐方案未提供", rationale: str = "决策依据未提供"):
    """记录推迟到退出报告的人类决策项"""
    mode_data, path = _read_mode_file()
    mode_data.setdefault("blocked_human", []).append({
        "description": description,
        "ai_recommendation": ai_recommendation,
        "rationale": rationale,
        "timestamp": get_now(),
    })
    _write_mode_file(mode_data, path)

    plan_dir = _get_plan_dir(mode_data)
    if plan_dir:
        plan_md = plan_dir / "plan.md"
        if plan_md.exists():
            with open(plan_md, "a", encoding="utf-8") as f:
                f.write(f"\n- [blocked-human] {description} → {ai_recommendation}  ({get_now()})\n")
        _update_lock_counter(plan_dir, "blocked_human")

    print(f"🤔 推迟决策已记录: {_sanitize(description)} → 推荐: {_sanitize(ai_recommendation)}")


def cmd_retry():
    """重试计数 +1"""
    mode_data, path = _read_mode_file()
    mode_data["retry_count"] = mode_data.get("retry_count", 0) + 1
    _write_mode_file(mode_data, path)
    print("📝 重试计数 +1")


def cmd_subagent_log(action: str, agent_name: str = "", subtask: str = "", detail: str = ""):
    """记录 subagent 分配/回收/结果"""
    mode_data, _ = _read_mode_file()
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir:
        print("❌ 计划目录不存在")
        sys.exit(1)
    if mode_data.get("mode") == "goal" and not _require_execution_phase(plan_dir, "subagent-log"):
        sys.exit(2)

    # subagent 日志写入 executor.md
    executor_md = plan_dir / "executor.md"
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(executor_md, "a", encoding="utf-8") as f:
        if action == "assign":
            f.write(f"\n### {ts} — 分配: {agent_name} → {subtask}\n")
        elif action == "complete":
            f.write(f"\n### {ts} — 完成: {agent_name} → {subtask}\n  - 结果: {detail}\n")
        elif action == "fail":
            f.write(f"\n### {ts} — 失败: {agent_name} → {subtask}\n  - 原因: {detail}\n")
        elif action == "summary":
            f.write(f"\n---\n### SubAgent 执行摘要 @ {ts}\n")
            # 简单的统计
            content = executor_md.read_text(encoding="utf-8")
            f.write(f"- 分配: {content.count('分配:')}\n")
            f.write(f"- 完成: {content.count('完成:')}\n")
            f.write(f"- 失败: {content.count('失败:')}\n")
        else:
            print("用法: lx-goal.py subagent-log assign|complete|fail|summary <agent> <subtask> [detail]")
            sys.exit(1)

    print(f"📝 subagent 日志已更新: {executor_md}")


def cmd_checklist_verify():
    """检测 executor.md 的 Checklist 是否全部 [x]。未达标 → exit=1"""
    mode_data, _ = _read_mode_file()
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir:
        return 0  # 无计划目录时不阻断（向后兼容）
    executor_md = plan_dir / "executor.md"
    if not executor_md.exists():
        return 0

    text = executor_md.read_text(encoding="utf-8")
    import re
    checked = len(re.findall(r'- \[x\]', text, re.IGNORECASE))
    unchecked = len(re.findall(r'- \[ \]', text))
    if unchecked > 0:
        print(f"❌ Checklist 未达标: {checked}/{checked + unchecked} 项通过，还有 {unchecked} 项未完成", file=sys.stderr)
        for line in text.splitlines():
            l = line.strip()
            if l.startswith("- [ ]"):
                print(f"   ⬜ {l[5:].strip()}", file=sys.stderr)
        print(f"\n   完成所有 [ ] 项后重试: lx-goal.py done", file=sys.stderr)
        sys.exit(1)
    return 0


def cmd_done(plan_dir: Path | str | None = None):
    """Finalize the explicitly selected Goal task after verification."""
    mode_data, _ = _read_mode_file(plan_dir)
    plan_dir = _get_plan_dir(mode_data)
    if not plan_dir:
        print("❌ 计划目录不存在，无法完成验收")
        sys.exit(1)

    # 门禁：计划步骤未全部勾选时不得关闭 goal，即使阶段性 checklist 通过。
    step_count = plan_step_count(plan_dir)
    if step_count == 0:
        print("❌ plan.md 未解析出任何步骤，不得关闭 goal", file=sys.stderr)
        sys.exit(1)
    incomplete_steps = incomplete_plan_steps(plan_dir)
    if incomplete_steps:
        print(f"❌ 计划仍有未完成步骤: {', '.join(incomplete_steps)}；继续执行，不得关闭 goal", file=sys.stderr)
        sys.exit(1)
    missing_evidence = missing_verified_evidence(plan_dir)
    if missing_evidence:
        print(f"❌ 缺少成功 EV evidence: {', '.join(missing_evidence)}；不得关闭 goal", file=sys.stderr)
        sys.exit(1)

    # 门禁：先跑 checklist-verify
    try:
        cmd_checklist_verify()
    except SystemExit as e:
        if e.code != 0:
            print("❌ checklist 未全部通过，不得关闭任务", file=sys.stderr)
            sys.exit(1)

    lock_file = _token_path_for_plan(plan_dir)

    # ── GoalMachine 推进: ARCHIVING → ARCHIVED ──
    if _GSM is None:
        print("❌ GoalMachine 不可用，拒绝归档并保留物理锁", file=sys.stderr)
        sys.exit(1)
    if not lock_file.exists():
        print("❌ Goal token 不存在，拒绝归档", file=sys.stderr)
        sys.exit(1)
    try:
        gsm = _GSM(str(lock_file))
        gsm.transition("ARCHIVING", reason="done: checklist passed")
        gsm.transition("ARCHIVED", reason="done: task completed")
    except _GSM_Error as e:
        print(f"❌ GoalMachine 状态转换失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 只有成功推进到 ARCHIVED 后才终态化 token；只删除 sidecar lock
    try:
        finalize_token(lock_file, status="archived", reason="done: task completed")
        print(f"🔓 终态锁已删除，token 保留: {lock_file}")
        print("✅ 任务验收完成，锁已移除")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"❌ Token 终态清理失败: {exc}", file=sys.stderr)
        sys.exit(1)

    # 更新 plan.md
    plan_md = plan_dir / "plan.md"
    with open(plan_md, "a", encoding="utf-8") as f:
        f.write(f"\n---\n✅ **任务验收完成** @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


def cmd_update_lock(plan_dir_str: str = "", field: str = "", inc: int = 1):
    """更新物理锁计数器 — 内部子命令"""
    if not plan_dir_str:
        return
    plan_dir = Path(plan_dir_str)
    if not plan_dir.exists():
        return
    _update_lock_counter(plan_dir, field, inc)


# ============================================================
# 主入口
# ============================================================
KNOWN_SUBCOMMANDS = {
    "on": cmd_on,
    "off": cmd_off,
    "status": cmd_status,
    "set": cmd_set,
    "phase0-done": cmd_phase0_done,
    "plan-done": cmd_plan_done,
    "checklist-verify": cmd_checklist_verify,
    "assert-plan-dir": cmd_assert_plan_dir,
    "report": cmd_report,
    "poll": cmd_poll,
    "is-active": cmd_is_active,
    "task-done": cmd_task_done,
    "verify-step": cmd_verify_step,
    "skip-risk": cmd_skip_risk,
    "hard-boundary-hit": cmd_hard_boundary_hit,
    "blocked-human": cmd_blocked_human,
    "retry": cmd_retry,
    "subagent-log": cmd_subagent_log,
    "done": cmd_done,
    "_update-lock": cmd_update_lock,
}


def parse_on_args(args: list[str]) -> tuple[str, int, str | None]:
    """Parse `on` arguments without touching lifecycle or task state."""
    goal_parts: list[str] = []
    expiry = 6
    expiry_set = False
    task_id = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--task-id":
            if i + 1 >= len(args) or args[i + 1].startswith("-"):
                raise ValueError("--task-id requires a value")
            task_id = args[i + 1]
            i += 2
            continue
        if arg in ("--expiry", "--hours"):
            if expiry_set or i + 1 >= len(args):
                raise ValueError(f"{arg} requires one integer value")
            raw_expiry = args[i + 1]
            i += 2
            try:
                expiry = int(raw_expiry, 10)
            except ValueError as exc:
                raise ValueError("expiry must be an integer") from exc
            expiry_set = True
            continue
        if arg.startswith("--"):
            raise ValueError(f"unknown option: {arg}")
        goal_parts.append(arg)
        i += 1

    if not expiry_set and len(goal_parts) > 1 and goal_parts[-1].isdigit():
        expiry = int(goal_parts.pop(), 10)
    if not goal_parts:
        goal_parts = ["目标任务未指定"]
    if not 1 <= expiry <= 168:
        raise ValueError("expiry hours must be between 1 and 168")
    return " ".join(goal_parts), expiry, task_id


def _usage() -> str:
    cmds = "、".join(sorted(k for k in KNOWN_SUBCOMMANDS if k != "_update-lock"))
    return (
        "用法: lx-goal.py <子命令> [参数]  或  lx-goal.py on \"<目标描述>\" [小时|--expiry N] [--task-id ID]\n"
        f"子命令: {cmds}\n"
        "说明: 参数先完整校验，未知 option/非法小时数不会创建 mode、token 或 lock。"
    )


def _bind_task_dir_arg(args: list[str]) -> list[str]:
    positions = [index for index, value in enumerate(args) if value == "--task-dir"]
    if not positions:
        return args
    if len(positions) > 1:
        raise ValueError("--task-dir may be provided only once")
    index = positions[0]
    if index + 1 >= len(args) or args[index + 1].startswith("-"):
        raise ValueError("--task-dir requires a task directory")
    _resolve_plan_dir(args[index + 1])
    return args[:index] + args[index + 2:]


def main():
    if len(sys.argv) < 2:
        cmd_status()
        return

    # 参数守卫: help 与未知 dash 参数 → usage,绝不激活(F7 修复: --help 曾被当 goal 建锁)
    if sys.argv[1] in ("-h", "--help", "help"):
        print(_usage())
        sys.exit(0)
    if sys.argv[1].startswith("-") and sys.argv[1] not in KNOWN_SUBCOMMANDS:
        print(f"ERROR: 未知参数 {sys.argv[1]!r}(若以 - 开头请用 on \"目标\" 显式激活)", file=sys.stderr)
        print(_usage(), file=sys.stderr)
        sys.exit(2)

    if sys.argv[1] not in KNOWN_SUBCOMMANDS:
        # 非子命令文本 → 当作目标描述自动激活
        raw = sys.argv[1:]
        goal = " ".join(raw)
        expiry = 6
        if raw and raw[-1].isdigit():
            expiry = int(raw[-1])
            goal = " ".join(raw[:-1])
        cmd_on(goal, expiry)
        return

    cmd_name = sys.argv[1]
    args = sys.argv[2:]

    if cmd_name != "on":
        try:
            args = _bind_task_dir_arg(args)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(2)

    if cmd_name == "on":
        try:
            goal, expiry, task_id = parse_on_args(args)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            print(_usage(), file=sys.stderr)
            sys.exit(2)
        try:
            cmd_on(goal, expiry, task_id)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            print(_usage(), file=sys.stderr)
            sys.exit(2)
    elif cmd_name == "set":
        if len(args) < 2:
            print("用法: lx-goal.py set <key> <value>")
            sys.exit(1)
        cmd_set(args[0], args[1])
    elif cmd_name == "subagent-log":
        if not args:
            print("用法: lx-goal.py subagent-log assign|complete|fail|summary <agent> <subtask> [detail]")
            sys.exit(1)
        cmd_subagent_log(*args[:4])
    elif cmd_name == "_update-lock":
        # kwargs parsing: key=value
        kwargs = {}
        for arg in args:
            if "=" in arg:
                k, v = arg.split("=", 1)
                kwargs[k] = v
        cmd_update_lock(**kwargs)
    elif cmd_name == "skip-risk":
        # skip-risk "描述" [risk_level] [reason] [impact]
        cmd_skip_risk(*(args[:4]))
    elif cmd_name in ("task-done", "verify-step", "hard-boundary-hit", "blocked-human"):
        handlers = {
            "task-done": cmd_task_done,
            "verify-step": cmd_verify_step,
            "hard-boundary-hit": cmd_hard_boundary_hit,
            "blocked-human": cmd_blocked_human,
        }
        rc = handlers[cmd_name](*(args[:3]))
        if isinstance(rc, int):
            sys.exit(rc)
    else:
        # off, status, phase0-done, plan-done, report, poll, retry, done — 无参数
        rc = KNOWN_SUBCOMMANDS[cmd_name]()
        if isinstance(rc, int):
            sys.exit(rc)


if __name__ == "__main__":
    main()
