#!/usr/bin/env python3
"""
session-resume.py — SessionStart — 跨会话恢复: 注入进行中的 goal/ghost 任务上下文

#36: 新会话启动时检测活跃自主模式，注入进度摘要 + 恢复指令
哲学 #7(文档优先): 从 RPE progress.md 重建上下文，而非依赖记忆
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import (
    hc_enabled, flywheel_event, output_continue,
    PROJECT_ROOT, STATE_DIR,
)


def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    goal_file = STATE_DIR / "tokens" / "lx-goal.json"
    ghost_file = STATE_DIR / "tokens" / "lx-ghost.json"

    resume_ctx = ""
    now = datetime.now(timezone.utc)

    # ── Goal mode recovery ──
    if goal_file.exists():
        try:
            with open(str(goal_file), encoding="utf-8") as f:
                d = json.load(f)
            goal = d.get("goal", "?")
            activated = d.get("activated_at", "?")
            expires = d.get("expires_at", "?")
            done = len(d.get("completed_tasks", []))
            skip = len(d.get("skipped_risks", []))
            hard = len(d.get("hard_boundary_hits", []))
            blocked = len(d.get("blocked_human", []))
            plan_dir = d.get("rpe_plan_dir", "")
            phase0 = d.get("phase0_passed_at", "")

            # Check expiry
            expired = False
            if expires:
                try:
                    exp = datetime.fromisoformat(expires)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    expired = now > exp
                except (ValueError, TypeError):
                    pass

            if expired:
                resume_ctx += (
                    f"\n⏰ [session-resume] 目标模式已过期 ({expires})，请运行 lx-goal off 清理。\n"
                )
            else:
                phase_label = "Phase 0 (draft)"
                if phase0:
                    phase_label = "Phase 1 (executing, 已通过 phase0-done)"

                resume_ctx += (
                    f"\n🔄 [session-resume·跨会话恢复] 目标模式活跃中 — {phase_label}\n"
                    f"\n"
                    f"   📋 目标: {goal}\n"
                    f"   📊 进度: {done} 完成 | {blocked} 推迟决策\n"
                    f"   📁 RPE: {plan_dir}\n"
                    f"\n"
                    f"   🔧 恢复指令:\n"
                    f"   1. 读取进度: cat {plan_dir}/progress.md\n"
                    f"   2. 读取计划: cat {plan_dir}/prd.md\n"
                    f"   3. 继续执行未完成任务 (使用 task-done/skip-risk/hard-boundary-hit/blocked-human)\n"
                    f"   4. 完成后: lx-goal off && lx-goal report\n"
                )

                # Append recent progress
                if plan_dir:
                    progress_file = Path(plan_dir) / "progress.md"
                    if progress_file.exists():
                        try:
                            lines = progress_file.read_text(encoding="utf-8").split("\n")
                            recent = lines[-5:] if len(lines) > 5 else lines
                            if recent:
                                recent_text = "\n".join(f"     {l}" for l in recent if l.strip())
                                resume_ctx += f"\n   📝 最近进度:\n{recent_text}\n"
                        except OSError:
                            pass
        except (json.JSONDecodeError, OSError):
            pass

    # ── Ghost mode recovery ──
    if ghost_file.exists():
        try:
            with open(str(ghost_file), encoding="utf-8") as f:
                d = json.load(f)
            direction = d.get("direction", "?")
            activated = d.get("activated_at", "?")
            expires = d.get("expires_at", "?")
            retry = d.get("retry_count", 0)
            skip = len(d.get("skipped_risks", []))
            hard = len(d.get("hard_boundary_hits", []))
            chat_dir = d.get("rpe_chat_dir", "")

            # Check expiry
            expired = False
            if expires:
                try:
                    exp = datetime.fromisoformat(expires)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    expired = now > exp
                except (ValueError, TypeError):
                    pass

            if expired:
                resume_ctx += (
                    f"\n⏰ [session-resume] 幽灵模式已过期 — 请运行 lx-ghost off 清理。\n"
                )
            else:
                resume_ctx += (
                    f"\n👻 [session-resume] 幽灵模式活跃中\n"
                    f"\n"
                    f"   🧭 方向: {direction}\n"
                    f"   🔄 轮次: {retry}\n"
                    f"   📁 Chat: {chat_dir}\n"
                    f"\n"
                    f"   🔧 恢复指令:\n"
                    f"   1. 读取探索进度: cat {chat_dir}/progress.md\n"
                    f"   2. 继续围绕方向探索\n"
                    f"   3. 记录发现: 追加到 {chat_dir}/progress.md\n"
                    f"   4. 如有风险: lx-ghost skip-risk '描述'\n"
                    f"   5. 如方向完成: lx-ghost off\n"
                )
        except (json.JSONDecodeError, OSError):
            pass

    # Output
    if resume_ctx:
        print(resume_ctx)
        flywheel_event("session_resume", "inject_active_mode", "P1")

    # Always pass through (SessionStart should not block)
    output_continue()


if __name__ == "__main__":
    main()
