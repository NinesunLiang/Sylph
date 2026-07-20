#!/usr/bin/env python3
"""oracle-gate.py — SessionStart — 检测 Agent 独立进程能力是否可用
Role: 检测 claude/opencode/gh CLI 是否可用，Oracle 审核依赖独立 agent 进程
"""
import json
import shutil
import sys
from pathlib import Path

# Import shared library
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness_lib import hc_enabled, flywheel_event


def main():
    # ── Guard ──
    if not hc_enabled("oracle_gate"):
        print('{"continue": true}')
        sys.exit(0)

    # ── Detect Agent CLI availability ──
    can_agent = False

    # Claude Code CLI
    if shutil.which("claude"):
        can_agent = True

    # OpenCode CLI
    if shutil.which("opencode"):
        can_agent = True

    # GH CLI
    if shutil.which("gh"):
        can_agent = True

    # ── Output ──
    if not can_agent:
        flywheel_event("oracle-gate", "agent_unavailable", "P2")
        result = {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": (
                    "[oracle-gate] ⚠️ 未检测到 Agent 独立进程能力 "
                    "(claude/opencode/gh CLI)。Oracle 双法官审核将降级为本地 "
                    "prompt 审核，物理隔离打折扣。"
                )
            }
        }
        print(json.dumps(result, ensure_ascii=True))
    else:
        print('{"continue": true}')

    sys.exit(0)


if __name__ == "__main__":
    main()
