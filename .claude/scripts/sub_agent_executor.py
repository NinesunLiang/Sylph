from __future__ import annotations
#!/usr/bin/env python3
"""
sub_agent_executor.py — 轻量 subagent 运行器

职责:
1. 读 sub_task/ 中的 instruction.md（main agent 写好的指令）
2. 调代理 API 执行指令
3. 写 result.json（完成状态）+ executor.md（产出）

用法:
    python3 sub_agent_executor.py <sub_task_dir> [--timeout 120]

通信契约:
    instruction.md  → main agent 写的具体指令（纯文本）
    result.json     ← subagent 汇报（status/summary）
    executor.md     ← subagent 产出

环境变量:
    ANTHROPIC_BASE_URL — 代理地址 (默认: http://127.0.0.1:9998)
    ANTHROPIC_AUTH_TOKEN — 认证 token
    ANTHROPIC_MODEL — 模型名 (默认: deepseek-chat)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from sub_agent_result import TERMINAL_STATUSES, is_loopback_url, read_result, remote_agent_authorized, update_result_locked
from goal_document_gate import GoalDocumentGateError, require_parent_write


DEFAULT_TIMEOUT = 180
DEFAULT_AGENT_URL = "http://127.0.0.1:9998"
DEFAULT_MODEL = "deepseek-chat"

SUBAGENT_SYSTEM_PROMPT = """你是一个干净的执行工具。只做一件事：按照 instruction.md 的指令执行并输出结果。

