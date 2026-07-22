#!/usr/bin/env python3
"""
verify_and_register.py — 技能验证 + 注册

用于 skillify Phase 4-5 的确定性操作：
  1. 调用 validate-skill.sh 检查 11 条规则
  2. 调用 validate_skill_refs.py 检查引用完整性
  3. 通过后追加 feature-registry.yaml
  4. 通过后追加 skills-catalog.md

用法:
  python3 verify_and_register.py --skill-name <name> [--skip-register] [--dry-run]
"""

import sys
import os
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


def get_project_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent.parent.parent.parent  # scripts/lx-skillify/scripts -> project root


PROJECT_ROOT = get_project_root()
SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills"
SCRIPTS_DIR = PROJECT_ROOT / ".claude" / "scripts"
FEATURE_REGISTRY = PROJECT_ROOT / ".claude" / "feature-registry.yaml"
SKILLS_CATALOG = PROJECT_ROOT / "docs" / "guides" / "cn" / "skills-catalog.md"


def run_validation(skill_name: str) -> dict:
    """运行 validate-skill.sh 并解析结果。"""
    validate_script = SCRIPTS_DIR / "validate-skill.sh"

    if not validate_script.exists():
        return {
            "passed": False,
            "error": f"验证脚本不存在: {validate_script}",
            "violations": [],
            "warnings": []
        }

    try:
        result = subprocess.run(
            ["bash", str(validate_script), skill_name],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT)
        )

        output = result.stdout + result.stderr
        passed = result.returncode == 0

        # 提取违规和警告
        violations = []
        warnings = []
        for line in output.split('\n'):
            if '❌' in line or 'FAIL' in line.upper() or 'violation' in line.lower():
                violations.append(line.strip())
            elif '⚠️' in line or 'WARNING' in line.upper() or 'warning' in line.lower():
                warnings.append(line.strip())

        return {
            "passed": passed,
            "exit_code": result.returncode,
            "output": output[:2000],
            "violations": violations[:20],
            "warnings": warnings[:20]
        }
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "error": "验证超时（30秒）",
            "violations": [],
            "warnings": []
        }
    except Exception as e:
        return {
            "passed": False,
            "error": str(e),
            "violations": [],
            "warnings": []
        }


def run_ref_check() -> dict:
    """运行 validate_skill_refs.py 检查引用完整性。"""
    ref_script = SCRIPTS_DIR / "validate_skill_refs.py"

    if not ref_script.exists():
        return {
            "passed": True,
            "skipped": True,
            "message": "validate_skill_refs.py 不存在，跳过引用检查"
        }

    try:
        result = subprocess.run(
            ["python3", str(ref_script)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT)
        )
        return {
            "passed": result.returncode == 0,
            "exit_code": result.returncode,
            "output": result.stdout[:2000]
        }
    except Exception as e:
        return {
            "passed": False,
            "error": str(e)
        }


def determine_skill_type(skill_name: str) -> str:
    """基于名称推断技能类型。"""
    name_lower = skill_name.lower()
    if any(kw in name_lower for kw in ['review', 'scan', 'audit', 'check', 'lint']):
        return 'reviewer'
    if any(kw in name_lower for kw in ['test', 'spec', 'gen', 'generator']):
        return 'tester'
    if any(kw in name_lower for kw in ['commit', 'push', 'gate', 'guard']):
        return 'gate'
    if any(kw in name_lower for kw in ['orch', 'sync', 'fix', 'repair', 'workflow', 'pipeline']):
        return 'orchestrator'
    return 'workflow'


def determine_category(skill_name: str) -> str:
    """基于名称推断技能分类。"""
    name_lower = skill_name.lower()
    if any(kw in name_lower for kw in ['review', 'scan', 'audit', 'lint']):
        return 'quality'
    if any(kw in name_lower for kw in ['security', 'varlock', 'privacy']):
        return 'security'
    if any(kw in name_lower for kw in ['test', 'spec', 'tdd']):
        return 'test'
    if any(kw in name_lower for kw in ['debug', 'trace', 'root-cause']):
        return 'debug'
    if any(kw in name_lower for kw in ['commit', 'push', 'gate', 'guard', 'pre-']):
        return 'infrastructure'
    return 'automation'


