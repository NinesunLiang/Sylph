#!/usr/bin/env python3
"""产品依赖闭包审计：lx-goal 最小范围是否真的齐了。

做法（不靠印象）：
  1. 从产品内的 lx-goal 指令层（SKILL.md / references/*.md）抓所有 `.claude/...` 路径引用
  2. 从 lx-goal.py / carros_base.py 抓所有 subprocess 调用的脚本名
  3. 从全部产品 .py 抓 `from X import` / `import X`，判断本地模块能否在产品内解析
  4. 逐项核对产品目录，输出缺失清单

用法：python3 .omc/scripts/audit_product_closure.py
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "packaging" / "products" / "carroros-delivery"

PATH_RE = re.compile(r"\.claude/[A-Za-z0-9_\-./*]+\.(?:py|md|yaml|yml|json)")
SCRIPT_RE = re.compile(r"([A-Za-z0-9_\-]+\.py)")
CMD_RE = re.compile(r"\.claude/(scripts|hooks|skills/[A-Za-z0-9_\-]+/scripts)/([A-Za-z0-9_\-]+\.py)")


def product_files() -> set[str]:
    return {p.relative_to(PRODUCT).as_posix() for p in PRODUCT.rglob("*") if p.is_file()}


def referenced_paths() -> dict[str, set[str]]:
    """谁引用了哪个 .claude 路径。"""
    out: dict[str, set[str]] = {}
    for md in list((PRODUCT / ".claude/skills/lx-goal").rglob("*.md")) + [PRODUCT / "AGENTS.md"]:
        if not md.is_file():
            continue
        for m in PATH_RE.finditer(md.read_text(encoding="utf-8")):
            out.setdefault(m.group(0), set()).add(md.relative_to(PRODUCT).as_posix())
    return out


def code_only(text: str) -> str:
    """去掉注释与 docstring，只留可执行代码 —— 避免把示例文本当成真依赖。"""
    import io
    import tokenize

    try:
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError):
        return text
    drop_lines: set[int] = {t.start[0] for t in toks if t.type == tokenize.COMMENT}

    try:
        tree = ast.parse(text)
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = getattr(node, "body", [])
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    start = body[0].lineno
                    end = getattr(body[0], "end_lineno", start)
                    drop_lines.update(range(start, end + 1))

    kept = [ln for i, ln in enumerate(text.splitlines(), 1) if i not in drop_lines]
    return "\n".join(kept)


def invoked_scripts() -> dict[str, set[str]]:
    """代码里通过 subprocess / 命令行调用的脚本名（忽略注释与 docstring 中的示例）。"""
    out: dict[str, set[str]] = {}
    for py in (PRODUCT / ".claude").rglob("*.py"):
        text = code_only(py.read_text(encoding="utf-8", errors="ignore"))
        for m in CMD_RE.finditer(text):
            rel = f".claude/{m.group(1)}/{m.group(2)}"
            out.setdefault(rel, set()).add(py.relative_to(PRODUCT).as_posix())
    return out


def local_imports() -> dict[str, set[str]]:
    """本地模块 import（顶层名 → 引用它的文件）。"""
    local_mods: set[str] = set()
    for py in (PRODUCT / ".claude").rglob("*.py"):
        local_mods.add(py.stem.split(".")[0])
    out: dict[str, set[str]] = {}
    for py in (PRODUCT / ".claude").rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for n in names:
                if n in local_mods:
                    out.setdefault(n, set()).add(py.relative_to(PRODUCT).as_posix())
    return out


def main() -> int:
    if not PRODUCT.is_dir():
        print(f"❌ 产品目录不存在: {PRODUCT}", file=sys.stderr)
        return 2
    have = product_files()
    problems: list[str] = []

    # 1. 文档引用的路径
    # 已知设计缺口：DECISIONS.md 由人类首次裁决时本机生成（D-031），不随包发行。
    DESIGNED_GAPS = {".claude/decisions/DECISIONS.md"}
    missing_refs = []
    designed = []
    for rel, owners in sorted(referenced_paths().items()):
        if "*" in rel:            # 通配引用不逐个校验
            continue
        if rel not in have:
            if rel in DESIGNED_GAPS:
                designed.append(rel)
                continue
            missing_refs.append((rel, sorted(owners)[:2]))
    if missing_refs:
        problems.append(f"文档引用了产品内缺失的路径 {len(missing_refs)} 个")
        for rel, owners in missing_refs:
            problems.append(f"   - {rel}  ← {owners}")

    # 2. 代码调用的脚本
    missing_scripts = []
    for rel, owners in sorted(invoked_scripts().items()):
        if rel not in have:
            missing_scripts.append((rel, sorted(owners)[:2]))
    if missing_scripts:
        problems.append(f"代码调用了产品内缺失的脚本 {len(missing_scripts)} 个")
        for rel, owners in missing_scripts:
            problems.append(f"   - {rel}  ← {owners}")

    # 3. 本地 import 是否都能解析（同名文件在产品内存在）
    stems = {p.rsplit("/", 1)[-1].removesuffix(".py") for p in have if p.endswith(".py")}
    unresolvable = {n: o for n, o in local_imports().items() if n not in stems}
    if unresolvable:
        problems.append(f"本地 import 无法在产品内解析 {len(unresolvable)} 个")
        for n, owners in sorted(unresolvable.items()):
            problems.append(f"   - {n}  ← {sorted(owners)[:2]}")

    print(f"产品文件数: {len(have)}")
    print(f"文档路径引用: {len(referenced_paths())}（缺失 {len(missing_refs)}，设计缺口 {len(designed)}）")
    print(f"代码脚本调用: {len(invoked_scripts())}（缺失 {len(missing_scripts)}）")
    print(f"本地模块 import: {len(local_imports())}（无法解析 {len(unresolvable)}）")
    if designed:
        print(f"  设计缺口（预期不随包）: {', '.join(designed)}")

    if problems:
        print("\n❌ 闭包不完整:")
        for p in problems:
            print(p)
        return 1
    print("\n✅ 依赖闭包完整：文档引用的路径、代码调用的脚本、本地 import 全部在产品内可解析")
    return 0


if __name__ == "__main__":
    sys.exit(main())
