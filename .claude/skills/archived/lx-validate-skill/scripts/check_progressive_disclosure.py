#!/usr/bin/env python3

"""

check_progressive_disclosure.py — 验证 skill 是否符合渐进式披露原则

规则：

 R-PD-1: references/ 加载必须在路由分支内，不得出现在 ## 顶级章节作为静态引用

 R-PD-2: scripts/ 调用必须有明确触发条件（if/when/路由分支），不得只出现在表格声明里

 R-PD-3: SKILL.md 底部不得有纯静态的 "加载 @references/xxx" 章节堆叠

 R-PD-4: 每个 reference 加载点必须有路由条件前置（命令/阶段/Gate/条件）


用法：
 python3 check_progressive_disclosure.py --skill lx-rpe --skills-dir .claude/skills
 python3 check_progressive_disclosure.py --all --skills-dir .claude/skills

exit: 0=通过, 2=有违规
"""
import argparse, sys, json, re
from pathlib import Path


def check_skill(skill_dir: Path):
    violations = []
    warnings = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return [f"SKILL.md 不存在"], []

    content = skill_md.read_text(encoding="utf-8")
    lines = content.split("\n")

    # ─── R-PD-1: 检测静态 reference 堆叠 ────────────────────────
    # 特征：连续多个 ## 章节，每个章节体只有一行 "加载 @references/xxx"
    static_load_sections = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("## ") and i + 1 < len(lines):
            # 检查后面几行是否只有加载语句
            body_lines = []
            j = i + 1
            while j < len(lines) and not lines[j].startswith("## "):
                if lines[j].strip():
                    body_lines.append(lines[j].strip())
                j += 1
            # 如果章节体只有1-2行且都是加载引用
            if 1 <= len(body_lines) <= 2:
                load_lines = [
                    l for l in body_lines
                    if "@references/" in l or ("加载" in l and "references" in l)
                ]
                if len(load_lines) == len(body_lines):
                    static_load_sections.append((i + 1, lines[i].strip()))
        i += 1

    if len(static_load_sections) >= 3:
        violations.append(
            f"R-PD-1: 发现 {len(static_load_sections)} 个静态 reference 章节堆叠（应移入路由分支）："
            + ", ".join(f"L{l}:{t[:30]}" for l, t in static_load_sections[:5])
        )

    # ─── R-PD-2: reference 加载有无前置路由条件 ────────────────
    load_pattern = re.compile(r"@references/(\S+)")
    for i, line in enumerate(lines):
        if "@references/" in line:
            # 检查前8行 + 当前行 是否有路由条件关键词
            context_before = "\n".join(lines[max(0, i - 8): i])
            ROUTE_KEYWORDS = [
                "Go 项目", "前端项目", "Gate-", "Step ", "Phase ", "status", "new", "batch",
                "命中", "触发", "if ", "when", "子命令", "路由", "条件", "→",
                "按项目类型", "路由命中", "触发条件", "进入时", "请求时", "初始化时",
                "时：", "时,",
            ]
            has_route = (
                any(kw in context_before for kw in ROUTE_KEYWORDS)
                or any(kw in line for kw in ROUTE_KEYWORDS)
            )
            # 仅当前面只有 ## 章节标题（无任何正文）且无路由条件时才警告
            prev_meaningful = [
                l for l in lines[max(0, i - 3): i]
                if l.strip() and not l.startswith("#")
            ]
            if not has_route and not prev_meaningful:
                matched = load_pattern.search(line)
                ref_name = matched.group(1) if matched else "?"
                warnings.append(
                    f"R-PD-2: L{i + 1} 加载 {ref_name} "
                    f"缺少前置路由条件"
                )

    # ─── R-PD-3: scripts 调用是否有明确触发 ────────────────────
    script_calls = [
        (i + 1, line) for i, line in enumerate(lines)
        if "python3" in line and "scripts/" in line
    ]
    for lineno, line in script_calls:
        # 检查前10行是否有路由/步骤/条件
        context = "\n".join(lines[max(0, lineno - 10): lineno])
        has_trigger = any(
            kw in context for kw in [
                "Step ", "Gate", "→", "执行", "调用", "if ", "when", "命中", "路由", "子命令",
            ]
        )
        if not has_trigger:
            warnings.append(f"R-PD-3: L{lineno} script 调用缺少触发上下文")

    # ─── R-PD-4: 检查 scripts 是否只在表格声明，未在流程中调用 ──
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        for py_file in scripts_dir.glob("*.py"):
            script_name = py_file.name
            # 在 SKILL.md 中查找实际调用（python3 命令）
            actual_calls = [
                l for l in lines
                if "python3" in l and script_name.replace(".py", "") in l
            ]
            # 只在表格中提及，没有实际调用
            table_mentions = [l for l in lines if script_name in l and "|" in l]
            if table_mentions and not actual_calls:
                warnings.append(
                    f"R-PD-4: {script_name} 只在声明表格出现，"
                    f"未找到实际 python3 调用（应在路由分支中明确调用）"
                )

    return violations, warnings


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--skill", help="单个 skill 名称")
    p.add_argument("--all", action="store_true", help="检查所有 skill")
    p.add_argument("--skills-dir", default=".claude/skills")
    p.add_argument("--strict", action="store_true", help="warnings 也算违规")
    args = p.parse_args()

    skills_dir = Path(args.skills_dir)
    skills_to_check = []
    if args.all:
        skills_to_check = [d for d in sorted(skills_dir.glob("lx-*")) if d.is_dir()]
    elif args.skill:
        d = skills_dir / args.skill
        if not d.exists():
            print(json.dumps({"error": f"skill 不存在: {d}"}))
            sys.exit(1)
        skills_to_check = [d]
    else:
        print(json.dumps({"error": "需要 --skill 或 --all"}))
        sys.exit(1)

    results = []
    total_violations = 0
    total_warnings = 0

    for skill_dir in skills_to_check:
        v, w = check_skill(skill_dir)
        passed = len(v) == 0 and (len(w) == 0 if args.strict else True)
        results.append({
            "skill": skill_dir.name,
            "passed": passed,
            "violations": v,
            "warnings": w,
        })
        total_violations += len(v)
        total_warnings += len(w)

    output = {
        "total_skills": len(skills_to_check),
        "total_violations": total_violations,
        "total_warnings": total_warnings,
        "passed": total_violations == 0,
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if total_violations == 0 else 2)


if __name__ == "__main__":
    main()
