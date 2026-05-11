#!/usr/bin/env python3
"""add-skill-frontmatter.py — 批量添加 role + execution_mode 到所有 SKILL.md frontmatter

在 frontmatter 闭合 --- 前插入两个字段。
对无 fields 区隔空行的 compact 格式保持一致。
"""

import os
import re

SKILLS_DIR = os.path.join(os.path.dirname(__file__), '..', 'skills')

SKILL_DEFS = {
    "lx-todo": ("Lightweight single-terminal fix-verify-close workflow for small tasks", "stepwise"),
    "lx-tdd-spec": ("Test spec & acceptance criteria generator for new features", "stepwise"),
    "lx-code-review": ("Go code quality reviewer — 8 categories, 39 rules", "stepwise"),
    "lx-web-perf": ("Web performance auditor — bundle analysis, Web Vitals, Next.js optimization", "stepwise"),
    "lx-pre-push": ("Pre-push quality gate — commit message validation, diff sanity check", "stepwise"),
    "lx-varlock": ("Privacy desensitization proxy manager for sensitive data", "stepwise"),
    "lx-race": ("Swarm coordinator — sub-task registration, dispatch, collection, conflict resolution", "race"),
    "lx-pre-commit": ("Pre-commit quality gate — compile, test, lint, coverage check", "stepwise"),
    "lx-security-review": ("Security vulnerability scanner for Go code and dependencies", "stepwise"),
    "lx-debug-spec": ("Root-cause debugger for Go — structured investigation protocol", "stepwise"),
    "lx-validate-skill": ("Skill atomization compliance validator — 11-rule architecture check", "stepwise"),
    "lx-task-spec": ("Task specification engine — structured task decomposition and execution", "stepwise"),
    "lx-react-review": ("React/Next.js code quality reviewer — component patterns, hooks, performance", "stepwise"),
    "lx-golang-test": ("Go test code generator — pattern-based test scaffolding", "stepwise"),
    "lx-browser-verify": ("Browser visual verification & acceptance testing via Playwright", "stepwise"),
    "lx-status": ("Carror OS health dashboard — system status panel", "race"),
    "lx-oma-orch": ("Pipeline orchestrator — 4-skill lifecycle orchestration with Oracle gates", "stepwise"),
    "lx-oma-hier": ("PRD hierarchical decomposer — master PRD to Sub PRDs (Level 1)", "stepwise"),
    "lx-oma-split": ("OMA commander — Sub PRD to feature decomposition (Level 2)", "race"),
    "lx-rpe": ("RPE-driven feature development — 9-step closed loop with quality gates", "stepwise"),
    "lx-oma-gov": ("PRD governance — drift detection, reconciliation, propagation", "stepwise"),
    "lx-prd": ("PRD production pipeline — specification authoring and quality review", "stepwise"),
    "lx-root-cause-analysis": ("Five Whys root cause analysis for recurring Go bugs", "stepwise"),
}


def main():
    for skill_name, (role, mode) in sorted(SKILL_DEFS.items()):
        fpath = os.path.join(SKILLS_DIR, skill_name, 'SKILL.md')
        if not os.path.exists(fpath):
            print(f"⚠️  不存在: {skill_name}/SKILL.md")
            continue

        with open(fpath, 'r') as f:
            content = f.read()

        # 检查是否已有 role 或 execution_mode
        if re.search(r'^role:', content, re.MULTILINE):
            print(f"⏭️  {skill_name}: 已有 role, 跳过")
            continue
        if re.search(r'^execution_mode:', content, re.MULTILINE):
            print(f"⏭️  {skill_name}: 已有 execution_mode, 跳过")
            continue

        # 找到 frontmatter 范围: 第一组 --- ... ---
        # 匹配 --- 行，记录起始和结束
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
            print(f"⚠️  {skill_name}: 无法找到 frontmatter (---), 跳过")
            continue

        # 找到 fm_end 前最后一个非空行，在其后插入新字段
        insert_idx = fm_end
        for i in range(fm_end - 1, fm_start, -1):
            if lines[i].strip():
                insert_idx = i + 1
                break

        # 判断空隙风格：检查 frontmatter 内部字段间是否有空行
        has_internal_gaps = False
        for i in range(fm_start + 1, fm_end):
            if not lines[i].strip():
                has_internal_gaps = True
                break

        new_lines = lines[:]
        indent = ''

        new_fields = [
            f'role: "{role}"',
            f'execution_mode: {mode}',
        ]

        # 在 insert_idx 插入
        if has_internal_gaps:
            # 有内部空行 → 带空行插入
            insertion = '\n' + '\n'.join(new_fields) + '\n'
        else:
            # compact 无空行 → 直接插入
            insertion = '\n' + '\n'.join(new_fields) + '\n'

        new_lines.insert(insert_idx, insertion.strip())
        new_content = '\n'.join(new_lines) + '\n'

        with open(fpath, 'w') as f:
            f.write(new_content)

        print(f"✅ {skill_name}: role={role}, mode={mode}")


if __name__ == '__main__':
    main()
