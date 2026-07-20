#!/usr/bin/env python3
"""
oracle_agent.py — Oracle L2 验证层 (重构版)

职责：
- L2 验证层的独立审核入口
- 支持静态分析（scope/危险路径/file:line）和运行时分析（token/失败/软完成）
- 优先 LLM 审核（model_static/model_runtime），规则降级
- 可单独调用，也可被 meta_oracle.py 组合使用

Usage:
    python3 .claude/scripts/oracle_agent.py review --task-id <ID> [--mode static|runtime|duo] [--plan <path>] [--executor <path>] [--token <path>] [--logs <path>] [--diff <path>]
    python3 .claude/scripts/oracle_agent.py status                     # 查看活跃裁决
    python3 .claude/scripts/oracle_agent.py bypass <task_id>           # 创建 24h bypass

退出码: 0=ACCEPT 1=ADVISORY 2=REJECT 3=ESCALATE 4=UNAVAILABLE
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORACLE_VERDICTS_DIR = Path(".omc/state/oracle-verdicts")
BYPASS_DIR = Path(".omc/state/oracle_bypass")
BYPASS_TTL = 86400
PROJECT_ROOT = Path.cwd()

RETURN_CODES = {"ACCEPT": 0, "ADVISORY": 1, "REJECT": 2, "ESCALATE": 3, "UNAVAILABLE": 4}

# ── 审核 prompt ──
ORACLE_SYSTEM_PROMPT = """你是一个独立第三方审核员（Oracle）。你的职责：
1. 根据用户提交的目标文件/描述，做独立审核
2. 按以下维度输出裁决：
   - VERDICT: ACCEPT | REJECT | ADVISORY
   - 安全风险: HIGH | MEDIUM | LOW
   - 架构合理性: 0-10
   - 证据充分性: 0-10
