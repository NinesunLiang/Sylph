#!/usr/bin/env python3
"""
sub_agent_recovery.py — compact checkpoint → resume 恢复

当 subagent 的工作因 compact/resume 中断时:
1. 读取最近的 checkpoint（token.json/result.json/executor.md）
2. 判断完成状态
3. 生成 resume 摘要供新的 main/sub agent 恢复上下文

用法:
    python3 sub_agent_recovery.py <task_dir> [--step S1] [--status]
    python3 sub_agent_recovery.py <task_dir> [--generate-resume]
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ─── 状态常量 ───
STATUS_NOT_STARTED = "not_started"
STATUS_RUNNING = "running"
STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"
STATUS_TIMEOUT = "timeout"


class RecoveryCheckpoint:
    """子代理恢复检查点 — 判断完成状态并生成恢复上下文"""

    def __init__(self, task_dir: Path, step_id: str = None):
        self.task_dir = Path(task_dir)
        self.step_id = step_id
        self.sub_dir = None

        if step_id:
            self.sub_dir = self.task_dir / "sub_task" / f"sub-{step_id}"

    def check_status(self) -> dict:
        """检查子任务完成状态

        顺序:
        1. result.json → status
        2. token.json → parent/session 信息
        3. executor.md → 证据行数
        4. compact checkpoint → plan.md 快照
        """
        if not self.sub_dir or not self.sub_dir.exists():
            return self._task_level_check()

        return self._sub_task_check()

    def _task_level_check(self) -> dict:
        """任务级检查 — 读 plan.md 看哪些 step 已完成/未完成"""
        plan_path = self.task_dir / "plan.md"
        plan_json = self.task_dir / "plan.json"
        spec_path = self.task_dir / "spec.md"
        executor_path = self.task_dir / "executor.md"

        result = {
            "status": STATUS_RUNNING,
            "type": "task",
            "completed_steps": [],
            "pending_steps": [],
            "failed_steps": [],
            "evidence_count": 0,
            "plan_summary": "",
            "spec_summary": "",
            "has_checkpoint": False,
            "last_activity": None,
        }

        # 读 plan.md 标记
        if plan_path.exists():
            plan_text = plan_path.read_text()
            completed = self._find_completed_steps(plan_text)
            pending = self._find_pending_steps(plan_text)
            result["completed_steps"] = completed
            result["pending_steps"] = pending
            result["plan_summary"] = plan_text[:200]

        # 读 plan.json (原子分解版本)
        if plan_json.exists():
            try:
                plan = json.loads(plan_json.read_text())
                result["has_checkpoint"] = True
                result["max_concurrency"] = plan.get("max_concurrency", 3)
                result["max_retries"] = plan.get("max_retries", 3)
                # 读 steps 状态
                for step in plan.get("steps", []):
                    sid = step.get("id", "?")
                    if sid in result["completed_steps"]:
                        step["_status"] = STATUS_COMPLETED
                    elif sid in result["pending_steps"]:
                        step["_status"] = STATUS_PENDING
            except (json.JSONDecodeError, OSError):
                pass

        # 读 spec.md
        if spec_path.exists():
            result["spec_summary"] = spec_path.read_text()[:300]

        # 读 executor.md 证据行数
        if executor_path.exists():
            evidence_lines = [l for l in executor_path.read_text().split("\n")
                              if l.strip() and not l.startswith("#")]
            result["evidence_count"] = len(evidence_lines)
            result["last_activity"] = datetime.fromtimestamp(
                executor_path.stat().st_mtime
            ).isoformat()

        # 判断整体状态
        total = len(result["pending_steps"]) + len(result["completed_steps"])
        if total > 0 and len(result["completed_steps"]) >= total:
            result["status"] = STATUS_COMPLETED
        elif len(result["failed_steps"]) > 0:
            result["status"] = STATUS_FAILED
        elif len(result["completed_steps"]) > 0:
            result["status"] = STATUS_RUNNING

        return result

    def _sub_task_check(self) -> dict:
        """单 step 级检查"""
        result = {
            "status": STATUS_NOT_STARTED,
            "type": "sub_task",
            "step_id": self.step_id,
            "summary": "",
            "evidence": [],
            "files_changed": [],
            "failure": None,
            "has_checkpoint": True,
            "retry_count": 0,
        }

        # token.json
        token_path = self.sub_dir / "token.json"
        if token_path.exists():
            try:
                token = json.loads(token_path.read_text())
                result["parent_id"] = token.get("parent", {}).get("task_id")
                result["subtask_plan"] = token.get("subtask", {}).get("plan", "")
                created = token.get("session", {}).get("created_at")
                if created:
                    result["started_at"] = created
            except (json.JSONDecodeError, OSError):
                pass

        # result.json — 核心状态来源
        result_path = self.sub_dir / "result.json"
        if result_path.exists():
            try:
                r = json.loads(result_path.read_text())
                result["status"] = r.get("status", STATUS_NOT_STARTED)
                result["summary"] = r.get("summary", "")
                result["evidence"] = r.get("evidence", [])
                result["files_changed"] = r.get("files_changed", [])
                result["failure"] = r.get("failure")

                # 重试计数
                if "retry_count" in r:
                    result["retry_count"] = r["retry_count"]

                # 完成时间
                completed = r.get("completed_at") or r.get("started_at")
                if completed:
                    result["last_activity"] = completed
            except (json.JSONDecodeError, OSError):
                pass

        # executor.md
        exec_path = self.sub_dir / "executor.md"
        if exec_path.exists():
            result["evidence_count"] = len([
                l for l in exec_path.read_text().split("\n")
                if l.strip() and not l.startswith("#")
            ])
            result["executor_mtime"] = datetime.fromtimestamp(
                exec_path.stat().st_mtime
            ).isoformat()

        return result

    def _find_completed_steps(self, plan_text: str) -> list:
        """从 plan.md 提取已完成的步骤"""
        return re.findall(r"^- \[x\] (\S+?):", plan_text, re.MULTILINE)

    def _find_pending_steps(self, plan_text: str) -> list:
        """从 plan.md 提取未完成的步骤"""
        return re.findall(r"^- \[ \] (\S+?):", plan_text, re.MULTILINE)

    def generate_resume(self) -> str:
        """生成 resume 摘要 — 供新的 main/sub agent 恢复上下文"""
        status = self.check_status()
        lines = [
            f"# Resume: {self.task_dir.name}",
            f"**Status:** {status['status']}",
            f"**Type:** {status['type']}",
            f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
            "",
        ]

        if status["type"] == "task":
            lines.extend([
                "## Task Status",
                f"Completed: {len(status.get('completed_steps', []))}",
                f"Pending: {len(status.get('pending_steps', []))}",
                f"Failed: {len(status.get('failed_steps', []))}",
                "",
            ])
            if status.get("completed_steps"):
                lines.append("### ✅ Completed")
                for s in status["completed_steps"]:
                    lines.append(f"- {s}")
                lines.append("")
            if status.get("pending_steps"):
                lines.append("### ◷ Pending")
                for s in status["pending_steps"]:
                    lines.append(f"- {s}")
                lines.append("")

            if status.get("plan_summary"):
                lines.extend([
                    "## Plan Snapshot",
                    "```",
                    status["plan_summary"],
                    "```",
                    "",
                ])
            if status.get("spec_summary"):
                lines.extend([
                    "## Spec Snapshot",
                    "```",
                    status["spec_summary"],
                    "```",
                    "",
                ])
        else:
            # sub_task 级
            lines.extend([
                f"## Step: {status.get('step_id', '?')}",
                f"Status: {status['status']}",
                "",
            ])
            if status.get("summary"):
                lines.append(f"Summary: {status['summary']}")
                lines.append("")
            if status.get("evidence"):
                lines.append("### Evidence")
                for ev in status["evidence"][:5]:
                    lines.append(f"- {ev[:100]}")
                lines.append("")
            if status.get("failure"):
                lines.append(f"⚠ Failure: {status['failure']}")
                lines.append("")

        lines.extend([
            "---",
            "_Generated by sub_agent_recovery.py_",
        ])
        return "\n".join(lines)

    def save_resume(self, output_path: Path = None) -> Path:
        """保存 resume 到文件"""
        if output_path is None:
            resume_dir = self.task_dir / "state"
            resume_dir.mkdir(parents=True, exist_ok=True)
            output_path = resume_dir / "resume.md"

        content = self.generate_resume()
        output_path.write_text(content)
        return output_path


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="subagent compact checkpoint → resume 恢复"
    )
    parser.add_argument("task_dir", help="task 目录 (.omc/tasks/{date}/{task}/)")
    parser.add_argument("--step", default=None, help="指定 step 恢复")
    parser.add_argument("--generate-resume", action="store_true",
                       help="生成 resume.md")
    parser.add_argument("--status", action="store_true",
                       help="仅查询状态")
    parser.add_argument("--output", "-o", default=None,
                       help="resume.md 输出路径")

    args = parser.parse_args(argv)

    task_dir = Path(args.task_dir)
    if not task_dir.exists():
        print(f"❌ Task dir not found: {task_dir}", file=sys.stderr)
        return 2

    rc = RecoveryCheckpoint(task_dir, step_id=args.step)

    if args.status:
        status = rc.check_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
        sys.stdout.flush()
        return 0

    if args.generate_resume:
        path = rc.save_resume(output_path=Path(args.output) if args.output else None)
        print(f"✅ Resume saved: {path}")
        print(rc.generate_resume())
        return 0

    # 默认: 打印状态
    status = rc.check_status()
    print(f"📋 Recovery Check: {task_dir.name}")
    print(f"   Type: {status['type']}")
    print(f"   Status: {status['status']}")

    if status["type"] == "task":
        print(f"   Completed: {len(status.get('completed_steps', []))}")
        print(f"   Pending: {len(status.get('pending_steps', []))}")
        if status.get("failed_steps"):
            print(f"   Failed: {len(status['failed_steps'])}")
        if status.get("evidence_count"):
            print(f"   Evidence: ~{status['evidence_count']} lines")
    else:
        print(f"   Step: {status.get('step_id')}")
        if status.get("summary"):
            print(f"   Summary: {status['summary'][:60]}")

    return 0


if __name__ == "__main__":
    # 确保模块可以被发现
    _script_dir = Path(__file__).resolve().parent
    if str(_script_dir) not in sys.path:
        sys.path.insert(0, str(_script_dir))
    sys.exit(main())