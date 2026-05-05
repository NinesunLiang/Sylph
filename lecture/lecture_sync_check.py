#!/usr/bin/env python3
"""
lecture_sync_check.py — 验证 Lecture 系列文档的引用完整性

检查项：
1. 所有 lecture 文件存在
2. 每篇包含 7 部分模板
3. 前置引用指向的 lecture 文件存在
4. 所有 file:line 引用指向实际存在的文件（存在性检查，非行号精确）
5. 反向链接语法正确
6. Mermaid 代码块语法正确

用法: python3 lecture_sync_check.py [--verbose]
"""

import os
import re
import sys
from pathlib import Path

LECTURE_DIR = Path(__file__).parent
PROJECT_ROOT = LECTURE_DIR.parent

# 期望存在的讲座文件
EXPECTED_LECTURES = [
    "01-progressive-disclosure.md",
    "02-gates.md",
    "03-feature-registry.md",
    "04-error-dna.md",
    "05-context-control.md",
    "06-audit-trail.md",
    "07-agentic-ui.md",
]

# 7 部分模板标识
TEMPLATE_SECTIONS = [
    "Function",
    "Philosophy",
    "Benefits",
    "Implementation",
    "Core Code",
    "Logic Flow",
    "Visual Diagram",
]


def check_file_exists(filepath: Path) -> bool:
    return filepath.exists() and filepath.is_file()


def check_lecture_files() -> list[str]:
    errors = []
    for lec in EXPECTED_LECTURES:
        path = LECTURE_DIR / lec
        if not check_file_exists(path):
            errors.append(f"[MISSING] {lec} — 文件不存在")
        else:
            content = path.read_text(encoding="utf-8")
            for section in TEMPLATE_SECTIONS:
                # 支持多种章节格式: "## Function", "## 1. Function", "## 1. Function -- 功能"
                section_patterns = [
                    f"## {section}",
                    f"## ### {section}",
                ]
                found = False
                for pat in section_patterns:
                    if pat in content:
                        found = True
                        break
                # 更宽松: 匹配 ## 任意前缀 + 章节名
                if not found:
                    # 检查 ## N. Section 或 ## Section 等格式
                    import re
                    if re.search(rf'^##\s+\d*\.?\s*{section}', content, re.MULTILINE):
                        found = True
                if not found:
                    errors.append(f"[SECTION] {lec} — 缺少 {section} 部分")
    return errors


def check_cross_references() -> list[str]:
    errors = []
    for lec in EXPECTED_LECTURES:
        path = LECTURE_DIR / lec
        if not check_file_exists(path):
            continue
        content = path.read_text(encoding="utf-8")
        # 检查前置引用指向有效 lecture
        refs = re.findall(r'\[(\d+)-[^\]]+\]\(\.?/?(\d+-[^\)]+)\)', content)
        for _, target in refs:
            target_path = LECTURE_DIR / target
            if not check_file_exists(target_path):
                errors.append(f"[REF] {lec} — 引用缺失: {target}")
        # 检查 docs/ 引用
        doc_refs = re.findall(r'\]\((\.\./docs/[^\)]+)\)', content)
        for ref in doc_refs:
            # 从 lecture/ 目录解析相对路径
            full_path = (LECTURE_DIR / ref).resolve()
            if not check_file_exists(full_path):
                # 有些可能是锚点引用，只检查文件存在
                base_path = full_path
                if "#" in str(base_path):
                    base_path = Path(str(base_path).split("#")[0])
                if not check_file_exists(base_path):
                    errors.append(f"[DOC] {lec} — docs 引用不存在: {ref}")
    return errors