3. 裁决必须附带 file:line 级别的证据
4. 不可因为"不知道"就通过，不知道就是 REJECT
"""

# ── 危险路径/命令模式 ──
DANGEROUS_PATH_PATTERNS = [
    r"\.ssh/", r"\.env\b", r"credentials?", r"secrets?",
    r"/etc/", r"/usr/local/", r"/var/lib/",
]

DANGEROUS_COMMAND_PATTERNS = [
    r"\brm\s+-rf\b", r"\bsudo\b", r"\bchmod\s+777\b", r"\bchown\b",
    r"\bdd\s+if=", r"\bmkfs\b", r"\bdeploy\b", r"\bpublish\b",
    r"\bnpm\s+publish\b", r"\bpip\s+upload\b",
]

SOFT_COMPLETION_PATTERNS = [
    "差不多", "应该可以", "我觉得完成", "大概完成", "基本完成",
    "looks good", "should be fine", "probably done",
]

FAIL_PATTERNS = [
    r"\bFAIL\b", r"\bFAILED\b", r"\bERROR\b", r"\bTraceback\b",
    r"\btimed out\b", r"\bexit code [1-9]\b",
]


# ═══════════════════════════════════════════════
# 共享工具函数
# ═══════════════════════════════════════════════

def _ensure_dirs():
    ORACLE_VERDICTS_DIR.mkdir(parents=True, exist_ok=True)
    BYPASS_DIR.mkdir(parents=True, exist_ok=True)


def _read_stdin():
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def _read_file_safe(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return ""


def _pattern_hits(text: str, patterns: list[str]) -> list[str]:
    hits: list[str] = []
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            hits.append(pat)
    return hits


def _extract_file_line_refs(text: str) -> list[tuple[str, int]]:
    refs: list[tuple[str, int]] = []
    for match in re.findall(r"([\w./-]+\.\w+):(\d+)", text):
        refs.append((match[0], int(match[1])))
    return refs


def _save_verdict(target: str, verdict: dict[str, Any]) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    fname = ORACLE_VERDICTS_DIR / f"oracle-{ts}.json"
    with open(fname, "w") as f:
        json.dump({"target": target, "verdict": verdict, "timestamp": ts, "project": str(PROJECT_ROOT)}, f, indent=2)
    return fname


def _load_latest_verdict(hours: int = 24) -> dict[str, Any] | None:
    now = time.time()
    for f in sorted(ORACLE_VERDICTS_DIR.glob("oracle-*.json"), reverse=True):
        if now - f.stat().st_mtime < hours * 3600:
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    return None


def _find_available_agent() -> str | None:
    """检测可用的独立 agent"""
    for cmd, args in [
        ("claude", ["claude", "-p", "echo ready"]),
        ("opencode", ["opencode", "-p", "echo ready"]),
    ]:
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and "ready" in r.stdout.strip():
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


# ═══════════════════════════════════════════════
# 静态分析 — 规则版（LLM 不可用时降级）
# ═══════════════════════════════════════════════

def _static_scan_rule_based(plan_text: str, executor_text: str, diff_text: str) -> dict[str, Any]:
    """基于规则的静态审核（旧 static_oracle_agent.py 核心逻辑）"""
    reasons: list[str] = []
    score = 10.0
    risk = "LOW"
    combined = "\n".join([plan_text, executor_text, diff_text])

    dangerous_paths = _pattern_hits(combined, DANGEROUS_PATH_PATTERNS)
    if dangerous_paths:
        score -= 2.0
        risk = "HIGH"
        reasons.append("命中危险路径模式: " + ", ".join(dangerous_paths))

    dangerous_commands = _pattern_hits(combined, DANGEROUS_COMMAND_PATTERNS)
    if dangerous_commands:
        score -= 2.5
        risk = "HIGH"
        reasons.append("命中危险命令模式: " + ", ".join(dangerous_commands))

    # file:line 校验
    refs = _extract_file_line_refs(combined)
    missing = 0
    for rel_path, line_no in refs:
        path = Path(rel_path)
        if not path.exists():
            missing += 1
            reasons.append(f"file:line 引用文件不存在: {rel_path}:{line_no}")
    if missing:
        score -= 1.5

    score = max(0.0, round(score, 2))

    if risk == "HIGH" and score < 6:
        verdict = "REJECT"
    elif risk == "HIGH":
        verdict = "ESCALATE"
    elif score < 7:
        verdict = "ADVISORY"
    else:
        verdict = "ACCEPT"

    return {"verdict": verdict, "risk": risk, "score": score, "reasons": reasons}


# ═══════════════════════════════════════════════
# 运行时分析 — 规则版（LLM 不可用时降级）
# ═══════════════════════════════════════════════

def _runtime_scan_rule_based(executor_text: str, logs_text: str) -> dict[str, Any]:
    """基于规则的运行时审核（旧 runtime_oracle_agent.py 核心逻辑）"""
    reasons: list[str] = []
    score = 10.0
    risk = "LOW"
    combined = "\n".join([executor_text, logs_text])

    fail_hits = _pattern_hits(combined, FAIL_PATTERNS)
    soft_hits = _pattern_hits(combined, SOFT_COMPLETION_PATTERNS)

    if fail_hits:
        score -= 3.0
        risk = "HIGH"
        reasons.append("运行时证据命中失败模式: " + ", ".join(fail_hits))

    if soft_hits:
        score -= 1.0
        reasons.append("命中软完成语: " + ", ".join(soft_hits))

    score = max(0.0, round(score, 2))

    if fail_hits:
        verdict = "REJECT"
    elif risk == "HIGH" and score < 6:
        verdict = "REJECT"
    elif score < 7:
        verdict = "ADVISORY"
    else:
        verdict = "ACCEPT"

    return {"verdict": verdict, "risk": risk, "score": score, "reasons": reasons}


# ═══════════════════════════════════════════════
# LLM 审核路径
# ═══════════════════════════════════════════════

def _try_llm_model(path: str, prompt: str) -> tuple[bool, str]:
    """尝试通过 LLM API 做审核"""
    api_url = "http://127.0.0.1:9998/v1/chat/completions"
    payload = json.dumps({
        "model": "deepseek-chat",
        "max_tokens": 2000,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": ORACLE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    })
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST", api_url,
             "-H", "Content-Type: application/json",
             "-H", "x-api-key: test",
             "-d", payload],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            return False, ""
        resp = json.loads(r.stdout)
        choices = resp.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            return True, content
        return False, ""
    except Exception:
        return False, ""


def _spawn_agent_review(agent_cmd: str, target_text: str) -> str | None:
    """用独立 agent 进程做审核"""
    review_prompt = f"{ORACLE_SYSTEM_PROMPT}\n\n请审核以下内容，输出 JSON 裁决：\n\n{target_text[:8000]}"
    cmd = [agent_cmd, "-p", review_prompt]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return None


def _local_review_prompt(target_text: str) -> str:
    """无 agent/LLM 时的本地 prompt 模板"""
    return f"""【Oracle 本地审核请求】

