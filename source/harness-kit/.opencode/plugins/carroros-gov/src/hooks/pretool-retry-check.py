#!/usr/bin/env python3
"""pretool-retry-check.py — PreToolUse — 阻断超过重试上限的 Bash 命令

Role: PreToolUse 检查 retry-budget，阻断超过上限的重复失败命令

原理：
  retry-budget.json 记录每个错误签名的重试次数。
  当某个签名超过 MAX_RETRIES（默认 3），后续 Bash 调用被阻断。
  避免 AI 在同一个错误上无限重试（C9 错误恢复）。

注意：直接读取 retry-budget.json，不调用 retry-budget.sh check
（retry-budget.sh 存在 bash 退出码传播 bug）

用法（作为 hook 从 stdin 接收 JSON）:
  echo '{"tool": "Bash", "tool_input": {"command": "go build"}}' | python3 pretool-retry-check.py
"""

import json
import os
import re
import glob
import sys
import time
from pathlib import Path

# ── 引入同级共享库 ──
_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, is_mode_active, flywheel_event, agentic_menu, hc_emit_hook_json

# ── 路径常量 ──
PROJECT_ROOT = (_HOOKS_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
BUDGET_FILE = STATE_DIR / "retry-budget.json"
E4_STATE_DIR = STATE_DIR
ERROR_SIGNALS_FILE = E4_STATE_DIR / "error-signals.jsonl"
DIAGNOSIS_FILE = E4_STATE_DIR / "diagnosis.json"
BUILD_FAIL_GATE = STATE_DIR / "build-fail-gate.json"

MAX_RETRIES = 3


def read_stdin():
    """Read stdin as raw string."""
    return sys.stdin.read()


def get_tool_name(input_str: str) -> str:
    """Extract 'tool' field from stdin JSON."""
    try:
        data = json.loads(input_str)
        return (data.get("tool") or "").strip()
    except (json.JSONDecodeError, Exception):
        return ""


def get_command(input_str: str) -> str:
    """Extract 'command' from tool_input."""
    try:
        data = json.loads(input_str)
        return (data.get("tool_input", {}).get("command") or "").strip()
    except (json.JSONDecodeError, Exception):
        return ""


def check_budget_exceeded() -> list:
    """Check retry-budget.json for signatures >= MAX_RETRIES. Returns list of (sig, count, label)."""
    if not BUDGET_FILE.exists():
        return []
    try:
        with open(str(BUDGET_FILE), encoding="utf-8") as f:
            data = json.load(f)
        sigs = data.get("signatures", {})
        exceeded = []
        for sig, info in sigs.items():
            retry_count = info.get("retry_count", 0)
            if retry_count >= MAX_RETRIES:
                label = (info.get("label") or sig)[:80]
                exceeded.append((sig[:40], retry_count, label))
        return exceeded
    except Exception:
        return []


def check_near_limit() -> list:
    """Check for signatures with retry_count >= 2 and < MAX_RETRIES (near limit)."""
    if not BUDGET_FILE.exists():
        return []
    try:
        with open(str(BUDGET_FILE), encoding="utf-8") as f:
            data = json.load(f)
        sigs = data.get("signatures", {})
        near = []
        for sig, info in sigs.items():
            retry_count = info.get("retry_count", 0)
            if 2 <= retry_count < MAX_RETRIES:
                label = (info.get("label") or sig)[:80]
                near.append((sig[:40], retry_count, label))
        return near
    except Exception:
        return []


def has_diagnosis() -> bool:
    """E4 Layer 1: 结构化诊断检测 (>=3/5 字段).

    来源优先级:
    (a) 证据文件 .completion-evidence-* (最近5个)
    (b) error-signals.jsonl 最后100行
    (c) diagnosis.json (1小时内创建)
    """
    diag_fields = {
        "root_cause": re.compile(r"root[._]cause[:=]\s*\S+", re.I),
        "repro": re.compile(r"(repro|复现|触发条件)[:=]\s*\S+", re.I),
        "underlying": re.compile(r"(underlying|底层原因|why.*fail)[:=]\s*\S+", re.I),
        "fix_approach": re.compile(r"(fix[._]approach|修复方式|approach)[:=]\s*\S+", re.I),
        "diff_prev": re.compile(r"(diff.*prev|direction[._]change|different|方向变更|新方向)[:=]\s*\S+", re.I),
    }

    found = 0

    # Source A: Recent evidence files (5 most recent)
    ev_files = sorted(
        glob.glob(str(E4_STATE_DIR / ".completion-evidence-*")),
        key=os.path.getmtime,
        reverse=True,
    )[:5]
    for ef in ev_files:
        try:
            with open(ef, encoding="utf-8") as f:
                text = f.read()
            score = sum(1 for _, rx in diag_fields.items() if rx.search(text))
            if score >= 3:
                found += 1
        except Exception:
            pass

    # Source B: error-signals.jsonl last 100 lines
    if ERROR_SIGNALS_FILE.exists():
        try:
            with open(str(ERROR_SIGNALS_FILE), encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines[-100:]:
                try:
                    rec = json.loads(line)
                    text = (rec.get("message", "") or "") + " " + (rec.get("cmd", "") or "")
                    score = sum(1 for _, rx in diag_fields.items() if rx.search(text))
                    if score >= 3:
                        found += 1
                except Exception:
                    pass
        except Exception:
            pass

    # Source C: diagnosis.json (within 1 hour)
    if DIAGNOSIS_FILE.exists():
        try:
            mtime = os.path.getmtime(str(DIAGNOSIS_FILE))
            age = time.time() - mtime
            if age < 3600:
                with open(str(DIAGNOSIS_FILE), encoding="utf-8") as f:
                    text = f.read()
                score = sum(1 for _, rx in diag_fields.items() if rx.search(text))
                if score >= 3:
                    found += 1
        except Exception:
            pass

    return found > 0


def is_build_command(cmd: str) -> bool:
    """Check if command is a build/test/install command (not a read/diagnostic command)."""
    build_pattern = re.compile(
        r"(go\s+build|go\s+test|npm\s+(install|test|build)|make|cargo\s+build|cargo\s+test|"
        r"pip\s+install|poetry\s+install|yarn|pnpm|compile|cmake)",
        re.I,
    )
    return bool(build_pattern.search(cmd))


def is_read_command(cmd: str) -> bool:
    """Check if command is a read/diagnostic command."""
    read_pattern = re.compile(
        r"(cat|head|tail|less|more|Read|grep.*error|journalctl|dmesg|log|查看|检查|诊断|"
        r"analyze|why.*fail|error.*show|build.*fail|test.*output)",
        re.I,
    )
    return bool(read_pattern.search(cmd))


def get_build_fail_streak() -> int:
    """Read build-fail-gate.json streak count."""
    if not BUILD_FAIL_GATE.exists():
        return 0
    try:
        with open(str(BUILD_FAIL_GATE), encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("streak", 0))
    except Exception:
        return 0


def log_skipped_error(exceeded_info: str):
    """Record skipped error to skipped-errors.md in ghost/goal mode."""
    skipped_file = STATE_DIR / "skipped-errors.md"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(str(skipped_file), "a", encoding="utf-8") as f:
            f.write(f"- {timestamp} | retry-budget exceeded | {exceeded_info}\n")
    except Exception:
        pass


def main():
    # ── Config check ──
    if not hc_enabled("retry_budget_check"):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Mode detection ──
    mode = is_mode_active()
    if mode != "normal":
        print(f"[{mode}] pretool-retry-check 已记录（模式降级，不阻断）", file=sys.stderr)
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── Read stdin ──
    input_str = read_stdin()
    if not input_str:
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ── 仅检查 Bash 命令 ──
    tool_name = get_tool_name(input_str)
    if tool_name.lower() not in ("bash",):
        print(json.dumps({"continue": True}))
        sys.exit(0)

    # ════════════════════════════════════════════
    # 1. Retry Budget Check (超上限阻断)
    # ════════════════════════════════════════════
    exceeded = check_budget_exceeded()
    if exceeded:
        exceeded_lines = "\n".join(f"{sig} ({cnt} retries): {label}" for sig, cnt, label in exceeded)

        if mode != "normal":
            # 自主模式: 记录跳过错误并继续
            print(f"[pretool-retry-check] 自主模式: 记录跳过错误并继续", file=sys.stderr)
            log_skipped_error(exceeded_lines)
            print(json.dumps({"continue": True}))
            sys.exit(0)

        # 正常模式: agentic_menu 阻断
        flywheel_event("pretool_retry_check", "blocked", "P2")
        agentic_menu(
            "Retry Budget",
            f"存在超过重试上限的重复失败:\n{exceeded_lines}",
            "重置重试计数并重试",
            "清除错误签名计数，重新尝试",
            "升级到 lx-task-spec",
            "启动结构化任务处理流程",
        )
        # agentic_menu calls sys.exit(2)

    # ════════════════════════════════════════════
    # 2. E4 惯性执行诊断门禁
    # ════════════════════════════════════════════
    near_limit = check_near_limit()
    if near_limit:
        near_lines = "\n".join(f"{sig} (count={cnt}): {label}" for sig, cnt, label in near_limit)

        if not has_diagnosis():
            if mode != "normal":
                print("[pretool-retry-check] 自主模式: E4 诊断门禁跳过", file=sys.stderr)
            else:
                flywheel_event("pretool_retry_check", "e4_gate_blocked", "P2")
                agentic_menu(
                    "E4 Inertia Gate",
                    f"重试接近上限，但未检测到诊断分析:\n{near_lines}\n"
                    "请先做根因分析(5-Why)并记录诊断结论，再重试修复。\n"
                    '提示: echo \'{"root_cause":"...","direction":"..."}\' > .omc/state/diagnosis.json',
                    "执行 5-Why 根因分析",
                    "先完成诊断分析，再重新尝试修复",
                    "强制继续（下次将硬阻断）",
                    "跳过诊断检查，但需承担风险",
                )
                # agentic_menu calls sys.exit(2)

    # ════════════════════════════════════════════
    # 3. E5 Build Fail Gate (B3 增强)
    # ════════════════════════════════════════════
    if BUILD_FAIL_GATE.exists():
        cmd = get_command(input_str)
        build_cmd = is_build_command(cmd)
        read_cmd = is_read_command(cmd)
        streak = get_build_fail_streak()

        if build_cmd and not read_cmd:
            if mode != "normal":
                print(f"[pretool-retry-check] 自主模式: E5 Build Fail Gate active — streak={streak}", file=sys.stderr)
            else:
                agentic_menu(
                    "E5 Build Fail Gate (B3)",
                    f"构建已在{streak}次连续失败中。直接重试通常无效。\n"
                    "请先读取编译错误消息做根因分析，而非盲目重试。\n\n"
                    "可选操作:",
                    "先读取编译错误",
                    "执行 cat/head/grep 查看错误日志",
                    "查看诊断记录",
                    "检查之前的诊断记录和分析",
                    "强制重试",
                    "跳过诊断，直接重试构建",
                )
                # agentic_menu calls sys.exit(2)
        elif build_cmd:
            print("[pretool-retry-check] ✅ E5 Build Fail Gate — 当前为先读后修模式，放行", file=sys.stderr)

    # ── All checks passed ──
    print(json.dumps({"continue": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
