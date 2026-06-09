#!/usr/bin/env python3
"""
pretool-python-bridge.py — Python 桥接脚本
用途：hook 中调用 Python 脚本的入口点
对应 pretool-python-bridge.sh 的 Python 移植
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, output_continue, read_input, HOME_DIR

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent


def main():
    if len(sys.argv) < 2:
        print("usage: pretool-python-bridge.py <context-inject|handoff-before|handoff-after|smoke> [args]", file=sys.stderr, flush=True)
        sys.exit(0)

    cmd = sys.argv[1]
    extra_args = sys.argv[2:]

    if cmd == "context-inject":
        subprocess.run([sys.executable, str(SCRIPT_DIR / "context.py")] + extra_args)
    elif cmd == "handoff-before":
        subprocess.run([sys.executable, str(SCRIPT_DIR / "handoff.py"), "before-compact"] + extra_args)
    elif cmd == "handoff-after":
        subprocess.run([sys.executable, str(SCRIPT_DIR / "handoff.py"), "after-compact"] + extra_args)
    elif cmd == "smoke":
        r1 = subprocess.run([sys.executable, str(SCRIPT_DIR / "context.py"), "--smoke"])
        r2 = subprocess.run([sys.executable, str(SCRIPT_DIR / "handoff.py"), "--smoke"])
        if r1.returncode != 0 or r2.returncode != 0:
            sys.exit(1)
    else:
        print("usage: pretool-python-bridge.py <context-inject|handoff-before|handoff-after|smoke> [args]", file=sys.stderr, flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
