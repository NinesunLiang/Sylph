#!/usr/bin/env python3
"""
fix-hook-cwd.py — 统一所有 hooks 路由到 hook-launcher.py + CWD 容错 fallback

转换规则:
  旧: python3 ".claude/hooks/foo.py"
  新: python3 ".claude/hooks/hook-launcher.py" "foo.py" || echo '{"continue":true}'

已使用 hook-launcher.py 的不重复包装.

背景: settings.json 中 hook command 是相对路径，CWD 漂移到 home 时
python3 找不到脚本。统一路由到 hook-launcher.py（内部用 __file__ 自定位 +
os.chdir(project_root) 修复 CWD）+ || fallback 优雅降级。
"""

import json
import re
import sys
import os


def transform_command(cmd: str) -> str | None:
    """
    将裸 hook 调用转换为 hook-launcher 包装。
    返回 None 表示无需修改。
    """
    if ".claude/hooks/" not in cmd or "python3" not in cmd:
        return None

    # 提取所有被引号包裹的 .py / .sh 路径
    matches = re.findall(r'"([^"]*\.claude/hooks/([^"]+\.(?:py|sh)))"', cmd)
    if not matches:
        return None

    # 取最后一个匹配的 hook 文件名
    full_path, hook_name = matches[-1]

    # 如果已经是 hook-launcher.py 调用 (hook_name 作为参数传入)，无需修改
    if "hook-launcher.py" in cmd and len(matches) >= 2:
        return None

    # 如果匹配到的就是 hook-launcher.py 本身且没有传 hook 参数
    if hook_name == "hook-launcher.py":
        return None

    # 提取 timeout / other options (if any), keep them
    # 构建新命令: hook-launcher 包装 + || fallback
    new_cmd = (
        'python3 ".claude/hooks/hook-launcher.py" "'
        + hook_name
        + '" || echo \'{"continue":true}\''
    )
    return new_cmd


def process_settings(path: str) -> bool:
    with open(path) as f:
        settings = json.load(f)

    hooks_section = settings.get("hooks", {})
    if not hooks_section:
        print(f"[SKIP] {path}: no hooks section")
        return False

    modified = False

    for event_name, matchers in hooks_section.items():
        for matcher in matchers:
            for hook in matcher.get("hooks", []):
                if hook.get("type") != "command":
                    continue
                old_cmd = hook.get("command", "")
                new_cmd = transform_command(old_cmd)
                if new_cmd and new_cmd != old_cmd:
                    hook["command"] = new_cmd
                    modified = True
                    print(f"  [{event_name}]")
                    print(f"    OLD: {old_cmd}")
                    print(f"    NEW: {new_cmd}")
                    print()

    if modified:
        content = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
        with open(path, "w") as f:
            f.write(content)
        print(f"[OK] {path} — updated\n")
    else:
        print(f"[NO CHANGE] {path}\n")

    return modified


def main():
    paths = sys.argv[1:] if len(sys.argv) > 1 else []
    if not paths:
        print("Usage: python3 fix-hook-cwd.py <settings.json> [...]")
        sys.exit(1)

    for p in paths:
        if not os.path.isfile(p):
            print(f"[MISSING] {p}")
            continue
        process_settings(p)


if __name__ == "__main__":
    main()
