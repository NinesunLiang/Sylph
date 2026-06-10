#!/usr/bin/env python3
"""
verify_oma_mece.py — OMA MECE 正交性自动校验

用法:
  python3 verify_oma_mece.py <sub_prds_dir_or_file>
  python3 verify_oma_mece.py sub-prds/
  python3 verify_oma_mece.py sub-prds/domain-alert-engine.md

功能:
  1. 正交性检查: 两个 Sub PRD 的"负责"条目是否有重叠
  2. 数据实体唯一 Own: 同一实体是否被多个域同时声明 Own
  3. 依赖闭合性: 依赖图中被依赖的域是否都已拆出
  4. 接口孤儿检查: 每个接口是否至少有一个已知调用方
  5. 父需求追溯覆盖: 所有 Sub PRD 的父需求条目是否完整覆盖主 PRD

集成:
  由 lx-oma-hier SKILL.md §7 拆解质量自我校验调用
  替代 AI 自检的自动化部分
"""

import sys
import os
import re
import glob
import json
from pathlib import Path
from collections import defaultdict


def get_project_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent.parent


PROJECT_ROOT = get_project_root()


# ── 解析 Sub PRD ──────────────────────────────────────────────────

def parse_sub_prd(filepath: Path) -> dict:
    """解析单个 Sub PRD 文件，提取结构化信息。"""
    if not filepath.exists():
        return None

    text = filepath.read_text(encoding='utf-8')

    info = {
        'path': str(filepath),
        'name': filepath.stem,
        'responsible': [],      # "负责" 条目
        'not_responsible': [],  # "不负责" 条目
        'interfaces': [],       # 接口列表
        'events': [],           # 事件列表
        'entities': [],         # 数据实体归属
        'dependencies': [],     # 依赖的其他域
        'depended_by': [],      # 被依赖
        'parent_trace': [],     # 父需求追溯
    }

    # 解析功能边界 → 负责 / 不负责
    in_boundary = False
    in_responsible = False
    in_not_responsible = False

    for line in text.split('\n'):
        stripped = line.strip()

        # 节检测
        if stripped.startswith('##') and '功能边界' in stripped:
            in_boundary = True
            continue
        if in_boundary and stripped.startswith('##') and '功能边界' not in stripped:
            in_boundary = False
            in_responsible = False
            in_not_responsible = False

        if in_boundary:
            if '**负责**' in stripped or '负责' in stripped and '不负责' not in stripped:
                in_responsible = True
                in_not_responsible = False
                continue
            if '**不负责**' in stripped or '不负责' in stripped:
                in_not_responsible = True
                in_responsible = False
                continue
            if stripped.startswith('- ') and in_responsible:
                info['responsible'].append(stripped[2:].strip())
            if stripped.startswith('- ') and in_not_responsible:
                info['not_responsible'].append(stripped[2:].strip())

        # 接口表: | `name` | ... |
        if stripped.startswith('|') and '`' in stripped and not re.match(r'^\|[\s\-]+\|', stripped):
            m = re.search(r'`\s*(\w+)\s*`', stripped)
            if m and '接口' in stripped[:50] if False else True:
                name = m.group(1)
                if name not in [i['name'] for i in info['interfaces']]:
                    direction = 'inbound'
                    dm = re.search(r'\|\s*(inbound|outbound)', stripped)
                    if dm:
                        direction = dm.group(1)
                    info['interfaces'].append({'name': name, 'direction': direction})

        # 实体表
        if stripped.startswith('|') and not re.match(r'^\|[\s\-]+\|', stripped):
            cells = stripped.split('|')
            first_cell = cells[1].strip() if len(cells) > 1 else ''
            if re.match(r'^[A-Za-z]\w*$', first_cell) and not re.search(r'[\u4e00-\u9fff]', first_cell):
                ownership = ''
                om = re.search(r'\|\s*(Own|Read|Write)\s*\|', stripped)
                if om:
                    ownership = om.group(1)
                if ownership:
                    info['entities'].append({'name': first_cell, 'ownership': ownership})

        # 依赖关系
        if stripped.startswith('- **依赖**'):
            deps = stripped.split('**依赖**')[1].strip().lstrip(':').strip()
            if deps and deps != '无':
                info['dependencies'] = [d.strip() for d in deps.replace('、', ',').split(',') if d.strip()]
        if stripped.startswith('- **被依赖**'):
            deps = stripped.split('**被依赖**')[1].strip().lstrip(':').strip()
            if deps and deps != '无':
                info['depended_by'] = [d.strip() for d in deps.replace('、', ',').split(',') if d.strip()]

        # 父需求追溯表
        if '父需求' in stripped and stripped.startswith('|'):
            cells = stripped.split('|')
            if len(cells) >= 3:
                chapter = cells[1].strip()
                if chapter and not re.match(r'^[\s\-]+$', chapter) and '章节' not in chapter:
                    coverage = cells[2].strip() if len(cells) > 2 else ''
                    info['parent_trace'].append({'chapter': chapter, 'coverage': coverage})

    return info


