#!/usr/bin/env python3
"""
Oracle Spawn.

Spawns static and runtime oracle agents as separate subprocess contexts,
then calls meta_oracle.py to aggregate their verdicts.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

RETURN_CODES = {
    "ACCEPT": 0,
    "ADVISORY": 1,
    "REJECT": 2,
    "ESCALATE": 3,
    "UNAVAILABLE": 4,
}

def run_child(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

def review(args: argparse.Namespace) -> int:
    static_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "static_oracle_agent.py"),
        "review",
        "--task-id",
        args.task_id,
    ]

    runtime_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "runtime_oracle_agent.py"),
        "review",
        "--task-id",
        args.task_id,
    ]

    if args.target:
        static_cmd.extend(["--target", args.target])
    if args.plan:
        static_cmd.extend(["--plan", args.plan])
    if args.executor:
        static_cmd.extend(["--executor", args.executor])
        runtime_cmd.extend(["--executor", args.executor])
    if args.token:
        runtime_cmd.extend(["--token", args.token])
    if args.audit_dir:
        runtime_cmd.extend(["--audit-dir", args.audit_dir])

    static_result = run_child(static_cmd)
    runtime_result = run_child(runtime_cmd)

    print("[static_oracle stdout]")
    print(static_result.stdout.strip())
    if static_result.stderr.strip():
        print("[static_oracle stderr]", file=sys.stderr)
        print(static_result.stderr.strip(), file=sys.stderr)

    print("[runtime_oracle stdout]")
    print(runtime_result.stdout.strip())
    if runtime_result.stderr.strip():
        print("[runtime_oracle stderr]", file=sys.stderr)
        print(runtime_result.stderr.strip(), file=sys.stderr)

    if static_result.returncode >= 4 or runtime_result.returncode >= 4:
        return RETURN_CODES["UNAVAILABLE"]

    meta_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "meta_oracle.py"),
        "aggregate",
        "--task-id",
        args.task_id,
    ]

    meta_result = run_child(meta_cmd)
    print("[meta_oracle stdout]")
    print(meta_result.stdout.strip())
    if meta_result.stderr.strip():
        print("[meta_oracle stderr]", file=sys.stderr)
        print(meta_result.stderr.strip(), file=sys.stderr)

    return meta_result.returncode

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("review")
    p.add_argument("--task-id", required=True)
    p.add_argument("--target")
    p.add_argument("--plan")
    p.add_argument("--executor")
    p.add_argument("--token")
    p.add_argument("--audit-dir", default=".omc/state/audit")
    p.set_defaults(func=review)

    args = parser.parse_args()
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())