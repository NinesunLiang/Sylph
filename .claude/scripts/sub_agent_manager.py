#!/usr/bin/env python3
"""
sub_agent_manager.py — Main-Sub 双层架构核心编排器

职责:
1. 分发: spec.md / plan.json → 创建 sub_task/{step} 目录 + token/result/executor
2. 轮询: 每 10s 检查 sub_task 状态，超时检测 (默认 5min)
3. 重试: 失败 → retry_count < max_retries → 重置状态
4. 回收: 完成 → 证据汇入 main executor.md，标记 main token
5. 取消: 手动中止

对接 carros_base.py 的 dispatch/poll/collect/cancel 子命令。
兼容现有的 _sub_token/_result_template/dispatch/poll/collect/cancel 结构。

用法:
    python3 sub_agent_manager.py plan <plan.json> --task-dir <dir> [--max-concurrency 3]
    python3 sub_agent_manager.py check <task_dir> [--step S1]
    python3 sub_agent_manager.py poll <task_dir> [--verbose]
    python3 sub_agent_manager.py cancel <task_dir> --step S1 [--reason \"...\"]
    python3 sub_agent_manager.py auto <task_dir> [--plan plan.json] [--timeout 300]
"""

import json
import os
import subprocess as sb
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread, Event
from typing import Optional


# ─── 默认参数 ───
DEFAULT_POLL_INTERVAL = 10  # 秒
DEFAULT_TIMEOUT = 300       # 5 分钟
DEFAULT_MAX_CONCURRENCY = 3
DEFAULT_MAX_RETRIES = 3

# ─── 外部依赖 ───
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = None  # 由调用者设置或自动检测
OMC_SCRIPTS = str(SCRIPT_DIR)
if OMC_SCRIPTS not in sys.path:
    sys.path.insert(0, OMC_SCRIPTS)

try:
    import sub_agent_recovery as recovery
except ImportError:
    recovery = None


# ═══════════════════════════════════════════
# SubAgent Manager
# ═══════════════════════════════════════════