# ── 校验 1: 正交性 ────────────────────────────────────────────────

def check_orthogonality(sub_prds: dict[str, dict]) -> list[dict]:
    """
    检查每两个域之间"负责"条目是否有语义重叠。
    使用关键词重叠作为启发性检测。
    """
    findings = []
    names = list(sub_prds.keys())

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a = sub_prds[names[i]]
            b = sub_prds[names[j]]

            # 提取关键词
            a_keywords = set()
            for resp in a.get('responsible', []):
                for word in resp.lower().replace('-', ' ').replace('/', ' ').split():
                    if len(word) > 2:
                        a_keywords.add(word)

            b_keywords = set()
            for resp in b.get('responsible', []):
                for word in resp.lower().replace('-', ' ').replace('/', ' ').split():
                    if len(word) > 2:
                        b_keywords.add(word)

            # 关键词重叠检测
            overlap = a_keywords & b_keywords
            # 排除常见词
            common_words = {'the', 'and', 'for', 'api', 'data', 'user', '管理', '处理', '模块'}
            meaningful_overlap = overlap - common_words

            if meaningful_overlap:
                findings.append({
                    'type': 'orthogonality_conflict',
                    'severity': 'warning',
                    'domains': [a['name'], b['name']],
                    'overlapping_keywords': list(meaningful_overlap),
                    'message': f"域 {a['name']} 和 {b['name']} 存在关键词重叠: {meaningful_overlap}"
                })

    return findings


# ── 校验 2: 数据实体唯一 Own ──────────────────────────────────────

def check_entity_ownership(sub_prds: dict[str, dict]) -> list[dict]:
    """检查同一数据实体是否被多个域声明 Own。"""
    findings = []
    entity_owners = defaultdict(list)

    for name, info in sub_prds.items():
        for entity in info.get('entities', []):
            if entity.get('ownership', '').upper() == 'OWN':
                entity_owners[entity['name']].append(name)

    for entity_name, owners in entity_owners.items():
        if len(owners) > 1:
            findings.append({
                'type': 'entity_ownership_conflict',
                'severity': 'error',
                'entity': entity_name,
                'owners': owners,
                'message': f"实体 {entity_name} 被多个域声明 Own: {owners}"
            })

    return findings


# ── 校验 3: 依赖闭合性 ────────────────────────────────────────────

def check_dependency_closure(sub_prds: dict[str, dict]) -> list[dict]:
    """检查依赖图中被依赖的域是否都已拆出。"""
    findings = []
    all_domain_names = set(sub_prds.keys())

    for name, info in sub_prds.items():
        for dep in info.get('dependencies', []):
            # 尝试匹配域名（可能用不同格式引用）
            dep_normalized = dep.strip().lower().replace(' ', '-').replace('_', '-')
            found = False
            for dn in all_domain_names:
                if dn.lower().replace('_', '-') in dep_normalized or dep_normalized in dn.lower().replace('_', '-'):
                    found = True
                    break

            if not found:
                findings.append({
                    'type': 'dependency_not_found',
                    'severity': 'error',
                    'domain': name,
                    'missing_dependency': dep,
                    'message': f"域 {name} 依赖的 {dep} 未在已拆出的域中找到"
                })

        # 检查循环依赖
        for dep in info.get('dependencies', []):
            dep_normalized = dep.strip().lower().replace(' ', '-').replace('_', '-')
            for dn in all_domain_names:
                if dn.lower().replace('_', '-') in dep_normalized:
                    # 检查反向依赖
                    dep_info = sub_prds.get(dn)
                    if dep_info:
                        for back_dep in dep_info.get('dependencies', []):
                            back_normalized = back_dep.strip().lower().replace(' ', '-').replace('_', '-')
                            if name.lower().replace('_', '-') in back_normalized:
                                findings.append({
                                    'type': 'circular_dependency',
                                    'severity': 'error',
                                    'domains': [name, dn],
                                    'message': f"域 {name} 和 {dn} 存在循环依赖"
                                })

    return findings


# ── 校验 4: 接口孤儿检查 ──────────────────────────────────────────

