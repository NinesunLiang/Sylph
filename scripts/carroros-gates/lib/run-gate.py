#!/usr/bin/env python3
"""
run-gate.py — 通用门禁执行器 (v6.0, .sh → .py 迁移)
跑任意命令，按退出码写 gate-result 信封。
用于 C2/C4/C5/C6 等"外部工具即门禁"的场景。

用法:
  python3 run-gate.py --gate-id C2 --manifest M --night-dir D --page-id P \
                      [--target-repo R] [--evidence JSON] -- cmd [args...]
退出码: 0=PASS；被包装命令非 0 → 1=FAIL；命令无法启动 → 2=ERROR。
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
GATES_DIR = SCRIPT_DIR.parent

# 也加入到 sys.path 以便 import common
sys.path.insert(0, str(GATES_DIR))
from lib import common

# ── 解析 -- 之前的参数和之后的命令 ──
our_args = []
cmd = []
seen_sep = False
for a in sys.argv[1:]:
    if not seen_sep and a == "--":
        seen_sep = True
        continue
    if not seen_sep:
        our_args.append(a)
    else:
        cmd.append(a)

if not seen_sep or not cmd:
    print("ERROR: 用法: run-gate.py --gate-id X --manifest M --night-dir D --page-id P [--target-repo R] -- cmd", file=sys.stderr)
    sys.exit(2)

# 解析 our_args
gate_id = ""
evidence = "[]"
pass_args = []
i = 0
while i < len(our_args):
    if our_args[i] == "--gate-id" and i + 1 < len(our_args):
        gate_id = our_args[i + 1]
        i += 2
    elif our_args[i] == "--evidence" and i + 1 < len(our_args):
        evidence = our_args[i + 1]
        i += 2
    else:
        pass_args.append(our_args[i])
        i += 1

if not gate_id:
    print("ERROR: 需要 --gate-id", file=sys.stderr)
    sys.exit(2)

common.parse_args(pass_args)
common.preamble()

started_at = common.now_iso()
r = subprocess.run(cmd)
cmd_exit = r.returncode

if cmd_exit == 0:
    status, final_exit = "PASS", 0
elif cmd_exit in (126, 127):
    status, final_exit = "ERROR", 2
else:
    status, final_exit = "FAIL", 1

wrapped_str = " ".join(cmd)
argv_digest = common.sha256_string(wrapped_str)

# 追加 wrapped_argv 到 evidence
ev = json.loads(evidence)
ev.append({"type": "wrapped_argv", "argv": wrapped_str, "argv_digest": argv_digest})
evidence_final = json.dumps(ev, ensure_ascii=False)

common.write_result(gate_id, status, cmd_exit, started_at, evidence_final, argv_digest)
print(f"run-gate {gate_id}: {status} (exit {cmd_exit})")
sys.exit(final_exit)
