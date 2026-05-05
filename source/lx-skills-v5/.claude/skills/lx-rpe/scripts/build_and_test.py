#!/usr/bin/env python3

"""

build_and_test.py — lx-rpe Step 3 编译+测试验证（复用 lx-pre-commit 逻辑）

用法：python3 build_and_test.py --type go|node [--runner vitest|jest] [--changed-only]

exit: 0=通过, 2=失败

"""

import argparse, subprocess, sys, json


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr

def check_budget():
    """检查 Change Budget：变更文件数"""
    _, out, _ = run("git diff --name-only HEAD 2>/dev/null")
    files = [f for f in out.strip().split('\n') if f]
    return len(files), files

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--type", required=True, choices=["go","node"])
    p.add_argument("--runner", default="npm")
    p.add_argument("--budget", type=int, default=0)
    args = p.parse_args()

    results = []

    if args.type == "go":
        code, out, err = run("go build ./... 2>&1")
        results.append({"step":"build","passed":code==0,"output":(out+err)[:400]})
        if code == 0:
            _, changed, _ = run("git diff --name-only HEAD -- '*.go' 2>/dev/null")
            pkgs = set()
            for f in changed.strip().split('\n'):
                if f and not any(f.endswith(s) for s in ('_test.go','.pb.go','_gen.go')):
                    import os
                    pkgs.add("./" + os.path.dirname(f) if os.path.dirname(f) else "./")
            pkg_str = " ".join(pkgs) if pkgs else "./..."
            code2, out2, err2 = run(f"go test -race -count=1 {pkg_str} 2>&1")
            results.append({"step":"test","passed":code2==0,"output":(out2+err2)[:800]})
    else:
        code, out, err = run("npx tsc --noEmit 2>&1")
        results.append({"step":"typecheck","passed":code==0,"output":(out+err)[:400]})
        if code == 0:
            cmd = {"vitest":"npx vitest run","jest":"npx jest --passWithNoTests"}.get(args.runner,"npm test")
            code2, out2, err2 = run(f"{cmd} 2>&1")
            results.append({"step":"test","passed":code2==0,"output":(out2+err2)[:800]})

    if args.budget > 0:
        count, files = check_budget()
        ok = count <= args.budget
        results.append({"step":"budget","passed":ok, "changed":count,"limit":args.budget,"files":files})

    overall = all(r["passed"] for r in results)
    print(json.dumps({"passed":overall,"results":results}, ensure_ascii=False, indent=2))
    sys.exit(0 if overall else 2)

if __name__ == "__main__":
    main()
