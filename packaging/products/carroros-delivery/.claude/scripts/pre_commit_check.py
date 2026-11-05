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


def _git(*args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"git {args[0]} failed: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout


def changed_files(staged_only: bool = False) -> list[str]:
    """Include deletions; NUL-separated paths preserve Unicode and whitespace."""
    args = ["diff", "--cached"] if staged_only else ["diff", "HEAD"]
    raw = _git(*args, "--name-only", "-z", "--diff-filter=ACMRD")
    if not staged_only:
        raw += _git("ls-files", "--others", "--exclude-standard", "-z")
    return list(dict.fromkeys(p.decode("utf-8", errors="surrogateescape") for p in raw.split(b"\0") if p))


def _read_content(rel: str, staged_only: bool = False) -> bytes | None:
    if staged_only:
        # A deletion has no stage-0 entry; other Git errors must remain visible.
        entry = _git("ls-files", "--stage", "-z", "--", rel)
        if not entry:
            return None
        return _git("show", f":{rel}")
    path = ROOT / rel
    return path.read_bytes() if path.exists() else None


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


def check_syntax(rel: str, staged_only: bool = False) -> str | None:
    """Parse the selected snapshot without creating bytecode or executing code."""
    suffix = Path(rel).suffix.lower()
    if suffix not in SYNTAX_CHECKABLE:
        return None
    try:
        content = _read_content(rel, staged_only)
        if content is None:
            return None  # Deleted files are meaningful changes, not syntax inputs.
        if suffix == ".py":
            compile(content, rel, "exec", dont_inherit=True)
        elif suffix == ".json":
            json.loads(content)
        elif suffix in (".yaml", ".yml"):
            import yaml
            yaml.safe_load(content)
        elif suffix == ".sh":
            r = subprocess.run(["bash", "-n"], input=content, capture_output=True, timeout=20)
            if r.returncode != 0:
                detail = r.stderr.decode(errors="replace").strip()
                return detail.splitlines()[-1] if detail else "bash -n 失败"
    except Exception as exc:
        return f"{type(exc).__name__}: {str(exc)[:160]}"
    return None


def check_format(rel: str, staged_only: bool = False) -> list[str]:
    """Check formatting in the same snapshot used for syntax checks."""
    if is_noise(rel):
        return []
    if Path(rel).suffix.lower() not in (".py", ".md", ".json", ".yaml", ".yml", ".sh", ".txt"):
        return []
    try:
        content = _read_content(rel, staged_only)
        if content is None:
            return []
        text = content.decode("utf-8")
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
    syn_errors = [(f, e) for f in files if (e := check_syntax(f, staged_only))]
    print(f"\n[2] 语法    {'✅' if not syn_errors else '❌'}")
    for f, e in syn_errors:
        print(f"    {f}: {e}")

    # 3. 格式（不阻断，只提示）
    fmt = [(f, issues) for f in files if (issues := check_format(f, staged_only))]
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