class SubAgentManager:
    """SubAgent 生命周期管理器"""

    def __init__(self, task_dir: Path, project_root: Path = None):
        self.task_dir = Path(task_dir)
        self.project_root = project_root or self._detect_project_root()
        self.sub_task_dir = self.task_dir / "sub_task"
        self.config = {
            "max_concurrency": DEFAULT_MAX_CONCURRENCY,
            "max_retries": DEFAULT_MAX_RETRIES,
            "poll_interval": DEFAULT_POLL_INTERVAL,
            "timeout": DEFAULT_TIMEOUT,
        }
        self._spawned_procs = {}
        self._spawned = set()  # 已 spawn 的 step，用于 _wait_all 去重

    def _detect_project_root(self) -> Path:
        """自动检测项目根目录"""
        # task_dir: .omc/tasks/{date}/{task}/
        # project root: task_dir/../../.. (向上4级)
        candidate = self.task_dir
        for _ in range(6):
            parent = candidate.parent
            if (parent / ".omc").exists():
                return parent
            candidate = parent
        return Path.cwd()

    def set_config(self, **kwargs):
        """更新配置"""
        for k, v in kwargs.items():
            if k in self.config:
                self.config[k] = v

    # ─── 分发 ───

    def distribute(self, plan: dict, token_path: Path = None) -> list:
        """从 plan.json 分发所有步骤到 sub_task

        Args:
            plan: decompose() 输出的 plan dict
            token_path: main token 路径（用于更新 step 状态）

        Returns:
            [(step_id, sub_dir, success)]
        """
        steps = plan.get("steps", [])
        if not steps:
            print("⚠  Empty plan — nothing to distribute")
            return []

        results = []
        for step in steps:
            step_id = step["id"]
            sub_dir = self.sub_task_dir / f"sub-{step_id}"
            sub_dir.mkdir(parents=True, exist_ok=True)

            # 创建 subagent token
            token_data = self._make_sub_token(step, plan)
            (sub_dir / "token.json").write_text(
                json.dumps(token_data, indent=2, ensure_ascii=False) + "\n"
            )

            # 创建 result.json（模板）
            result_data = self._make_result(step, plan, token_path)
            (sub_dir / "result.json").write_text(
                json.dumps(result_data, indent=2, ensure_ascii=False) + "\n"
            )

            # 创建 executor.md
            exec_path = sub_dir / "executor.md"
            if not exec_path.exists():
                exec_path.write_text(
                    f"# Executor: {plan.get('plan_id', '?')}-{step_id}\n"
                    f"## Step: {step_id}\n"
                    f"## Goal: {step['goal']}\n\n"
                    f"## Evidence\n\n---\n"
                )

            # 创建 checkpoints 目录
            (sub_dir / "checkpoints").mkdir(exist_ok=True)

            results.append((step_id, sub_dir, True))
            print(f"   ✅ {step_id}: {step['goal'][:50]}")

        # 保存 plan.json 到 task_dir
        plan_path = self.task_dir / "plan.json"
        plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
        print(f"   Plan saved: {plan_path}")

        return results

    def _make_sub_token(self, step: dict, plan: dict) -> dict:
        """生成 subagent token.json"""
        now = datetime.now(timezone.utc)
        return {
            "schema_version": "v1.0",
            "session": {
                "id": f"{plan.get('plan_id', 'plan')}-{step['id']}",
                "level": f"L1_SUB",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            },
            "parent": {
                "plan_id": plan.get("plan_id"),
                "task_dir": str(self.task_dir),
                "step_id": step["id"],
                "ac_refs": step.get("ac_refs", []),
            },
            "subtask": {
                "goal": step["goal"],
                "type": step.get("type", "code"),
                "ac_refs": step.get("ac_refs", []),
                "deps": step.get("deps", []),
                "files": step.get("files", []),
                "plan_text": json.dumps({
                    "goal": step["goal"],
                    "type": step.get("type"),
                    "files": step.get("files", []),
                    "deps": step.get("deps", []),
                }, ensure_ascii=False),
            },
            "config": {
                "max_retries": plan.get("max_retries", DEFAULT_MAX_RETRIES),
                "timeout": plan.get("timeout", DEFAULT_TIMEOUT),
            },
            "status": "active",
            "stats": {"done": 0, "total": 1, "tick": 0},
        }

    def _make_result(self, step: dict, plan: dict, token_path: Path = None) -> dict:
        """生成 result.json 模板"""
        return {
            "status": "pending",
            "step_id": step["id"],
            "summary": "",
            "evidence": [],
            "files_changed": [],
            "failure": None,
            "retry_count": 0,
            "max_retries": plan.get("max_retries", DEFAULT_MAX_RETRIES),
            "parent": {
                "task_dir": str(self.task_dir),
                "token_path": str(token_path) if token_path else "",
            },
            "started_at": None,  # executor.py 会设置真实时间
            "completed_at": None,
        }

    def get_concurrency_limit(self) -> int:
        """获取当前并发限流 — 考虑项目根资源约束"""
        return self.config["max_concurrency"]

    # ─── 轮询 ───

    def poll(self, verbose: bool = False) -> dict:
        """轮询所有 sub_task 状态

        Returns:
            {status: completed|has_failed|running, summary: str,
             steps: [{id, status, summary, files}], completed, failed, pending}
        """
        steps_info = []
        sub_dirs = sorted(self._get_sub_dirs())

        for sd in sub_dirs:
            step_info = self._check_one(sd, verbose)
            steps_info.append(step_info)

        completed = sum(1 for s in steps_info if s["status"] == "completed")
        failed = sum(1 for s in steps_info if s["status"] in ("failed", "timeout"))
        pending = len(steps_info) - completed - failed

        # 判断整体状态
        if failed > 0:
            status = "has_failed"
        elif pending == 0:
            status = "completed"
        else:
            status = "running"

        return {
            "status": status,
            "steps": steps_info,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "total": len(steps_info),
            "summary": f"{completed}/{len(steps_info)} done, {failed} failed",
        }

    def _get_sub_dirs(self) -> list:
        """获取排序后的 sub_task 目录列表"""
        if not self.sub_task_dir.exists():
            return []
        return sorted([
            d for d in self.sub_task_dir.iterdir()
            if d.is_dir() and d.name.startswith("sub-")
        ])

    def _check_one(self, sub_dir: Path, verbose: bool) -> dict:
        """检查单个 sub_task 状态"""
        name = sub_dir.name
        result_path = sub_dir / "result.json"
        token_path = sub_dir / "token.json"

        info = {
            "id": name.replace("sub-", ""),
            "dir": str(sub_dir),
            "status": "pending",
            "summary": "",
            "files_changed": [],
            "failure": None,
        }

        if result_path.exists():
            try:
                r = json.loads(result_path.read_text())
                info["status"] = r.get("status", "unknown")
                info["summary"] = r.get("summary", "")[:80] or ""
                info["files_changed"] = r.get("files_changed", [])
                info["failure"] = r.get("failure")
                # 超时检测
                if info["status"] == "running":
                    started = r.get("started_at")
                    if started:
                        elapsed = (datetime.now(timezone.utc) -
                                   datetime.fromisoformat(started)).total_seconds()
                        if elapsed > self.config["timeout"]:
                            info["status"] = "timeout"
                            info["failure"] = f"timeout after {elapsed:.0f}s"
            except (json.JSONDecodeError, OSError):
                pass

        # 如果 result.json 不存在但 token.json 存在 → pending
        if not result_path.exists() and token_path.exists():
            info["status"] = "pending"

        return info

    # ─── 重试 ───

    def retry(self, step_id: str) -> bool:
        """重置 sub_task 状态以允许重试

        操作:
        1. 读 result.json 检查 retry_count
        2. 未超上限则: 重置 status=running, 清除 failure, retry_count+1
        3. 超上限则: 标记 failed, 返回 False

        Returns:
            True if retry initiated, False if max retries exceeded
        """
        sub_dir = self.sub_task_dir / f"sub-{step_id}"
        result_path = sub_dir / "result.json"

        if not result_path.exists():
            return False

        try:
            r = json.loads(result_path.read_text())
        except (json.JSONDecodeError, OSError):
            return False

        max_retries = r.get("max_retries", self.config["max_retries"])
        current = r.get("retry_count", 0)

        if current >= max_retries:
            r["status"] = "failed"
            r["failure"] = f"max retries ({max_retries}) exceeded"
            result_path.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
            return False

        # 重置
        r["status"] = "pending"  # 设为 pending 让 _wait_all 能重新 spawn
        r["failure"] = None
        r["retry_count"] = current + 1
        r["summary"] = ""
        r["evidence"] = []
        r["files_changed"] = []
        r["started_at"] = datetime.now(timezone.utc).isoformat()
        r["completed_at"] = None

        # 清空 executor.md
        exec_path = sub_dir / "executor.md"
        exec_path.write_text(
            f"# Executor: sub-{step_id} (retry {current + 1})\n\n"
            f"## Evidence\n\n---\n"
        )

        # 从 spawned 移除，允许重新 spawn
        self._spawned.discard(step_id)

        result_path.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
        print(f"   🔄 {step_id}: retry #{current + 1}")
        return True

    def retry_failed(self) -> list:
        """批量重试所有失败的 step — 自动重试(不超过 max_retries)

        Returns: [(step_id, success)]
        """
        results = self.poll()
        retried = []

        for step in results["steps"]:
            if step["status"] in ("failed", "timeout"):
                success = self.retry(step["id"])
                retried.append((step["id"], success))
                if success:
                    # 重置主 token 对应的 status
                    self._update_main_token_step_status(step["id"], "running")

        return retried

    def _update_main_token_step_status(self, step_id: str, status: str):
        """更新主 token 中对应 step 的状态"""
        token_path = self._find_main_token()
        if not token_path:
            return
        try:
            token = json.loads(token_path.read_text())
            if "steps" in token:
                for s in token["steps"]:
                    if s["id"] == step_id:
                        s["status"] = status
                        break
            token_path.write_text(json.dumps(token, indent=2, ensure_ascii=False) + "\n")
        except (json.JSONDecodeError, OSError):
            pass

    def _find_main_token(self) -> Optional[Path]:
        """在主 token 目录查找最新的 active token"""
        tokens_dir = self.project_root / ".omc" / "tokens"
        if not tokens_dir.exists():
            return None
        for dd in sorted(tokens_dir.iterdir(), reverse=True):
            if dd.is_dir():
                for jf in sorted(dd.glob("*.json"), reverse=True):
                    try:
                        t = json.loads(jf.read_text())
                        if t.get("status") == "active":
                            return jf
                    except Exception:
                        continue
        return None

    # ─── 回收 ───

    def collect(self, step_id: str) -> dict:
        """回收单个 step 的结果到 main executor.md

        Returns:
            {success: bool, result: dict, summary: str}
        """
        sub_dir = self.sub_task_dir / f"sub-{step_id}"
        result_path = sub_dir / "result.json"

        if not result_path.exists():
            return {"success": False, "error": "result.json not found"}

        try:
            result = json.loads(result_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            return {"success": False, "error": str(e)}

        status = result.get("status", "unknown")
        if status == "failed":
            return {"success": False, "error": result.get("failure", "unknown failure")}
        if status not in ("completed", "cancelled"):
            return {"success": False, "error": f"not completed: {status}"}

        # 追加到 main executor.md
        executor_path = self.task_dir / "executor.md"
        if executor_path.exists():
            ev_lines = [
                f"\n### SubAgent {step_id} — collected at {datetime.now(timezone.utc).isoformat()}",
                f"- source: {sub_dir.name}",
            ]
            if result.get("summary"):
                ev_lines.append(f"- summary: {result['summary']}")
            for ev in result.get("evidence", [])[:5]:
                ev_lines.append(f"- evidence: {ev[:100]}")
            for fc in result.get("files_changed", [])[:10]:
                ev_lines.append(f"- file: {fc}")
            if result.get("failure"):
                ev_lines.append(f"- failure: {result['failure'][:100]}")

            with executor_path.open("a") as f:
                f.write("\n".join(ev_lines) + "\n")

        return {
            "success": True,
            "result": result,
            "summary": result.get("summary", ""),
        }

    def collect_all(self) -> dict:
        """回收所有完成的 sub_task

        Returns:
            {collected: [step_ids], failed: [step_ids], skipped: [step_ids]}
        """
        results = self.poll()
        collected = []
        failed = []
        skipped = []

        for step in results["steps"]:
            if step["status"] == "completed":
                cr = self.collect(step["id"])
                if cr["success"]:
                    collected.append(step["id"])
                else:
                    failed.append((step["id"], cr.get("error", "?")))
            else:
                skipped.append((step["id"], step["status"]))

        return {
            "collected": collected,
            "failed": failed,
            "skipped": skipped,
        }

    # ─── 取消 ───

    def cancel(self, step_id: str, reason: str = "cancelled by main agent") -> bool:
        """取消一个 sub_task

        Returns: True if cancelled
        """
        sub_dir = self.sub_task_dir / f"sub-{step_id}"
        result_path = sub_dir / "result.json"

        if not result_path.exists():
            return False

        try:
            r = json.loads(result_path.read_text())
        except (json.JSONDecodeError, OSError):
            r = {}

        r["status"] = "cancelled"
        r["failure"] = reason
        r["completed_at"] = datetime.now(timezone.utc).isoformat()
        result_path.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")

        # 更新 token
        token_path = sub_dir / "token.json"
        if token_path.exists():
            try:
                t = json.loads(token_path.read_text())
                t["status"] = "cancelled"
                token_path.write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n")
            except Exception:
                pass

        self._update_main_token_step_status(step_id, "cancelled")
        return True

    # ─── 自动编排 ───

    def auto_run(self, plan: dict = None, wait: bool = True) -> dict:
        """自动运行完整管道: distribute → wait → collect

        用法:
            manager.auto_run(plan=plan)
            # 或者如果已经分发过了:
            manager.auto_run()

        返回:
            {status, completed, failed, summary, steps_results}
        """
        # 第1步: 分发
        if plan:
            self.distribute(plan)

        sub_dirs = self._get_sub_dirs()
        if not sub_dirs:
            return {"status": "no_tasks", "completed": 0, "failed": 0, "summary": ""}

        if not wait:
            # 只分发不等待 — 调用者自己 poll
            return {"status": "distributed", "total": len(sub_dirs), "pending": len(sub_dirs)}

        # 第2步: 等待所有 sub_task 完成（带超时）
        print(f"\n⏳ Auto-run: {len(sub_dirs)} sub-tasks (timeout={self.config['timeout']}s)...")
        overall_status = self._wait_all()

        # 第3步: 回收
        print(f"\n📦 Collecting results...")
        collect_result = self.collect_all()

        # 第4步: 重试失败项
        retried = self.retry_failed()
        if retried:
            print(f"\n🔄 Retrying {len(retried)} failed tasks...")
            # 重试后再等一轮
            time.sleep(2)
            self._wait_all()
            # 再回收
            extra = self.collect_all()
            collect_result["collected"].extend(extra["collected"])
            collect_result["failed"].extend(extra["failed"])

        completed = len(collect_result["collected"])
        failed = len(collect_result["failed"])

        return {
            "status": "completed" if failed == 0 else "has_failures",
            "completed": completed,
            "failed": failed,
            "total": len(sub_dirs),
            "summary": f"{completed} completed, {failed} failed",
            "collect_result": collect_result,
        }

    def _wait_all(self) -> str:
        """阻塞等待所有 sub_task 完成（带超时和进度汇报）

        自动 spawn pending 的 sub_task 到 sub_agent_executor.py。
        """
        start = time.time()
        last_report = 0

        while True:
            elapsed = time.time() - start
            if elapsed > self.config["timeout"]:
                # 超时 — 标记剩余为 timeout
                for sd in self._get_sub_dirs():
                    self._mark_timeout(sd)
                print(f"\n⏰ Timeout after {self.config['timeout']}s")
                return "timeout"

            result = self.poll()

            # 自动 spawn pending 的 sub_task
            for step in result["steps"]:
                if step["status"] == "pending" and step["id"] not in self._spawned:
                    sub_dir = Path(step["dir"])
                    self._spawn_subagent(sub_dir, step["id"])

            done = result["completed"] + result["failed"]
            total = result["total"]

            # 进度汇报（每 30s 一次，不下于上次）
            if elapsed - last_report >= 30:
                print(f"   {done}/{total} done ({result['failed']} failed, {result['pending']} pending) ...")
                last_report = elapsed

            if done >= total:
                break

            time.sleep(self.config["poll_interval"])

        return "has_failures" if result["failed"] > 0 else "completed"

    def _spawn_subagent(self, sub_dir: Path, step_id: str):
        """在后台调用 sub_agent_executor.py 执行子任务

        用 background subprocess spawn 避免阻塞 AutoRun。
        """
        executor_script = self.project_root / ".omc" / "scripts" / "sub_agent_executor.py"
        if not executor_script.exists():
            executor_script = SCRIPT_DIR / "sub_agent_executor.py"
        if not executor_script.exists():
            print(f"   ⚠ sub_agent_executor.py not found — {step_id} skipped")
            return

        # 回收 zombie 进程
        self._reap_zombies()

        # 并发控制：如果已达并发上限，先不启动
        running = self._count_running()
        max_cc = self.config["max_concurrency"]
        if running >= max_cc:
            print(f"   ◷ {step_id}: queued (cc={running}/{max_cc})")
            return  # 不加 spawned，下次 poll 再试

        cmd = [sys.executable, str(executor_script), str(sub_dir),
               "--timeout", str(self.config["timeout"])]
        env = os.environ.copy()
        env["ANTHROPIC_BASE_URL"] = os.environ.get(
            "ANTHROPIC_BASE_URL", "http://127.0.0.1:9998"
        )

        print(f"   🚀 {step_id}: spawning subagent (claude CLI)...")
        try:
            proc = sb.Popen(
                cmd,
                stdout=sb.DEVNULL,
                stderr=sb.DEVNULL,
                env=env,
                cwd=self.project_root,
            )
            self._spawned_procs[step_id] = proc
            # 真正 spawn 成功后才加入 spawned，避免并发阻塞
            self._spawned.add(step_id)
        except Exception as e:
            print(f"   ❌ {step_id}: spawn failed: {e}")
            self._mark_failed(sub_dir, f"spawn error: {e}")

    def _reap_zombies(self):
        """回收已退出的子进程"""
        done = []
        for sid, proc in self._spawned_procs.items():
            if proc.poll() is not None:  # 已退出
                done.append(sid)
        for sid in done:
            del self._spawned_procs[sid]

    def _count_running(self) -> int:
        """统计当前 running 的 sub_task 数量"""
        count = 0
        for sd in self._get_sub_dirs():
            result_path = sd / "result.json"
            if result_path.exists():
                try:
                    r = json.loads(result_path.read_text())
                    if r.get("status") == "running":
                        count += 1
                except Exception:
                    pass
        return count

    def _mark_failed(self, sub_dir: Path, failure: str):
        """标记子任务为失败"""
        result_path = sub_dir / "result.json"
        if result_path.exists():
            try:
                r = json.loads(result_path.read_text())
                r["status"] = "failed"
                r["failure"] = failure
                r["completed_at"] = datetime.now(timezone.utc).isoformat()
                result_path.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
            except Exception:
                pass

    def _mark_timeout(self, sub_dir: Path):
        """标记 sub_task 为超时"""
        result_path = sub_dir / "result.json"
        try:
            r = json.loads(result_path.read_text())
            if r.get("status") == "running":
                r["status"] = "timeout"
                r["failure"] = "timeout"
                r["completed_at"] = datetime.now(timezone.utc).isoformat()
                result_path.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n")
        except Exception:
            pass


# ═══════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════

def _read_plan(plan_path: Path) -> dict:
    if not plan_path.exists():
        print(f"❌ Plan not found: {plan_path}", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(plan_path.read_text())
    except json.JSONDecodeError as e:
        print(f"❌ Invalid plan.json: {e}", file=sys.stderr)
        sys.exit(2)


def _get_manager(task_dir: Path, args_config: dict = None) -> SubAgentManager:
    mgr = SubAgentManager(task_dir)
    if args_config:
        mgr.set_config(**args_config)
    return mgr


def cmd_plan(args):
    """从 plan.json 分发任务"""
    plan_path = Path(args.plan)
    task_dir = Path(args.task_dir)
    plan = _read_plan(plan_path)

    mgr = _get_manager(task_dir, {"max_concurrency": args.max_concurrency})
    mgr.distribute(plan)
    return 0


def cmd_check(args):
    """检查 sub_task 状态"""
    task_dir = Path(args.task_dir)
    mgr = _get_manager(task_dir)

    if args.step:
        if recovery:
            rc = recovery.RecoveryCheckpoint(task_dir, step_id=args.step)
            status = rc.check_status()
            print(json.dumps(status, indent=2, ensure_ascii=False))
        else:
            result = mgr.poll()
            for s in result["steps"]:
                if s["id"] == args.step:
                    print(json.dumps(s, indent=2, ensure_ascii=False))
                    break
    else:
        result = mgr.poll(verbose=args.verbose)
        print(f"📊 SubAgent Status: {result['total']} tasks")
        print(f"   ✅ {result['completed']} completed")
        print(f"   ❌ {result['failed']} failed")
        print(f"   ◷ {result['pending']} pending")
        if result["failed"] > 0:
            for s in result["steps"]:
                if s["status"] in ("failed", "timeout"):
                    print(f"   ⚠ {s['id']}: {s.get('failure', '?')[:80]}")
        # 输出 JSON 状态给脚本人用
        print()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_poll(args):
    """轮询所有 sub_task 状态"""
    task_dir = Path(args.task_dir)
    mgr = _get_manager(task_dir)
    result = mgr.poll(verbose=args.verbose)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result["failed"] > 0 else 0


def cmd_retry(args):
    """重试失败的 sub_task"""
    task_dir = Path(args.task_dir)
    mgr = _get_manager(task_dir)

    if args.step:
        success = mgr.retry(args.step)
        if success:
            print(f"✅ Retry initiated for {args.step}")
            return 0
        else:
            print(f"❌ {args.step}: max retries exceeded")
            return 2
    else:
        retried = mgr.retry_failed()
        print(f"Retried {len(retried)} tasks:")
        for sid, ok in retried:
            icon = "✅" if ok else "❌"
            print(f"   {icon} {sid}")
        return 0


def cmd_collect(args):
    """回收 sub_task 结果"""
    task_dir = Path(args.task_dir)
    mgr = _get_manager(task_dir)

    if args.step:
        cr = mgr.collect(args.step)
        if cr["success"]:
            print(f"✅ {args.step}: collected")
            if cr.get("summary"):
                print(f"   {cr['summary']}")
            return 0
        else:
            print(f"❌ {args.step}: {cr.get('error', 'collect failed')}")
            return 2
    else:
        result = mgr.collect_all()
        print(f"Collected: {len(result['collected'])} step(s)")
        for sid in result["collected"]:
            print(f"   ✅ {sid}")
        for sid, err in result["failed"]:
            print(f"   ❌ {sid}: {err}")
        for sid, status in result["skipped"]:
            print(f"   ◷ {sid}: {status}")
        return 1 if result["failed"] else 0


def cmd_cancel(args):
    """取消 sub_task"""
    task_dir = Path(args.task_dir)
    mgr = _get_manager(task_dir)

    if not args.step:
        print("❌ --step is required", file=sys.stderr)
        return 2

    success = mgr.cancel(args.step, reason=args.reason or "cancelled")
    if success:
        print(f"✅ {args.step}: cancelled")
        return 0
    else:
        print(f"⚠  {args.step}: not found or already done")
        return 0


def cmd_auto(args):
    """全自动运行: 分发 → 等待 → 回收"""
    task_dir = Path(args.task_dir)
    mgr = _get_manager(task_dir, {
        "timeout": args.timeout,
        "max_concurrency": args.max_concurrency,
        "poll_interval": args.poll_interval,
    })

    plan = None
    if args.plan:
        plan = _read_plan(Path(args.plan))
        print(f"📋 Auto-run plan: {plan.get('title', '?')} ({len(plan['steps'])} steps)")
    else:
        # 尝试从 task_dir 读已有的 plan.json
        existing = task_dir / "plan.json"
        if existing.exists():
            plan = _read_plan(existing)
            print(f"📋 Auto-run existing plan: {plan.get('title', '?')} ({len(plan['steps'])} steps)")

    if not plan:
        print("⚠  No plan provided and no existing plan.json found — scanning sub_task/ for existing tasks")
        result = mgr.auto_run(wait=True)
    else:
        result = mgr.auto_run(plan=plan, wait=True)

    print(f"\n{'=' * 50}")
    print(f"🏁 Auto-run complete")
    print(f"   Status: {result['status']}")
    print(f"   {result['summary']}")
    print(f"{'=' * 50}")
    return 0 if result["failed"] == 0 else 1


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="SubAgent Manager — Main-Sub 双层架构编排器"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="从 plan.json 分发任务")
    p_plan.add_argument("plan", help="plan.json 路径")
    p_plan.add_argument("--task-dir", required=True, help="task 目录")
    p_plan.add_argument("--max-concurrency", type=int, default=DEFAULT_MAX_CONCURRENCY)

    p_check = sub.add_parser("check", help="检查状态")
    p_check.add_argument("task_dir", help="task 目录")
    p_check.add_argument("--step", help="指定 step")
    p_check.add_argument("--verbose", action="store_true")

    p_poll = sub.add_parser("poll", help="轮询状态")
    p_poll.add_argument("task_dir", help="task 目录")
    p_poll.add_argument("--verbose", action="store_true")

    p_retry = sub.add_parser("retry", help="重试失败任务")
    p_retry.add_argument("task_dir", help="task 目录")
    p_retry.add_argument("--step", help="指定 step 重试")

    p_collect = sub.add_parser("collect", help="回收结果")
    p_collect.add_argument("task_dir", help="task 目录")
    p_collect.add_argument("--step", help="指定 step 回收")

    p_cancel = sub.add_parser("cancel", help="取消任务")
    p_cancel.add_argument("task_dir", help="task 目录")
    p_cancel.add_argument("--step", required=True, help="step ID")
    p_cancel.add_argument("--reason", default="cancelled by main agent")

    p_auto = sub.add_parser("auto", help="全自动运行")
    p_auto.add_argument("task_dir", help="task 目录")
    p_auto.add_argument("--plan", help="plan.json 路径（省略则用已存在的）")
    p_auto.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="超时秒数")
    p_auto.add_argument("--max-concurrency", type=int, default=DEFAULT_MAX_CONCURRENCY)
    p_auto.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL)

    args = parser.parse_args(argv)

    command_map = {
        "plan": cmd_plan,
        "check": cmd_check,
        "poll": cmd_poll,
        "retry": cmd_retry,
        "collect": cmd_collect,
        "cancel": cmd_cancel,
        "auto": cmd_auto,
    }

    handler = command_map.get(args.command)
    if handler:
        return handler(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
