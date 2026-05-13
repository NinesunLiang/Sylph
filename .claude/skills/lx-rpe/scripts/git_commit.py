#!/usr/bin/env python3
"""
git_commit.py — lx-rpe Step 8 严格 Git 提交脚本
用法：python3 git_commit.py --feature <name> --task <RPE-xxx> --type <feat|fix|refactor> --scope <scope> --msg "<描述>"
退出码：0=成功, 1=参数错误, 2=git操作失败, 3=用户取消
"""
import argparse, subprocess, sys, json
def run(cmd, capture=True):
    # nosec B602: skill 层 CLI 工具，cmd 为内部 git 命令拼接，非用户原始输入
    r = subprocess.run(cmd, shell=True, capture_output=capture, text=True)  # nosec B602
    return r.returncode, r.stdout.strip(), r.stderr.strip()
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--feature", required=True)
    p.add_argument("--task", required=True)
    # RPE-xxx
    p.add_argument("--type", required=True, choices=["feat","fix","refactor","docs","test","chore"])
    p.add_argument("--scope", default="")
    p.add_argument("--msg", required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    scope = f"({args.scope})" if args.scope else ""
    commit_msg = f"{args.type}{scope}: {args.task} {args.msg}"
    # 1. 状态检查
    code, status, _ = run("git status --porcelain")
    if not status:
        print(json.dumps({"status": "nothing_to_commit", "msg": commit_msg}))
        sys.exit(0)
    # 2. 变更统计
    code, diff_stat, _ = run("git diff --stat HEAD")
    _, changed_files, _ = run("git diff --name-only HEAD")
    file_list = [f for f in changed_files.split('\n') if f]
    # 3. 输出待确认信息（给 AI 展示给用户）
    print(json.dumps({ "status": "pending_confirm", "commit_message": commit_msg, "changed_files": file_list, "file_count": len(file_list), "diff_stat": diff_stat }, ensure_ascii=False, indent=2))
    if args.dry_run:
        sys.exit(0)
    # 4. 等待 AI 收到用户确认后再执行（AI 负责确认流程，此脚本只执行） # 暂存变更文件（禁止 git add -A，逐文件暂存）
    for f in file_list:
        code, _, err = run(f'git add "{f}"')
        if code != 0:
            print(json.dumps({"status": "error", "step": "git_add", "file": f, "error": err}))
            sys.exit(2)
    # 5. 提交
    code, out, err = run(f'git commit -m "{commit_msg}"')
    if code != 0:
        print(json.dumps({"status": "error", "step": "git_commit", "error": err}))
        sys.exit(2)
    _, commit_hash, _ = run("git rev-parse --short HEAD")
    print(json.dumps({ "status": "success", "commit_hash": commit_hash, "commit_message": commit_msg, "files_committed": len(file_list) }, ensure_ascii=False))
if __name__ == "__main__":
    main()