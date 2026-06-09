#!/usr/bin/env python3
"""doc-sync-check.py — 文档-代码一致性全量校验 v2.0

覆盖范围:
  - [已验证: path:line] 交叉引用完整性
  - 裸 file:line 引用验证
  - 数值声明 vs 实际计数（hook/skill 数量）
  - 营销文档中的技术断言检测
  - hooks-table / skills-catalog 与磁盘一致性

Usage:
  python3 .claude/scripts/doc-sync-check.py                  # 默认: 全部检查
  python3 .claude/scripts/doc-sync-check.py --check-refs     # 仅交叉引用
  python3 .claude/scripts/doc-sync-check.py --check-counts   # 仅数值声明
  python3 .claude/scripts/doc-sync-check.py --check-marketing # 仅营销断言
  python3 .claude/scripts/doc-sync-check.py --check-tables   # 仅 table 一致性
  python3 .claude/scripts/doc-sync-check.py --verbose        # 详细输出
  python3 .claude/scripts/doc-sync-check.py --json           # JSON 输出

注意: 本脚本始终 exit 0（符合 kernel.md Hook 铁律）。问题数量通过 stdout 报告。
"""
import sys
import re
import json
import tempfile
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ISSUES = 0
WARNINGS = 0
VERBOSE = False
JSON_OUT = False
ISSUE_LOG_FILE = Path(tempfile.mktemp(prefix="doc-sync-issues-", suffix=".txt"))

# 检查模式
DO_REFS = True
DO_COUNTS = True
DO_MARKETING = True
DO_TABLES = True

# 解析参数
for arg in sys.argv[1:]:
    if arg == "--check-refs":
        DO_REFS = True; DO_COUNTS = False; DO_MARKETING = False; DO_TABLES = False
    elif arg == "--check-counts":
        DO_REFS = False; DO_COUNTS = True; DO_MARKETING = False; DO_TABLES = False
    elif arg == "--check-marketing":
        DO_REFS = False; DO_COUNTS = False; DO_MARKETING = True; DO_TABLES = False
    elif arg == "--check-tables":
        DO_REFS = False; DO_COUNTS = False; DO_MARKETING = False; DO_TABLES = True
    elif arg == "--verbose":
        VERBOSE = True
    elif arg == "--json":
        JSON_OUT = True


def log_issue(severity, category, msg):
    global ISSUES, WARNINGS
    with ISSUE_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{severity}: [{category}] {msg}\n")
    if severity == "error":
        ISSUES += 1
    else:
        WARNINGS += 1


