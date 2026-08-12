#!/usr/bin/env python3
"""
carros_base.py — CarrorOS Base 核心状态系统

L1 Workflow: Plan → Step → Verify → Archive

Usage:
    python3 .claude/scripts/carros_base.py init --task-id TASK_ID [--step S1 [S2 ...]] [--level L1|L2]
    python3 .claude/scripts/carros_base.py status
    python3 .claude/scripts/carros_base.py tick
    python3 .claude/scripts/carros_base.py report              # 生成 final-report.md
    python3 .claude/scripts/carros_base.py verify [--step S1]
    python3 .claude/scripts/carros_base.py clarify --title "任务名"
    python3 .claude/scripts/carros_base.py verify [--step S1]
    python3 .claude/scripts/carros_base.py archive [--force]
    python3 .claude/scripts/carros_base.py bench [scene]
    python3 .claude/scripts/carros_base.py lint [path]
    python3 .claude/scripts/carros_base.py help

Exit codes: 0 = ok, 1 = warnings, 2 = errors
"""

import fcntl
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    from sub_agent_result import TERMINAL_STATUSES, update_result_locked
except ImportError:
    TERMINAL_STATUSES = frozenset({"completed", "failed", "timeout", "cancelled"})
    update_result_locked = None

try:
    import carros_utils
except ImportError:
    carros_utils = None

try:
    import task_state_tracker as tst
except ImportError:
    tst = None

try:
    import goal_state_machine as gsm
    from goal_state_machine import GoalMachine, GoalError
except ImportError:
    gsm = None
    GoalMachine = None
    GoalError = Exception

try:
    import goal_contracts
    from goal_contracts import ResearchGate, ResearchGateError, PlanGate, PlanGateError
except ImportError:
    goal_contracts = None
    ResearchGate = None
    ResearchGateError = Exception
    PlanGate = None
    PlanGateError = Exception

try:
    import task_planner
except ImportError:
    task_planner = None

try:
    import sub_agent_manager as sam
except ImportError:
    sam = None

try:
    import step_contracts
except ImportError:
    step_contracts = None

try:
    import phase_contracts
except ImportError:
    phase_contracts = None

try:
    import state_transitions
except ImportError:
    state_transitions = None

from token_lifecycle import finalize_token


# ─── Optional-import guard helper ─────────────────────────────
# Task75: Use at call sites where an optional import is required.
# Raises RuntimeError with context on missing module instead
# of silent AttributeError or type confusion.

def _require_import(obj: Any, name: str, ctx: str = "") -> None:
    """Assert that an optional import is available.

    Args:
        obj: The imported module/object (may be None).
        name: Human-readable module name for error message.
        ctx: Calling context description (e.g. function name).

    Raises:
        RuntimeError: If obj is None (import failed).
    """
    if obj is None:
        hint = f" [{ctx}]" if ctx else ""
        raise RuntimeError(
            f"Required module '{name}' is unavailable{hint}. "
            "Install or restore the module and retry."
        )


# ============================================================
# Shared Goal Lifecycle Functions (Task74+)
# ============================================================

def advance_goal_phase(token_path, target_state, research_path=None, plan_path=None,
                       executor_path=None, verify_results=None, reason=""):
    """推进 Goal 状态机到目标状态，途经 gate 验证。

    供 Task76 lx-goal 调用，确保 lifecycle wrapper 必须传文档路径。

    Task75: 新增 executor_path + verify_results 参数，支持 EXECUTING→VERIFYING
    和 VERIFYING→ARCHIVING 的全程证据验证。

    goal 模式：import 失败时 raise RuntimeError（fail-closed）
    非 goal 模式：静默降级返回 None

    Args:
        token_path: token.json 路径
        target_state: 目标状态名
        research_path: research.md 路径（用于 ResearchGate）
        plan_path: plan.md 路径（用于 PlanGate）
        executor_path: executor.md 路径（用于 evidence 验证）
        verify_results: VerifyGate 裁决结果 dict（用于 ARCHIVING 门禁）
        reason: 转换原因

    Returns:
        str: 转换后的状态名
        None: 非 goal 模式且 GoalMachine 不可用时

    Raises:
        RuntimeError: goal 模式下 GoalMachine 不可用
        GoalMachine.GoalError: 转换非法或 gate 拒绝
    """
    if GoalMachine is None:
        raise RuntimeError(
            "GoalMachine import failed -- goal lifecycle unavailable"
        )

    # Task75: EXECUTING→VERIFYING 前校验 plan/executor 存在
    if target_state == "VERIFYING" and plan_path and executor_path:
        _plan_p = Path(plan_path) if isinstance(plan_path, (str, Path)) else None
        _exec_p = Path(executor_path) if isinstance(executor_path, (str, Path)) else None
        if _plan_p and not _plan_p.exists():
            raise GoalError(f"advance_goal_phase: plan.md not found at {plan_path}")
        if _exec_p and not _exec_p.exists():
            raise GoalError(f"advance_goal_phase: executor.md not found at {executor_path}")

    # Task75: VERIFYING→ARCHIVING 前校验 verify_results 全部 green
    if target_state == "ARCHIVING" and verify_results is not None:
        if isinstance(verify_results, dict):
            decisions = verify_results.get("decisions", []) if isinstance(verify_results.get("decisions"), list) else []
            has_failure = any(d not in ("VERIFIED", "WARN") for d in decisions)
            if has_failure:
                raise GoalError(f"advance_goal_phase: VerifyGate has failures, cannot archive")
            if verify_results.get("all_passed") is False:
                raise GoalError(f"advance_goal_phase: not all steps verified, cannot archive")

    gm = GoalMachine(str(token_path) if token_path else None)
    gm.transition(target_state, reason=reason,
                  research_path=research_path, plan_path=plan_path)
    return gm.current_state


def _require_goal_execution_state(token: dict, action: str, allowed: set[str] | None = None) -> bool:
    """Block Goal execution writes until the plan transition has passed."""
    if token.get("mode") != "goal":
        return True
    allowed_states = allowed or {"EXECUTING"}
    state = token.get("goal", {}).get("state")
    if state in allowed_states:
        return True
    print(
        f"❌ {action} blocked: Goal state={state or 'UNKNOWN'}; "
        "complete research → plan-done → EXECUTING first",
        file=sys.stderr,
    )
    return False

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
    HANDOFF_PATH = Path(".omc/session-handoff.md")
    AUDIT_DIR = STATE_DIR / "audit"


def _init_paths_from_token(token, found_path):
    """跨天恢复：用 _find_latest_token 找到的实际路径初始化。

    修复跨天 bug：_init_task_paths 按今天日期推导路径，token 在昨天目录时
    导致 "No active task"。found_path 是 token 的真实落盘路径。
    """
    _init_task_paths(
        task_id=token.get("session", {}).get("id", "unknown"),
        task_dir=token.get("task_dir") or None,
    )
    global TOKEN_PATH
    TOKEN_PATH = Path(found_path)

# ─── ANSI helpers ───
def _green(s): return f"\033[32m{s}\033[0m"
def _yellow(s): return f"\033[33m{s}\033[0m"
def _red(s): return f"\033[31m{s}\033[0m"
def _bold(s): return f"\033[1m{s}\033[0m"

# ═══════════════════════════════════════════
# Token helpers
# ═══════════════════════════════════════════

