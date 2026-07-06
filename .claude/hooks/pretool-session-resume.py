#!/usr/bin/env python3
"""
pretool-session-resume.py — compact 后任务恢复

CC hook: PostToolExecution 或 UserPromptSubmit
功能：检测 session-handoff.md 中是否有 active 任务需要恢复。
如果有，将 token/plan/handoff 摘要注入到系统提示或代理消息中。

工作流：
1. compact 后新会话启动
2. 此 hook 在用户发送第一个消息时触发
3. 读取 handoff.md → 如果有 active 任务 → 将任务状态注入到控制输出
4. main agent 读到控制输出后，可以继续执行任务

兼容 carros_base.py 的 token 路径和 handoff 格式。
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path.cwd()
OMC_ROOT = PROJECT_ROOT / ".omc"
OMC_TOKENS = OMC_ROOT / "tokens"
OMC_TASKS = OMC_ROOT / "tasks"
OMC_STATE = OMC_ROOT / "state"

HANDOFF_PATH = Path(".claude/session-handoff.md")


def _find_latest_token():
    """与 carros_base.py 一致的 token 查找"""
    if not OMC_TOKENS.exists():
        return None
    candidates = []
    for dd in sorted(OMC_TOKENS.iterdir(), reverse=True):
        if dd.is_dir():
            for jf in dd.glob("*.json"):
                try:
                    candidates.append((jf.stat().st_mtime, jf))
                except OSError:
                    continue
    candidates.sort(key=lambda x: x[0], reverse=True)
    for _, jf in candidates:
        try:
            token = json.loads(jf.read_text())
            if token.get("status") == "active":
                return token, jf
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _read_handoff():
    """读取 handoff.md"""
    for hp in [HANDOFF_PATH, OMC_ROOT / "state" / "session-handoff.md"]:
        if hp.exists():
            try:
                return hp.read_text()
            except OSError:
                continue
    return ""


def _parse_handoff(content: str) -> dict:
    """解析 handoff.md 中的元数据字段"""
    info = {"status": "no_active_task"}
    for line in content.split("\n"):
        if line.startswith("status:"):
            info["status"] = line.split(":", 1)[1].strip()
        elif line.startswith("progress:"):
            parts = line.split(":", 1)[1].strip().split("/")
            if len(parts) == 2:
                info["done"] = int(parts[0]) if parts[0].isdigit() else 0
                info["total"] = int(parts[1]) if parts[1].isdigit() else 0
        elif line.startswith("id:"):
            info["task_id"] = line.split(":", 1)[1].strip()
        elif line.startswith("token_path:"):
            info["token_path"] = line.split(":", 1)[1].strip()
        elif line.startswith("level:"):
            info["level"] = line.split(":", 1)[1].strip()
        elif line.startswith("pending:"):
            info["pending"] = line.split(":", 1)[1].strip()
    return info


def _find_task_dir(task_id: str):
    """找任务目录"""
    if not OMC_TASKS.exists():
        return None
    for dd in sorted(OMC_TASKS.iterdir(), reverse=True):
        if not dd.is_dir():
            continue
        for td in dd.iterdir():
            if td.is_dir() and td.name == task_id:
                return td
    return None


def _get_terminal_id():
    """获取终端唯一标识，用于多终端隔离 last-user-prompts。
    优先级: tty > OPENCODE_SESSION_ID > CLAUDE_SESSION_ID > PID
    """
    try:
        tty_id = os.popen("tty 2>/dev/null").read().strip()
        if tty_id and tty_id != "not a tty":
            return tty_id.replace("/dev/", "")
    except Exception:
        pass
    oc_id = os.environ.get("OPENCODE_SESSION_ID", "")
    if oc_id:
        return "oc-" + oc_id[:8]
    cc_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if cc_id:
        return "cc-" + cc_id[:8]
    return "pid-" + str(os.getpid())


def _read_last_prompts():
    """读取当前终端的最近20条用户 query。"""
    try:
        prompts_dir = OMC_STATE / "last-user-prompts"
        term_id = _get_terminal_id()
        prompt_path = prompts_dir / term_id
        if not prompt_path.exists():
            return []
        lines = prompt_path.read_text(encoding="utf-8", errors="replace").splitlines()
        return [l.strip() for l in lines if l.strip()]
    except OSError:
        return []


def main():
    stdin_data = sys.stdin.read() if not sys.stdin.isatty() else ""
    user_msg = stdin_data.strip() if stdin_data else ""

    # 只在有用户消息时运行
    if not user_msg:
        print(json.dumps({"continue": True, "message": "Resume: no message, skip"}))
        return 0

    # 检查是否有 active 的任务需要恢复
    result = _find_latest_token()
    if not result:
        # 没有 active token — 不需要恢复
        print(json.dumps({"continue": True, "message": "Resume: no active task"}))
        return 0

    token, token_path = result
    task_id = token.get("session", {}).get("id", "unknown")
    done = token.get("stats", {}).get("done", 0)
    total = token.get("stats", {}).get("total", 0)
    pending = [s["id"] for s in token.get("steps", []) if s.get("status") == "pending"]

    # 从 token 读 task_dir，不需要猜目录
    task_dir_str = token.get("task_dir", "")
    task_dir = Path(task_dir_str) if task_dir_str else None
    handoff = _read_handoff()

    # 读取 plan.md
    plan_content = ""
    if task_dir and task_dir.exists():
        plan_path = task_dir / "plan.md"
        if plan_path.exists():
            plan_content = plan_path.read_text()[:500]  # 只取前 500 字符

    # 读取当前终端最近的用户 query
    recent_prompts = _read_last_prompts()

    # 输出恢复信息 — 通过 message 字段给 main agent
    msg_parts = [
        f"🔄 **任务恢复: {task_id}**",
        f"- 状态: {token.get('status', 'active')}",
        f"- 进度: {done}/{total} 步完成",
        f"- 未完成: {pending if pending else '无'}",
    ]
    if plan_content:
        msg_parts.append(f"- Plan:\n{plan_content}")
    if recent_prompts:
        prompts_str = "\n".join(f"  • {p}" for p in recent_prompts[-5:])  # 只展示最近5条
        msg_parts.append(f"- 最近用户询问:\n{prompts_str}")
    msg_parts.append(f"- Token: {token_path}")

    msg = "\n".join(msg_parts)

    # 通过 sys.stderr 输出给用户看，通过 continue message 给 context
    sys.stderr.write(msg + "\n")
    print(json.dumps({"continue": True, "message": msg}))

    # 也写一次 handoff（确保新会话有最新的 handoff）
    from datetime import timezone
    steps_summary = "\n".join(
        f"  {'✅' if s['status'] == 'completed' else '⬜'} {s['id']}: {s['status']}"
        for s in token.get("steps", [])
    )
    handoff_content = (
        f"# Session Handoff\n"
        f"ts: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"id: {task_id}\n"
        f"level: {token.get('session', {}).get('level', 'L1_BASE')}\n"
        f"status: {token.get('status', 'active')}\n"
        f"progress: {done}/{total}\n"
        f"token_path: {token_path}\n"
        f"pending: {','.join(pending) if pending else 'none'}\n"
        f"\n"
        f"## Steps\n"
        f"{steps_summary}\n"
    )
    HANDOFF_PATH.parent.mkdir(parents=True, exist_ok=True)
    HANDOFF_PATH.write_text(handoff_content)

    return 0


if __name__ == "__main__":
    main()