# ─────────────────────────────────────────────────────
# Check 1: 交叉引用完整性
# ─────────────────────────────────────────────────────
def check_cross_refs():
    ref_count = 0
    valid_count = 0
    broken_count = 0
    warn_count_local = 0

    search_dirs = [
        ROOT / "docs",
        ROOT / ".claude/reference",
        ROOT / ".claude",
    ]

    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue

        for md_file in search_dir.rglob("*.md"):
            text = md_file.read_text(encoding="utf-8")
            # Find [已验证: ...] patterns
            for m in re.finditer(r'\[已验证:\s*([^\]]*)\]', text):
                ref_count += 1
                verified_content = m.group(1).strip()
                if not verified_content:
                    continue

                # Try to extract path:line
                ref_line = ""
                ref_path = verified_content

                if ":" in verified_content:
                    line_m = re.findall(r':(\d+)', verified_content)
                    if line_m:
                        ref_line = line_m[-1]
                    # Strip line number and trailing non-path content
                    ref_path = re.sub(r':\d+-\d+$', '', verified_content)
                    ref_path = re.sub(r':\d+$', '', ref_path)
                    # Strip trailing whitespace+extra content
                    clean = re.sub(r'\s.*$', '', ref_path)
                    if re.search(r'\.(md|sh|yaml|json|py|txt|ts|js|go|html|css)$', clean):
                        ref_path = clean
                else:
                    ref_line = ""

                ref_path = ref_path.strip()

                # Skip non-file-path references
                if ref_path in ("所有文件", "") or re.match(r'^战区', ref_path):
                    continue
                if ref_path in ("file", "path", "...", "some_file", "some_dir", "example", "test", "TODO", "REF", "N/A"):
                    continue
                if ".git" in ref_path:
                    continue

                # Skip if no known extension or known directory prefix
                if not re.search(r'\.(md|sh|yaml|json|py|txt|ts|js|go|html|css)$|^\.claude/|^docs/|^source/|^packages/|^scripts/|^rpe/|\.omc/', ref_path):
                    if VERBOSE:
                        print(f"  ~ {ref_path} (跳过 — 不含已知路径特征)")
                    continue

                # Resolve path
                if ref_path.startswith("/"):
                    target = Path(ref_path)
                else:
                    target = ROOT / ref_path

                if not target.exists():
                    broken_count += 1
                    log_issue("error", "ref", f"断链: {ref_path} (引用于 {md_file})")
                else:
                    valid_count += 1
                    if VERBOSE:
                        print(f"  ✓ {ref_path} ({md_file})")

                    # Verify line number if specified
                    if ref_line and target.is_file():
                        total_lines = len(target.read_text(encoding="utf-8").splitlines())
                        if int(ref_line) > total_lines:
                            log_issue("warning", "ref", f"行号偏移: {ref_path}:{ref_line} 超出文件 ({total_lines} 行) (引用于 {md_file})")
                            warn_count_local += 1

    print(f"  [交叉引用] 总计: {ref_count}, 有效: {valid_count}, 失效: {broken_count}, 警告: {warn_count_local}")
    return broken_count


