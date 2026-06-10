#!/usr/bin/env python3
"""
task-workspace.py — 日常复杂任务持久化工作区（哲学 #7 物化）
Cross-platform Python resolution (DG-105)

用法: task-workspace.py init "任务标题"
      task-workspace.py progress "进度描述"
      task-workspace.py decision "决策描述"
      task-workspace.py done "完成摘要"
      task-workspace.py list
      task-workspace.py resume <workspace-id>

对标 RPE 四文件闭环，但更轻量：
  .omc/state/tasks/{datetime-id}-{slug}/
    progress.md   — 当前进度、卡点、决策记录
    prd.md        — 需求/方案描述
    executor.md   — 执行步骤和状态

哲学追溯:
  #7(文档优先): 全流程持久化，调研→方案→执行→留痕
  #5(以人为本): 人随时打开可看进度，跨会话可恢复
  #4(没验证=没做): 完成时必须有强证据
"""
import sys
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
TASKS_DIR = STATE_DIR / "tasks"
TASKS_DIR.mkdir(parents=True, exist_ok=True)


def slugify(raw):
    """Portable slugify: Python for proper Unicode (BSD sed doesn't handle \u4e00-\u9fff)"""
    s = raw.lower()
    s = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', '-', s)
    s = s.strip('-')
    if not s:
        s = 'task'
    return s


def get_datetime_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_ts():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def init_task(title):
    if not title:
        title = "未命名任务"
    ts = get_ts()
    slug = slugify(title)
    ws_id = f"{ts}-{slug}"
    ws_dir = TASKS_DIR / ws_id

    if ws_dir.exists():
        print(f"⚠️  工作区已存在: {ws_dir}")
        print(ws_id)
        return 1

    ws_dir.mkdir(parents=True)

    now = get_datetime_str()

    # prd.md
    prd = f"""# {title}

> 创建时间: {now}
> 工作区 ID: {ws_id}
> 状态: 🟢 进行中

## 需求/方案描述

{title}

## 边界

- 范围:
- 明确不在范围内:

## 验收条件

- [ ] AC1:
- [ ] AC2:

## 风险点

-
"""
    (ws_dir / "prd.md").write_text(prd, encoding="utf-8")

    # executor.md
    executor = f"""# Executor — 执行步骤

> 工作区: {ws_id}
> 当前 Step: 0
> 状态: 🟢 进行中

## 执行步骤

- [ ] Step 1:
- [ ] Step 2:

## 重试记录

(无)

## 跳过的风险

(无)

## 附带发现

(无)
"""
    (ws_dir / "executor.md").write_text(executor, encoding="utf-8")

    # progress.md
    progress = f"""# Progress — 进度日志

> 工作区: {ws_id}
> 最后更新: {now}

## {now} — 工作区创建

- 任务: {title}
- 状态: 初始化

"""
    (ws_dir / "progress.md").write_text(progress, encoding="utf-8")

    # 创建活跃工作区链接
    active_link = TASKS_DIR / ".active"
    if active_link.exists():
        active_link.unlink()
    os.symlink(str(ws_dir), str(active_link))

    print(ws_id)
    print(f"✅ 工作区已创建: {ws_dir}")
    print("")
    print("文件:")
    print("  prd.md      — 需求/方案描述")
    print("  executor.md — 执行步骤和状态")
    print("  progress.md — 进度日志")
    print("")
    print("后续命令:")
    print('  task-workspace.py progress "描述"  — 记录进度')
    print('  task-workspace.py decision "描述"  — 记录决策')
    print('  task-workspace.py done "摘要"      — 标记完成')


def progress(msg):
    if not msg:
        msg = "进度更新"
    active_link = TASKS_DIR / ".active"
    if not active_link.exists() or not active_link.is_symlink():
        print('❌ 无活跃工作区。先用 task-workspace.py init "标题" 创建。')
        return 1
    ws_dir = Path(os.readlink(str(active_link)))
    if not ws_dir.is_absolute():
        ws_dir = TASKS_DIR / ws_dir
    if not ws_dir.exists():
        print('❌ 无活跃工作区。先用 task-workspace.py init "标题" 创建。')
        return 1

    now = get_datetime_str()
    prog_file = ws_dir / "progress.md"
    with prog_file.open("a", encoding="utf-8") as f:
        f.write(f"\n## {now} — 进度更新\n\n")
        f.write(f"- {msg}\n")
    print("✅ 进度已记录")


def decision(msg):
    if not msg:
        msg = "决策记录"
    active_link = TASKS_DIR / ".active"
    if not active_link.exists() or not active_link.is_symlink():
        print("❌ 无活跃工作区。")
        return 1
    ws_dir = Path(os.readlink(str(active_link)))
    if not ws_dir.is_absolute():
        ws_dir = TASKS_DIR / ws_dir
    if not ws_dir.exists():
        print("❌ 无活跃工作区。")
        return 1

    now = get_datetime_str()
    prog_file = ws_dir / "progress.md"
    with prog_file.open("a", encoding="utf-8") as f:
        f.write(f"\n## {now} — 🔵 决策\n\n")
        f.write(f"- {msg}\n")
        f.write(f"- 依据: [哲学先行: 待补充]\n")
    print("✅ 决策已记录")


