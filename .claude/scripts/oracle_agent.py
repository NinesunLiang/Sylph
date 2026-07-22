#!/usr/bin/env python3
"""oracle_agent.py -- Oracle review gate for CarrorOS Base.

Static analysis (Oracle-D) + runtime verification (Oracle-V) + duo mode.
Uses DeepSeek API for LLM-based review, falls back to rule-based scan.

Usage:
    python3 oracle_agent.py review --task-id <ID> [--mode static|runtime|duo] [--plan <path>] [--executor <path>] [--token <path>] [--logs <path>] [--diff <path>]
    python3 oracle_agent.py status
    python3 oracle_agent.py bypass <task_id>

Exit codes: 0=ACCEPT 1=ADVISORY 2=REJECT 3=ESCALATE 4=UNAVAILABLE
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
from typing import Any, Optional, List, Tuple

ORACLE_VERDICTS_DIR = Path(".omc/state/oracle-verdicts")
BYPASS_DIR = Path(".omc/state/oracle_bypass")
BYPASS_TTL = 86400
PROJECT_ROOT = Path.cwd()

RETURN_CODES = {"ACCEPT": 0, "ADVISORY": 1, "REJECT": 2, "ESCALATE": 3, "UNAVAILABLE": 4}

ORACLE_SYSTEM_PROMPT = """You are an independent third-party reviewer (Oracle). Your responsibilities:
1. Review the submitted task description, plan, executor log, and code diff independently
2. Output verdict with these dimensions:
   - VERDICT: ACCEPT | REJECT | ADVISORY
   - Safety Risk: HIGH | MEDIUM | LOW
   - Architecture: 0-10
   - Evidence: 0-10
3. Verdict must include evidence citations:
   - For code changes: use file:line references
   - For documents/skills/designs: reference sections, filenames, design concepts
4. Check for autonomous/unmanned mode signal: if `.omc/state/tokens/autonomous.active` or `.omc/state/tokens/lx-goal.json` exists, the system is in autonomous/unmanned mode. In this mode:
   - HARD-GATE and structural constraints are EXPECTED and NECESSARY, not a risk
   - The autonomous execution guide (references/autonomous-execution.md) handles all blocking scenarios
   - Do NOT flag autonomous guards as MEDIUM/HIGH risk - they are by-design safety features