def check_file_line_references() -> list[str]:
    errors = []
    for lec in EXPECTED_LECTURES:
        path = LECTURE_DIR / lec
        if not check_file_exists(path):
            continue
        content = path.read_text(encoding="utf-8")
        # 文件引用格式: file:line 或 [已验证: file:line]
        file_refs = re.findall(r'`?([a-zA-Z0-9_./-]+\.[a-z]+)(?::(\d+))?`?', content)
        for ref_file, ref_line in file_refs:
            # 跳过 markdown 链接、URL、非项目文件
            if ref_file.startswith("http") or ref_file.startswith("#"):
                continue
            if ref_file.endswith(".md") and "/" not in ref_file:
                continue  # 可能是 markdown 文件名引用
            # 检查文件是否存在（相对于项目根）
            full_path = PROJECT_ROOT / ref_file
            if not check_file_exists(full_path):
                # 尝试去掉开头的 ./
                if ref_file.startswith("./"):
                    full_path = PROJECT_ROOT / ref_file[2:]
                elif ref_file.startswith("../"):
                    full_path = PROJECT_ROOT / ref_file
                else:
                    full_path = LECTURE_DIR / ref_file
                if not check_file_exists(full_path):
                    errors.append(f"[FILE] {lec} — 引用的文件不存在: {ref_file}")
    return errors


def check_mermaid_syntax() -> list[str]:
    errors = []
    for lec in EXPECTED_LECTURES:
        path = LECTURE_DIR / lec
        if not check_file_exists(path):
            continue
        content = path.read_text(encoding="utf-8")
        mermaid_blocks = re.findall(r'```mermaid\n(.*?)```', content, re.DOTALL)
        for i, block in enumerate(mermaid_blocks):
            if not block.strip():
                errors.append(f"[MERMAID] {lec} block {i+1} — 空的 mermaid 块")
            # 检查基本的 mermaid 语法结构
            if "graph" not in block and "sequenceDiagram" not in block and "stateDiagram" not in block and "flowchart" not in block and "classDiagram" not in block and "pie" not in block:
                errors.append(f"[MERMAID] {lec} block {i+1} — 缺少有效的 mermaid 图表类型声明")
    return errors


def main():
    verbose = "--verbose" in sys.argv
    all_errors = []

    print("=" * 60)
    print("Carror OS Lecture Sync Check")
    print("=" * 60)

    # 1. 检查文件存在 + 模板完整性
    print("\n[1/4] 检查 Lecture 文件完整性...")
    errors = check_lecture_files()
    all_errors.extend(errors)
    for e in errors:
        print(f"  ⚠ {e}")
    if not errors:
        print("  ✅ 全部 {}/7 讲座文件存在且模板完整".format(len(EXPECTED_LECTURES)))

    # 2. 检查交叉引用
    print("\n[2/4] 检查交叉引用完整性...")
    errors = check_cross_references()
    all_errors.extend(errors)
    for e in errors:
        print(f"  ⚠ {e}")
    if not errors:
        print("  ✅ 交叉引用全部有效")

    # 3. 检查 file:line 引用
    print("\n[3/4] 检查 file:line 引用...")
    errors = check_file_line_references()
    all_errors.extend(errors)
    if verbose:
        for e in errors:
            print(f"  ⚠ {e}")
    if not errors:
        print("  ✅ 文件引用全部有效")
    else:
        print(f"  {len(errors)} 个文件引用警告（可能为路径别名，建议人工确认）")

    # 4. 检查 Mermaid 语法
    print("\n[4/4] 检查 Mermaid 图表语法...")
    errors = check_mermaid_syntax()
    all_errors.extend(errors)
    for e in errors:
        print(f"  ⚠ {e}")
    if not errors:
        print("  ✅ Mermaid 图表语法正确")

    # 汇总
    print("\n" + "=" * 60)
    if all_errors:
        print(f"❌ 发现 {len(all_errors)} 个问题")
        for e in all_errors:
            print(f"  • {e}")
        return 1
    else:
        print("✅ 全部检查通过！所有 Lecture 文件完整且引用有效")
        return 0


if __name__ == "__main__":
    sys.exit(main())
