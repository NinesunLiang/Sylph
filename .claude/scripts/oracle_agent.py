#!/usr/bin/env python3
"""
oracle_agent.py — Oracle 独立第三方审核

环境自适应：
- 有 Claude Code/OpenCode → spawn 独立进程做第三方审核
- 无 agent → 本地 prompt 评审

Usage:
    python3 .claude/scripts/oracle_agent.py review --target <path|description> [--context <file>]
    python3 .claude/scripts/oracle_agent.py status                     # 查看活跃裁决
    python3 .claude/scripts/oracle_agent.py bypass <task_id>           # 创建 24h bypass
"""

import json, os, sys, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

ORACLE_VERDICTS_DIR = Path(".omc/state/oracle-verdicts")
BYPASS_DIR = Path(".omc/state/oracle_bypass")
BYPASS_TTL = 86400
PROJECT_ROOT = Path.cwd()

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


def _ensure_dirs():
    ORACLE_VERDICTS_DIR.mkdir(parents=True, exist_ok=True)
    BYPASS_DIR.mkdir(parents=True, exist_ok=True)


def _read_stdin():
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def _find_available_agent():
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


def _spawn_agent_review(agent_cmd, target_text):
    """用独立 agent 进程做审核"""
    review_prompt = f"{ORACLE_SYSTEM_PROMPT}\n\n请审核以下内容，输出 JSON 裁决：\n\n{target_text[:8000]}"
    cmd = [agent_cmd, "-p", review_prompt]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return None


def _local_review(target_text):
    """无 agent 时本地 prompt 评审（返回 prompt，由主 agent 执行）"""
    return f"""【Oracle 本地审核请求】

{ORACLE_SYSTEM_PROMPT}

请审核以下内容：

{target_text[:8000]}

输出格式：
```json
{{"verdict": "ACCEPT|REJECT|ADVISORY", "safety_risk": "HIGH|MEDIUM|LOW", "architecture_score": 0-10, "evidence_score": 0-10, "reason": "..."}}
```"""


def _save_verdict(target, verdict):
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    fname = ORACLE_VERDICTS_DIR / f"oracle-{ts}.json"
    with open(fname, "w") as f:
        json.dump({"target": target, "verdict": verdict, "timestamp": ts, "project": str(PROJECT_ROOT)}, f, indent=2)
    return fname


def _load_latest_verdict(hours=24):
    """获取 24h 内最新的裁决"""
    now = time.time()
    latest = None
    for f in sorted(ORACLE_VERDICTS_DIR.glob("oracle-*.json"), reverse=True):
        if now - f.stat().st_mtime < hours * 3600:
            with open(f) as fh:
                latest = json.load(fh)
            break
    return latest


def cmd_review(args):
    target = None
    context_file = None

    i = 0
    while i < len(args):
        if args[i] == "--target" and i + 1 < len(args):
            target = args[i + 1]
            i += 2
        elif args[i] == "--context" and i + 1 < len(args):
            context_file = args[i + 1]
            i += 2
        else:
            i += 1

    if not target:
        stdin_content = _read_stdin()
        if stdin_content:
            target = stdin_content

    if not target:
        print(json.dumps({"error": "No target provided. Usage: --target <path|description>"}))
        return 1

    # 收集审核内容
    target_path = Path(target)
    if target_path.exists():
        if target_path.is_file():
            target_text = target_path.read_text(errors="replace")
        else:
            target_text = f"目录: {target_path}"
    else:
        target_text = target

    if context_file:
        ctx_path = Path(context_file)
        if ctx_path.exists():
            target_text = f"[上下文]\n{ctx_path.read_text(errors='replace')[:2000]}\n\n[审核目标]\n{target_text}"

    agent = _find_available_agent()
    if agent:
        result = _spawn_agent_review(agent, target_text)
        if result:
            print(result)
            _save_verdict(target, {"mode": "agent_spawn", "result": result[:500]})
            return 0

    # fallback: 本地 prompt
    prompt = _local_review(target_text)
    print(prompt)
    verdict_file = _save_verdict(target, {"mode": "local_prompt", "status": "pending"})
    print(f"\n[Oracle] 裁决写入: {verdict_file}")
    return 0


def cmd_status(args):
    _ensure_dirs()
    verdict = _load_latest_verdict()
    if verdict:
        print(f"最新裁决 ({verdict.get('timestamp', '?')}):")
        print(json.dumps(verdict, indent=2))
    else:
        print("24h 内无活跃裁决")
    return 0


def cmd_bypass(args):
    if not args:
        print("Usage: oracle_agent.py bypass <task_id>")
        return 1
    task_id = args[0]
    _ensure_dirs()
    bypass_file = BYPASS_DIR / f"{task_id}_approved.md"
    bypass_file.write_text(f"Approved by Oracle bypass at {datetime.now(timezone.utc).isoformat()}")
    print(f"[Oracle] Bypass created for {task_id} (24h)")


def main():
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
