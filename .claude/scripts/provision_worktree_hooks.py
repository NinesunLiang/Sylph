#!/usr/bin/env python3
"""provision_worktree_hooks.py — 把主仓库的 .claude/hooks/ 安全同步到 worktree。
核心逻辑：逐个文件 shutil.copy2 覆盖，绝不用 copytree，杜绝嵌套。
只复制主仓库 hooks 目录里实际存在的文件（lite 套件），
不删除 worktree 已有但主仓库没有的 hook 文件。

用法:  python3 .claude/scripts/provision_worktree_hooks.py <worktree-path>
例子:  python3 .claude/scripts/provision_worktree_hooks.py .claude/worktrees/agent-xxx/
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

SKIP_DIRS = {"__pycache__", "lib", "tests"}


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    main_hooks = (script_dir / ".." / "hooks").resolve()

    if len(sys.argv) < 2:
        print(f"ERROR: 用法: python3 {sys.argv[0]} <worktree-path>", file=sys.stderr)
        return 1

    worktree_path = sys.argv[1]
    wt_real = Path(worktree_path).resolve()
    if not wt_real.is_dir():
        print(f"ERROR: 目录不存在: {worktree_path}", file=sys.stderr)
        return 1

    wt_hooks = wt_real / ".claude" / "hooks"
    if not wt_hooks.is_dir():
        print(f"WARN: {wt_real} 没有 .claude/hooks 目录，创建中...")
        wt_hooks.mkdir(parents=True, exist_ok=True)

    print(f"syncing hooks into {wt_real}")

    errors = 0
    for entry in sorted(main_hooks.iterdir()):
        if entry.name in SKIP_DIRS:
            continue
        if entry.is_file():
            dst = wt_hooks / entry.name
            try:
                if dst.exists():
                    dst.unlink()
                shutil.copy2(str(entry), str(dst))
                print(f"  {entry.name}")
            except OSError as e:
                print(f"  FAIL: {entry.name}: {e}", file=sys.stderr)
                errors += 1

    if errors:
        print(f"WARN: {errors} 个文件复制失败", file=sys.stderr)

    project_name = main_hooks.parent.parent.name
    print(f"done: {project_name} hooks -> {wt_real}/.claude/hooks/")
    print()
    print(f'验证: ls "{wt_hooks / "hook-launcher.py"}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
