#!/usr/bin/env python3
"""lx-code-review-auto — 轻量自动代码审查（posttool-checkpoint 触发）

在任务/步骤完成时自动扫描变更文件的语言无关问题。
发现写入 checkpoint 的 additionalContext，不阻断流程。
"""

import json
import os
import re
import sys
from pathlib import Path

# 要检查的文件扩展名（语言无关）
SCAN_EXTENSIONS = {
    '.py', '.go', '.js', '.ts', '.java', '.rs', '.rb', '.php',
    '.sh', '.yaml', '.yml', '.json', '.toml', '.md', '.css', '.html',
}

# 要跳过的目录
SKIP_DIRS = {'__pycache__', 'node_modules', '.git', '.venv', 'vendor', '.claude/worktrees'}


def find_changed_files(repo_root: str, task_dir: str) -> list:
    """从 git diff 或 executor.md 定位变更文件。优先 git（精确）。"""
    files = set()

    # 方法1: git diff（最近提交或未暂存）
    try:
        result = os.popen(f"cd {repo_root} && git diff --name-only HEAD 2>/dev/null || git diff --name-only 2>/dev/null").read()
        for f in result.strip().splitlines():
            f = f.strip()
            if any(f.endswith(ext) for ext in SCAN_EXTENSIONS) and not any(s in f for s in SKIP_DIRS):
                full = Path(repo_root) / f
                if full.exists():
                    files.add(str(full))
    except Exception:
        pass

    # 方法2: executor.md 文件引用
    executor = Path(task_dir) / "executor.md" if task_dir else None
    if executor and executor.exists():
        try:
            text = executor.read_text()
            for line in text.splitlines():
                m = re.match(r'\s*[-*]\s*`([^`]+)`', line)
                if m:
                    f = m.group(1)
                    if any(f.endswith(ext) for ext in SCAN_EXTENSIONS):
                        full = Path(repo_root) / f
                        if full.exists():
                            files.add(str(full))
        except Exception:
            pass

    return sorted(files)


def scan_file(fpath: str) -> list:
    """扫描单个文件，返回 [(severity, line, msg), ...]"""
    findings = []
    try:
        text = Path(fpath).read_text(encoding='utf-8', errors='replace')
    except Exception:
        return findings

    relpath = os.path.relpath(fpath)
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith(('# ', '// ', '/*', '* ', '<!--')):
            continue

        # P0: 硬编码凭据
        if re.search(r'(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*["\'][^"\']{8,}', stripped):
            findings.append(("P0", relpath, i, f"硬编码凭据: {stripped[:60]}"))

        # P1: debug 遗留
        if re.search(r'(?i)(console\.log|fmt\.Print|print\(|debugger;|pdb\.set_trace)', stripped):
            if not re.search(r'(?i)(TODO|FIXME|XXX)', stripped):
                findings.append(("P1", relpath, i, f"debug遗留: {stripped[:60]}"))

        # P1: TODO/FIXME 无 issue
        if re.search(r'(?i)(TODO|FIXME)\b', stripped) and not re.search(r'#\d+', stripped):
            # 排除: 类别名（TODO/  /lx-todo）和注释中的说明
            if not re.search(r'(?i)(/lx-todo|TODO\s*/|FIXME\s*[：:]\s*已知)', stripped):
                findings.append(("P1", relpath, i, f"无issue TODO: {stripped[:60]}"))

    return findings


def main():
    repo_root = os.environ.get("CARROROS_ROOT", os.getcwd())
    task_dir = os.environ.get("TASK_DIR", "")

    changed = find_changed_files(repo_root, task_dir)

    all_findings = []
    for fpath in changed:
        all_findings.extend(scan_file(fpath))

    if not all_findings:
        print(json.dumps({"review": "clean", "finding_count": 0}))
        return

    # 按严重度分组
    p0 = [f for f in all_findings if f[0] == "P0"]
    p1 = [f for f in all_findings if f[0] == "P1"]

    summary_lines = [
        f"## 自动代码审查",
        f"> 扫描 {len(changed)} 个文件，发现 {len(all_findings)} 个问题",
    ]
    if p0:
        summary_lines.append(f"- 🔴 {len(p0)} 个 P0 问题（硬编码凭据）")
    if p1:
        summary_lines.append(f"- 🟡 {len(p1)} 个 P1 问题（debug遗留/TODO）")
    summary_lines.append("")

    for severity, path, ln, msg in all_findings:
        summary_lines.append(f"- `{severity}` {path}:{ln} — {msg}")

    output = {
        "review": "passed" if not p0 else "warn",
        "finding_count": len(all_findings),
        "p0_count": len(p0),
        "p1_count": len(p1),
        "files_scanned": len(changed),
        "details": all_findings,
        "summary": "\n".join(summary_lines),
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