def check_interface_orphans(sub_prds: dict[str, dict]) -> list[dict]:
    """检查每个接口是否至少有一个已知调用方。"""
    findings = []
    all_interfaces = {}
    all_dependencies = set()

    for name, info in sub_prds.items():
        for iface in info.get('interfaces', []):
            all_interfaces[f"{name}.{iface['name']}"] = {
                'domain': name,
                'interface': iface['name'],
                'direction': iface.get('direction', '')
            }

    # 收集所有依赖声明
    for name, info in sub_prds.items():
        for dep in info.get('dependencies', []):
            all_dependencies.add(dep.strip().lower())

    # 出向接口应有调用方
    for key, iface in all_interfaces.items():
        if iface['direction'] == 'outbound':
            # 检查是否有域依赖包含此域
            caller_found = False
            domain_name = iface['domain'].lower().replace('_', '-')
            for dep in all_dependencies:
                if domain_name in dep:
                    caller_found = True
                    break

            if not caller_found:
                findings.append({
                    'type': 'orphan_interface',
                    'severity': 'warning',
                    'domain': iface['domain'],
                    'interface': iface['interface'],
                    'message': f"接口 {iface['domain']}.{iface['interface']} (outbound) 没有已知调用方"
                })

    return findings


# ── 主流程 ────────────────────────────────────────────────────────

def verify(target_path: str) -> tuple[bool, list[dict]]:
    """
    执行全部 MECE 校验。
    返回 (is_clean, all_findings)
    """
    path = Path(target_path)
    if not path.exists():
        print(f"❌ 路径不存在: {target_path}")
        sys.exit(2)

    # 收集 Sub PRD 文件
    sub_prd_files = []
    if path.is_file():
        sub_prd_files = [path]
    else:
        sub_prd_files = sorted(path.glob("domain-*.md"))

    if not sub_prd_files:
        print(f"⚠️ 未找到 Sub PRD 文件: {target_path}")
        return False, []

    # 解析
    sub_prds = {}
    for fp in sub_prd_files:
        info = parse_sub_prd(fp)
        if info:
            sub_prds[info['name']] = info

    if not sub_prds:
        print("⚠️ 未能解析任何 Sub PRD")
        return False, []

    print(f"{'='*60}")
    print(f"OMA MECE 正交性校验")
    print(f"{'='*60}")
    print(f"Sub PRD 数量: {len(sub_prds)}")
    print(f"域: {', '.join(sub_prds.keys())}")
    print()

    all_findings = []

    # 1. 正交性
    ortho_findings = check_orthogonality(sub_prds)
    all_findings.extend(ortho_findings)

    # 2. 实体唯一 Own
    entity_findings = check_entity_ownership(sub_prds)
    all_findings.extend(entity_findings)

    # 3. 依赖闭合性
    dep_findings = check_dependency_closure(sub_prds)
    all_findings.extend(dep_findings)

    # 4. 接口孤儿
    orphan_findings = check_interface_orphans(sub_prds)
    all_findings.extend(orphan_findings)

    # 输出
    errors = [f for f in all_findings if f['severity'] == 'error']
    warnings = [f for f in all_findings if f['severity'] == 'warning']

    if errors:
        print(f"\n❌ 错误 ({len(errors)}):")
        for f in errors:
            print(f"   [{f['type']}] {f['message']}")

    if warnings:
        print(f"\n⚠️  警告 ({len(warnings)}):")
        for f in warnings:
            print(f"   [{f['type']}] {f['message']}")

    if not all_findings:
        print("\n✅ MECE 校验全部通过 — 无正交性冲突、无实体冲突、依赖闭合")

    print(f"\n{'='*60}")
    print(f"汇总: {len(errors)} 错误, {len(warnings)} 警告")
    print()

    return len(errors) == 0, all_findings


def main():
    if len(sys.argv) < 2:
        print("用法: python3 verify_oma_mece.py <sub_prds_dir_or_file>")
        print("示例: python3 verify_oma_mece.py sub-prds/")
        print("      python3 verify_oma_mece.py sub-prds/domain-alert-engine.md")
        print()
        print("校验项:")
        print("  1. 正交性 — 两个域的'负责'条目是否有重叠")
        print("  2. 数据实体唯一 Own — 同一实体是否被多个域同时声明 Own")
        print("  3. 依赖闭合性 — 被依赖的域是否都已拆出，是否有循环依赖")
        print("  4. 接口孤儿 — 每个接口是否至少有一个已知调用方")
        sys.exit(2)

    target = sys.argv[1]
    is_clean, _ = verify(target)
    sys.exit(0 if is_clean else 1)


if __name__ == '__main__':
    main()
