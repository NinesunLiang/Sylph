#!/usr/bin/env python3
"""add-skill-triggers.py — 批量添加 triggers 到 SKILL.md frontmatter

为所有未设置斜杠命令的 skill 添加 triggers 字段。
"""

import os
import re

SKILLS_DIR = os.path.join(os.path.dirname(__file__), '..', 'skills')

# (skill_name, triggers_list)
SKILL_TRIGGERS = {
    "lx-todo": ["/lx-todo"],
    "lx-tdd-spec": ["/lx-tdd-spec"],
    "lx-code-review": ["/lx-code-review", "review code", "code review"],
    "lx-web-perf": ["/lx-web-perf"],
    "lx-pre-push": ["/lx-pre-push"],
    "lx-varlock": ["/lx-varlock"],
    "lx-race": ["/lx-race"],
    "lx-pre-commit": ["/lx-pre-commit"],
    "lx-security-review": ["/lx-security-review", "security scan"],
    "lx-debug-spec": ["/lx-debug-spec", "debug"],
    "lx-validate-skill": ["/lx-validate-skill"],
    "lx-task-spec": ["/lx-task-spec"],
    "lx-react-review": ["/lx-react-review", "react review"],
    "lx-golang-test": ["/lx-golang-test"],
    "lx-browser-verify": ["/lx-browser-verify"],
    "lx-status": ["/lx-status", "status", "dashboard"],
    "lx-prd": ["/lx-prd", "write prd"],
    "lx-root-cause-analysis": ["/lx-root-cause-analysis", "root cause"],
}

def main():
    for skill_name, triggers in sorted(SKILL_TRIGGERS.items()):
        fpath = os.path.join(SKILLS_DIR, skill_name, 'SKILL.md')
        if not os.path.exists(fpath):
            print(f"⚠️  不存在: {skill_name}/SKILL.md")
            continue

        with open(fpath, 'r') as f:
            content = f.read()

        # 检查是否已有 triggers
        if re.search(r'^triggers:', content, re.MULTILINE):
            print(f"⏭️  {skill_name}: 已有 triggers, 跳过")
            continue

        # 找到 frontmatter 闭合 ---
        lines = content.split('\n')
        fm_start = None
        fm_end = None

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == '---':
                if fm_start is None:
                    fm_start = i
                else:
                    fm_end = i
                    break

        if fm_start is None or fm_end is None:
            print(f"⚠️  {skill_name}: 无法找到 frontmatter, 跳过")
            continue

        # 构建 triggers YAML
        trigger_lines = ['triggers:']
        for t in triggers:
            trigger_lines.append(f'  - "{t}"')

        # 在闭合 --- 前插入
        new_lines = lines[:fm_end] + trigger_lines + lines[fm_end:]
        new_content = '\n'.join(new_lines) + '\n'

        with open(fpath, 'w') as f:
            f.write(new_content)

        print(f"✅ {skill_name}: {triggers}")


if __name__ == '__main__':
    main()
