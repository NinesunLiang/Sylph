#!/usr/bin/env python3
"""
merge-profile.py — base+diff 合并工具 (v6.0, .sh → .py 迁移)
用法:
  python3 .claude/profiles/merge-profile.py go         # 合并 base+go
  python3 .claude/profiles/merge-profile.py node       # 合并 base+node
  python3 .claude/profiles/merge-profile.py python     # 合并 base+python
  python3 .claude/profiles/merge-profile.py rust       # 合并 base+rust
  python3 .claude/profiles/merge-profile.py go --dry-run  # 预览不写文件
  python3 .claude/profiles/merge-profile.py --list     # 列出可用 profile

合并规则:
  1. 从 base/harness.yaml 读取所有通用字段
  2. 用 {lang}/harness.yaml 的字段覆盖（同名 section.key 以 diff 为准）
  3. diff 中的 hooks_enabled 子键做"增量覆盖"（不替换整块，仅覆盖出现的键）
  4. 输出合并后的完整 harness.yaml
"""

import os
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(SCRIPT_DIR, "base", "harness.yaml")
CLAUDE_DIR = os.environ.get("CLAUDE_DIR", ".claude")
OUTPUT = os.path.join(CLAUDE_DIR, "harness.yaml")

SECTION_ORDER = [
    "project",
    "protected_files",
    "architecture",
    "workflow",
    "task_decomposition",
    "knowledge",
    "turn_counter",
    "fuzzy_detection",
    "lsp_suggest",
    "subagent_guard",
    "completion_gate",
    "bash_audit",
    "permission_gate",
    "sublimation",
    "correction_detector",
    "session_handoff",
    "error_dna",
    "coupling",
    "hooks_enabled",
]

# ── ANSI colors ──
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"


def parse_yaml_flat(path: str) -> dict:
    """解析 YAML 为嵌套 dict（支持 2 层 + 列表）"""
    result = {}
    current_section = None
    current_list_key = None
    current_list = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n\r")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                if current_list_key and current_list:
                    if current_section not in result:
                        result[current_section] = {}
                    result[current_section][current_list_key] = current_list[:]
                    current_list_key, current_list = None, []
                continue
            indent = len(line) - len(line.lstrip())
            if stripped.startswith("- "):
                if current_list_key:
                    current_list.append(
                        stripped[2:].strip().strip('"').strip("'")
                    )
                continue
            if current_list_key and current_list:
                if current_section not in result:
                    result[current_section] = {}
                result[current_section][current_list_key] = current_list[:]
                current_list_key, current_list = None, []
            if ":" in stripped:
                colon = stripped.index(":")
                key = stripped[:colon].strip()
                val = stripped[colon + 1 :].strip()
                if val and val[0] in ('"', "'") and val[-1] == val[0]:
                    val = val[1:-1]
                if indent == 0:
                    if val:
                        result[key] = val
                    else:
                        current_section = key
                        if key not in result:
                            result[key] = {}
                elif indent > 0 and current_section:
                    if val:
                        result[current_section][key] = val
                    else:
                        current_list_key = key
                        current_list = []
        if current_list_key and current_list and current_section:
            result[current_section][current_list_key] = current_list[:]
    return result


def merge(base: dict, diff: dict) -> dict:
    merged = {}
    for k, v in base.items():
        if isinstance(v, dict):
            merged[k] = dict(v)
        elif isinstance(v, list):
            merged[k] = list(v)
        else:
            merged[k] = v
    for k, v in diff.items():
        if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
            merged[k] = {**merged[k], **v}
        elif isinstance(v, list):
            merged[k] = list(v)
        else:
            merged[k] = v
    return merged


def val_to_yaml(v, indent=2):
    pad = " " * indent
    if isinstance(v, list):
        return "\n" + "\n".join(f"{pad}- {item}" for item in v)
    if isinstance(v, bool):
        return "true" if v else "false"
    s = str(v)
    special = "#:{}[]&*?|<=>!%@`"
    if any(c in s for c in special):
        return f'"{s}"'
    return s


def to_lines(merged: dict, lang: str) -> str:
    lines = [
        f"# harness-kit harness.yaml — {lang} profile (base+diff merged)",
        f"# 由 merge-profile.py 生成，源文件: profiles/base + profiles/{lang}",
        "# 手动编辑此文件的修改在下次 merge 时会被覆盖",
        "",
    ]
    seen = set()
    for section in SECTION_ORDER:
        if section not in merged:
            continue
        seen.add(section)
        v = merged[section]
        lines.append(f"{section}:")
        if isinstance(v, dict):
            for sk, sv in v.items():
                yv = val_to_yaml(sv)
                if yv.startswith("\n"):
                    lines.append(f"  {sk}:{yv}")
                else:
                    lines.append(f"  {sk}: {yv}")
        else:
            lines.append(f"  {val_to_yaml(v)}")
        lines.append("")
    for section, v in merged.items():
        if section in seen:
            continue
        lines.append(f"{section}:")
        if isinstance(v, dict):
            for sk, sv in v.items():
                yv = val_to_yaml(sv)
                if yv.startswith("\n"):
                    lines.append(f"  {sk}:{yv}")
                else:
                    lines.append(f"  {sk}: {sv}")
        else:
            lines.append(f"  {val_to_yaml(v)}")
        lines.append("")
    return "\n".join(lines)


def list_profiles():
    print("可用 profile：")
    for entry in sorted(os.listdir(SCRIPT_DIR)):
        d = os.path.join(SCRIPT_DIR, entry)
        if not os.path.isdir(d) or entry == "base":
            continue
        if os.path.isfile(os.path.join(d, "harness.yaml")):
            print(f"  {entry}")


def main():
    args = sys.argv[1:]

    if not args or args[0] == "--list":
        list_profiles()
        sys.exit(0)

    lang = args[0]
    dry_run = "--dry-run" in args

    if not lang:
        print(f"{RED}[ERROR]{NC} 请指定语言: go / node / python / rust", file=sys.stderr)
        print("  用法: python3 .claude/profiles/merge-profile.py <lang> [--dry-run]", file=sys.stderr)
        sys.exit(1)

    diff_path = os.path.join(SCRIPT_DIR, lang, "harness.yaml")

    if not os.path.isfile(BASE):
        print(f"{RED}[ERROR]{NC} base/harness.yaml 不存在: {BASE}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(diff_path):
        print(f"{RED}[ERROR]{NC} 未找到 profile: {diff_path}", file=sys.stderr)
        sys.exit(1)

    base_data = parse_yaml_flat(BASE)
    diff_data = parse_yaml_flat(diff_path)
    merged_data = merge(base_data, diff_data)
    merged_yaml = to_lines(merged_data, lang)

    if dry_run:
        print(f"{YELLOW}[DRY-RUN]{NC} 合并结果（不写文件）：")
        print("---")
        print(merged_yaml)
        print("---")
        lines = merged_yaml.count("\n") + 1
        print(f"{GREEN}[INFO]{NC} 合并后 {lines} 行（base 覆盖 + {lang} diff）")
    else:
        os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
        with open(OUTPUT, "w", encoding="utf-8") as f:
            f.write(merged_yaml)
            f.write("\n")
        with open(OUTPUT) as f:
            lines = sum(1 for _ in f)
        print(f"{GREEN}[OK]{NC} 已写入 {OUTPUT}（{lines} 行，base + {lang} diff 合并）")


if __name__ == "__main__":
    main()