5. Do not pass something just because you don't know. Unknown = REJECT
6. Be specific about what needs to change for ACCEPT"""

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


def _ensure_dirs() -> None:
    ORACLE_VERDICTS_DIR.mkdir(parents=True, exist_ok=True)
    BYPASS_DIR.mkdir(parents=True, exist_ok=True)


def _read_stdin() -> str:
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def _read_file_safe(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return ""


def _is_autonomous_mode() -> bool:
    """Check if system is in autonomous/unmanned mode."""
    tokens_dir = Path(".omc/state/tokens")
    return (tokens_dir / "autonomous.active").exists() or \
           (tokens_dir / "lx-goal.json").exists()


def _pattern_hits(text: str, patterns: List[str]) -> List[str]:
    hits: List[str] = []
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            hits.append(pat)
    return hits


def _extract_file_line_refs(text: str) -> List[Tuple[str, int]]:
    refs: List[Tuple[str, int]] = []
    for match in re.findall(r"([\w./-]+\.\w+):(\d+)", text):
        refs.append((match[0], int(match[1])))
    return refs


def _save_verdict(target: str, verdict: dict) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    fname = ORACLE_VERDICTS_DIR / "oracle-{}.json".format(ts)
    with open(fname, "w") as f:
        json.dump({"target": target, "verdict": verdict, "timestamp": ts,
                    "project": str(PROJECT_ROOT)}, f, indent=2)
    return fname


def _load_latest_verdict(hours: int = 24) -> Optional[dict]:
    now = time.time()
    for f in sorted(ORACLE_VERDICTS_DIR.glob("oracle-*.json"), reverse=True):
        if now - f.stat().st_mtime < hours * 3600:
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    return None


def _find_available_agent() -> Optional[str]:
    """Check for available review agents (claude, opencode)."""
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


# ---- Rule-based static scan (fallback when LLM unavailable) ----


def _static_scan_rule_based(plan_text: str, executor_text: str,
                            diff_text: str) -> dict:
    """Fallback rule-based static review."""
    reasons: List[str] = []
    score = 10.0
    risk = "LOW"
    combined = "\n".join([plan_text, executor_text, diff_text])

    dangerous_paths = _pattern_hits(combined, DANGEROUS_PATH_PATTERNS)
    if dangerous_paths:
        score -= 2.0
        risk = "HIGH"
        reasons.append("Dangerous path patterns: " + ", ".join(dangerous_paths))

    dangerous_commands = _pattern_hits(combined, DANGEROUS_COMMAND_PATTERNS)
    if dangerous_commands:
        score -= 2.5
        risk = "HIGH"
        reasons.append("Dangerous commands: " + ", ".join(dangerous_commands))

    refs = _extract_file_line_refs(combined)
    missing = 0
    for rel_path, line_no in refs:
        p = Path(rel_path)
        if not p.exists():
            missing += 1
            reasons.append("Missing file ref: {}:{}".format(rel_path, line_no))
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

    return {"verdict": verdict, "risk": risk, "score": score,
            "reasons": reasons}


# ---- Rule-based runtime scan (fallback when LLM unavailable) ----


def _runtime_scan_rule_based(executor_text: str, logs_text: str) -> dict:
    """Fallback rule-based runtime review."""
    reasons: List[str] = []
    score = 10.0
    risk = "LOW"
    combined = "\n".join([executor_text, logs_text])

    fail_hits = _pattern_hits(combined, FAIL_PATTERNS)
    soft_hits = _pattern_hits(combined, SOFT_COMPLETION_PATTERNS)

    if fail_hits:
        score -= 3.0
        risk = "HIGH"
        reasons.append("Failure patterns found: " + ", ".join(fail_hits))

    if soft_hits:
        score -= 1.0
        reasons.append("Soft completion language: " + ", ".join(soft_hits))

    score = max(0.0, round(score, 2))

    if fail_hits:
        verdict = "REJECT"
    elif risk == "HIGH" and score < 6:
        verdict = "REJECT"
    elif score < 7:
        verdict = "ADVISORY"
    else:
        verdict = "ACCEPT"

    return {"verdict": verdict, "risk": risk, "score": score,
            "reasons": reasons}


# ---- LLM integration ----


def _get_deepseek_key() -> str:
    """Get DeepSeek API key from env or shell config."""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    for rc_path in [
        os.path.expanduser("~/.zshrc"),
        os.path.expanduser("~/.bashrc"),
        os.path.expanduser("~/.profile"),
    ]:
        if os.path.isfile(rc_path):
            with open(rc_path) as f:
                for line in f:
                    if "DEEPSEEK_API_KEY" in line and "export" in line:
                        key = line.split("=")[-1].strip().strip("\"'")
                        break
            if key:
                break
    return key


def _try_llm_model(task_id: str, prompt: str) -> Tuple[bool, str]:
    """Call DeepSeek API for review. Returns (success, text)."""
    api_key = _get_deepseek_key()
    if not api_key:
        return False, ""

    api_url = "https://api.deepseek.com/v1/chat/completions"
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
             "-H", "Authorization: Bearer " + api_key,
             "-d", payload],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            return False, ""

        resp = json.loads(r.stdout)
        choices = resp.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            if content.strip():
                return True, content
        return False, ""
    except Exception:
        return False, ""


def _parse_llm_verdict(llm_text: str) -> dict:
    """Parse LLM output text into structured verdict.

    Expected format from LLM:
      VERDICT: ACCEPT|REJECT|ADVISORY
      Safety Risk: HIGH|MEDIUM|LOW
      Architecture: 7/10
      Evidence: 8/10
    """
    text = llm_text[:3000]
    result: dict = {"verdict": "ADVISORY", "risk": "LOW", "score": 7.0}

    # Extract VERDICT
    m = re.search(r'VERDICT\s*[:\s]\s*(ACCEPT|REJECT|ADVISORY)', text, re.IGNORECASE)
    if m:
        result["verdict"] = m.group(1).upper()

    # Extract Safety Risk
    m = re.search(r'(?:Safety Risk|安全风险)\s*[:\s]\s*(HIGH|MEDIUM|LOW)', text, re.IGNORECASE)
    if m:
        result["risk"] = m.group(1).upper()

    # Extract Architecture score
    m = re.search(r'(?:Architecture|架构)[^:]*[:：]\s*(\d+(?:\.\d+)?)\s*/?\s*10', text, re.IGNORECASE)
    if m:
        result["score"] = float(m.group(1))

    # Extract Evidence score if architecture missing
    if result["score"] == 7.0:
        m = re.search(r'(?:Evidence|证据)[^:]*[:：]\s*(\d+(?:\.\d+)?)\s*/?\s*10', text, re.IGNORECASE)
        if m:
            result["score"] = float(m.group(1))

    return result


def _spawn_agent_review(agent_cmd: str, target_text: str) -> Optional[str]:
    """Spawn an independent agent process for review."""
    review_prompt = ("{}\n\nPlease review the following and output "
                     "JSON verdict:\n\n{}").format(
        ORACLE_SYSTEM_PROMPT, target_text[:8000])
    cmd = [agent_cmd, "-p", review_prompt]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return None


def _local_review_prompt(target_text: str) -> str:
    """Build a local review prompt template."""
    return ("[Oracle Local Review Request]\n\n"
            "{}\n\n"
            "Review content:\n\n"
            "{}\n\n"
            "Output format:\n"
            '{{"verdict": "ACCEPT|REJECT|ADVISORY", '
            '"safety_risk": "HIGH|MEDIUM|LOW", '
            '"architecture_score": 0-10, '
            '"evidence_score": 0-10, '
            '"reason": "..."}}').format(
        ORACLE_SYSTEM_PROMPT, target_text[:8000])


# ---- Review functions ----


def review_static(task_id: str, plan_text: str = "",
                  executor_text: str = "", diff_text: str = "") -> dict:
    """Static analysis: LLM-first, rule-based fallback."""
    target_text = "### Task: {}\n".format(task_id)
    if plan_text:
        target_text += "### Plan\n{}\n\n".format(plan_text[:3000])
    if executor_text:
        target_text += "### Executor\n{}\n\n".format(executor_text[:5000])
    if diff_text:
        target_text += "### Diff\n{}\n\n".format(diff_text[:5000])
    if _is_autonomous_mode():
        target_text += "\n[Context] Autonomous/Unmanned mode ACTIVE. HARD-GATE and structural guards are by-design safety features of this mode.\n"

    # Try LLM first
    ok, result = _try_llm_model(task_id, target_text[:8000])
    if ok:
        parsed = _parse_llm_verdict(result)
        return {"verdict": parsed["verdict"], "risk": parsed["risk"],
                "score": parsed["score"],
                "reasons": ["llm: " + result[:300]],
                "mode": "llm", "source": "oracle_agent"}

    # Fallback to rule-based
    result = _static_scan_rule_based(plan_text, executor_text, diff_text)
    result["mode"] = "rule_fallback"
    result["source"] = "oracle_agent"
    return result


def review_runtime(task_id: str, executor_text: str = "",
                   logs_text: str = "") -> dict:
    """Runtime analysis: LLM-first, rule-based fallback."""
    target_text = "### Task: {}\n".format(task_id)
    if executor_text:
        target_text += "### Executor\n{}\n\n".format(executor_text[:5000])
    if logs_text:
        target_text += "### Logs\n{}\n\n".format(logs_text[:5000])
    if _is_autonomous_mode():
        target_text += "\n[Context] Autonomous/Unmanned mode ACTIVE. HARD-GATE and structural guards are by-design safety features of this mode.\n"

    # Try LLM first
    ok, result = _try_llm_model(task_id, target_text[:8000])
    if ok:
        parsed = _parse_llm_verdict(result)
        return {"verdict": parsed["verdict"], "risk": parsed["risk"],
                "score": parsed["score"],
                "reasons": ["llm: " + result[:300]],
                "mode": "llm", "source": "oracle_agent"}

    # Fallback
    result = _runtime_scan_rule_based(executor_text, logs_text)
    result["mode"] = "rule_fallback"
    result["source"] = "oracle_agent"
    return result


def review_duo(task_id: str, plan_text: str = "",
               executor_text: str = "", diff_text: str = "",
               logs_text: str = "") -> dict:
    """Dual review: static + runtime, combined verdict."""
    static_result = review_static(task_id, plan_text, executor_text, diff_text)
    runtime_result = review_runtime(task_id, executor_text, logs_text)

    scores = [static_result.get("score", 5.0),
              runtime_result.get("score", 5.0)]
    verdicts = [static_result.get("verdict", "ADVISORY"),
                runtime_result.get("verdict", "ADVISORY")]

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


# ---- CLI ----


def cmd_review(args: List[str]) -> int:
    task_id = ""
    mode = "static"
    plan = executor = token = logs = diff = ""

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
            agent = _find_available_agent()
            if agent:
                result = _spawn_agent_review(agent, stdin_content)
                if result:
                    print(result)
                    _save_verdict("stdin", {"mode": "agent_spawn",
                                             "result": result[:500]})
                    return 0
            prompt = _local_review_prompt(stdin_content)
            print(prompt)
            _save_verdict("stdin", {"mode": "local_prompt",
                                     "status": "pending"})
            print("\n[Oracle] Verdict saved to: {}".format(ORACLE_VERDICTS_DIR))
            return 0

        print(json.dumps({"error": "No task-id provided"}))
        return 1

    if mode == "static":
        result = review_static(task_id, plan, executor, diff)
    elif mode == "runtime":
        result = review_runtime(task_id, executor, logs)
    elif mode == "duo":
        result = review_duo(task_id, plan, executor, diff, logs)
    else:
        result = review_static(task_id, plan, executor, diff)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    _save_verdict(task_id, result)
    code = RETURN_CODES.get(result.get("verdict", "UNAVAILABLE"), 4)
    return code


def cmd_status(args: List[str]) -> int:
    _ensure_dirs()
    latest = _load_latest_verdict()
    if latest:
        print(json.dumps(latest, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"status": "no recent verdicts"}, indent=2))
    return 0


def cmd_bypass(args: List[str]) -> int:
    _ensure_dirs()
    if not args:
        print(json.dumps({"error": "No task-id provided for bypass"}))
        return 1
    task_id = args[0]
    ts = int(time.time())
    bypass = {"task_id": task_id, "bypass_until": ts + BYPASS_TTL,
              "created_at": ts}
    fname = BYPASS_DIR / "{}.json".format(task_id.replace("/", "_"))
    with open(fname, "w") as f:
        json.dump(bypass, f)
    print(json.dumps({"status": "bypass_created", "task_id": task_id,
                       "expires_in_hours": BYPASS_TTL // 3600}))
    return 0


def main() -> int:
    _ensure_dirs()
    if len(sys.argv) < 2:
        print("Usage: oracle_agent.py <review|status|bypass> [...]")
        return 1

    command = sys.argv[1]
    rest = sys.argv[2:]

    handlers = {
        "review": cmd_review,
        "status": cmd_status,
        "bypass": cmd_bypass,
    }

    handler = handlers.get(command)
    if handler:
        return handler(rest)
    else:
        print("Unknown command: {}".format(command))
        return 1


if __name__ == "__main__":
    sys.exit(main())
