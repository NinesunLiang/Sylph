#!/usr/bin/env python3
"""
lx-plan.py — CarrorOS 任务文档体系自动创建/更新
注册: PostToolUse:TaskUpdate（checkpoint 自动创建）+ 也可 CLI 直接调用
参考: task_sys/task_fs.md（目录结构）+ templates/（模板）

用法:
  python3 lx-plan.py init <task_name> [--target <goal>] [--priority p0|p1|p2]
  python3 lx-plan.py checkpoint <task_name> <description>
  python3 lx-plan.py update-executor <task_name> <field> <value>
  python3 lx-plan.py done <task_name>
  python3 lx-plan.py latest       # 返回最新任务目录路径
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))


def _project_root() -> Path:
    """从 CWD 向上搜索项目根（含 .claude/ 的目录）"""
    cwd = Path.cwd().resolve()
    for p in [cwd] + list(cwd.parents):
        if (p / ".claude").is_dir():
            return p
    # Fallback: 绝对路径的 Desktop 项目
    desktop = Path.home() / "Desktop" / "Sylph" / "Carror_OS"
    if desktop.is_dir():
        return desktop
    # 最后回退 CWD
    return cwd


def _state_dir(root: Path) -> Path:
    return root / ".omc" / "plan"


def _task_dir(root: Path, date: str, slug: str) -> Path:
    return _state_dir(root) / date / slug


def _slugify(name: str) -> str:
    """转为 kebab-case，≤50 字符"""
    s = name.lower().strip()
    s = re.sub(r'[^a-z0-9\u4e00-\u9fff-]', '-', s)
    s = re.sub(r'-+', '-', s)
    s = s.strip('-')
    return s[:50]


def _today() -> str:
    return datetime.now(CST).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.now(CST).isoformat()


def _read_workflow_state(root: Path) -> dict | None:
    """Read workflow-state.json if exists."""
    paths = [
        root / ".claude" / "state" / "workflow-state.json",
        Path.home() / ".claude" / "state" / "workflow-state.json",
    ]
    for p in paths:
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
    return None


def _task_is_l3plus(stage: str | None, description: str | None) -> bool:
    """判断当前任务是否 >= L3（需要文档体系）"""
    # workflow stage 判断
    if stage in ("planning", "executing", "done", "blocked"):
        return True
    # 关键字启发式判断
    if description:
        keywords = ["设计", "重构", "迁移", "审计", "架构", "方案",
                     "implement", "refactor", "migrate", "design",
                     "rearchitect", "overhaul", "integrate"]
        for kw in keywords:
            if kw in description.lower():
                return True
    return False


def _best_task_name(stage: str | None, description: str | None) -> str | None:
    """从 workflow state 或描述中提取最佳任务名"""
    if description and len(description) > 3:
        return description[:80]
    return stage or "task"


# ═══════════════════════════════════════════════════════════
# 任务目录模板
# ═══════════════════════════════════════════════════════════

TEMPLATE_TASK_INPUT = """# task_input.yaml — 结构化任务输入
task_name: "{name}"
target: "{target}"
priority: "{priority}"
executor_mode: stepwise
"""

TEMPLATE_PLAN = """# Plan: {name}

## 目标
{target}

## 验收标准
- AC1: （待补充）

## 步骤
- [ ] Step 1: （待补充）

## 影响范围
- （待评估）

## 风险与降级
- （待评估）
"""

TEMPLATE_CRITERIA = """# Criteria: {name}

## 验收标准
- AC1:
  - type: behavior
  - description: （待补充）
  - how_to_check: （待补充）
  - expected: （待补充）

## 检查点
- CP1: （待补充）
"""

TEMPLATE_EXECUTOR = """# Executor: {name}
## 当前状态
- state: executing
- updated_at: {now}
## 本轮产出
- （待补充）
## 风险与回退
- （待补充）
## 下一步
- [ ] （待补充）
"""

TEMPLATE_SUMMARY = """# Summary: {name}

