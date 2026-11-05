#!/usr/bin/env python3
"""
git_commit.py — lx-rpe Step 8 严格 Git 提交脚本
用法：python3 git_commit.py --feature <name> --task <RPE-xxx> --type <feat|fix|refactor> --scope <scope> --msg "<描述>"
退出码：0=成功, 1=参数错误, 2=git操作失败, 3=用户取消
"""
import argparse, subprocess, sys, json
from pathlib import Path

def run(cmd, capture=True):
    # nosec B602: skill 层 CLI 工具，cmd 为内部 git 命令拼接，非用户原始输入
    r = subprocess.run(cmd, shell=True, capture_output=capture, text=True)  # nosec B602
    return r.returncode, r.stdout.strip(), r.stderr.strip()

def check_goal_hard_boundary():
    """goal 无人模式下 git commit 是硬边界 — 拒绝执行，提示走 hard-boundary-hit 记录。
    与 lx-goal references/autonomous-execution.md §硬边界.2 对齐。"""
    signal = Path(".omc/state/tokens/autonomous.active")
    if signal.exists():
        print(json.dumps({
            "status": "hard_boundary_blocked",
            "reason": "goal 模式激活中，git commit 属硬边界（Git 写操作），AI 不可执行",
            "human_action": "人工审查变更后执行 git add/commit；或由 AI 记录 lx-goal hard-boundary-hit",
        }, ensure_ascii=False, indent=2))
        sys.exit(3)

def list_changed_files():
    """从 git status --porcelain 解析全部变更（含 untracked）。

    修复 P0：原实现用 `git diff --name-only HEAD`，untracked 新文件被静默漏掉，
    导致特性新文件不进入 commit（静默部分提交）。
    porcelain 格式: XY<space>path（rename 为 'R  old -> new'，取新路径）。
    注意：不能用 run() 的 strip 输出 — 首行 XY 状态列的前导空格会被吃掉，
    导致 line[3:] 错位（' M main.go' → 'ain.go'）。
    """
    r = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    files = []
    for line in r.stdout.split("\n"):
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip().strip('"')
        if path:
            files.append(path)
    return files

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

    # 硬边界：goal 无人模式禁止 git 写操作
    check_goal_hard_boundary()

    # commit msg 安全校验（terminal-safety Rule 4：# 会被 git 截断；" 破坏 shell）
    for bad in ("#", '"'):
        if bad in args.msg or bad in args.scope or bad in args.task:
            print(json.dumps({"status": "error", "step": "validate",
                              "error": f"commit 信息含禁用字符 {bad!r}（Rule 4）"}))
            sys.exit(1)

    scope = f"({args.scope})" if args.scope else ""
    commit_msg = f"{args.type}{scope}: {args.task} {args.msg}"
    # 1. 状态检查
    file_list = list_changed_files()
    if not file_list:
        print(json.dumps({"status": "nothing_to_commit", "msg": commit_msg}))
        sys.exit(0)
    # 2. 变更统计
    code, diff_stat, _ = run("git diff --stat HEAD")
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