def _default_token(task_id=None, level="L1", steps=None):
    now = datetime.now(timezone.utc)
    suffix = now.strftime("%Y%m%d")
    tid = task_id or f"sess_{suffix}_0000"
    if steps is None:
        steps = ["S1"]
    return {
        "schema_version": _SCHEMA_VERSION,
        "revision": 0,
        "session": {
            "id": tid,
            "level": level,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
        "task_dir": str(TASK_DIR) if TASK_DIR else "",
        "status": "active",
        "task": {
            "current_step": None,
            "status": "planning",
            "blocked": None,
        },
        "stats": {
            "done": 0,
            "total": len(steps),
            "tick": 0,
        },
    }


def _load_token(path=None):
    p = Path(path) if path else TOKEN_PATH
    if p and p.exists():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


class CASConflict(RuntimeError):
    """Raised when strict token CAS detects a stale expected revision."""

    def __init__(self, expected_revision, current_revision):
        self.expected_revision = expected_revision
        self.current_revision = current_revision
        super().__init__(
            f"CAS_CONFLICT expected_revision={expected_revision} current_revision={current_revision}"
        )


def _save_token(token, path=None, expected_revision=None):
    p = Path(path) if path else TOKEN_PATH
    if p is None:
        raise ValueError("TOKEN_PATH is not initialized")
    p.parent.mkdir(parents=True, exist_ok=True)
    lock_path = p.with_suffix(p.suffix + ".lock")
    tmp_path = p.with_suffix(p.suffix + f".{os.getpid()}.tmp")

    with lock_path.open("a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            token.setdefault("session", {})["updated_at"] = datetime.now(timezone.utc).isoformat()

            if expected_revision is not None:
                current = _load_token(p) if p.exists() else None
                current_revision = current.get("revision", 0) if isinstance(current, dict) else 0
                if current_revision != expected_revision:
                    raise CASConflict(expected_revision, current_revision)
                token["revision"] = current_revision + 1
            else:
                token["revision"] = token.get("revision", 0) + 1  # legacy monotonic increment

            data = json.dumps(token, indent=2, ensure_ascii=False) + "\n"
            with tmp_path.open("w", encoding="utf-8") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, p)
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def now_iso():
    return carros_utils.now_iso() if carros_utils else datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_handoff(token, plan_summary=None):
    """写入 Resume Capsule — 7 段结构化 handoff（R2 Compact Storm）"""
    import sys
    print(f"DEBUG: token type={type(token)}, repr={token!r}", file=sys.stderr)
    try:
        import lib.handoff_writer as hw
        tid = token.get("session", {}).get("id", "unknown")
        hw.write_handoff(TASK_DIR, tid, token, PLAN_PATH)
    except (ImportError, Exception) as e:
        pass
    HANDOFF_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    done = token.get("stats", {}).get("done", 0)
    total = token.get("stats", {}).get("total", 0)
    current = token.get("task", {}).get("current_step", "?")
    task_desc = (token.get("description") or (token.get("goal") or {}).get("description") or "")
    if not task_desc or task_desc == "未知":
        # Lossless handoff: derive goal from plan.md when the token has none.
        try:
            _plan_lines = PLAN_PATH.read_text(encoding="utf-8").splitlines() if PLAN_PATH else []
            for _l in _plan_lines:
                if _l.startswith("#") and not _l.startswith("# Plan"):
                    task_desc = _l.lstrip("# ").strip()
                    break
        except Exception:
            pass
    task_desc = (task_desc or "未知")[:200]
    level = token.get("level", token.get("session", {}).get("level", "L1"))
    # 读取 error-dna（最近 3 条）
    errors = ""
    try:
        edna = OMC_ROOT/ "error-dna.jsonl"
        if edna.exists():
            _lines = edna.read_text().strip().splitlines()[-3:]
            _types = []
            for _l in _lines:
                try:
                    _e = json.loads(_l)
                    _types.append(_e.get("type", _e.get("error_type", "?")))
                except Exception:
                    pass
            if _types:
                errors = ", ".join(_types)
    except Exception:
        pass
    # 读取 scope
    scope_lines = ""
    scope = token.get("scope", [])
    if scope:
        scope_lines = "\n".join(f"  - {s}" for s in scope[:8])
    # 读取 last-user-prompt
    last_intent = ""
    try:
        _lup = OMC_ROOT/ "state" / "last-user-prompt.md"
        if _lup.exists():
            last_intent = _lup.read_text(encoding="utf-8", errors="replace")[:200]
    except Exception:
        pass
    content = (
        f"# Session Handoff\n"
        f"\n"
        f"> 由 carros_base.py 于 {now} 更新\n"
        f"> 紧凑后自动读取本文件可恢复会话\n"
        f"\n"
        f"## Current Goal\n"
        f"{task_desc}\n"
        f"{('用户最后意图: ' + last_intent) if last_intent else ''}\n"
        f"\n"
        f"## Current State\n"
        f"- task_id: {token.get('session', {}).get('id', 'unknown')}\n"
        f"- level: {level}\n"
        f"- step: {current} ({done}/{total})\n"
        f"{('- errors: ' + errors) if errors else ''}\n"
        f"\n"
        f"## Active Files / Scope\n"
        f"{scope_lines if scope_lines else '  (未设定 scope)'}\n"
        f"\n"
        f"## Decisions Made\n"
        f"由 kernel.md 的哲学铁律指导，具体决策见 audit 日志。\n"
        f"\n"
        f"## Next Action\n"
        f"- 继续当前 step ({current})\n"
        f"- carros_base.py status 查看进度\n"
        f"- carros_base.py verify 验证\n"
        f"\n"
        f"## Risks\n"
        f"- 治理文件不可修改（hooks/ harness.yaml settings.json）\n"
        f"- token scope 不可越界写入\n"
        f"\n"
    )
    HANDOFF_PATH.write_text(content)


# ═══════════════════════════════════════════
# Plan / Executor helpers
# ═══════════════════════════════════════════

def _write_default_plan(steps=None):
    """创建默认 plan.md 模板 — RPE 标准（Task7 Phase2 GREEN）"""
    if steps is None:
        steps = ["S1"]
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Plan\n", "", "## Goal\n\n", "## Scope\n\n"]
    for i, s in enumerate(steps):
        phase_num = i + 1
        lines.append(f"## Phase {phase_num}\n")
        lines.append(f"- [ ] {s}: \n")
        lines.append(f"  - status: pending\n")
        lines.append(f"  - depends_on: none\n")
        lines.append(f"  - scope: task directory\n")
        lines.append(f"  - acceptance: step evidence is recorded\n")
        lines.append(f"  - verify: assertion: step {s} evidence is recorded\n")
        lines.append("\n")
    lines.append("---\n")
    lines.append("> 冻结规则：不改 scope、不改 step 顺序、不改 verify 条件。\n")
    PLAN_PATH.write_text("".join(lines))


def _write_default_executor():
    """创建 executor.md 证据账簿 — RPE 标准（Task7 Phase2 GREEN）"""
    EXECUTOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = """# Executor Evidence Ledger

> schema_version: v2
> 格式对齐 AGENTS.md §executor.md 证据块模板 — 每步对应一个 ### EV-<step_id> 块
> verify_gate 和 oracle 通过解析 ### EV-xxx / step: / assertion: 字段验证完成状态。

## Conditions

- 记录本 step 的范围、依赖和安全边界。

## Key Changes

- 记录本 step 的实际改动或明确 no-op。

## Decisions

- Rationale: 记录选择该执行路径的原因。

## Acceptance Checklist

- [ ] 在 VerifyGate 前完成本 step 的验收项。

## TDD Evidence

- Dependency TDD command: pending -> exit 0
- Regression TDD command: pending -> exit 0

## S1

### EV-S1

- step: S1
- type: test/review/change
- evidence_level: E2
- source: step execution
- exit_code: 0
- file: pending
- assertion: step evidence pending

---
"""
    EXECUTOR_PATH.write_text(content)


def _write_default_research():
    """创建 research.md — 子任务也可引用 src.md

    所有任务都写入 ResearchGate 门禁要求（L1/L2 均适用），防止 AI 声称 Phase 0 完成但文档为空。
    """
    RESEARCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    is_goal = os.environ.get("CARROROS_TASK_MODE") == "goal"
    content = """# Research

> 事实层：技术决策、架构边界、参考来源

<!-- ⚠️ ResearchGate 门禁：所有 8 个 section 必须有非占位内容 + 依赖树至少 1 条 -->

## 背景

## 约束

## 已知信息

## 不确定性

## 全貌

## 依赖树

## 方案

## Dependency TDD
"""
    if is_goal:
        content += """
## Phase 0（goal 模式前置澄清）
<!-- ⓪ 以下内容由 AI 在 Phase 0 完成后写入 -->

"""
    RESEARCH_PATH.write_text(content)


def _write_goal_scaffolds() -> None:
    """Create sealed document skeletons; Goal phases fill them in order."""
    _write_default_research()
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_text(
        "# Plan\n\n"
        "## Gate\n"
        "- level: L2\n\n"
        "## Plan Pending\n"
        "<!-- Fill only after phase0-done moves Goal to PLANNING. -->\n",
        encoding="utf-8",
    )
    EXECUTOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    # 复用 RPE 标准 executor 模板：预声明终态门禁要求的全部工件节
    # （Conditions/Key Changes/Decisions/Acceptance Checklist/TDD Evidence），
    # 避免「先过门禁后补信息」的次序缺陷 —— 信息须在门禁前就位。
    _write_default_executor()


def _init_task_dirs():
    """初始化任务子目录：sub_task/ + state/ + state/audit + artifacts/"""
    for d in [SUB_TASK_DIR, STATE_DIR, AUDIT_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    # artifacts/ for tool store
    artifacts_dir = TASK_DIR / "artifacts" if TASK_DIR else None
    if artifacts_dir:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
    # evidence.jsonl for L2+
    if TASK_DIR:
        evidence_path = TASK_DIR / "evidence.jsonl"
        if not evidence_path.exists():
            evidence_path.touch()
    # working-set.yaml for L2+
    if TASK_DIR:
        ws_path = TASK_DIR / "working-set.yaml"
        if not ws_path.exists():
            ws_template = PROJECT_ROOT / ".claude/references/working-set-template.yaml"
            if ws_template.exists():
                ws_path.write_text(ws_template.read_text(encoding="utf-8"))
            else:
                ws_path.write_text("# working-set.yaml — auto-generated by carros_base.py\n")


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
    """追加审计事件到当天 JSONL — 委托 carros_utils（自动绑定 task_id）"""
    if isinstance(data, dict) and "task_id" not in data:
        _tid = None
        try:
            _token = _load_token()
            if _token:
                _tid = (_token.get("session") or {}).get("id")
        except Exception:
            _tid = None
        data = dict(data)
        data["task_id"] = _tid or "unknown"
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


def _dry_run_migration() -> list[dict]:
    """Dry-run migration report: scan legacy YYYY-MM-DD dirs, print source/target/collision.

    0 writes, re-entrant. 返回 list of {source, target, slug, collision}.
    """
    results: list[dict] = []
    OMC_TASKS.mkdir(parents=True, exist_ok=True)
    if not OMC_TASKS.exists():
        return results

    try:
        from lib.task_paths import scan_task_dirs, find_conflicts
        entries = scan_task_dirs(OMC_TASKS, include_legacy=True)
        conflicts = find_conflicts(entries)
        conflict_slugs = {c["slug"] for c in conflicts}
        legacy_entries = [e for e in entries if e.is_legacy]

        for e in legacy_entries:
            target_date = e.date
            target = str(OMC_TASKS / target_date / e.slug)
            results.append({
                "source": str(e.path),
                "target": target,
                "slug": e.slug,
                "collision": e.slug in conflict_slugs,
            })
    except ImportError:
        pass

    if results:
        print(f"{'Source':<60} {'Target':<60} {'Collision':<10}")
        print("-" * 130)
        for r in results:
            print(f"{r['source']:<60} {r['target']:<60} {str(r['collision']):<10}")
    else:
        print("No legacy YYYY-MM-DD directories found.")

    return results


def cmd_migrate():
    """Dry-run migration: 扫描 legacy YYYY-MM-DD → YYYYMMDD 报告.

    用法:
        carros_base.py migrate [--dry-run]

    当前仅支持 dry-run (零写入), 可安全重入。
    """
    _dry_run_migration()
    return 0


def cmd_resolve_conflict():
    """显示 slug 跨格式冲突 (YYYYMMDD + YYYY-MM-DD 并存).

    用法:
        carros_base.py resolve-conflict [--slug <slug>]

    Dry-run only, 零写入。
    """
    OMC_TASKS.mkdir(parents=True, exist_ok=True)
    try:
        from lib.task_paths import scan_task_dirs, find_conflicts
        entries = scan_task_dirs(OMC_TASKS, include_legacy=True)
        conflicts = find_conflicts(entries)
        if not conflicts:
            print("No conflicts found.")
            return 0

        argv = sys.argv[sys.argv.index("resolve-conflict") + 1:]
        slug_filter = None
        i = 0
        while i < len(argv):
            if argv[i] == "--slug" and i + 1 < len(argv):
                slug_filter = argv[i + 1]; i += 2
            else:
                i += 1

        print(f"{'Slug':<40} {'Canonical Path':<60} {'Legacy Path':<60}")
        print("-" * 160)
        for c in conflicts:
            if slug_filter and c["slug"] != slug_filter:
                continue
            print(f"{c['slug']:<40} {c['canonical_path']:<60} {c['legacy_path']:<60}")
    except ImportError:
        print("lib/task_paths.py not available")
        return 2
    return 0


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


def cmd_auto_init(steps=None, target=None):
    """自动初始化模式 — 不要求 task_id，根据当前上下文自动推导。

    用于 PretoolUse hook 自动 init 场景：检测到无 token 写操作时，
    自动生成 token + task 文档，不阻断 agent 工作流。

    task_id 格式：auto_{ts}_{target_file_hash_short}
    scope 自动推导：从写操作的目标文件路径
    """
    import hashlib
    now = datetime.now(timezone.utc)
    ts = now.strftime("%H%M%S")
    if target:
        h = hashlib.md5(target.encode()).hexdigest()[:6]
        tid = f"auto_{h}_{ts}"
    else:
        tid = f"auto_{ts}"
    if steps is None:
        steps = ["S1"]
    _init_task_paths(task_id=tid)
    token = _default_token(task_id=tid, level="L1", steps=steps)
    # 如果提供了 target，写入 scope
    if target:
        token["scope"] = [target]
    _save_token(token)
    _write_default_plan(steps=steps)
    _write_default_executor()
    _write_default_research()
    _init_task_dirs()
    _write_handoff(_load_token() or token)
    print(f"Auto-init complete: {tid}")
    _write_audit("auto_init", {
        "task_id": tid,
        "target": target,
        "reason": "no_active_token",
    }, fallback=True)
    return 0


def _task_token_exists(task_id: str) -> "Path | None":
    """Return the first token path whose session.id equals task_id (any status).

    Used by cmd_init to fail-closed on explicit task-id reuse instead of
    silently overwriting an existing task (irreversible). Lock sidecar files
    (.json.lock) are never matched by the *.json glob.
    """
    if not OMC_TOKENS:
        return None
    OMC_TOKENS.mkdir(parents=True, exist_ok=True)
    for jf in OMC_TOKENS.glob("*/*.json"):
        try:
            token = json.loads(jf.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(token, dict) and token.get("session", {}).get("id") == task_id:
            return jf
    return None


def cmd_resume(task_doc=None, auto_continue=False):
    """从任务文档路径恢复中断任务（中断续传）。

    唯一合法输入: `.omc/tasks/YYYYMMDD/{task_name}`。
    校验路径 → 读 plan/executor/token/continuation → 恢复报告 + Next Action
    + 写 state/continuation.json 与 state/resume.md（复用 RecoveryCheckpoint）。
    """
    if not task_doc:
        print(_red("❌ resume 需要任务文档路径: .omc/tasks/YYYYMMDD/{task_name}"), file=sys.stderr)
        print("   例: carros_base.py resume .omc/tasks/20260812/我的-任务名-abc123", file=sys.stderr)
        return 2
    try:
        from lib.task_paths import resolve_task_document
    except ImportError:
        print(_red("❌ lib/task_paths.py 不可用"), file=sys.stderr)
        return 2

    try:
        doc = resolve_task_document(task_doc)
    except ValueError as e:
        print(_red(f"❌ {e}"), file=sys.stderr)
        return 2

    task_dir = doc["task_dir"]
    if not task_dir.exists():
        print(_red(f"❌ 任务目录不存在: {task_dir}"), file=sys.stderr)
        return 2

    # ── 读 token（若存在）──
    token_info: dict[str, Any] = {}
    if doc["token_path"].exists():
        try:
            tok = json.loads(doc["token_path"].read_text(encoding="utf-8"))
            token_info = {
                "level": tok.get("session", {}).get("level", "?"),
                "status": tok.get("status", "?"),
                "task_status": (tok.get("task") or {}).get("status", "?"),
                "current_step": (tok.get("task") or {}).get("current_step"),
                "done": (tok.get("stats") or {}).get("done", 0),
                "total": (tok.get("stats") or {}).get("total", "?"),
                "goal_state": (tok.get("goal") or {}).get("state"),
            }
        except (OSError, json.JSONDecodeError):
            pass

    # ── 复用 RecoveryCheckpoint 生成恢复上下文 + 续跑产物 ──
    status = {"status": "unknown", "type": "task", "completed_steps": [], "pending_steps": []}
    cont: dict[str, Any] | None = None
    try:
        from sub_agent_recovery import RecoveryCheckpoint
        rc = RecoveryCheckpoint(task_dir)
        status = rc.check_status()
        cont = rc.save_continuation()   # 写 state/continuation.json
        rc.save_resume()                # 写 state/resume.md
    except Exception:
        pass

    # ── 恢复报告 ──
    slug = doc["slug"]
    print(_green(f"⏩ Resume: {slug} [{token_info.get('level', '?')}]"))
    print(f"   Date: {doc['date']} | Status: {token_info.get('status') or status.get('status')}")
    print(f"   文档: {task_dir}")
    done = token_info.get("done", 0)
    total = token_info.get("total", "?")
    print(f"   Progress: {done}/{total}")
    if token_info.get("task_status"):
        print(f"   Task status: {token_info['task_status']}")
    if token_info.get("current_step"):
        print(f"   Current step: {token_info['current_step']}")
    if token_info.get("goal_state"):
        print(f"   Goal state: {token_info['goal_state']}")

    completed = status.get("completed_steps") or []
    pending = status.get("pending_steps") or []
    if completed:
        print(_green(f"   ✅ 已完成: {', '.join(completed)}"))
    if pending:
        print(f"   ◷ 待办: {', '.join(pending)}")

    if cont is not None:
        action = "已标记续跑" if cont.get("continuation_attempted") else "任务处于终态，无需续跑"
        print(f"   → {action} (state/continuation.json)")
    print(f"   → 恢复摘要: {task_dir / 'state' / 'resume.md'}")

    # 持久化激活指针：后续 status/tick/verify 无需 env 直接定位（给路径即续传）
    try:
        state_root = OMC_ROOT / "state"
        state_root.mkdir(parents=True, exist_ok=True)
        (state_root / "active-resume.json").write_text(
            json.dumps({
                "date": doc["date"],
                "slug": doc["slug"],
                "task_dir": str(task_dir),
                "token_path": str(doc["token_path"]),
                "activated_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(_green("   → 已写入活跃任务指针：后续 tick/verify 直接继续，无需 env"))
    except OSError:
        pass

    print()
    if pending:
        print(_yellow(f"   ⏭️  Next Action: 继续执行 {pending[0]}"))
        print(f"      python3 .claude/scripts/carros_base.py tick --step {pending[0]}")
    elif token_info.get("goal_state"):
        print(_yellow(f"   ⏭️  Next Action: 继续推进 Goal 阶段（{token_info['goal_state']}）"))
    else:
        print(_green("   ✅ 无待办步骤，任务可能已完成"))

    # ── resume → continue → verify 完整链（精专化，C9/E8 提分）──
    # --continue 时自动执行下一个 pending step 的 tick + verify，不依赖人手动续跑。
    if auto_continue and pending:
        next_step = pending[0]
        print(_green(f"\n   ▶ 自动续跑 (--continue): tick {next_step} → verify"))
        try:
            tick_rc = cmd_tick(step_id=next_step)
            if tick_rc != 0:
                print(_red(f"   ⚠️  tick {next_step} 返回 {tick_rc}，跳过 verify"), file=sys.stderr)
                return tick_rc
            verify_rc = cmd_verify(step_id=next_step)
            print(f"   → tick+verify {next_step} 完成 (verify rc={verify_rc})")
            return verify_rc
        except Exception as exc:  # 完整链失败不炸任务
            print(_red(f"   ⚠️ 续跑异常: {exc}"), file=sys.stderr)
            return 2
    return 0


def cmd_init(task_id, level="L1", steps=None, user_request=None, task_dir=None, feature=None, task_mode=None, force=False):
    """初始化任务 — IntakeGate 分级 → PlanBuilder 生成冻结计划

    task_mode: "goal" 时写入 token 标记,由 lx-goal.py 委托调用。
    force=True: 显式覆盖已存在任务（不可逆，须人类授权并记录 audit）。
    """
    # S3: 任务名合法性校验（防路径逃逸）— 复用 task_paths SSOT
    if task_id:
        try:
            from lib.task_paths import is_valid_task_name
            if not is_valid_task_name(task_id):
                print(_red(f"❌ 非法任务名: {task_id!r}"), file=sys.stderr)
                print("   任务名仅允许 CJK 字母数字 . _ -（首字符非符号），且不得含路径分隔符或 ..", file=sys.stderr)
                return 2
        except ImportError:
            pass  # lib 不可用时回退原行为（不炸）

    _init_task_paths(task_id=task_id, task_dir=task_dir)
    if not force:
        existing = _task_token_exists(task_id)
        if existing is not None:
            print(_red(f"❌ 任务已存在: {task_id} (token: {existing})"), file=sys.stderr)
            print("   已拒绝覆盖。如确需重建，请显式传 --force（不可逆，将覆盖 token 与任务文档）。", file=sys.stderr)
            return 2
        if TASK_DIR and TASK_DIR.exists() and any(TASK_DIR.iterdir()):
            print(_red(f"❌ 任务目录已存在且非空: {TASK_DIR}"), file=sys.stderr)
            print("   已拒绝覆盖。如确需重建，请显式传 --force（不可逆）。", file=sys.stderr)
            return 2
    else:
        _write_audit("task.init.force", {"task_id": task_id, "task_dir": str(TASK_DIR or "")})
    if task_mode:
        os.environ.setdefault("CARROROS_TASK_MODE", task_mode)

    intake_decision_data = None

    # IntakeGate 前置分级（如有 user_request）
    if user_request:
        try:
            import subprocess
            intake_script = _hook_dir / "intake_gate.py"
            if intake_script.exists():
                cmd = [sys.executable, str(intake_script), user_request]
                if level in ("L2_ENHANCE", "L2"):
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

    # ── PlanBuilder 生成冻结计划 ──
    if task_mode == "goal":
        token = _default_token(task_id=task_id, level=level, steps=steps)
        _save_token(token)
        _write_goal_scaffolds()
        if phase_contracts is not None:
            phase_contracts.start_phase(TASK_DIR, "CLARIFY")
        print(_green("   Goal scaffolds created: research → plan → executor → phase handoff"))
    elif steps and len(steps) > 1:
        # 显式多步骤：绕过 PlanBuilder，按步骤列表生成
        token = _default_token(task_id=task_id, level=level, steps=steps)
        _save_token(token)
        _write_default_plan(steps=steps)
        _write_default_executor()
        _write_default_research()
        print(_green(f"   Multi-step plan: {len(steps)} steps (bypassed PlanBuilder)"))
    elif intake_decision_data:
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

    # task_mode="goal": 向 token 注入 mode 字段,供 lx-goal.py 捕获
    if task_mode == "goal":
        token_data = _load_token()
        if token_data:
            token_data["mode"] = "goal"
            _save_token(token_data)
        else:
            # 静默丢失比明确失败更危险 — token 不存在时 mode 注入丢失,必须告警
            print("⚠️ goal mode: token 未生成, mode=goal 注入跳过", file=sys.stderr)
        # 输出机器可读路径供 lx-goal.py 解析 (stdout 最后一行的 CARROROS_TASK_DIR= 为契约)
        print(f"\nCARROROS_TASK_DIR={TASK_DIR}")
    return 0


def _find_latest_token(require_active=True):
    """按显式上下文读取 token；无上下文时不扫描其他任务。"""
    override = os.environ.get("CARROROS_TOKEN_PATH", "").strip()
    task_id = os.environ.get("CARROROS_TASK_ID", "").strip()
    task_dir = os.environ.get("CARROROS_TASK_DIR", "").strip()

    def matches(token, path):
        if require_active and token.get("status") != "active":
            return False
        if task_id and token.get("session", {}).get("id") != task_id:
            return False
        if task_dir:
            token_dir = token.get("task_dir", "")
            if not token_dir:
                return False
            if Path(token_dir).expanduser().resolve() != Path(task_dir).expanduser().resolve():
                return False
        return True

    if override:
        explicit = Path(override).expanduser()
        try:
            token = json.loads(explicit.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None, None
        if not isinstance(token, dict) or not matches(token, explicit):
            return None, None
        return token, explicit

    if not task_id and not task_dir:
        # 无上下文：读显式激活指针（resume 写入），不扫描其他任务
        ptr = OMC_ROOT / "state" / "active-resume.json"
        try:
            data = json.loads(ptr.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        if data:
            tp = Path(str(data.get("token_path", ""))).expanduser()
            try:
                token = json.loads(tp.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                token = None
            if isinstance(token, dict) and matches(token, tp):
                return token, tp
        return None, None

    OMC_TOKENS.mkdir(parents=True, exist_ok=True)
    candidates = []
    for jf in OMC_TOKENS.glob("*/*.json"):
        try:
            token = json.loads(jf.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(token, dict) and matches(token, jf):
            candidates.append((jf.stat().st_mtime, jf, token))

    if task_id or task_dir:
        if len(candidates) != 1:
            return None, None
        _, path, token = candidates[0]
        return token, path

    if require_active and len(candidates) == 1:
        _, path, token = candidates[0]
        return token, path
    return None, None


def _sync_token_scope_from_plan(token: dict, plan_path: Path | None = None) -> dict:
    """Copy the frozen plan scope into the top-level hook scope before execution."""
    plan_path = plan_path or PLAN_PATH
    if not plan_path or not plan_path.exists():
        return token
    lines = plan_path.read_text(encoding="utf-8").splitlines()
    in_scope = False
    scope: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "## Scope":
            in_scope = True
            continue
        if in_scope and stripped.startswith("## "):
            break
        if in_scope and stripped.startswith("-"):
            value = stripped[1:].strip()
            if value and value not in scope:
                scope.append(value)
    if scope and token.get("scope") != scope:
        token["scope"] = scope
        token.setdefault("task", {})["scope"] = scope
        _save_token(token)
    return token


def cmd_status(hot_mode=True):
    """展示当前任务状态。默认 Hot Card 模式。--full 出完整状态。"""
    if not TOKEN_PATH or not TOKEN_PATH.exists():
        token, found_path = _find_latest_token()
        if token and found_path:
            _init_paths_from_token(token, found_path)
        else:
            print(_yellow("⚠  No active task"))
            return 0
    token = _load_token()
    if not token:
        print(_yellow("⚠  No active task (token.json not found)"))
        return 0

    if hot_mode:
        # Hot Card — 极简状态（默认）
        try:
            import lib.hot_card as hc
            card = hc.cmd_status_hot(token, TOKEN_PATH, PLAN_PATH, EXECUTOR_PATH)
            print(card)
            hc_len = len(card)
            if hc_len > 4500:
                print(_yellow(f"\n⚠  Hot Card exceeds 4.5K chars: {hc_len}"))
            return 0
        except ImportError:
            # fallback: lib/ not available
            pass

    # Full status（--full 模式或 fallback）
    s = token.get("stats", {})
    status_top = token.get("status", "?")
    status_icon = _green("●") if status_top == "active" else _red("●")
    print(f"{status_icon} Task: {token.get('session', {}).get('id', '?')} [{token.get('session', {}).get('level', '?')}]")
    print(f"   Status: {status_top}")
    print(f"   Progress: {s.get('done', 0)}/{s.get('total', 0)} steps completed")
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


def cmd_tick(step_id=None):
    """递增 tick 计数器并原子激活可执行步骤。"""
    if not TOKEN_PATH or not TOKEN_PATH.exists():
        token, found_path = _find_latest_token()
        if token and found_path:
            _init_paths_from_token(token, found_path)
        else:
            print(_red("❌ No active task"))
            return 2
    token = _load_token()
    if not token:
        print(_red("❌ No active task"))
        return 2
    if not _require_goal_execution_state(token, "tick"):
        return 2
    token = _sync_token_scope_from_plan(token)

    # Use an explicit step when requested; otherwise find the first activatable step.
    current_step = step_id
    if current_step is None and PLAN_PATH and PLAN_PATH.exists() and step_contracts:
        plan_content = PLAN_PATH.read_text()
        steps = step_contracts.parse_plan_steps(plan_content)
        activatable = step_contracts.find_first_activatable_step(steps)
        if activatable:
            current_step = activatable
    elif current_step is None and PLAN_PATH and PLAN_PATH.exists():
        # fallback: simple regex
        plan_content = PLAN_PATH.read_text()
        pending_steps = re.findall(r"^- \[ \] (\S+?):", plan_content, re.MULTILINE)
        if pending_steps:
            current_step = pending_steps[0]
    elif current_step is None:
        current_step = token.get("task", {}).get("current_step")

    if current_step and step_contracts and PLAN_PATH and PLAN_PATH.exists():
        step_info = next(
            (step for step in step_contracts.parse_plan_steps(PLAN_PATH.read_text())
             if step["id"] == current_step),
            None,
        )
        if step_info and step_info["status"] in ("active", "completed"):
            print(f"   ◷ Step {current_step} already {step_info['status']}; tick is idempotent")
            return 0

    if "tick" in token.get("stats", {}):
        token["stats"]["tick"] += 1
        print(f"   Tick: {token['stats']['tick']}")
    else:
        token["stats"]["turns"] = token["stats"].get("turns", 0) + 1
        print(f"   Turn: {token['stats']['turns']}")

    # Task75: atomic step activation via step_contracts
    if current_step and step_contracts and PLAN_PATH and EXECUTOR_PATH and TOKEN_PATH:
        try:
            step_contracts.start_step_atomic(TOKEN_PATH, PLAN_PATH, EXECUTOR_PATH, current_step)
            print(f"   ◷ Activated step: {current_step} (atomic)")
        except ValueError as e:
            print(_yellow(f"   ⚠ Step activation skipped: {e}"))
        except Exception as e:
            print(_yellow(f"   ⚠ Step activation error: {e}"))
    elif current_step:
        # legacy task-state tracking
        if tst:
            tst.mark_step_started(TOKEN_PATH, current_step)
            print(f"   ◷ Tracking {current_step} (use 'verify' to complete)")
    return 0


def _run_dual_judge(token: dict) -> int:
    """L2 任务 verify 自动双审判：static + runtime oracle → meta 聚合。

    裁决落盘 .omc/state/oracle/{task_id}/meta-latest.json。
    Returns: 0=ACCEPT/ADVISORY（放行）, 2=REJECT（verify 不通过）, 3=ESCALATE（放行但提示人工）。
    """
    task_id = token.get("session", {}).get("id", "unknown")
    # Primary: unified oracle_agent.py (v2.0.0+)
    oracle_agent = _hook_dir / "oracle_agent.py"
    # Legacy fallback: static/runtime/meta are deprecated, keep for backward compat
    static_agent = _hook_dir / "static_oracle_agent.py"
    runtime_agent = _hook_dir / "runtime_oracle_agent.py"
    meta = _hook_dir / "meta_oracle.py"
    if oracle_agent.exists():
        # Use unified oracle_agent.py (static+runtime+duo in one script)
        pass  # caller should prefer oracle_agent.py over legacy scripts
    elif not (static_agent.exists() and runtime_agent.exists() and meta.exists()):
        print(_yellow("⚠  dual-judge 脚本缺失，跳过（降级为人工复核）"))
        return 0

    print("⚖️  L2 双审判官裁决（static → runtime → meta）...")
    for name, agent in (("static", static_agent), ("runtime", runtime_agent)):
        try:
            r = subprocess.run(
                [sys.executable, str(agent), "review", "--task-id", task_id],
                capture_output=True, text=True, timeout=120,
            )
            if r.returncode not in (0, 1):
                print(_yellow(f"⚠  {name} oracle exit={r.returncode}: {r.stderr[:200]}"))
        except Exception as exc:
            print(_yellow(f"⚠  {name} oracle 异常: {exc}"))

    try:
        r = subprocess.run(
            [sys.executable, str(meta), "aggregate", "--task-id", task_id],
            capture_output=True, text=True, timeout=30,
        )
        out = r.stdout.strip()
        verdict = "UNAVAILABLE"
        try:
            json_start = out.find("{")
            if json_start >= 0:
                verdict = json.loads(out[json_start:]).get("verdict", "UNAVAILABLE")
        except Exception:
            pass
        _write_audit("dual_judge", {"task_id": task_id, "verdict": verdict, "exit": r.returncode})
        if verdict == "REJECT":
            print(_red(f"⚖️  双审判 REJECT — verify 不通过，详见 .omc/state/oracle/{task_id}/meta-latest.json"))
            return 2
        if verdict == "ESCALATE":
            print(_yellow(f"⚖️  双审判 ESCALATE — 建议人工复核"))
            return 3
        print(_green(f"⚖️  双审判 {verdict}"))
        return 0
    except Exception as exc:
        print(_yellow(f"⚠  meta 聚合异常: {exc}（降级放行，需人工复核）"))
        return 0


def _run_verify_gate(step_id):
    """Shell out 到 verify_gate.py 裁决 step — 返回 (decision, reason, payload)。

    fail-closed: 脚本缺失/执行异常/输出不可解析 一律 BLOCKED。
    decision 取自 stdout JSON(exit code 仅辅助: VERIFIED=0, 其余=1)。
    """
    import subprocess
    # carros_base.py 是符号链接(.claude/scripts -> .omc/scripts),
    # verify_gate.py 实体在 .claude/scripts — 三候选定位,fail-closed
    _candidates = [
        Path(__file__).parent / "verify_gate.py",
        Path(__file__).resolve().parent / "verify_gate.py",
        Path(__file__).resolve().parents[2] / ".claude/scripts" / "verify_gate.py",
    ]
    script = next((c for c in _candidates if c.exists()), None)
    if script is None:
        return "BLOCKED", "verify_gate_missing", {
            "required_action": "恢复 .claude/scripts/verify_gate.py 后重跑"}
    cmd = [sys.executable, str(script), "--step", step_id,
           "--plan", str(PLAN_PATH), "--executor", str(EXECUTOR_PATH)]
    if TOKEN_PATH:
        cmd += ["--token", str(TOKEN_PATH)]
    spec = (TASK_DIR / "spec.md") if TASK_DIR else None
    if spec and spec.exists():
        cmd += ["--spec", str(spec)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as exc:
        return "BLOCKED", f"verify_gate_error:{type(exc).__name__}", {}
    try:
        payload = json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return "BLOCKED", f"verify_gate_bad_output:{(r.stdout or r.stderr or '')[:160]}", {}
    return payload.get("decision", "BLOCKED"), payload.get("reason", ""), payload


def cmd_verify(step_id=None, all_steps=False):
    """验证 step 完成 — VerifyGate 裁决通过才标记 plan.md [x] + 写 task-bound audit"""
    if not TOKEN_PATH or not TOKEN_PATH.exists():
        token, found_path = _find_latest_token()
        if token and found_path:
            _init_paths_from_token(token, found_path)
        else:
            print(_red("❌ No active task"))
            return 2
    token = _load_token()
    if not token:
        print(_red("❌ No active task"))
        return 2
    if not _require_goal_execution_state(token, "verify", {"EXECUTING", "VERIFYING"}):
        return 2
    token = _sync_token_scope_from_plan(token)
    if step_contracts is None:
        print(_red("❌ VerifyGate dependency unavailable: step_contracts.py"))
        return 2

    if not PLAN_PATH.exists():
        print(_red("❌ plan.md not found"))
        return 2

    plan = PLAN_PATH.read_text()

    if step_id:
        targets = [step_id]
    elif all_steps:
        # --all: 扫描 plan.md 找所有 [ ] 步骤，逐个验证
        targets = re.findall(r"^\- \[ \] (\S+?):", plan, re.MULTILINE)
        if not targets:
            print(_yellow("⚠  No pending steps to verify"))
            return 0
        print(f"   Batch verify: {len(targets)} pending step(s)")
    else:
        targets = []
        current = token.get("task", {}).get("current_step")
        if not current and PLAN_PATH:
            steps = step_contracts.parse_plan_steps(plan)
            current = step_contracts.find_first_activatable_step(steps)
            if not current:
                pending = [step["id"] for step in steps if step["status"] in ("pending", "active")]
                if pending:
                    print(_red(f"❌ Cannot resolve current step; pending steps remain: {', '.join(pending)}"))
                    return 2
        if current:
            targets.append(current)
        elif not re.search(r"^- \[ \] ", plan, re.MULTILINE):
            print(_yellow("⚠  All steps already completed"))
            return 0
        else:
            print(_red("❌ Cannot resolve current step from plan.md"))
            return 2

    level = token.get("session", {}).get("level", "L1_BASE")
    # ── Oracle 审查 ──
    # Base 不做深度审查（属 Enhance 域），仅做流程验证
    # 如需深度审查：在 Enhance 层调用 lib.phase3_oracle.spawn_oracle()
    verified_any = False
    plan_steps = step_contracts.parse_plan_steps(plan) if step_contracts else []
    for target in targets:
        target_info = next((step for step in plan_steps if step["id"] == target), None)
        if target_info and target_info["status"] == "completed":
            print(f"✅ {target}: already completed; verify is idempotent")
            verified_any = True
            continue
        # ── VerifyGate 接线（PKG-A）：无证据不 [x]，fail-closed ──
        decision, reason, gate_payload = _run_verify_gate(target)
        degraded = False
        if decision in ("VERIFIED", "WARN"):
            pass
        elif level != "L2_ENHANCE" and reason in ("no_verify_rules", "executor_missing"):
            # L1 轻量任务无验证契约：允许标记但必须留痕（不产生 VERIFIED，Gate6 不放行）
            degraded = True
        else:
            _write_audit("verify", {"step": target, "result": decision, "reason": reason})
            print(_red(f"❌ {target}: VerifyGate {decision} — {reason}"))
            required = gate_payload.get("required_action")
            if required:
                print(_yellow(f"   需要: {required}"))
            return 2

        # Oracle must pass before the completion transaction can persist [x].
        if level == "L2_ENHANCE" and not degraded:
            judge_rc = _run_dual_judge(token)
            if judge_rc == 2:
                return 2

        # ── Task75 Atomic Evidence Gate (non-degraded) ──
        # complete_step_atomic validates evidence, updates plan [x], token done++
        if step_contracts and not degraded:
            try:
                step_contracts.complete_step_atomic(
                    TOKEN_PATH, PLAN_PATH, EXECUTOR_PATH, target
                )
                # reload after atomic write
                plan = PLAN_PATH.read_text()
                token = _load_token()
            except ValueError as e:
                _write_audit("verify", {"step": target, "result": "REJECTED", "reason": str(e)})
                print(_red(f"❌ {target}: evidence incomplete — {e}"))
                return 2

        # Legacy/downgraded: manual plan+token update
        legacy_update = not step_contracts or degraded
        if legacy_update:
            pattern = re.compile(r"^- \[[ aA]\] " + re.escape(target) + r":", re.MULTILINE)
            replacement = f"- [x] {target}:"
            new_plan, count = pattern.subn(replacement, plan)
            if count > 0:
                plan = new_plan
                token["stats"]["done"] = token["stats"].get("done", 0) + 1
                if token["stats"]["done"] >= token["stats"]["total"]:
                    token["task"]["status"] = "completed"
            else:
                print(_yellow(f"⚠  {target}: not found in plan.md"))
                continue

        # ── Audit + feedback ──
        if degraded:
            _write_audit("verify_degraded", {"step": target, "reason": reason})
            print(_yellow(f"⚠  {target}: {reason} — 降级标记并留痕（非 VERIFIED）"))
        else:
            _write_audit("verify", {
                "step": target, "result": "VERIFIED", "gate": decision,
                "warnings": gate_payload.get("warnings", []),
            })
            print(_green(f"✅ {target}: VERIFIED"))

        # task-state: 标记完成
        if tst:
            tst.mark_step_completed(TOKEN_PATH, target)
            verdict = tst.format_tick_verdict(TOKEN_PATH, target)
            if verdict:
                print(verdict)
        verified_any = True

    if verified_any:
        # When step_contracts was used, plan/token already written; this is a safe re-write
        PLAN_PATH.write_text(plan)
        _save_token(token)
        _write_handoff(token)

        # state_transitions 强制 gate（ADR 0015）：任务全绿完成必须经过合法转换校验
        # 统一在 verify 尾部覆盖 step_contracts 与 legacy 两条完成路径
        if (state_transitions is not None
                and token.get("stats", {}).get("done", 0) >= token.get("stats", {}).get("total", 1)):
            state_transitions.require_transition("executing", "done")

        # Goal 状态自动推进: all steps done → EXECUTING ready → VERIFYING
        done = token.get("stats", {}).get("done", 0)
        total = token.get("stats", {}).get("total", 0)
        if phase_contracts is not None and TASK_DIR and token.get("mode") == "goal" and done >= total:
            try:
                phase_contracts.complete_step(TASK_DIR, target)
                phase_contracts.complete_phase(TASK_DIR, "EXECUTING", {
                    key: "execution complete" for key in phase_contracts.phase_contract("EXECUTING")["outputs"]["required"]
                })
                phase_contracts.start_phase(TASK_DIR, "VERIFYING")
                print("   已提交 VERIFYING 入参 schema：executor.md / step handoffs / verify rules")
            except (OSError, ValueError) as exc:
                print(_yellow(f"   ⚠ VERIFYING handoff 尚未就绪: {exc}"))
        if done >= total and GoalMachine:
            try:
                gm = GoalMachine(TOKEN_PATH)
                gm.auto_progress(token)
            except GoalError:
                pass
    return 0


def cmd_report(use_stdout=True, archive_mode=False):
    """
    生成 final-report.md — 共享节点，所有流程的终止点都应调用。

    从 executor.md + plan.md + audit JSONL 提取事实，不会编造。

    Args:
        use_stdout: 输出到 stdout（默认 True）
        archive_mode: 归档模式（写入 task_dir + 额外标记）

    Returns:
        0 = 成功, 1 = 无活跃任务, 2 = 错误
    """
    if not TOKEN_PATH or not TOKEN_PATH.exists():
        token, tp = _find_latest_token()
        if token and tp:
            _init_paths_from_token(token, tp)
        else:
            print(_red("❌ No active task"))
            return 2

    token = _load_token()
    if not token:
        print(_red("❌ No active task"))
        return 2

    report_text = ""

    if carros_utils and hasattr(carros_utils, "generate_final_report"):
        report_text = carros_utils.generate_final_report(token, TASK_DIR)
    else:
        # fallback brief
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        stats = token.get("stats", {})
        sid = token.get("session", {}).get("id", "unknown")
        report_text = (
            f"# Final Report: {sid}\n\n"
            f"**生成时间:** {now}\n"
            f"**状态:** {token.get('status', '?')}\n"
            f"**完成度:** {stats.get('done', 0)}/{stats.get('total', 0)}\n\n"
        )

    # 输出到 stdout（用户直接看到）
    if use_stdout:
        print(_bold("=" * 50))
        print(report_text)
        print(_bold("=" * 50))

    # 输出到 task_dir/final-report.md
    if TASK_DIR:
        from content_writer import write_chunked

        report_path = TASK_DIR / "final-report.md"
        write_chunked(report_path, report_text)
        print(_green(f"✅ Report saved: {report_path}"))

    return 0


def cmd_archive(force=False):
    """归档任务 — archive = lint + verify-summary + final-report + tombstone"""
    if not TOKEN_PATH or not TOKEN_PATH.exists():
        token, found_path = _find_latest_token()
        if token and found_path:
            _init_paths_from_token(token, found_path)
        else:
            print(_red("❌ No active task"))
            return 2
    print(_bold("Archiving task..."))

    # Step 1: run lint — 仅 error (exit>=2) 阻断，warning (exit=1) 可归档
    if not force:
        lint_ok = cmd_lint()
        if lint_ok >= 2:
            print(_red("❌ Lint has errors. Use --force to archive anyway."))
            return 2
        elif lint_ok == 1:
            print(_yellow("⚠  Lint warnings only — proceeding with archive"))
    else:
        print(_yellow("⚠  --force: skipping lint"))

    token = _load_token()
    if not token:
        print(_red("❌ No active task"))
        return 2

    if token.get("mode") == "goal":
        if GoalMachine is None:
            print(_red("❌ GoalMachine unavailable; archive aborted"), file=sys.stderr)
            return 2
        if phase_contracts is None or not TASK_DIR:
            print(_red("❌ phase handoff validator unavailable; archive aborted"), file=sys.stderr)
            return 2
        try:
            phase_contracts.validate_contract_ready(TASK_DIR, "VERIFYING")
        except ValueError as exc:
            print(_red(f"❌ VERIFYING handoff 未就绪，不能归档: {exc}"), file=sys.stderr)
            return 2
        try:
            archive_gate = GoalMachine(TOKEN_PATH)
        except Exception as exc:
            print(_red(f"❌ Goal state unreadable; archive aborted: {exc}"), file=sys.stderr)
            return 2
        if archive_gate.current_state != gsm.VERIFYING:
            print(
                _red(
                    f"❌ Goal archive requires VERIFYING, current={archive_gate.current_state}"
                ),
                file=sys.stderr,
            )
            return 2

    # Step 2: compare the frozen plan with token progress before reporting.
    plan_completed = None
    plan_total = None
    if step_contracts and PLAN_PATH and PLAN_PATH.exists():
        plan_steps = step_contracts.parse_plan_steps(PLAN_PATH.read_text())
        plan_completed = sum(1 for step in plan_steps if step.get("status") == "completed")
        plan_total = len(plan_steps)
        token_stats = token.get("stats", {})
        if (token_stats.get("done"), token_stats.get("total")) != (plan_completed, plan_total):
            conflict = f"token {token_stats.get('done', 0)}/{token_stats.get('total', 0)} vs plan {plan_completed}/{plan_total}"
            if not force:
                print(_red(f"❌ Archive blocked: state_conflict ({conflict})"))
                return 2
            token.setdefault("archive_warnings", []).append(f"state_conflict: {conflict}")
            print(_yellow(f"⚠  --force: preserving token progress despite {conflict}"))

    # Step 3: check all steps completed — 统一新格式
    if not force:
        pending = []
        if token.get("stats", {}).get("done", 0) < token.get("stats", {}).get("total", 0):
            pending = ["current_step not completed"]
        if pending:
            print(_red(f"❌ Steps not completed: {pending}"))
            return 2
    else:
        print(_yellow("⚠  --force: skipping step completion check"))

    # Step 4: generate final report (shared node)
    task_sid = token.get("session", {}).get("id", "unknown")

    # 用 task 目录语义名替代 session ID 作为 archive 目录名
    if TASK_DIR and TASK_DIR.exists():
        _d = TASK_DIR.parent.name
        _n = TASK_DIR.name
        archive_name = f"{_d}_{_n}"
    else:
        archive_name = task_sid
    archive_dir = OMC_ROOT / "archive" / archive_name
    archive_dir.mkdir(parents=True, exist_ok=True)
    token["status"] = "archived"
    token["archived_at"] = datetime.now(timezone.utc).isoformat()
    _save_token(token)
    # 归档成功 → 清除活跃任务指针（避免残留指向已归档任务）
    try:
        _aptr = OMC_ROOT / "state" / "active-resume.json"
        if _aptr.exists():
            _aptr.unlink()
    except OSError:
        pass
    cmd_report(use_stdout=False)
    print(_green(f"✅ Final report: {archive_dir / 'final-report.md'}"))

    # Step 4: 复制 report 到 archive 目录
    if token.get("mode") == "goal":
        if GoalMachine is None:
            print(_red("❌ GoalMachine unavailable; archive aborted"), file=sys.stderr)
            return 2
        try:
            gm = GoalMachine(TOKEN_PATH)
            if gm.current_state != gsm.VERIFYING:
                raise GoalError(
                    f"Goal archive requires VERIFYING, current={gm.current_state}"
                )
            gm.transition(gsm.ARCHIVING, reason="archive precondition passed")
            if phase_contracts is not None and TASK_DIR:
                phase_contracts.start_phase(TASK_DIR, "ARCHIVING")
                phase_contracts.complete_phase(TASK_DIR, "ARCHIVING", {
                    "archive.manifest": str(archive_dir),
                    "archive.verdict": "archive precondition passed",
                })
                phase_contracts.validate_contract_ready(TASK_DIR, "ARCHIVING")
            gm.transition(gsm.ARCHIVED, reason="archive completed")
            print(_green(f"   Goal State: {gsm.get_state_header(gm.current_state)}"))
            token = _load_token() or token
        except GoalError as exc:
            print(_red(f"❌ Goal state transition failed; archive aborted: {exc}"), file=sys.stderr)
            return 2
    elif GoalMachine:
        try:
            gm = GoalMachine(TOKEN_PATH)
            gm.transition(gsm.ARCHIVED, reason="archive completed")
            print(_green(f"   Goal State: {gsm.get_state_header(gm.current_state)}"))
            token = _load_token() or token
        except GoalError:
            pass

    # Step 5: tombstone — 复制 token 到 archive 目录作为墓碑
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
    handoff_src = HANDOFF_PATH if HANDOFF_PATH else Path(".omc/session-handoff.md")
    if handoff_src.exists():
        shutil.copy2(handoff_src, archive_dir / "session-handoff.md")

    # Step 5a: 将 task 目录整体 mv 到 archive（统一存储策略）
    if TASK_DIR and TASK_DIR.exists():
        # 如果 TASK_DIR 已是 symlink，shutil.move 会移走真实目标导致 dangling symlink
        if TASK_DIR.is_symlink():
            print(_yellow("⚠  TASK_DIR 是 symlink，跳过 archive mv 避免 dangling"))
        else:
            _dst_task = archive_dir / TASK_DIR.name
            if not _dst_task.exists():
                try:
                    shutil.move(str(TASK_DIR), str(_dst_task))
                    TASK_DIR.parent.mkdir(parents=True, exist_ok=True)
                    # 创建 symlink 从 TASK_DIR 指向 archive，存根保兼容
                    TASK_DIR.symlink_to(_dst_task, target_is_directory=True)
                    print(_green(f"✅ Task dir moved: {TASK_DIR} → {_dst_task}"))
                except Exception as e:
                    print(_yellow(f"⚠  Task dir mv failed: {e}"))
            else:
                print(_yellow("⚠  Archive target exists, skipping task dir mv"))

    _write_audit("archive", {"task_id": token["session"]["id"], "result": "ARCHIVED"})
    _write_handoff(token)

    # Step 6: terminal finalizer — retain the archived token and remove only its sidecar
    try:
        finalize_token(TOKEN_PATH, status="archived", reason="archive completed")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(_red(f"❌ Token terminal finalization failed: {exc}"), file=sys.stderr)
        return 2
    print(_green(f"✅ Token 保留为 archived，锁已删除: {TOKEN_PATH}"))

    # Step X: 清除信任破裂标记（archive = 人工确认任务结束）
    trust_breach = PROJECT_ROOT / ".omc" / "state" / "trust-breach.json"
    if trust_breach.exists():
        try:
            trust_breach.unlink()
            print(_green("✅ trust_breach 标记已清除"))
        except OSError:
            print(_yellow("⚠  trust_breach 清除失败"))

    # Step 7: 输出 {"continue": false}
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
        python3 .claude/scripts/carros_base.py gate --action-type write_file --paths README.md --step S1 --intent "update docs"
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
        _init_paths_from_token(token, tp)

    token = _load_token()
    if not token:
        print(_red("❌ Active token unreadable"))
        return 2

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

    if not _require_goal_execution_state(token, "dispatch"):
        return 2

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
    total_cancelled = 0
    for sd in sub_dirs:
        name = sd.name
        result_path = sd / "result.json"
        token_path = sd / "token.json"

        if not result_path.exists():
            print(f"   ○ {name}: no result yet")
            continue

        try:
            result = json.loads(result_path.read_text())
            if not isinstance(result, dict) or not result.get("status"):
                status = "failed"
                result = {"status": status, "failure": "empty result.json status"}
            else:
                status = result.get("status", "unknown")

            if status == "completed":
                icon = _green("✔")
                total_done += 1
            elif status in ("failed", "timeout"):
                icon = _red("✘")
                total_failed += 1
            elif status == "cancelled":
                icon = _yellow("⊘")
                total_cancelled += 1
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
    print(f"   {total_done} completed, {total_failed} failed, {total_cancelled} cancelled, "
          f"{len(sub_dirs) - total_done - total_failed - total_cancelled} running/pending")

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
                        elif r.get("status") in ("failed", "timeout", "cancelled"):
                            s["status"] = r.get("status")
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
                _init_paths_from_token(tok, tp)
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
        print(_red(f"❌ {step_id} cannot be collected: terminal status={status}"))
        return 2

    main_token = _load_token()
    if main_token and not _require_goal_execution_state(
        main_token, "collect", {"EXECUTING", "VERIFYING"}
    ):
        return 2

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
            _init_paths_from_token(tok, tp)

    sub_dir = SUB_TASK_DIR / f"sub-{step_id}" if SUB_TASK_DIR else None
    if not sub_dir or not sub_dir.exists():
        print(_yellow(f"⚠  No sub task: sub-{step_id}"))
        return 0

    result_path = sub_dir / "result.json"
    if result_path.exists() and update_result_locked is not None:
        def mark_cancelled(current: dict) -> dict | None:
            if current.get("status") in TERMINAL_STATUSES:
                return None
            current["status"] = "cancelled"
            current["failure"] = reason
            current["completed_at"] = datetime.now(timezone.utc).isoformat()
            return current

        current, changed = update_result_locked(result_path, mark_cancelled)
        if not changed and current.get("status") != "cancelled":
            print(_red(f"❌ {step_id}: already terminal ({current.get('status', 'unknown')})"))
            return 1

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



def cmd_oracle():
    """Oracle 复核 — LLM 驱动双审

    用法:
        carros_base.py oracle review --task-id <ID> [--plan <path>] [--executor <path>] [--token <path>] [--logs <path>] [--diff <path>] [--policy security_strict|runtime_strict|fast_path|balanced]
        carros_base.py oracle health
        carros_base.py oracle status --task-id <ID>

    Legacy (旧版 oracle_engine.py):
        carros_base.py oracle <review_pack_path>
    """
    import subprocess
    argv = sys.argv[sys.argv.index("oracle") + 1:]

    # 探测新/旧模式
    if not argv:
        print(__doc__)
        return 2

def cmd_fallback():
    """Fallback Protocol — 调用 fallback_engine.py 处理能力失效降级"""
    import subprocess
    if len(sys.argv) >= 3:
        failure_type = sys.argv[2]
        risk = sys.argv[3] if len(sys.argv) >= 4 else None
        token_path = sys.argv[4] if len(sys.argv) >= 5 else str(TOKEN_PATH or ".omc/state/token.json")
        engine = _hook_dir / "fallback_engine.py"
        if not engine.exists():
            print("fallback_engine.py not found")
            return 1
        cmd = [sys.executable, str(engine), failure_type]
        if risk:
            cmd.append(risk)
        cmd.append(token_path)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(result.stdout.strip())
        return result.returncode
    print("usage: carros_base.py fallback <failure_type> [risk] [token_path]")
    return 2


def cmd_help():
    """打印帮助信息"""
    print(__doc__.strip())
    return 0


def cmd_clarify():
    """Goal 前置澄清 — 交互式探查目标/AC/边界/依赖，输出 spec.md

    用法:
        python3 .claude/scripts/carros_base.py clarify --title "任务名"
        python3 .claude/scripts/carros_base.py clarify --title "任务名" --batch < spec.json

    Goal 状态机: 自动推进到 CLARIFY 状态
    """
    import subprocess as sb
    _scripts_parent = Path(__file__).resolve().parent  # .claude/scripts/  
    argv = sys.argv[sys.argv.index("clarify") + 1:]

    title = "unnamed"
    batch = False
    output_path = None
    i = 0
    while i < len(argv):
        if argv[i] == "--title" and i + 1 < len(argv):
            title = argv[i + 1]; i += 2
        elif argv[i] == "--batch":
            batch = True; i += 1
        elif argv[i] == "--output" and i + 1 < len(argv):
            output_path = argv[i + 1]; i += 2
        else:
            i += 1

    # 确保有 active token
    if not TOKEN_PATH or not TOKEN_PATH.exists():
        tok, tp = _find_latest_token()
        if tok and tp:
            _init_paths_from_token(tok, tp)
        else:
            # 自动 init
            cmd_init(title, level="L1", steps=["S1"])
            print(_yellow("  ⚠ 已自动 init 新任务"))

    # 调用 clarify_engine.py — 直接在 .claude/scripts/ 中查找
    script = _scripts_parent / "clarify_engine.py"
    if not script.exists():
        print(_red("❌ clarify_engine.py not found (.claude/scripts/)"))
        return 2

    spec_path = output_path or (TASK_DIR / "spec.md") if TASK_DIR else ".omc/spec.md"
    cmd = [sys.executable, str(script), "--title", title]
    if batch:
        cmd.append("--batch")
    cmd.extend(["--output", str(spec_path)])

    if batch:
        result = sb.run(cmd, capture_output=True, text=True, timeout=15)
        print(result.stdout)
        if result.returncode != 0:
            print(_red(f"❌ clarify failed: {result.stderr[:200]}"))
            return 2
    else:
        result = sb.run(cmd, timeout=300)
        if result.returncode != 0:
            print(_red("❌ clarify cancelled"))
            return 2

    # 更新 Goal 状态机
    if GoalMachine:
        try:
            gm = GoalMachine(TOKEN_PATH)
            gm.transition(gsm.CLARIFY, reason=f"clarify: {title}")
            print(_green(f"   Goal State: {gsm.get_state_header(gm.current_state)}"))
        except GoalError as e:
            print(_yellow(f"  ⚠ Goal state: {e}"))

    print(_green(f"✅ Clarified: {title}"))
    print(f"   Spec: {spec_path}")
    return 0


def cmd_plan():
    """分解 spec.md → 原子任务 → plan.json

    用法:
        python3 .claude/scripts/carros_base.py plan [--spec spec.md] [--level L2] [--output plan.json]

    流程:
        1. 读 spec.md
        2. 调用 task_planner.py 分解为 plan.json
        3. 更新 Goal 状态机 → PLANNING
    """
    argv = sys.argv[sys.argv.index("plan") + 1:]
    spec_path = None
    level = "L1"
    output_path = None
    i = 0
    while i < len(argv):
        if argv[i] == "--spec" and i + 1 < len(argv):
            spec_path = argv[i + 1]; i += 2
        elif argv[i] == "--level" and i + 1 < len(argv):
            level = argv[i + 1]; i += 2
        elif argv[i] == "--output" and i + 1 < len(argv):
            output_path = argv[i + 1]; i += 2
        else:
            i += 1

    # 确保有 active token
    if not TOKEN_PATH or not TOKEN_PATH.exists():
        tok, tp = _find_latest_token()
        if tok and tp:
            _init_paths_from_token(tok, tp)
        else:
            print(_red("❌ No active task. Run 'clarify' or 'init' first."))
            return 2

    token = _load_token()
    if not token:
        print(_red("❌ Active token unreadable"))
        return 2
    if token.get("mode") == "goal" and token.get("goal", {}).get("state") != "PLANNING":
        print(
            _red(
                f"❌ plan blocked: Goal state={token.get('goal', {}).get('state') or 'UNKNOWN'}; "
                "先完成 research → phase0-done → PLANNING"
            )
        )
        return 2

    # 找 spec.md
    spec_file = Path(spec_path) if spec_path else (TASK_DIR / "spec.md")
    if not spec_file.exists():
        spec_file = OMC_TASKS / "spec.md"
    if not spec_file.exists():
        print(_red(f"❌ spec.md not found. Run 'clarify' first."))
        return 2

    if task_planner is None:
        # 直接调用 subprocess
        planner_script = _hook_dir / "task_planner.py"
        if not planner_script.exists():
            print(_red("❌ task_planner.py not available"))
            return 2

        plan_out = output_path or str(TASK_DIR / "plan.json") if TASK_DIR else ".omc/plan.json"
        cmd = [sys.executable, str(planner_script), str(spec_file),
               "--output", plan_out, "--level", level]
        result = sb.run(cmd, capture_output=True, text=True, timeout=15)
        print(result.stdout)
        if result.returncode != 0:
            return 2
        plan_path = Path(plan_out)
    else:
        parsed = task_planner.parse_spec(spec_file)
        plan = task_planner.decompose(parsed, level=level)
        plan_path = Path(output_path) if output_path else (TASK_DIR / "plan.json")
        task_planner.save_plan(plan, plan_path)
        print(f"📋 Plan: {len(plan['steps'])} steps, level={level}")
        for s in plan["steps"]:
            print(f"   [{s['type']}] {s['id']}: {s['goal'][:50]}")

    # Goal 状态机 → PLANNING
    if GoalMachine:
        try:
            gm = GoalMachine(TOKEN_PATH)
            gm.transition(gsm.PLANNING, reason=f"plan: {spec_file.name}")
            print(_green(f"   Goal State: {gsm.get_state_header(gm.current_state)}"))
        except GoalError as e:
            print(_yellow(f"  ⚠ Goal state: {e}"))

    print(_green(f"✅ Plan generated: {plan_path}"))
    return 0


def cmd_auto():
    """全自动管道: clarify → plan → distribute → wait → collect → verify → archive

    用法:
        python3 .claude/scripts/carros_base.py auto [--plan plan.json] [--timeout 300]
                                                  [--max-concurrency 3] [--no-archive]

    流程:
        1. 有 plan.json 则跳过 clarify+plan
        2. 调用 sub_agent_manager auto_run
        3. 回收后 verify + archive
    """
    argv = sys.argv[sys.argv.index("auto") + 1:]
    plan_path = None
    timeout = 300
    max_concurrency = 3
    no_archive = False
    i = 0
    while i < len(argv):
        if argv[i] == "--plan" and i + 1 < len(argv):
            plan_path = argv[i + 1]; i += 2
        elif argv[i] == "--timeout" and i + 1 < len(argv):
            timeout = int(argv[i + 1]); i += 2
        elif argv[i] == "--max-concurrency" and i + 1 < len(argv):
            max_concurrency = int(argv[i + 1]); i += 2
        elif argv[i] == "--no-archive":
            no_archive = True; i += 1
        else:
            i += 1

    # 确保有 active token
    if not TOKEN_PATH or not TOKEN_PATH.exists():
        tok, tp = _find_latest_token()
        if tok and tp:
            _init_paths_from_token(tok, tp)
        else:
            print(_red("❌ No active task. Run 'init' first."))
            return 2

    if not TASK_DIR or not TASK_DIR.exists():
        print(_red("❌ Task directory not found"))
        return 2

    token = _load_token()
    if not token:
        print(_red("❌ Active token unreadable"))
        return 2
    if not _require_goal_execution_state(token, "auto"):
        return 2

    # 确保 sub_agent_manager 可用
    if sam is None:
        print(_yellow("⚠  sub_agent_manager.py not importable, using subprocess fallback"))

    print(_bold(f"🚀 Auto pipeline: {TASK_DIR.name} (timeout={timeout}s, cc={max_concurrency})"))

    # 创建 manager
    mgr = sam.SubAgentManager(TASK_DIR, PROJECT_ROOT) if sam else None

    if mgr:
        mgr.set_config(timeout=timeout, max_concurrency=max_concurrency)

    # Step 1: 读取或准备 plan
    plan = None
    if plan_path:
        plan_file = Path(plan_path)
        if plan_file.exists():
            plan = json.loads(plan_file.read_text())
            print(f"📋 Loaded plan: {plan.get('title', '?')} ({len(plan['steps'])} steps)")
    else:
        existing = TASK_DIR / "plan.json"
        if existing.exists():
            plan = json.loads(existing.read_text())
            print(f"📋 Using existing plan: {plan.get('title', '?')} ({len(plan['steps'])} steps)")

    if not plan:
        print(_red("❌ No plan.json found. Run 'plan' first or specify --plan"))
        return 2

    # Step 2: 分发 → 等待 → 回收
    if mgr:
        result = mgr.auto_run(plan=plan, wait=True)
    else:
        # fallback: 直接 carros_base.py dispatch + poll + collect
        print(_yellow("⚠  Using carros_base.py dispatch/poll/collect fallback"))
        from subprocess import run as sbrun
        for step in plan["steps"]:
            sid = step["id"]
            r = sbrun([sys.executable, __file__, "dispatch", "--step", sid],
                      capture_output=True, text=True, timeout=10)
            print(f"   dispatch {sid}: {'ok' if r.returncode == 0 else r.stderr[:80]}")
        print("   Tasks dispatched. Run 'poll' to check status.")
        return 0

    # Step 3: only a fully completed manager result can enter Verify/Archive.
    if result.get("status") != "completed":
        print(_red(f"❌ Auto pipeline stopped: {result.get('status', 'unknown')}"))
        return 1

    verified_count = 0
    if result.get("collect_result"):
        for sid in result["collect_result"].get("collected", []):
            r = cmd_verify(step_id=sid)
            if r == 0:
                verified_count += 1

    # Step 4: 自动 archive（除非 --no-archive）
    if not no_archive and verified_count > 0:
        print(_bold("\n📦 Archiving..."))
        cmd_archive(force=False)

    # 总结
    print(_bold(f"\n{'=' * 50}"))
    print(_bold(f"🏁 Auto pipeline complete"))
    print(f"   Plan: {plan.get('title', '?')} ({len(plan['steps'])} steps)")
    print(f"   Result: {result.get('summary', '?')}")
    print(f"   Verified: {verified_count}/{len(plan['steps'])}")
    print(f"{'=' * 50}")
    return 0 if result.get("status") == "completed" else 1


# ═══════════════════════════════════════════
# CLI entrypoint
# ═══════════════════════════════════════════

# ---------------------------------------------------------------------------
# 夜跑控制面扩展（FINAL.md v3.1 §16 CarrorOS 侧）
# ---------------------------------------------------------------------------

def cmd_manifest_json():
    """读取 night-manifest.yaml → 规范化 JSON（scope-check 等门禁消费，免 yq）。

    用法:
        carros_base.py manifest-json --manifest PATH [--get dotted.path] [--pages]
        --get   输出单值（标量/JSON），缺失 → exit 2（fail-closed）
        --pages 仅输出 pages[] 的 id 列表（每行一个）
    """
    argv = sys.argv[sys.argv.index("manifest-json") + 1:]
    manifest_path = None
    get_path = None
    pages_only = False
    page_id = None
    i = 0
    while i < len(argv):
        if argv[i] == "--manifest" and i + 1 < len(argv):
            manifest_path = argv[i + 1]; i += 2
        elif argv[i] == "--get" and i + 1 < len(argv):
            get_path = argv[i + 1]; i += 2
        elif argv[i] == "--page-id" and i + 1 < len(argv):
            page_id = argv[i + 1]; i += 2
        elif argv[i] == "--pages":
            pages_only = True; i += 1
        else:
            i += 1
    if not manifest_path:
        print(_red("ERROR: manifest-json 需要 --manifest PATH"), file=sys.stderr)
        return 2
    p = Path(manifest_path)
    if not p.exists():
        print(_red(f"ERROR: manifest 不存在: {p}"), file=sys.stderr)
        return 2
    try:
        import yaml
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(_red(f"ERROR: manifest 解析失败（fail-closed）: {e}"), file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print(_red("ERROR: manifest 顶层不是 mapping"), file=sys.stderr)
        return 2
    if pages_only:
        pages = data.get("pages") or []
        for pg in pages:
            print(pg.get("id", ""))
        return 0
    if page_id:
        pages = data.get("pages") or []
        match = [pg for pg in pages if isinstance(pg, dict) and pg.get("id") == page_id]
        if not match:
            print(_red(f"ERROR: page 不存在: {page_id}"), file=sys.stderr)
            return 2
        data = match[0]
    if get_path:
        cur = data
        for part in get_path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                cur = cur[int(part)]
            else:
                print(_red(f"ERROR: 字段缺失: {get_path}"), file=sys.stderr)
                return 2
        if isinstance(cur, (dict, list)):
            print(json.dumps(cur, ensure_ascii=False))
        elif cur is None:
            print("null")
        elif isinstance(cur, bool):
            print("true" if cur else "false")
        else:
            print(cur)
        return 0
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def cmd_token_write():
    """token.json 唯一合法写入入口（FINAL §4.4：模型对 token 的写入仅允许经此 API）。

    用法:
        carros_base.py token-write --token-path PATH --set dotted.path=value
              [--set ...] --expected-revision N
    CAS 冲突 → exit 3；缺参数 → exit 2。
    """
    argv = sys.argv[sys.argv.index("token-write") + 1:]
    token_path = None
    sets = []
    expected = None
    i = 0
    while i < len(argv):
        if argv[i] == "--token-path" and i + 1 < len(argv):
            token_path = argv[i + 1]; i += 2
        elif argv[i] == "--set" and i + 1 < len(argv):
            sets.append(argv[i + 1]); i += 2
        elif argv[i] == "--expected-revision" and i + 1 < len(argv):
            expected = int(argv[i + 1]); i += 2
        else:
            i += 1
    if not token_path or not sets or expected is None:
        print(_red("ERROR: token-write 需要 --token-path/--set/--expected-revision"), file=sys.stderr)
        return 2
    token = _load_token(Path(token_path))
    if token is None:
        print(_red(f"ERROR: token 不存在或损坏: {token_path}"), file=sys.stderr)
        return 2
    for kv in sets:
        if "=" not in kv:
            print(_red(f"ERROR: --set 格式应为 path=value: {kv}"), file=sys.stderr)
            return 2
        dotted, raw = kv.split("=", 1)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        cur = token
        parts = dotted.split(".")
        for part in parts[:-1]:
            nxt = cur.get(part)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[part] = nxt
            cur = nxt
        cur[parts[-1]] = value
    try:
        _save_token(token, Path(token_path), expected_revision=expected)
    except CASConflict as e:
        print(_red(f"CAS_CONFLICT: {e}"), file=sys.stderr)
        return 3
    print(_green(f"token 已写入 revision={token.get('revision')}"))
    return 0


def cmd_gate_results_init():
    """创建页级 gate-results 目录（FINAL §4.4 权威链事实目录）。

    用法:
        carros_base.py gate-results-init --night-dir .omc/night/{date} --page-id FE-xxx
    幂等；输出目录路径。
    """
    argv = sys.argv[sys.argv.index("gate-results-init") + 1:]
    night_dir = None
    page_id = None
    i = 0
    while i < len(argv):
        if argv[i] == "--night-dir" and i + 1 < len(argv):
            night_dir = argv[i + 1]; i += 2
        elif argv[i] == "--page-id" and i + 1 < len(argv):
            page_id = argv[i + 1]; i += 2
        else:
            i += 1
    if not night_dir or not page_id:
        print(_red("ERROR: gate-results-init 需要 --night-dir/--page-id"), file=sys.stderr)
        return 2
    d = Path(night_dir) / "gate-results" / page_id
    d.mkdir(parents=True, exist_ok=True)
    print(d)
    return 0


COMMANDS = {
    "init": cmd_init,
    "resume": cmd_resume,
    "status": cmd_status,
    "tick": cmd_tick,
    "verify": cmd_verify,
    "archive": cmd_archive,
    "clarify": cmd_clarify,
    "plan": cmd_plan,
    "auto": cmd_auto,
    "lint": cmd_lint,
    "bench": cmd_bench,
    "gate": cmd_gate,
    "dispatch": cmd_dispatch,
    "poll": cmd_poll,
    "collect": cmd_collect,
    "report": cmd_report,
    "cancel": cmd_cancel,
    "oracle": cmd_oracle,
    "fallback": cmd_fallback,
    "manifest-json": cmd_manifest_json,
    "token-write": cmd_token_write,
    "gate-results-init": cmd_gate_results_init,
    "migrate": cmd_migrate,
    "resolve-conflict": cmd_resolve_conflict,
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
        level = "L1"
        steps = None
        task_dir = None
        user_request = None
        feature = None
        auto_mode = False
        mode = None
        target = None
        task_mode = None
        force = False
        i = 0
        while i < len(args):
            if args[i] == "--force":
                force = True
                i += 1
            elif args[i] == "--task-id" and i + 1 < len(args):
                task_id = args[i + 1]
                i += 2
            elif args[i] == "--level" and i + 1 < len(args):
                level = args[i + 1]
                i += 2
            elif args[i] == "--mode" and i + 1 < len(args):
                mode = args[i + 1].lower()
                if mode in ("l1", "l2"):
                    os.environ["CARROROS_GATE_MODE"] = mode
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
            elif args[i] == "--steps" and i + 1 < len(args):
                # 支持 --steps "S1:xxx|S2:yyy" 管道符分割
                if steps is None:
                    steps = []
                raw = args[i + 1]
                for part in raw.split("|"):
                    part = part.strip()
                    if part:
                        steps.append(part)
                i += 2
            elif args[i] == "--user-request" and i + 1 < len(args):
                user_request = args[i + 1]
                i += 2
            elif args[i] == "--feature" and i + 1 < len(args):
                feature = args[i + 1]
                i += 2
            elif args[i] == "--auto":
                auto_mode = True
                i += 1
            elif args[i] == "--target" and i + 1 < len(args):
                target = args[i + 1]
                i += 2
            elif args[i] == "--task-mode" and i + 1 < len(args):
                task_mode = args[i + 1].lower()
                i += 2
            else:
                i += 1
        if any(arg in ("-h", "--help") for arg in args):
            return cmd_help()
        if auto_mode:
            return cmd_auto_init(steps=steps, target=target)
        if not task_id:
            print(_red("❌ init 需要 --task-id；自动任务请使用 --auto"), file=sys.stderr)
            return 2
        return cmd_init(task_id=task_id, level=level, steps=steps, user_request=user_request, task_dir=task_dir, feature=feature, task_mode=task_mode, force=force)

    elif command == "resume":
        task_doc = args[0] if args else None
        auto_continue = "--continue" in args
        return cmd_resume(task_doc=task_doc, auto_continue=auto_continue)

    elif command == "tick":
        step_id = None
        if args and args[0] == "--step" and len(args) >= 2:
            step_id = args[1]
        return cmd_tick(step_id=step_id)

    elif command == "verify":
        step_id = None
        all_steps = "--all" in args
        if args and args[0] == "--step" and len(args) >= 2:
            step_id = args[1]
        return cmd_verify(step_id=step_id, all_steps=all_steps)

    elif command == "archive":
        force = "--force" in args or "-f" in args
        return cmd_archive(force=force)

    elif command == "lint":
        path = args[0] if args else None
        return cmd_lint(path=path)

    elif command == "manifest-json":
        return cmd_manifest_json()

    elif command == "token-write":
        return cmd_token_write()

    elif command == "gate-results-init":
        return cmd_gate_results_init()

    else:
        return COMMANDS[command]()


if __name__ == "__main__":
    sys.exit(main())