# ─────────────────────────────────────────────────────
# Check 2: 数值声明验证
# ─────────────────────────────────────────────────────
def check_numeric_claims():
    count_issues = 0

    # 2a: Hook 数量声明
    hook_dir = ROOT / ".claude/hooks"
    actual_hooks = len(list(hook_dir.glob("*.sh")))
    hooks_minus_lib = max(actual_hooks - 1, 0)

    claude_md = ROOT / "CLAUDE.md"
    if claude_md.is_file():
        claude_text = claude_md.read_text(encoding="utf-8")
        claude_claim = re.search(r'(\d+)\s+个\s+hook', claude_text)
        if claude_claim:
            print(f"  CLAUDE.md 声称: {claude_claim.group(0)}")
            print(f"  实际 .sh 文件: {actual_hooks} (排除共享库: {hooks_minus_lib})")

        # Check "38 个 hook 默认激活"
        if "38 个 hook 默认激活" in claude_text:
            harness_yaml = ROOT / ".claude/harness.yaml"
            if harness_yaml.is_file():
                harness_text = harness_yaml.read_text(encoding="utf-8")
                actual_enabled = len(re.findall(r'^\s*[a-z_]+:\s*true\s*$', harness_text, re.MULTILINE))
                log_issue("warning", "count", f"CLAUDE.md 声称 38 个激活 hook，harness.yaml 实际 ~{actual_enabled} 个 true 值 (含 sub-feature toggles)")
                count_issues += 1

    # Check source mirror CLAUDE.md
    source_claude = ROOT / "source/harness-kit/CLAUDE.md"
    if source_claude.is_file():
        if "38 个 hook 默认激活" in source_claude.read_text(encoding="utf-8"):
            log_issue("warning", "count", "source/harness-kit/CLAUDE.md 同样声称 38 个激活 hook — 与 root 同源漂移")
            count_issues += 1

    # 2b: hooks-table 数量声明
    hooks_table = ROOT / ".claude/reference/hooks-table.md"
    if hooks_table.is_file():
        table_text = hooks_table.read_text(encoding="utf-8")
        if "共 40 个" in table_text:
            table_entries = len(re.findall(r'^\|`[a-z]', table_text, re.MULTILINE))
            log_issue("warning", "count", f"hooks-table.md 声称 40 个，实际表格条目约 {table_entries} 个")
            count_issues += 1

    # 2c: Skill 数量声明
    skills_dir = ROOT / ".claude/skills"
    actual_skills = len(list(skills_dir.rglob("SKILL.md"))) if skills_dir.is_dir() else 0

    cn_catalog = ROOT / "docs/guides/cn/skills-catalog.md"
    if cn_catalog.is_file():
        cn_text = cn_catalog.read_text(encoding="utf-8")
        cn_claims = re.findall(r'(\d+)\s+个\s*(?:Skill|lx-|)', cn_text)
        if cn_claims:
            print(f"  skills-catalog CN 声称: {cn_claims}")
            print(f"  实际 SKILL.md: {actual_skills}")
            if not any(str(actual_skills) in c for c in cn_claims):
                log_issue("error", "count", f"skills-catalog.md (CN) 声明的 skill 数量与磁盘 ({actual_skills}) 不符")
                count_issues += 1

    us_catalog = ROOT / "docs/guides/us/skills-catalog.md"
    if us_catalog.is_file():
        us_text = us_catalog.read_text(encoding="utf-8")
        us_claim = re.search(r'(\d+)\s+lx-\s+skills', us_text)
        if us_claim:
            print(f"  skills-catalog US 声称: {us_claim.group(0)}")
            print(f"  实际 SKILL.md: {actual_skills}")
            if str(actual_skills) not in us_claim.group(0):
                log_issue("error", "count", f"skills-catalog.md (US) 声明的 skill 数量与磁盘 ({actual_skills}) 不符")
                count_issues += 1

    # 2d: feature-registry 重复条目检测
    feat_reg = ROOT / ".claude/feature-registry.yaml"
    if feat_reg.is_file():
        reg_text = feat_reg.read_text(encoding="utf-8")
        registry_hooks = len(re.findall(r'^\s*- name:', reg_text, re.MULTILINE))
        print(f"  feature-registry.yaml 总条目: {registry_hooks} (实际唯一 hook/skill 应约 68)")
        if registry_hooks > 100:
            log_issue("error", "count", f"feature-registry.yaml 条目数 ({registry_hooks}) 异常膨胀 — 疑似 snake_case/kebab-case 重复")
            count_issues += 1

    print(f"  [数值声明] 发现问题: {count_issues}")
    return count_issues


# ─────────────────────────────────────────────────────
# Check 3: 营销文档技术断言
# ─────────────────────────────────────────────────────
def check_marketing_claims():
    marketing_dir = ROOT / "docs/marketing"
    marketing_issues = 0

    if not marketing_dir.is_dir():
        print("  [营销断言] 无营销文档目录")
        return 0

    for md_file in marketing_dir.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            # Find numeric claims
            if re.search(r'\d+\.\d+%|\d{2,}%|减少.*\d+|提升.*\d+|节省.*\d+|\d+\s*倍', line):
                # Check context for source reference
                start = max(0, i - 3)
                end = min(len(lines), i + 2)
                context = "\n".join(lines[start:end])
                if not re.search(r'\[已验证:|file:line|来源:|source:|http', context):
                    # Skip dates/version numbers
                    if re.search(r'202[0-9]|#[0-9]+|\d+\.\d+\.\d+|v\d+\.\d+|第\d+|^\d+年|^\d+\.', line):
                        continue
                    log_issue("warning", "marketing", f"营销文档无来源数字: {md_file}:{i} — 建议添加来源标注")
                    marketing_issues += 1

    print(f"  [营销断言] 可疑数字声明: {marketing_issues}")
    return marketing_issues


