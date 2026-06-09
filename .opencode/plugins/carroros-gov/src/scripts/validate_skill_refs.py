#!/usr/bin/env python3
"""
validate_skill_refs.py — 轻量跨 skill 引用一致性校验

扫描 .claude/skills/*/SKILL.md 的引用表，确认：
1. 「使用的通用节点」表 → @../../nodes/ 引用的文件存在
2. 「引用的通用 Schema」表 → schemas/atomic/ 引用的文件存在

输出格式兼容 harness-smoke 回归框架。
只读校验，不修改任何文件。
"""

import os
import re
import sys
import json

SKILLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.claude', 'skills'))


def find_skill_dirs():
    """Find all .claude/skills/lx-*/ directories."""
    if not os.path.isdir(SKILLS_DIR):
        return []
    return sorted([
        d for d in os.listdir(SKILLS_DIR)
        if d.startswith('lx-') and os.path.isdir(os.path.join(SKILLS_DIR, d))
    ])


def resolve_path(skill_dir, raw_path):
    """
    Resolve a relative reference path from SKILL.md to absolute.
    SKILL.md is at .claude/skills/{name}/SKILL.md
    References use @../../ as relative to SKILL.md location.
    """
    # Strip backticks, @ prefix, whitespace
    path = raw_path.strip().strip('`').strip()
    path = path.lstrip('@')

    # Resolve relative to the SKILL.md location
    skill_md_dir = os.path.join(SKILLS_DIR, skill_dir)
    abs_path = os.path.normpath(os.path.join(skill_md_dir, path))
    return abs_path


def check_ref_table(content, skill_dir, section_keywords, path_pattern, ref_type):
    """Check a reference table in SKILL.md for broken paths.

    Args:
        content: Full SKILL.md content
        skill_dir: Skill directory name (e.g. 'lx-rpe')
        section_keywords: Keywords to detect section header
        path_pattern: Substring required in the reference path
        ref_type: Label for the type (node/schema/task_sys)
    """
    missing = []
    in_section = False
    in_table = False

    for line_num, line in enumerate(content.split('\n'), 1):
        if any(kw in line for kw in section_keywords):
            in_section = True
            continue

        if in_section:
            if line.strip().startswith('|') and '路径' in line and '用途' in line:
                in_table = True
                continue
            if line.startswith('##') or (line.strip() == '' and in_table):
                in_section = False
                in_table = False
                continue

        if in_table and line.strip().startswith('|'):
            parts = line.split('|')
            if len(parts) >= 3:
                cell = parts[2].strip()
                path_match = re.search(r'`([^`]+)`', cell)
                if path_match:
                    ref_path = path_match.group(1)
                    if path_pattern in ref_path:
                        abs_path = resolve_path(skill_dir, ref_path)
                        if not os.path.exists(abs_path):
                            missing.append({
                                'skill': skill_dir,
                                'type': ref_type,
                                'ref': ref_path,
                                'resolved': abs_path,
                                'line_number': line_num
                            })
    return missing


def main():
    skill_names = find_skill_dirs()
    if not skill_names:
        print(json.dumps({
            'passed': False,
            'total_skills': 0,
            'missing_refs': [],
            'error': 'No skill directories found'
        }, indent=2))
        return 1

    all_missing = []

    for name in skill_names:
        skill_md = os.path.join(SKILLS_DIR, name, 'SKILL.md')
        if not os.path.exists(skill_md):
            all_missing.append({
                'skill': name,
                'type': 'missing_skill',
                'ref': 'SKILL.md',
                'resolved': skill_md
            })
            continue

        with open(skill_md) as f:
            content = f.read()

        all_missing.extend(check_ref_table(content, name, ['使用的通用节点', '使用的节点'], '../../nodes/', 'node'))
        all_missing.extend(check_ref_table(content, name, ['引用的通用 Schema', '引用的 Schema'], 'schemas/atomic/', 'schema'))
        all_missing.extend(check_ref_table(content, name, ['引用的 task_sys 组件', 'task_sys'], '', 'task_sys'))

    result = {
        'passed': len(all_missing) == 0,
        'total_skills': len(skill_names),
        'missing_refs': all_missing
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Text summary for harness-smoke compatibility
    if all_missing:
        print(f'\n❌ FAIL: {len(all_missing)} broken skill references found:')
        for ref in all_missing:
            print(f'  [{ref["type"]}] {ref["skill"]}:{ref.get("line_number","?")} — {ref["ref"]} → {ref["resolved"]}')
        return 1
    else:
        print(f'\n✅ PASS: All {len(skill_names)} skills have valid references (0 broken)')
        return 0


if __name__ == '__main__':
    sys.exit(main())