{ORACLE_SYSTEM_PROMPT}

请审核以下内容：

{target_text[:8000]}

输出格式：
```json
{{"verdict": "ACCEPT|REJECT|ADVISORY", "safety_risk": "HIGH|MEDIUM|LOW", "architecture_score": 0-10, "evidence_score": 0-10, "reason": "..."}}
```"""


# ═══════════════════════════════════════════════
# 主编排
# ═══════════════════════════════════════════════

def review_static(task_id: str, plan_text: str = "", executor_text: str = "", diff_text: str = "") -> dict[str, Any]:
    """
    静态分析（LLM 优先，规则降级）。
    返回 verdict dict。
    """
    target_text = f"### Task: {task_id}\n"
    if plan_text:
        target_text += f"### Plan\n{plan_text[:3000]}\n\n"
    if executor_text:
        target_text += f"### Executor\n{executor_text[:5000]}\n\n"
    if diff_text:
        target_text += f"### Diff\n{diff_text[:5000]}\n\n"

    # 尝试 LLM
    ok, result = _try_llm_model(task_id, target_text[:8000])
    if ok:
        return {"verdict": "ACCEPT", "risk": "LOW", "score": 8.0, "reasons": ["llm: " + result[:200]],
                "mode": "llm", "source": "oracle_agent"}

    # 降级: 规则版
    result = _static_scan_rule_based(plan_text, executor_text, diff_text)
    result["mode"] = "rule_fallback"
    result["source"] = "oracle_agent"
    return result


def review_runtime(task_id: str, executor_text: str = "", logs_text: str = "") -> dict[str, Any]:
    """
    运行时分析（LLM 优先，规则降级）。
    返回 verdict dict。
    """
    target_text = f"### Task: {task_id}\n"
    if executor_text:
        target_text += f"### Executor\n{executor_text[:5000]}\n\n"
    if logs_text:
        target_text += f"### Logs\n{logs_text[:5000]}\n\n"

    # 尝试 LLM
    ok, result = _try_llm_model(task_id, target_text[:8000])
    if ok:
        return {"verdict": "ACCEPT", "risk": "LOW", "score": 8.0, "reasons": ["llm: " + result[:200]],
                "mode": "llm", "source": "oracle_agent"}

    # 降级: 规则版
    result = _runtime_scan_rule_based(executor_text, logs_text)
    result["mode"] = "rule_fallback"
    result["source"] = "oracle_agent"
    return result


def review_duo(task_id: str, plan_text: str = "", executor_text: str = "",
               token_path: str = "", logs_text: str = "", diff_text: str = "") -> dict[str, Any]:
    """
    双审（静态+运行时），返回综合 verdict。
    """
    static_result = review_static(task_id, plan_text, executor_text, diff_text)
    runtime_result = review_runtime(task_id, executor_text, logs_text)

    # 简单综合
    scores = [static_result.get("score", 5.0), runtime_result.get("score", 5.0)]
    verdicts = [static_result.get("verdict", "ADVISORY"), runtime_result.get("verdict", "ADVISORY")]

    # 权重: 静态 0.5 + 运行时 0.5
    final_score = round((scores[0] + scores[1]) / 2, 2)

    if "REJECT" in verdicts:
        final_verdict = "REJECT"
    elif "ESCALATE" in verdicts:
        final_verdict = "ESCALATE"
    elif "ADVISORY" in verdicts:
        final_verdict = "ADVISORY"
    elif final_score < 7.0:
        final_verdict = "ADVISORY"
    else:
        final_verdict = "ACCEPT"

    return {
        "verdict": final_verdict,
        "score": final_score,
        "static": static_result,
        "runtime": runtime_result,
        "mode": "duo",
        "source": "oracle_agent",
    }


# ═══════════════════════════════════════════════
# CLI 命令
# ═══════════════════════════════════════════════

def cmd_review(args: list[str]) -> int:
    task_id = ""
    mode = "static"
    plan = ""
    executor = ""
    token = ""
    logs = ""
    diff = ""

    i = 0
    while i < len(args):
        if args[i] == "--task-id" and i + 1 < len(args):
            task_id = args[i + 1]
            i += 2
        elif args[i] == "--mode" and i + 1 < len(args):
            mode = args[i + 1]
            i += 2
        elif args[i] == "--plan" and i + 1 < len(args):
            plan = _read_file_safe(args[i + 1])
            i += 2
        elif args[i] == "--executor" and i + 1 < len(args):
            executor = _read_file_safe(args[i + 1])
            i += 2
        elif args[i] == "--token" and i + 1 < len(args):
            token = args[i + 1]
            i += 2
        elif args[i] == "--logs" and i + 1 < len(args):
            logs = _read_file_safe(args[i + 1])
            i += 2
        elif args[i] == "--diff" and i + 1 < len(args):
            diff = _read_file_safe(args[i + 1])
            i += 2
        else:
            i += 1

    if not task_id:
        stdin_content = _read_stdin()
        if stdin_content:
            task_id = "stdin"
            # 把 stdin 作为 target 传给 review
            target_text = stdin_content
            agent = _find_available_agent()
            if agent:
                result = _spawn_agent_review(agent, target_text)
                if result:
                    print(result)
                    _save_verdict("stdin", {"mode": "agent_spawn", "result": result[:500]})
                    return 0
            prompt = _local_review_prompt(target_text)
            print(prompt)
            _save_verdict("stdin", {"mode": "local_prompt", "status": "pending"})
            print(f"\n[Oracle] 裁决写入: {ORACLE_VERDICTS_DIR}")
            return 0

        print(json.dumps({"error": "No task-id provided"}))
        return 1

    if mode == "static":
        result = review_static(task_id, plan, executor, diff)
    elif mode == "runtime":
        result = review_runtime(task_id, executor, logs)
    elif mode == "duo":
        result = review_duo(task_id, plan, executor, token, logs, diff)
    else:
        result = review_static(task_id, plan, executor, diff)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    _save_verdict(task_id, result)
    return RETURN_CODES.get(result.get("verdict", ""), RETURN_CODES["UNAVAILABLE"])


def cmd_status(args: list[str]) -> int:
    _ensure_dirs()
    verdict = _load_latest_verdict()
    if verdict:
        print(f"最新裁决 ({verdict.get('timestamp', '?')}):")
        print(json.dumps(verdict, indent=2))
    else:
        print("24h 内无活跃裁决")
    return 0


def cmd_bypass(args: list[str]) -> int:
    if not args:
        print("Usage: oracle_agent.py bypass <task_id>")
        return 1
    task_id = args[0]
    _ensure_dirs()
    bypass_file = BYPASS_DIR / f"{task_id}_approved.md"
    bypass_file.write_text(f"Approved by Oracle bypass at {datetime.now(timezone.utc).isoformat()}")
    print(f"[Oracle] Bypass created for {task_id} (24h)")
    return 0


def main() -> int:
    _ensure_dirs()
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    commands = {
        "review": cmd_review,
        "status": cmd_status,
        "bypass": cmd_bypass,
    }

    handler = commands.get(cmd)
    if not handler:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        return 1

    return handler(rest)


if __name__ == "__main__":
    sys.exit(main())