# ─────────────────────────────────────────────────────
# Check 4: Hooks/Skills Table 一致性
# ─────────────────────────────────────────────────────
def check_table_consistency():
    table_issues = 0

    # 4a: hooks-table.md 中列出的 hook 是否都有对应 .sh 文件
    hooks_table = ROOT / ".claude/reference/hooks-table.md"
    if hooks_table.is_file():
        table_text = hooks_table.read_text(encoding="utf-8")
        listed_hooks = set(re.findall(r'[a-z][-a-z]+\.sh', table_text))

        missing_on_disk = 0
        extra_on_disk = 0

        for hook_name in listed_hooks:
            if not (ROOT / f".claude/hooks/{hook_name}").is_file():
                log_issue("error", "table", f"hooks-table 引用但磁盘缺失: {hook_name}")
                missing_on_disk += 1

        disk_hooks = set(p.name for p in (ROOT / ".claude/hooks").glob("*.sh") if p.name != "harness_config.sh")
        for disk_hook in disk_hooks:
            if disk_hook not in listed_hooks:
                log_issue("warning", "table", f"磁盘存在但 hooks-table 缺失: {disk_hook}")
                extra_on_disk += 1

        print(f"  hooks-table: 缺失于磁盘={missing_on_disk}, 缺失于文档={extra_on_disk}")
        table_issues += missing_on_disk + extra_on_disk

    # 4b: skills-catalog 中列出的 skill 是否都有对应 SKILL.md
    for catalog in [ROOT / "docs/guides/cn/skills-catalog.md", ROOT / "docs/guides/us/skills-catalog.md"]:
        if not catalog.is_file():
            continue
        catalog_label = f"{catalog.parent.name}/{catalog.name}"
        catalog_text = catalog.read_text(encoding="utf-8")
        catalog_skills = set(re.findall(r'`/lx-([a-z][-a-z]*)`', catalog_text))

        skills_dirs = ROOT / ".claude/skills"
        if skills_dirs.is_dir():
            disk_skills = set(p.parent.name for p in skills_dirs.rglob("SKILL.md"))
        else:
            disk_skills = set()

        missing_in_catalog = 0
        for skill_name in disk_skills:
            if skill_name not in catalog_skills:
                log_issue("warning", "table", f"{catalog_label} 缺失: {skill_name}")
                missing_in_catalog += 1

        print(f"  {catalog_label}: 缺失 skill={missing_in_catalog}")
        table_issues += missing_in_catalog

    print(f"  [Table 一致性] 发现问题: {table_issues}")
    return table_issues


# ─────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────
def main():
    global ISSUES, WARNINGS
    print("=== doc-sync-check v2.0 ===")
    print()

    total_issues = 0

    if DO_REFS:
        total_issues += check_cross_refs()
        print()

    if DO_COUNTS:
        total_issues += check_numeric_claims()
        print()

    if DO_MARKETING:
        total_issues += check_marketing_claims()
        print()

    if DO_TABLES:
        total_issues += check_table_consistency()
        print()

    # 汇总报告
    print("════════════════════════════════════════════")
    if total_issues == 0 and WARNINGS == 0:
        print("✅ doc-sync-check: 全部通过")
    elif total_issues == 0:
        print(f"⚠️  doc-sync-check: {WARNINGS} 个警告 (无错误)")
    else:
        print(f"❌ doc-sync-check: {total_issues} 个错误, {WARNINGS} 个警告")
    print("════════════════════════════════════════════")

    # 输出详细问题列表
    if total_issues > 0 or WARNINGS > 0:
        print()
        print("--- 问题明细 ---")
        if ISSUE_LOG_FILE.is_file():
            issues_text = ISSUE_LOG_FILE.read_text(encoding="utf-8")
            for line in sorted(issues_text.splitlines()):
                if line.strip():
                    print(f"  {line}")

    # 清理临时文件
    ISSUE_LOG_FILE.unlink(missing_ok=True)

    # JSON 输出模式
    if JSON_OUT:
        print()
        print(json.dumps({
            "errors": total_issues,
            "warnings": WARNINGS,
            "checks": {
                "cross_refs": DO_REFS,
                "numeric_claims": DO_COUNTS,
                "marketing": DO_MARKETING,
                "table_consistency": DO_TABLES
            }
        }, indent=2, ensure_ascii=False))


main()
sys.exit(0)
