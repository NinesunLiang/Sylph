#!/usr/bin/env python3
"""
meta-oracle-agent-spawn.py — Meta-Oracle Agent spawn 入口
Python 移植版，完全等价 meta-oracle-agent-spawn.sh v1.0

Role: 用和 Oracle 相同的 Agent spawn 机制启动 Meta-Oracle 独立审查
只是 prompt 不同（Meta-Oracle 方法论 vs Oracle 方法论）

使用方式: AI 在收到 Meta-Oracle trigger 后调用此脚本
流程:
  1. prepare: 组装审核上下文 → stdout JSON
  2. spawn:   Agent(subagent_type="critic", prompt=<request.json + meta-oracle-protocol.md>)
  3. record:  记录裁决到 meta-oracle-verdicts.md

用法: python3 meta-oracle-agent-spawn.py [G1|G2|G3|G4] prepare|record [--verdict ...]
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Source harness_config.sh equivalent
HC_SCRIPT = Path(__file__).resolve().parent / ".." / "hooks" / "harness_config.sh"
# In Python, we don't source bash; use harness_lib if available
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
    from harness_lib import flywheel_event
except ImportError:
    def flywheel_event(name="", event_type="", severity="P2", project=""):
        logfile = Path.home() / ".claude" / "flywheel.log"
        logfile.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(logfile, "a") as f:
                f.write(f"{datetime.now():%Y-%m-%d},{name}_{event_type},{severity},{project or 'carror-os'}\n")
        except Exception:
            pass

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / "../..").resolve()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
META_PROTOCOL = PROJECT_ROOT / ".claude" / "reference" / "meta-oracle.md"
VERDICTS_FILE = STATE_DIR / "meta-oracle-verdicts.md"

PYTHON_BIN = os.environ.get("PYTHON_BIN", "python3")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─── Step 1: Prepare — 组装审核上下文 ───
def cmd_prepare(trigger_type: str):
    timestamp = now_utc()

    # Read protocol
    protocol_content = ""
    if META_PROTOCOL.exists():
        protocol_content = META_PROTOCOL.read_text(encoding="utf-8")

    # Read latest smoke test result
    smoke_result = ""
    smoke_files = sorted(STATE_DIR.glob("harness-smoke-*.log"), reverse=True)
    if smoke_files:
        latest_smoke = smoke_files[0]
        for line in latest_smoke.read_text(encoding="utf-8").splitlines():
            if "summary:" in line:
                smoke_result = line.strip()
                break
        if not smoke_result:
            smoke_result = "无 smoke test 数据"

    # Read latest Oracle verdicts
    oracle_verdicts = ""
    oracle_file = STATE_DIR / "oracle-verdicts.md"
    if oracle_file.exists():
        lines = oracle_file.read_text(encoding="utf-8").splitlines()
        oracle_verdicts = "\n".join(lines[-30:])

    # Output JSON to stdout
    output = {
        "meta_oracle_request": {
            "timestamp": timestamp,
            "trigger_type": trigger_type.replace("G", ""),
            "project_root": str(PROJECT_ROOT),
        },
        "protocol": protocol_content,
        "smoke_test": smoke_result,
        "oracle_verdicts": oracle_verdicts,
        "spawn": "READY",
        "agent_type": "critic",
        "instructions": "使用 Agent(subagent_type='critic') 拉起独立上下文，prompt = protocol + smoke_test + oracle_verdicts",
        "post_spawn": f"将 agent 输出写入 {VERDICTS_FILE}",
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))

    flywheel_event("meta_oracle_spawn", "prepare_ok", "P2")
    sys.exit(0)


# ─── Step 2: Record — 记录裁决 ───
def cmd_record(trigger_type: str, verdict: str = ""):
    if not verdict:
        # Parse from remaining args
        return

    timestamp = now_utc()

    # Extract verdict status
    status = "UNKNOWN"
    if "[Meta-Oracle: ACCEPT]" in verdict:
        status = "ACCEPT"
    elif "[Meta-Oracle: ADVISORY]" in verdict:
        status = "ADVISORY"
    elif "[Meta-Oracle: REJECT]" in verdict:
        status = "REJECT"

    # Write verdicts file
    VERDICTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(VERDICTS_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n## [{timestamp}] [{trigger_type}] [Meta-Oracle: {status}]\n\n")
        f.write(f"**审查类型**: {trigger_type} — Meta-Oracle Agent 独立审查\n")
        f.write(f"**Agent**: critic (独立上下文, 物理隔离)\n")
        f.write(f"**路径**: Agent spawn\n\n")
        f.write("```\n")
        f.write("\n".join(verdict.splitlines()[:30]))
        f.write("\n```\n\n")

    flywheel_event("meta_oracle_spawn", f"record_{status}", "P2")
    print(f"[meta-oracle-spawn] ✅ 裁决已记录: {timestamp} | {trigger_type} | {status}")
    sys.exit(0)


def print_usage():
    print("Usage: meta-oracle-agent-spawn.py [G1|G2|G3|G4] prepare|record", file=sys.stderr)
    print("  prepare             组装审核上下文 → stdout JSON", file=sys.stderr)
    print("  record --verdict    记录裁决到 meta-oracle-verdicts.md", file=sys.stderr)
    print("  G1|G2|G3|G4        触发类型(可选,默认G3)", file=sys.stderr)


def main():
    trigger_type = "G3"
    cmd = ""
    verdict_text = ""

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ("prepare", "record", "help", "--help", "-h"):
            cmd = args[i]
        elif args[i] in ("G1", "G2", "G3", "G4"):
            trigger_type = args[i]
        elif args[i] == "--verdict":
            i += 1
            if i < len(args):
                verdict_text = args[i]
        elif args[i] == "help":
            cmd = "help"
        i += 1

    if cmd in ("help", "--help", "-h"):
        print_usage()
        sys.exit(0)

    if cmd == "prepare":
        cmd_prepare(trigger_type)
    elif cmd == "record":
        # Gather remaining args as verdict if no --verdict flag
        if not verdict_text:
            remaining = [a for a in args if a not in ("record", trigger_type)]
            verdict_text = " ".join(remaining)
        cmd_record(trigger_type, verdict_text)
    else:
        print(f"[meta-oracle-spawn] Usage: {sys.argv[0]} [G1|G2|G3|G4] <prepare|record>", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
