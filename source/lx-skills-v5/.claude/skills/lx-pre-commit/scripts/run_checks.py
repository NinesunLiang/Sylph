#!/usr/bin/env python3

"""

运行项目门禁检查序列，输出结构化结果。

用法：python3 run_checks.py --type go|node --runner vitest|jest|npm

exit 0=全通过，2=有阻塞项

"""

import argparse, subprocess, sys, json
from pathlib import Path
from datetime import datetime


TRACE_FILE = Path(".omc/state/skill-trace.jsonl")

def write_trace(event: dict):
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = json.dumps({"ts": datetime.now().isoformat(), **event}, ensure_ascii=False)
    try:
        with open(TRACE_FILE, "a", encoding="utf-8") as tf:
            tf.write(entry + "\n")
    except:
        pass

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr

def check_go():
    results = []
    # 编译
    code, out, err = run("go build ./... 2>&1")
    results.append({"step": "build", "passed": code == 0, "output": (out+err)[:500], "blocking": True})
    if code != 0:
        return results
    # 变更包测试
    code2, out2, err2 = run("git diff --name-only HEAD | grep '\\.go$' | "
                            "xargs -I{} dirname {} | sort -u | "
                            "xargs -I{} go test -race -count=1 ./{} 2>&1")
    results.append({"step": "test", "passed": code2 == 0, "output": (out2+err2)[:1000], "blocking": True})
    return results

def check_node(runner):
    results = []
    # TypeScript 编译
    code, out, err = run("npx tsc --noEmit 2>&1")
    results.append({"step": "typecheck", "passed": code == 0, "output": (out+err)[:500], "blocking": True})

    # 测试
    cmd = {"vitest": "npx vitest run", "jest": "npx jest --passWithNoTests", "npm": "npm test -- --passWithNoTests"}.get(runner, "npm test")
    code2, out2, err2 = run(f"{cmd} 2>&1")
    results.append({"step": "test", "passed": code2 == 0, "output": (out2+err2)[:1000], "blocking": True})
    return results

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--type", required=True)
    p.add_argument("--runner", default="npm")
    args = p.parse_args()

    results = check_go() if args.type == "go" else check_node(args.runner)
    blocked = [r for r in results if not r["passed"] and r["blocking"]]

    print(json.dumps({
        "project_type": args.type,
        "checks": results,
        "blocked": len(blocked) > 0,
        "blocked_steps": [r["step"] for r in blocked]
    }, ensure_ascii=False, indent=2))

    for r in results:
        action = "complete" if r["passed"] else "block"
        write_trace({"skill": "lx-pre-commit", "feature": "pipeline", "task": args.type, "action": action, "step": r["step"], "status": "success"})
    sys.exit(2 if blocked else 0)

if __name__ == "__main__":
    main()
