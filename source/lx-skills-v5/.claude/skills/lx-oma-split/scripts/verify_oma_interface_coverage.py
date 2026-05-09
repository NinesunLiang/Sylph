#!/usr/bin/env python3
"""
OMA 接口覆盖自动校验脚本

用法:
  python3 verify_oma_interface_coverage.py sub-prds/domain-alert-engine.md

功能:
  读取 Sub PRD 的接口表 + 事件表 → 遍历 prd/{sub_prd_name}/feat-*/prd.md
  → 检查每个接口/事件是否至少被一个 feature 覆盖
  → 未覆盖 → exit 1，输出缺口报告

集成:
  由 lx-oma-split SKILL.md 在拆解完成后自动调用（§5.5 校验环节）
"""

import sys
import os
import re
import glob

# ── 解析 Sub PRD 的接口/事件列表 ──────────────────────────────

def parse_interfaces_from_md(text: str) -> list[dict]:
    """从 Sub PRD markdown 中提取接口表和事件表中的 names。"""
    interfaces = []

    # 匹配接口表: 形如 | `createAlert` | inbound | ...
    # Table columns: 接口名 | 方向 | 入参 | 出参 | 错误码
    in_interface_section = False
    in_event_section = False

    for line in text.split('\n'):
        stripped = line.strip()

        # 检测章节头
        if stripped.startswith('##') and ('接口' in stripped or '契约' in stripped):
            in_interface_section = True
            in_event_section = False
            continue
        if stripped.startswith('##') and '事件' in stripped:
            in_event_section = True
            in_interface_section = False
            continue
        if stripped.startswith('##') and stripped not in ('## 对外接口契约', '## 接口列表', '## 事件 / 消息', '## 事件'):
            in_interface_section = False
            in_event_section = False

        # 接口表行: | `name` | ... |
        if in_interface_section and stripped.startswith('|'):
            # Extract backtick-quoted name: | `methodName` | ...
            m = re.search(r'`\s*(\w+)\s*`', stripped)
            if m and not re.match(r'^\|[\s-]+\|', stripped):  # skip header separators
                name = m.group(1)
                direction = ''
                # Extract direction (2nd column or inline)
                dm = re.search(r'\|\s*(inbound|outbound)', stripped)
                if dm:
                    direction = dm.group(1)
                interfaces.append({
                    'name': name,
                    'type': 'interface',
                    'source_table': 'interface',
                    'direction': direction
                })

        # 事件表行: | `EventName` | ... |
        if in_event_section and stripped.startswith('|'):
            m = re.search(r'`\s*(\w+)\s*`', stripped)
            if m and not re.match(r'^\|[\s-]+\|', stripped):
                name = m.group(1)
                interfaces.append({
                    'name': name,
                    'type': 'event',
                    'source_table': 'event',
                    'direction': 'outbound'
                })

    return interfaces


def get_all_interface_names_from_md(text: str) -> set[str]:
    """提取单个 feature prd.md 中声明的所有接口/事件名称。"""
    names = set()
    # 匹配 | `name` | ... 格式（接口表和事件表）
    for m in re.finditer(r'`\s*(\w+)\s*`\s*\|', text):
        name = m.group(1)
        # 排除表头分隔行中的内容
        if not re.match(r'^[-]+$', name):
            names.add(name)
    return names


def extract_sub_prd_name(sub_prd_path: str) -> str:
    """从 sub-prd 文件路径提取 sub_prd_name。
    sub-prds/domain-alert-engine.md → alert-engine
    """
    basename = os.path.basename(sub_prd_path)
    name = os.path.splitext(basename)[0]
    # Remove 'domain-' prefix if present
    if name.startswith('domain-'):
        name = name[len('domain-'):]
    return name


def get_sub_prd_base_dir(sub_prd_path: str) -> str:
    """获取 sub_prd 对应的 prd 目录。
    sub-prds/domain-alert-engine.md → prd/alert-engine/
    """
    name = extract_sub_prd_name(sub_prd_path)
    # 从当前路径推断项目根
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    return os.path.join(project_root, 'prd', name)


# ── 主校验逻辑 ────────────────────────────────────────────────

def verify(sub_prd_path: str) -> tuple[bool, list[dict]]:
    """
    返回 (is_clean, gaps[])
    gaps: 未覆盖的接口/事件列表
    """
    if not os.path.exists(sub_prd_path):
        print(f"❌ Sub PRD 文件不存在: {sub_prd_path}")
        sys.exit(2)

    with open(sub_prd_path, 'r', encoding='utf-8') as f:
        sub_prd_text = f.read()

    # 1. 提取 Sub PRD 的接口/事件
    sub_prd_items = parse_interfaces_from_md(sub_prd_text)
    sub_prd_names = {item['name'] for item in sub_prd_items}

    # 2. 扫描 feature prd.md 文件
    prd_dir = get_sub_prd_base_dir(sub_prd_path)
    feature_prds = glob.glob(os.path.join(prd_dir, 'feat-*/prd.md'))

    if not feature_prds:
        print(f"⚠️ 未找到 feature PRD 文件: {prd_dir}/feat-*/prd.md")
        return False, [{'name': n, 'type': next(it['type'] for it in sub_prd_items if it['name'] == n)} for n in sub_prd_names]

    # 3. 收集所有 feature 中声明的接口名
    covered_names: set[str] = set()
    feature_coverage: dict[str, set[str]] = {}
    for fp in feature_prds:
        with open(fp, 'r', encoding='utf-8') as f:
            text = f.read()
        names = get_all_interface_names_from_md(text)
        feature_name = os.path.basename(os.path.dirname(fp))
        feature_coverage[feature_name] = names
        covered_names.update(names)

    # 4. 比对
    gaps = []
    for item in sub_prd_items:
        if item['name'] not in covered_names:
            gaps.append(item)

    # 5. 输出详情
    print(f"\n{'='*60}")
    print(f"OMA 接口覆盖校验: {os.path.basename(sub_prd_path)}")
    print(f"{'='*60}")
    print(f"Sub PRD 接口/事件数: {len(sub_prd_items)}")
    print(f"Feature PRD 文件数:  {len(feature_prds)}")
    print()

    # 归属表
    print(f"{'接口/事件':<30} {'类型':<10} {'归属':<20}")
    print(f"{'-'*30} {'-'*10} {'-'*20}")
    for item in sub_prd_items:
        name = item['name']
        itype = item['type']
        if name in covered_names:
            # 找出哪个 feature 覆盖了
            owner = next((fn for fn, names in feature_coverage.items() if name in names), '?')
            print(f"{name:<30} {itype:<10} ✅ {owner}")
        else:
            print(f"{name:<30} {itype:<10} ❌ 未归属")

    print()
    return len(gaps) == 0, gaps


def main():
    if len(sys.argv) < 2:
        print("用法: python3 verify_oma_interface_coverage.py <sub_prd_path>")
        print("示例: python3 verify_oma_interface_coverage.py sub-prds/domain-alert-engine.md")
        sys.exit(2)

    sub_prd_path = sys.argv[1]
    is_clean, gaps = verify(sub_prd_path)

    if is_clean:
        print("✅ 校验通过 — Sub PRD 所有接口/事件均有 feature 归属")
        sys.exit(0)
    else:
        print(f"❌ 校验失败 — {len(gaps)} 个接口/事件未归属:")
        for g in gaps:
            print(f"   · {g['name']} ({g['type']})")
        print("\n请将这些接口追加到对应 feature 的 prd.md 后重新验证。")
        sys.exit(1)


if __name__ == '__main__':
    main()