规则：
- 只输出指令要求的内容，不多做
- 不读文件、不分析架构、不写额外的内容
- 输出纯文本/markdown 格式
"""


class SubAgentExecutor:

    def __init__(self, sub_dir: Path):
        self.sub_dir = Path(sub_dir)
        self.instruction_path = self.sub_dir / "instruction.md"
        self.result_path = self.sub_dir / "result.json"
        self.executor_path = self.sub_dir / "executor.md"
        self.checkpoint_dir = self.sub_dir / "checkpoints"

        self.agent_url = os.environ.get(
            "ANTHROPIC_BASE_URL", DEFAULT_AGENT_URL
        ).rstrip("/")
        # Enforcement happens at the API call boundary (_call_api): construction
        # is allowed even for a remote-configured endpoint, but a non-loopback
        # call fails closed unless CARROROS_ALLOW_REMOTE_AGENT=1 is set.
        self.auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
        self.model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
        self.timeout = int(os.environ.get("SUBAGENT_TIMEOUT", DEFAULT_TIMEOUT))

        self.step_id = ""
        self.generation: int | None = None

    def check_resume(self) -> bool:
        """跳过已完成或已取消的 task。"""
        if not self.result_path.exists():
            return False
        result = read_result(self.result_path)
        return result.get("status") in TERMINAL_STATUSES

    def _read_instruction(self) -> str:
        """读 instruction.md，如果没有就 fallback 读 token.json 的 goal"""
        if self.instruction_path.exists():
            return self.instruction_path.read_text(encoding="utf-8")

        # fallback: 从 token.json 提取 goal
        token_path = self.sub_dir / "token.json"
        if token_path.exists():
            try:
                token = json.loads(token_path.read_text())
                self.step_id = token.get("parent", {}).get("step_id", "")
                goal = token.get("subtask", {}).get("goal", "")
                if goal:
                    return f"执行以下任务：\n{goal}"
            except Exception:
                pass
        return ""

    def _call_api(self, instruction: str) -> str:
        """调代理 API — curl 子进程"""
        import subprocess

        api_url = self.agent_url + "/v1/messages"

        # 端点 fail-closed：仅 loopback 默认可用，远程 endpoint 需显式
        # CARROROS_ALLOW_REMOTE_AGENT=1（见 sub_agent_result.remote_agent_authorized）
        if not is_loopback_url(api_url) and not remote_agent_authorized():
            from urllib.parse import urlparse
            raise RuntimeError(
                f"non-loopback endpoint blocked (fail-closed): {urlparse(api_url).hostname}"
            )

        body = json.dumps({
            "model": self.model,
            "max_tokens": 4096,
            "messages": [
                {"role": "user", "content": SUBAGENT_SYSTEM_PROMPT + "\n\n" + instruction}
            ],
        })

        curl_cmd = [
            "curl", "-s", "-X", "POST",
            api_url,
            "-H", "Content-Type: application/json",
            "-H", "x-api-key: test",
            "--data-binary", "@-",
            "--max-time", str(self.timeout),
        ]

        result = subprocess.run(
            curl_cmd,
            input=body.encode("utf-8"),
            capture_output=True,
            timeout=self.timeout + 10,
        )

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")[:200]
            raise RuntimeError(f"curl exit {result.returncode}: {stderr}")

        resp_data = json.loads(result.stdout.decode("utf-8", errors="replace"))

        if "error" in resp_data:
            err_msg = resp_data["error"].get("message", str(resp_data["error"]))[:200]
            raise RuntimeError(f"API error: {err_msg}")

        ai_output = ""
        if "content" in resp_data:
            for block in resp_data["content"]:
                if block.get("type") == "text":
                    ai_output += block.get("text", "")
        elif "choices" in resp_data and len(resp_data["choices"]) > 0:
            choice = resp_data["choices"][0]
            if "message" in choice:
                ai_output = choice["message"].get("content", "")
            else:
                ai_output = choice.get("text", "")

        return ai_output

    def run(self) -> dict:
        if self.check_resume():
            result = read_result(self.result_path)
            current_status = result.get("status", "failed")
            if current_status == "completed":
                current_status = "skipped"
            return {
                "status": current_status,
                "summary": result.get("summary", "already terminal"),
                "evidence_count": 0,
                "files_changed": [],
                "failure": result.get("failure"),
                "elapsed": 0,
            }

        instruction = self._read_instruction()
        if not instruction:
            self._update_result("failed", failure="no instruction.md found")
            return {
                "status": "failed",
                "failure": "no instruction.md found",
                "elapsed": 0,
                "summary": "",
                "evidence_count": 0,
                "files_changed": [],
            }

        # 保存 instruction 到 _instruction_sent.txt 用于调试
        (self.sub_dir / "_instruction_sent.txt").write_text(instruction)

        current = read_result(self.result_path)
        self.generation = int(current.get("generation", 0))
        if not self._update_result(
            "running",
            expected_generation=self.generation,
            allowed_statuses={"pending"},
        ):
            current = read_result(self.result_path)
            return {
                "status": current.get("status", "failed"),
                "failure": current.get("failure", "terminal result"),
                "elapsed": 0,
                "summary": current.get("summary", ""),
                "evidence_count": 0,
                "files_changed": [],
            }

        start = time.time()
        try:
            ai_output = self._call_api(instruction)
            elapsed = time.time() - start
            if not ai_output or not ai_output.strip():
                raise RuntimeError("empty agent output")

            # 写产出到 executor.md
            if not self._write_output(ai_output):
                raise RuntimeError("stale executor output")

            short = ai_output[:500] if len(ai_output) > 500 else ai_output
            if not self._update_result(
                "completed",
                summary=short,
                full_output=ai_output,
                expected_generation=self.generation,
                allowed_statuses={"running"},
            ):
                current = read_result(self.result_path)
                return {
                    "status": current.get("status", "failed"),
                    "summary": current.get("summary", ""),
                    "output_len": len(ai_output),
                    "evidence_count": 0,
                    "files_changed": [],
                    "failure": current.get("failure"),
                    "elapsed": elapsed,
                }
            return {
                "status": "completed",
                "summary": short,
                "output_len": len(ai_output),
                "evidence_count": 1,
                "files_changed": [],
                "failure": None,
                "elapsed": elapsed,
            }

        except Exception as e:
            elapsed = time.time() - start
            err_msg = str(e)[:200]
            committed = self._update_result(
                "failed",
                failure=err_msg,
                expected_generation=self.generation,
                allowed_statuses={"running"},
            )
            if not committed:
                current = read_result(self.result_path)
                err_msg = current.get("failure", err_msg)
                result_status = current.get("status", "failed")
            else:
                result_status = "failed"
            return {
                "status": result_status,
                "failure": err_msg,
                "elapsed": elapsed,
                "summary": "",
                "evidence_count": 0,
                "files_changed": [],
            }

    def _update_result(
        self,
        status: str,
        failure: str | None = None,
        summary: str = "",
        full_output: str = "",
        expected_generation: int | None = None,
        allowed_statuses: set[str] | None = None,
    ) -> bool:
        def publish(current: dict) -> dict | None:
            current_status = current.get("status", "pending")
            current_generation = int(current.get("generation", 0))
            if expected_generation is not None and current_generation != expected_generation:
                return None
            if current_status in TERMINAL_STATUSES:
                return None
            if allowed_statuses is not None and current_status not in allowed_statuses:
                return None

            result_data = {
                **current,
                "status": status,
                "step_id": self.step_id or current.get("step_id", ""),
                "summary": summary,
                "output_len": len(full_output),
                "evidence": [],
                "files_changed": [],
                "failure": failure,
                "retry_count": current.get("retry_count", 0),
                "generation": current_generation,
                "max_retries": current.get("max_retries", 0),
                "started_at": current.get("started_at"),
                "completed_at": current.get("completed_at"),
            }
            if status == "running":
                result_data["started_at"] = datetime.now(timezone.utc).isoformat()
                result_data["completed_at"] = None
            elif status in ("completed", "failed"):
                result_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            return result_data

        _, committed = update_result_locked(self.result_path, publish)
        return committed

    def _goal_write_allowed(self) -> bool:
        """Allow Goal subagent output only after the parent plan gate."""
        project_root = Path(__file__).resolve().parents[2]
        task_dir = self.sub_dir.parent.parent
        try:
            require_parent_write(
                task_dir,
                project_root,
                "executor",
                "subagent output",
                allowed_states={"EXECUTING", "VERIFYING"},
            )
        except GoalDocumentGateError as exc:
            raise RuntimeError(str(exc)) from exc
        return True

    def _write_output(self, text: str) -> bool:
        current = read_result(self.result_path)
        if current.get("status") != "running":
            return False
        if int(current.get("generation", 0)) != self.generation:
            return False
        self._goal_write_allowed()
        marker = f"# SubAgent: {self.step_id}\n\n## 产出\n\n"
        if self.executor_path.exists():
            marker = "\n\n---\n## 产出\n\n"
        with self.executor_path.open("a") as f:
            f.write(marker)
            f.write(text)
            f.write("\n")
        return True


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="轻量 SubAgent Executor")
    parser.add_argument("sub_task_dir", help="sub_task/{step}/ 目录路径")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)

    args = parser.parse_args(argv)

    sub_dir = Path(args.sub_task_dir)
    if not sub_dir.exists():
        print(f"❌ Sub task dir not found: {sub_dir}", file=sys.stderr)
        return 2

    executor = SubAgentExecutor(sub_dir)
    if args.timeout:
        executor.timeout = args.timeout

    result = executor.run()

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in ("completed", "skipped") else 1


if __name__ == "__main__":
    sys.exit(main())
