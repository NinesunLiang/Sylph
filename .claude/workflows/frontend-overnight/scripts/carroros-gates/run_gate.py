#!/usr/bin/env python3
"""run_gate.py — 通用门禁执行器（FINAL.md v4.0 §4.4）
用法: run_gate.py --gate-id C2 --manifest M --night-dir D --page-id P
                  [--target-repo R] [--evidence JSON] -- cmd [args...]
退出：0=PASS；被包装命令非 0 → 1=FAIL；无法启动 → 2=ERROR。
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from lib.common_lib import *

def main() -> int:
    argv = sys.argv[1:]
    try:
        sep = argv.index("--")
    except ValueError:
        print("ERROR: 用法: run_gate.py ... -- cmd", file=sys.stderr)
        return 2
    our_args = argv[:sep]
    cmd = argv[sep + 1:]
    if not cmd:
        print("ERROR: 需要被包装命令", file=sys.stderr)
        return 2

    gate_id = ""
    evidence_raw = "[]"
    pass_args = []
    i = 0
    while i < len(our_args):
        if our_args[i] == "--gate-id" and i + 1 < len(our_args):
            gate_id = our_args[i + 1]; i += 2
        elif our_args[i] == "--evidence" and i + 1 < len(our_args):
            evidence_raw = our_args[i + 1]; i += 2
        else:
            pass_args.append(our_args[i]); i += 1
    if not gate_id:
        print("ERROR: 需要 --gate-id", file=sys.stderr)
        return 2

    gates_parse_args(pass_args)
    gates_preamble()
    started_at = gates_now()

    r = subprocess.run(cmd, capture_output=False)
    cmd_exit = r.returncode if hasattr(r, 'returncode') else (subprocess.run(cmd).returncode if not cmd else 0)

    if cmd_exit == 0:
        status = "PASS"
        final_exit = 0
    elif cmd_exit in (126, 127):
        status = "ERROR"
        final_exit = 2
    else:
        status = "FAIL"
        final_exit = 1

    wrapped_str = " ".join(cmd)
    argv_digest = gates_sha256_string(wrapped_str)
    evidence = json.loads(evidence_raw)
    evidence.append({"type": "wrapped_argv", "argv": wrapped_str, "argv_digest": argv_digest})

    gates_write_result(gate_id, status, cmd_exit, started_at, evidence=evidence, argv_digest=argv_digest)
    print(f"run_gate {gate_id}: {status} (exit {cmd_exit})")
    return final_exit

if __name__ == "__main__":
    sys.exit(main())