def complete_task(summary):
    if not summary:
        summary = "任务完成"
    active_link = TASKS_DIR / ".active"
    if not active_link.exists() or not active_link.is_symlink():
        print("❌ 无活跃工作区。")
        return 1
    ws_dir = Path(os.readlink(str(active_link)))
    if not ws_dir.is_absolute():
        ws_dir = TASKS_DIR / ws_dir
    if not ws_dir.exists():
        print("❌ 无活跃工作区。")
        return 1

    # 更新状态
    prd_file = ws_dir / "prd.md"
    if prd_file.exists():
        content = prd_file.read_text(encoding="utf-8")
        content = content.replace("🟢 进行中", "✅ 已完成")
        prd_file.write_text(content, encoding="utf-8")

    exec_file = ws_dir / "executor.md"
    if exec_file.exists():
        content = exec_file.read_text(encoding="utf-8")
        content = content.replace("🟢 进行中", "✅ 已完成")
        exec_file.write_text(content, encoding="utf-8")

    now = get_datetime_str()
    prog_file = ws_dir / "progress.md"
    with prog_file.open("a", encoding="utf-8") as f:
        f.write(f"\n## {now} — ✅ 任务完成\n\n")
        f.write(f"- {summary}\n")

    # Remove active link
    active_link.unlink()
    print(f"✅ 工作区已标记完成: {ws_dir.name}")
    print(f"   摘要: {summary}")


def list_workspaces():
    # Check if .active link is a symlink or a directory
    active_link = TASKS_DIR / ".active"
    is_active = False
    if active_link.exists():
        try:
            if active_link.is_symlink():
                is_active = True
            else:
                # It's a regular file/dir, check if it looks like a workspace
                is_active = True
        except Exception:
            pass

    print("=== 活跃工作区 ===")
    if is_active:
        try:
            target = os.readlink(str(active_link)) if active_link.is_symlink() else str(active_link)
            active_name = Path(target).name if active_link.is_symlink() else active_link.name
            print(f"  🟢 活跃: {active_name}")
        except Exception:
            print("  (无活跃工作区)")
    else:
        print("  (无活跃工作区)")
    print("")
    print("=== 历史工作区 ===")

    workspaces = []
    for ws in TASKS_DIR.iterdir():
        ws_name = ws.name
        if ws_name == ".active":
            continue
        if ws.is_dir():
            status = "🟢"
            prd_file = ws / "prd.md"
            if prd_file.exists() and "已完成" in prd_file.read_text(encoding="utf-8"):
                status = "✅"
            workspaces.append((ws_name, status))

    for ws_name, status in sorted(workspaces, key=lambda x: x[0], reverse=True)[:15]:
        print(f"  {status} {ws_name}")


def resume(ws_id):
    if not ws_id:
        print("用法: task-workspace.py resume <workspace-id>")
        return 1
    ws_dir = TASKS_DIR / ws_id
    if not ws_dir.exists():
        # Try partial match
        matches = list(TASKS_DIR.glob(f"{ws_id}*"))
        if not matches:
            print(f"❌ 工作区不存在: {ws_id}")
            print("   可用: task-workspace.py list")
            return 1
        ws_dir = matches[0]

    # Create active link
    active_link = TASKS_DIR / ".active"
    if active_link.exists():
        active_link.unlink()
    os.symlink(str(ws_dir), str(active_link))

    print(f"✅ 已恢复工作区: {ws_dir.name}")
    print("")
    prd_file = ws_dir / "prd.md"
    if prd_file.exists():
        lines = prd_file.read_text(encoding="utf-8").split("\n")
        print("--- prd.md ---")
        for line in lines[:20]:
            print(line)

    exec_file = ws_dir / "executor.md"
    if exec_file.exists():
        print("")
        print("--- executor.md (最后 3 步) ---")
        steps = re.findall(r'\[.\]\s*Step.*', exec_file.read_text(encoding="utf-8"))
        for step in steps[-5:]:
            print(step)

    prog_file = ws_dir / "progress.md"
    if prog_file.exists():
        print("")
        print("--- progress.md (最后 5 条) ---")
        entries = re.findall(r'## 20.*', prog_file.read_text(encoding="utf-8"))
        for entry in entries[-5:]:
            print(entry)


cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
if cmd == "init":
    init_task(" ".join(sys.argv[2:]))
elif cmd == "progress":
    progress(" ".join(sys.argv[2:]))
elif cmd == "decision":
    decision(" ".join(sys.argv[2:]))
elif cmd in ("done", "complete", "finish"):
    complete_task(" ".join(sys.argv[2:]))
elif cmd == "list":
    list_workspaces()
elif cmd == "resume":
    resume(sys.argv[2] if len(sys.argv) > 2 else "")
else:
    print("用法: task-workspace.py init|progress|decision|done|list|resume [参数]")
    print("")
    print('  init "标题"        创建新工作区')
    print('  progress "描述"     记录进度')
    print('  decision "描述"     记录决策')
    print('  done "摘要"         标记完成')
    print("  list                 查看所有工作区")
    print("  resume <id>          恢复工作区")
    print("")
    print("工作区位于: .omc/state/tasks/{datetime}-{slug}/")
    sys.exit(1)
