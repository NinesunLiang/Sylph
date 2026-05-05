#!/usr/bin/env python3

"""

validate_skill.py — 验证 skill 目录结构是否符合三层规范（v6.0.1）

用法：python3 validate_skill.py --skill lx-{name} [--skills-dir .claude/skills]

exit: 0=通过, 2=有违规

"""

import argparse, sys, json

from pathlib import Path


REQUIRED_FIELDS = ["name", "version", "description", "when_to_use", "harness_version"]


def check(skill_dir: Path):
    violations = []
    warnings = []

    # 1. SKILL.md 存在
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        violations.append("SKILL.md 不存在")
        return violations, warnings

    content = skill_md.read_text(encoding="utf-8")

    # 2. frontmatter 字段
    for field in REQUIRED_FIELDS:
        if f"{field}:" not in content:
            violations.append(f"缺少 frontmatter 字段: {field}")

    # 3. 原子化声明
    if "## 原子化声明" not in content and "原子化声明" not in content:
        violations.append("缺少「原子化声明」区块")

    # 4. 降级策略
    if "## 降级策略" not in content:
        violations.append("缺少「降级策略」章节")

    # 5. 不含私有 nodes/ schemas/
    for bad in ["nodes/", "schemas/"]:
        if (skill_dir / bad).exists():
            violations.append(f"包含私有 {bad} 目录（违反 R1/R2）")

    # 6. scripts/*.py 如存在，必须有 exit code 处理
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        for py in scripts_dir.glob("*.py"):
            code = py.read_text(encoding="utf-8")
            if "sys.exit" not in code:
                warnings.append(f"scripts/{py.name} 缺少 sys.exit（建议加退出码）")

    # 7. docs/ 不应存在（应改为 references/）
    if (skill_dir / "docs").exists():
        violations.append("存在 docs/ 目录，应迁移到 references/（违反规范）")

    # 8. SKILL.md 行数警告（超过 300 行提示精简）
    lines = len(content.split('\n'))
    if lines > 300:
        warnings.append(f"SKILL.md 共 {lines} 行，建议精简到 300 行以内")

    return violations, warnings


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--skill", required=True)
    p.add_argument("--skills-dir", default=".claude/skills")
    args = p.parse_args()

    skill_dir = Path(args.skills_dir) / args.skill
    if not skill_dir.exists():
        print(json.dumps({"error": f"skill 目录不存在: {skill_dir}"}))
        sys.exit(1)

    violations, warnings = check(skill_dir)
    passed = len(violations) == 0

    print(json.dumps({
        "skill": args.skill,
        "passed": passed,
        "violations": violations,
        "warnings": warnings,
    }, ensure_ascii=False, indent=2))

    sys.exit(0 if passed else 2)


if __name__ == "__main__":
    main()