- **状态**: done
- **完成时间**: {now}
- **验收结论**: （待补充）
- **经验教训**: （待补充）
"""


def init_task(name: str, target: str = "", priority: str = "p1") -> str:
    """创建任务文档体系。如果目录已存在则跳过。"""
    root = _project_root()
    slug = _slugify(name)
    date = _today()
    td = _task_dir(root, date, slug)

    if td.exists():
        return f"SKIP (exists): {td}"

    # 创建目录结构
    (td / "input").mkdir(parents=True, exist_ok=True)
    (td / "output").mkdir(exist_ok=True)
    (td / "context").mkdir(exist_ok=True)

    # 写模板文件
    ctx = {"name": name, "target": target or name, "priority": priority, "now": _now_iso()}

    (td / "input" / "task_input.yaml").write_text(
        TEMPLATE_TASK_INPUT.format(**ctx), encoding="utf-8")
    (td / "output" / "plan.md").write_text(
        TEMPLATE_PLAN.format(**ctx), encoding="utf-8")
    (td / "output" / "criteria.md").write_text(
        TEMPLATE_CRITERIA.format(**ctx), encoding="utf-8")
    (td / "output" / "executor.md").write_text(
        TEMPLATE_EXECUTOR.format(**ctx), encoding="utf-8")

    # 写入 state.json
    state = {
        "task": name,
        "slug": slug,
        "stage": "planning",
        "status": "in_progress",
        "created_at": _now_iso(),
        "checkpoints": [],
    }
    (td / "state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return f"CREATED: {td}"


def checkpoint(name: str, description: str) -> str:
    """记录 checkpoint — 更新 state.json + 追加 executor.md"""
    root = _project_root()
    slug = _slugify(name)
    date = _today()
    task_state = _task_dir(root, date, slug) / "state.json"

    if not task_state.exists():
        # 没找到则自动创建
        init_task(name, description[:80])
        # 重新建后给一条初始 checkpoint
        return checkpoint(name, description)

    try:
        state = json.loads(task_state.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "ERROR: cannot read state.json"

    # 检测 [CHECKPOINT: xxx]
    m = re.search(r'\[CHECKPOINT:\s*([^\]]+)\]', description)
    cp_name = m.group(1).strip() if m else description[:60]

    now_iso = _now_iso()
    checkpoints = state.setdefault("checkpoints", [])
    found = [c for c in checkpoints if c.get("name") == cp_name]
    if found:
        found[0]["updated_at"] = now_iso
    else:
        checkpoints.append({"name": cp_name, "status": "completed", "completed_at": now_iso})

    state["stage"] = "executing"
    state["updated_at"] = now_iso
    task_state.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # 追加到 executor.md
    executor_file = _task_dir(root, date, slug) / "output" / "executor.md"
    append = f"\n### {now_iso[:19]} — {cp_name}\n- 产出: {description[:200]}\n"
    with open(executor_file, "a", encoding="utf-8") as f:
        f.write(append)

    return f"CHECKPOINT: {cp_name}"


def update_executor(name: str, field: str, value: str) -> str:
    """更新 executor.md 中的某个字段"""
    root = _project_root()
    slug = _slugify(name)
    date = _today()
    executor_file = _task_dir(root, date, slug) / "output" / "executor.md"
    if not executor_file.exists():
        return "ERROR: executor.md not found"

    now_iso = _now_iso()
    append = f"\n### {now_iso[:19]} — update {field}\n- {value}\n"
    with open(executor_file, "a", encoding="utf-8") as f:
        f.write(append)

    # 同时更新 state.json
    task_state = _task_dir(root, date, slug) / "state.json"
    if task_state.exists():
        try:
            state = json.loads(task_state.read_text(encoding="utf-8"))
            state["updated_at"] = now_iso
            if field == "state":
                state["stage"] = value
            elif field == "status":
                state["status"] = value
            task_state.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            pass

    return f"UPDATED executor.{field}: {value[:80]}"


def done_task(name: str) -> str:
    """结束任务 — 写 summary.md，更新 state.json"""
    root = _project_root()
    slug = _slugify(name)
    date = _today()
    td = _task_dir(root, date, slug)

    if not td.exists():
        return "ERROR: task dir not found"

    now_iso = _now_iso()

    # 写 summary.md
    ctx = {"name": name, "now": now_iso}
    (td / "output" / "summary.md").write_text(
        TEMPLATE_SUMMARY.format(**ctx), encoding="utf-8")

    # 更新 state.json
    task_state = td / "state.json"
    if task_state.exists():
        try:
            state = json.loads(task_state.read_text(encoding="utf-8"))
            state["stage"] = "done"
            state["status"] = "completed"
            state["completed_at"] = now_iso
            task_state.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            pass

    return f"DONE: {td}"


def latest() -> str:
    """返回最新任务目录路径（给 MUST_CHECK_PATHS 用）"""
    root = _project_root()
    sd = _state_dir(root)
    if not sd.is_dir():
        return ""

    dates = sorted([d for d in sd.iterdir() if d.is_dir()], reverse=True)
    for d in dates:
        tasks = sorted([t for t in d.iterdir() if t.is_dir()], reverse=True)
        if tasks:
            task_dir = tasks[0]
            state_file = task_dir / "state.json"
            if state_file.is_file():
                try:
                    st = json.loads(state_file.read_text(encoding="utf-8"))
                    if st.get("status") != "completed":
                        # 只返回未完成的最新任务
                        return str(task_dir)
                except (json.JSONDecodeError, OSError):
                    pass
            # fallback
            return str(task_dir)
    return ""


def scan_all() -> str:
    """扫描所有任务目录，返回列表"""
    root = _project_root()
    sd = _state_dir(root)
    if not sd.is_dir():
        return "NO TASKS"

    lines = []
    dates = sorted([d for d in sd.iterdir() if d.is_dir()], reverse=True)
    for d in dates:
        tasks = sorted([t for t in d.iterdir() if t.is_dir()], reverse=True)
        for t in tasks:
            state_file = t / "state.json"
            status = "?"
            if state_file.is_file():
                try:
                    st = json.loads(state_file.read_text(encoding="utf-8"))
                    status = f"{st.get('stage','?')}/{st.get('status','?')}"
                except (json.JSONDecodeError, OSError):
                    pass
            lines.append(f"- {d.name}/{t.name} [{status}]")
    return "\n".join(lines) if lines else "NO TASKS"


# ═══════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  lx-plan.py init <name> [--target <goal>] [--priority p0-p2]")
        print("  lx-plan.py checkpoint <name> <description>")
        print("  lx-plan.py update-executor <name> <field> <value>")
        print("  lx-plan.py done <name>")
        print("  lx-plan.py latest")
        print("  lx-plan.py scan")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        if len(sys.argv) < 3:
            print("ERROR: need task name")
            sys.exit(1)
        name = sys.argv[2]
        target = ""
        priority = "p1"
        for i in range(3, len(sys.argv)):
            if sys.argv[i] == "--target" and i + 1 < len(sys.argv):
                target = sys.argv[i + 1]
            elif sys.argv[i] == "--priority" and i + 1 < len(sys.argv):
                priority = sys.argv[i + 1]
        result = init_task(name, target, priority)
        print(result)
        sys.exit(0)

    elif cmd == "checkpoint":
        if len(sys.argv) < 4:
            print("ERROR: need name and description")
            sys.exit(1)
        result = checkpoint(sys.argv[2], sys.argv[3])
        print(result)
        sys.exit(0)

    elif cmd == "update-executor":
        if len(sys.argv) < 5:
            print("ERROR: need name, field, value")
            sys.exit(1)
        result = update_executor(sys.argv[2], sys.argv[3], sys.argv[4])
        print(result)
        sys.exit(0)

    elif cmd == "done":
        if len(sys.argv) < 3:
            print("ERROR: need task name")
            sys.exit(1)
        result = done_task(sys.argv[2])
        print(result)
        sys.exit(0)

    elif cmd == "latest":
        result = latest()
        print(result)
        sys.exit(0)

    elif cmd == "scan":
        result = scan_all()
        print(result)
        sys.exit(0)

    else:
        print(f"ERROR: unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
