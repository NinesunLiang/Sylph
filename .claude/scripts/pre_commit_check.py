#!/usr/bin/env python3
"""pre_commit_check.py — 提交前**轻量**检查：必要性 / 语法 / 格式。

设计原则（index50，人类要求）：
- **轻**：只查**改动的内容**，不跑全量编译、不跑全量测试（那是 push 的事）
- **不猜项目类型**：按**文件后缀**逐个处理，不依赖 go.mod/package.json 之类的存在
- **不依赖外部工具**：语法检查用标准库（py_compile/json/yaml），格式检查用内置规则
- 目标：高频 commit 前几秒内跑完，让基础问题提前暴露

三项检查：
  1. 必要性 — 有实际改动？是否只是在提交噪声（缓存/生成物）？
  2. 语法   — 改动的文件能否解析（py/json/yaml/sh）
  3. 格式   — 行尾空白 / tab 混用 / 文件末尾缺换行（仅改动文件）

用法（仓库根目录）:
  python3 ".claude/scripts/pre_commit_check.py"            # 检查工作区+暂存改动
  python3 ".claude/scripts/pre_commit_check.py" --staged   # 只看暂存

退出码：0 = 通过（可有警告）；1 = 阻断（语法错误 / 无改动却要提交）
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# 噪声路径：属生成物/缓存，不构成「有意义的改动」
NOISE_PARTS = {"__pycache__", ".pytest_cache", "node_modules", ".DS_Store"}
NOISE_SUFFIX = (".pyc", ".pyo", ".log", ".tmp")

# 可做语法检查的后缀 → 检查器
SYNTAX_CHECKABLE = (".py", ".json", ".yaml", ".yml", ".sh")


def changed_files(staged_only: bool = False) -> list[str]:
    """返回改动文件列表（相对仓库根）。

    注意：`git diff` **看不到未跟踪的新文件**。新建文件若不计入，会误判为「无改动」——
    实跑时确实踩到。故非 staged 模式额外并入 `git ls-files --others`。
    """
    if staged_only:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    else:
        cmd = ["git", "diff", "HEAD", "--name-only", "--diff-filter=ACMR"]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    files = [l.strip() for l in (r.stdout or "").splitlines() if l.strip()] if r.returncode == 0 else []
    if not staged_only:
        u = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                           cwd=str(ROOT), capture_output=True, text=True)
        if u.returncode == 0:
            files.extend(l.strip() for l in (u.stdout or "").splitlines() if l.strip())
    seen: set[str] = set()
    out: list[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def is_noise(rel: str) -> bool:
    parts = set(rel.split("/"))
    return bool(parts & NOISE_PARTS) or rel.endswith(NOISE_SUFFIX)


def check_necessity(files: list[str]) -> tuple[bool, list[str]]:
    """必要性：必须有实际改动，且不能全是噪声。"""
    msgs: list[str] = []
    real = [f for f in files if not is_noise(f)]
    if not files:
        return False, ["无任何改动——没有可提交的内容"]
    if not real:
        return True, [f"改动全部是缓存/生成物（{len(files)} 个）——通常不需要提交"]
    noise = [f for f in files if is_noise(f)]
    if noise:
        msgs.append(f"其中 {len(noise)} 个是缓存/生成物，建议不要提交")
    return True, msgs


def check_syntax(rel: str) -> str | None:
    """返回错误描述；None 表示通过（或该类型不做语法检查）。"""
    p = ROOT / rel
    if not p.exists():
        return None
    suffix = p.suffix.lower()
    if suffix not in SYNTAX_CHECKABLE:
        return None
    try:
        if suffix == ".py":
            import py_compile
            py_compile.compile(str(p), doraise=True)
        elif suffix == ".json":
            json.loads(p.read_text(encoding="utf-8"))
        elif suffix in (".yaml", ".yml"):
            import yaml
            yaml.safe_load(p.read_text(encoding="utf-8"))
        elif suffix == ".sh":
            r = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True, timeout=20)
            if r.returncode != 0:
                return (r.stderr or "").strip().splitlines()[-1] if r.stderr else "bash -n 失败"
    except Exception as exc:
        return f"{type(exc).__name__}: {str(exc)[:160]}"
    return None


def check_format(rel: str) -> list[str]:
    """基础格式：行尾空白 / tab 混用 / 末尾缺换行（只对文本文件）。"""
    p = ROOT / rel
    if not p.exists() or is_noise(rel):
        return []
    if p.suffix.lower() not in (".py", ".md", ".json", ".yaml", ".yml", ".sh", ".txt"):
        return []
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    issues: list[str] = []
    lines = text.split("\n")
    trailing = [i + 1 for i, l in enumerate(lines) if l != l.rstrip()]
    if trailing:
        issues.append(f"行尾空白 {len(trailing)} 处（如第 {trailing[0]} 行）")
    if text and not text.endswith("\n"):
        issues.append("文件末尾缺换行")
    if "\t" in text and "    " in text:
        issues.append("tab 与空格混用")
    return issues


def run(staged_only: bool = False) -> int:
    files = changed_files(staged_only)
    print(f"📋 pre-commit 轻量检查（改动 {len(files)} 个文件）\n")

    # 1. 必要性（阻断）
    ok_nec, nec_msgs = check_necessity(files)
    print(f"[1] 必要性  {'✅' if ok_nec else '❌'}")
    for m in nec_msgs:
        print(f"    {m}")
    if not ok_nec:
        print("\n❌ 阻断：没有可提交的内容")
        return 1

    # 2. 语法（阻断）
    syn_errors = [(f, e) for f in files if (e := check_syntax(f))]
    print(f"\n[2] 语法    {'✅' if not syn_errors else '❌'}")
    for f, e in syn_errors:
        print(f"    {f}: {e}")

    # 3. 格式（不阻断，只提示）
    fmt = [(f, issues) for f in files if (issues := check_format(f))]
    print(f"\n[3] 格式    {'✅' if not fmt else '⚠️'}")
    for f, issues in fmt:
        print(f"    {f}: {'; '.join(issues)}")

    if syn_errors:
        print(f"\n❌ 阻断提交：{len(syn_errors)} 个文件语法错误")
        return 1
    print(f"\n✅ lx-pre-commit 通过（语法 ✅ / 格式 {'⚠️ ' + str(len(fmt)) + ' 处提示' if fmt else '✅'}）")
    return 0


def main() -> int:
    return run(staged_only="--staged" in sys.argv)


if __name__ == "__main__":
    sys.exit(main())