def update_registry(skill_name: str, description: str, dry_run: bool = False) -> dict:
    """更新 feature-registry.yaml。"""
    if not FEATURE_REGISTRY.exists():
        return {
            "updated": False,
            "error": f"feature-registry.yaml 不存在: {FEATURE_REGISTRY}"
        }

    skill_type = determine_skill_type(skill_name)
    category = determine_category(skill_name)

    entry = (
        f"\n  - name: lx-{skill_name}\n"
        f"    type: {skill_type}\n"
        f"    category: {category}\n"
        f'    description: "{description[:80]}"\n'
        f"    enabled_by_default: true"
    )

    if dry_run:
        return {
            "updated": False,
            "dry_run": True,
            "entry": entry,
            "message": f"将追加到 {FEATURE_REGISTRY}"
        }

    try:
        content = FEATURE_REGISTRY.read_text(encoding='utf-8')
        # 在 skills: 段末尾追加
        if 'skills:' in content:
            # 找到 skills: 段的最后一条目
            lines = content.split('\n')
            insert_idx = len(lines)
            in_skills = False
            for i, line in enumerate(lines):
                if line.strip() == 'skills:':
                    in_skills = True
                elif in_skills and line.strip() and not line.startswith('  '):
                    insert_idx = i
                    break
            if insert_idx == len(lines):
                # skills 是最后一段
                content = content.rstrip() + entry + '\n'
            else:
                # 在 skills 段末尾插入
                content = '\n'.join(lines[:insert_idx]) + entry + '\n' + '\n'.join(lines[insert_idx:])
        else:
            # 没有 skills 段，追加以创建
            content = content.rstrip() + "\nskills:" + entry + "\n"

        if not dry_run:
            FEATURE_REGISTRY.write_text(content, encoding='utf-8')

        return {
            "updated": True,
            "entry": entry.strip(),
            "message": f"已更新 {FEATURE_REGISTRY}"
        }
    except Exception as e:
        return {
            "updated": False,
            "error": str(e)
        }


def update_catalog(skill_name: str, description: str, dry_run: bool = False) -> dict:
    """更新 skills-catalog.md。"""
    if not SKILLS_CATALOG.exists():
        return {
            "updated": False,
            "error": f"skills-catalog.md 不存在: {SKILLS_CATALOG}"
        }

    entry = f"| `/lx-{skill_name}` | {description[:60]} | `skillify`、`创建 skill` |"

    if dry_run:
        return {
            "updated": False,
            "dry_run": True,
            "entry": entry,
            "message": f"将追加到 {SKILLS_CATALOG}"
        }

    try:
        content = SKILLS_CATALOG.read_text(encoding='utf-8')

        # 查找「技能创建」section，没有则追加到末尾
        if '技能创建' in content:
            # 在「技能创建」section 末尾添加
            lines = content.split('\n')
            insert_idx = len(lines)
            in_section = False
            for i, line in enumerate(lines):
                if '技能创建' in line:
                    in_section = True
                elif in_section and line.startswith('##') and '技能创建' not in line:
                    insert_idx = i
                    break
            content = '\n'.join(lines[:insert_idx]) + '\n' + entry + '\n' + '\n'.join(lines[insert_idx:])
        else:
            # 追加到文件末尾
            content = content.rstrip() + f"\n\n## 技能创建\n\n| 技能 | 一句话 | 触发词 |\n|------|--------|--------|\n{entry}\n"

        if not dry_run:
            SKILLS_CATALOG.write_text(content, encoding='utf-8')

        return {
            "updated": True,
            "entry": entry,
            "message": f"已更新 {SKILLS_CATALOG}"
        }
    except Exception as e:
        return {
            "updated": False,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description="技能验证 + 注册")
    parser.add_argument("--skill-name", required=True, help="技能名称（不含 lx- 前缀）")
    parser.add_argument("--description", default="", help="技能描述")
    parser.add_argument("--skip-register", action="store_true", help="跳过注册，仅验证")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际写入")
    parser.add_argument("--json", action="store_true", help="JSON 输出")

    args = parser.parse_args()
    skill_name = args.skill_name

    report = {
        "skill": f"lx-{skill_name}",
        "timestamp": datetime.now().isoformat(),
        "validation": {},
        "ref_check": {},
        "registry": {},
        "catalog": {}
    }

    # 1. 验证
    report["validation"] = run_validation(skill_name)

    # 2. 引用检查
    if report["validation"].get("passed"):
        report["ref_check"] = run_ref_check()

    # 3. 注册
    if not args.skip_register:
        validation_ok = report["validation"].get("passed", False)
        refs_ok = report["ref_check"].get("passed", True)

        if validation_ok and refs_ok:
            report["registry"] = update_registry(
                skill_name,
                args.description or f"lx-{skill_name} skill",
                dry_run=args.dry_run
            )
            report["catalog"] = update_catalog(
                skill_name,
                args.description or f"lx-{skill_name} skill",
                dry_run=args.dry_run
            )
        else:
            report["registry"] = {
                "updated": False,
                "message": "验证未通过，跳过注册"
            }
            report["catalog"] = {
                "updated": False,
                "message": "验证未通过，跳过目录更新"
            }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"验证: {'✅ 通过' if report['validation'].get('passed') else '❌ 失败'}")
        if report["validation"].get("violations"):
            for v in report["validation"]["violations"][:5]:
                print(f"  - {v}")
        if report["registry"].get("updated"):
            print(f"注册: ✅ feature-registry.yaml 已更新")
        if report["catalog"].get("updated"):
            print(f"目录: ✅ skills-catalog.md 已更新")
        if args.dry_run:
            print("(dry-run 模式，未实际写入)")

    # exit code
    all_ok = report["validation"].get("passed", False)
    sys.exit(0 if all_ok else 1)


if __name__ == '__main__':
    main()
