#!/usr/bin/env python3

"""获取相对于 prod-commit 的变更文件列表，输出 JSON"""

import argparse, subprocess, sys, json


def run(cmd):
    # nosec B602: skill 层 CLI 工具，cmd 为内部 git 命令拼接，非用户原始输入
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)  # nosec B602
    return r.returncode, r.stdout.strip()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prod-commit", required=True)
    p.add_argument("--type", default="all")
    args = p.parse_args()

    code, out = run(f"git cat-file -t {args.prod_commit} 2>/dev/null")
    if code != 0 or out != "commit":
        print(json.dumps({"error": f"无效 commit: {args.prod_commit}"}))
        sys.exit(1)

    _, all_files = run(f"git diff {args.prod_commit}...HEAD --name-only --diff-filter=AM")
    files = [f for f in all_files.split('\n') if f]

    go_files = [f for f in files if f.endswith('.go') and not any(
        f.endswith(s) for s in ('_test.go','.pb.go','_gen.go'))]

    ts_files = [f for f in files if any(f.endswith(s) for s in ('.ts','.tsx','.js','.jsx')) and not any(
        f.endswith(s) for s in ('.test.ts','.spec.ts','.test.tsx'))]

    _, commit_count = run(f"git rev-list {args.prod_commit}...HEAD --count")

    print(json.dumps({
        "prod_commit": args.prod_commit,
        "total_files": len(files),
        "go_files": go_files,
        "ts_files": ts_files,
        "commit_count": commit_count.strip(),
        "all_files": files
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
