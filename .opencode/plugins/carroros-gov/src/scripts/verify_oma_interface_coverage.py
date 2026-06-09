#!/usr/bin/env python3
"""
OMA 接口 + 实体覆盖自动校验脚本

用法:
  python3 verify_oma_interface_coverage.py sub-prds/domain-alert-engine.md

功能:
  读取 Sub PRD 的接口表 + 事件表 + 数据实体表
  → 遍历 prd/{sub_prd_name}/feat-*/prd.md
  → 检查每个接口/事件/实体是否至少被一个 feature 覆盖
  → 未覆盖 → exit 1，输出缺口报告

集成:
  由 lx-oma-split SKILL.md 在拆解完成后自动调用（§5.5 校验环节）
"""

import sys
import os
import re
import glob

# ── 解析 Sub PRD ───────────────────────────────────────────────

def parse_interfaces_from_md(text: str) -> list[dict]:
    """从 Sub PRD markdown 中提取接口表和事件表中的 names。"""
    interfaces = []
    in_interface_section = False
    in_event_section = False

    for line in text.split('\n'):
        stripped = line.strip()

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
            m = re.search(r'`\s*(\w+)\s*`', stripped)
            if m and not re.match(r'^\|[\s-]+\|', stripped):
                name = m.group(1)
                direction = ''
                dm = re.search(r'\|\s*(inbound|outbound)', stripped)
                if dm:
                    direction = dm.group(1)
                interfaces.append({
                    'name': name,
                    'type': 'interface',
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
                    'direction': 'outbound'
                })

    return interfaces


def parse_entities_from_md(text: str) -> list[dict]:
    """从 Sub PRD markdown 中提取数据实体表中的 names。

    实体表格式示例（基于实盘子 PRD）:
      | 实体名 | 归属关系 | 操作类型 | 说明 |
      |--------|---------|---------|------|
      | DashboardLayout | Own | CRUD | 用户仪表盘布局偏好 |

    注意：实体名不使用反引号包裹，与接口表不同。
    """
    entities = []
    in_entity_section = False

    for line in text.split('\n'):
        stripped = line.strip()

        if stripped.startswith('##') and '实体' in stripped:
            in_entity_section = True
            continue
        if stripped.startswith('##') and '实体' not in stripped:
            in_entity_section = False

        if in_entity_section and stripped.startswith('|'):
            # 跳过表头行（首列含中文）和分隔行
            cells = stripped.split('|')
            first_cell = cells[1].strip() if len(cells) > 1 else ''
            if re.match(r'^[\s-]+$', first_cell) or re.search(r'[\u4e00-\u9fff]', first_cell):
                continue
            # 先尝试匹配反引号包裹的名称（兼容格式）
            m = re.search(r'`\s*(\w+)\s*`', stripped)
            if m:
                name = m.group(1)
            else:
                # 实体名无反引号，取第一条竖线间的纯英文标识符
                m = re.match(r'^\|\s*([A-Za-z]\w*)\s*\|', stripped)
                if not m:
                    continue
                name = m.group(1)
            ownership = ''
            om = re.search(r'\|\s*(Own|Read|Write)\s*\|', stripped)
            if om:
                ownership = om.group(1)
            entities.append({
                'name': name,
                'ownership': ownership
            })

    return entities


def get_all_feature_names_from_md(text: str) -> set[str]:
    """提取单个 feature prd.md 中声明的所有接口/事件/实体名称。

    覆盖两种格式:
      - 反引号包裹: | `renderDashboard` | ...
      - 纯文本:     | DashboardLayout | Own | ...
    两种格式可能共存于同一文件的接口表/实体表。
    """
    names = set()
    # 匹配反引号包裹的名称
    for m in re.finditer(r'`\s*(\w+)\s*`\s*\|', text):
        name = m.group(1)
        if not re.match(r'^[-]+$', name):
            names.add(name)
    # 匹配纯文本实体名（首列为大驼峰英文标识符，无中文）
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped.startswith('|'):
            continue
        # 跳过表头行（首列含中文）和分隔行
        cells = stripped.split('|')
        first_cell = cells[1].strip() if len(cells) > 1 else ''
        if re.match(r'^[\s-]+$', first_cell) or re.search(r'[\u4e00-\u9fff]', first_cell):
            continue
        # 纯文本名称: 首列是英文标识符（已在上述 filter 中排除中文）
        # 且不在反引号中（反引号已通过上方正则捕获）
        if not re.search(r'`', first_cell):
            m = re.match(r'([A-Za-z]\w*)', first_cell)
            if m:
                names.add(m.group(1))
    return names


def extract_sub_prd_name(sub_prd_path: str) -> str:
    """从 sub-prd 文件路径提取 sub_prd_name。"""
    basename = os.path.basename(sub_prd_path)
    name = os.path.splitext(basename)[0]
    if name.startswith('domain-'):
        name = name[len('domain-'):]
    return name


def get_sub_prd_base_dir(sub_prd_path: str) -> str:
    """获取 sub_prd 对应的 prd 目录。"""
    name = extract_sub_prd_name(sub_prd_path)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
    return os.path.join(project_root, 'prd', name)


# ── 打印帮助函数 ────────────────────────────────────────────────

def print_coverage_table(items: list[dict], covered_names: set[str],
                         feature_coverage: dict[str, set[str]],
                         label: str, col_width: int = 30):
    """打印统一归属表。"""
    print(f"\n{'='*60}")
    print(f"{label}")
    print(f"{'='*60}")
    print(f"{'名称':<{col_width}} {'类型':<12} {'归属':<20}")
    print(f"{'-'*col_width} {'-'*12} {'-'*20}")
    for item in items:
        name = item['name']
        itype = item.get('type', item.get('ownership', 'entity'))
        if name in covered_names:
            owner = next((fn for fn, names in feature_coverage.items() if name in names), '?')
            print(f"{name:<{col_width}} {itype:<12} ✅ {owner}")
        else:
            print(f"{name:<{col_width}} {itype:<12} ❌ 未归属")
    print()


# ── 主校验逻辑 ────────────────────────────────────────────────

def verify(sub_prd_path: str) -> tuple[bool, list[dict]]:
    """
    返回 (is_clean, all_gaps[])
    all_gaps: 未覆盖的接口/事件/实体列表
    """
    if not os.path.exists(sub_prd_path):
        print(f"❌ Sub PRD 文件不存在: {sub_prd_path}")
        sys.exit(2)

    with open(sub_prd_path, 'r', encoding='utf-8') as f:
        sub_prd_text = f.read()

    # 1. 提取 Sub PRD 的接口/事件 + 实体
    sub_prd_interfaces = parse_interfaces_from_md(sub_prd_text)
    sub_prd_entities = parse_entities_from_md(sub_prd_text)
    all_items = sub_prd_interfaces + sub_prd_entities
    all_names = {item['name'] for item in all_items}

    # 2. 扫描 feature prd.md 文件
    prd_dir = get_sub_prd_base_dir(sub_prd_path)
    feature_prds = sorted(glob.glob(os.path.join(prd_dir, 'feat-*/prd.md')))

    if not feature_prds:
        print(f"⚠️ 未找到 feature PRD 文件: {prd_dir}/feat-*/prd.md")
        return False, all_items

    # 3. 收集所有 feature 中声明的名称
    covered_names: set[str] = set()
    feature_coverage: dict[str, set[str]] = {}
    for fp in feature_prds:
        with open(fp, 'r', encoding='utf-8') as f:
            text = f.read()
        names = get_all_feature_names_from_md(text)
        feature_name = os.path.basename(os.path.dirname(fp))
        feature_coverage[feature_name] = names
        covered_names.update(names)

    # 4. 比对
    all_gaps = []
    for item in all_items:
        if item['name'] not in covered_names:
            all_gaps.append(item)

    # 5. 输出详情
    print(f"{'='*60}")
    print(f"OMA 覆盖校验: {os.path.basename(sub_prd_path)}")
    print(f"{'='*60}")
    print(f"Sub PRD 接口/事件数: {len(sub_prd_interfaces)}")
    print(f"Sub PRD 实体数:      {len(sub_prd_entities)}")
    print(f"Feature PRD 文件数:  {len(feature_prds)}")
    print()

    # 接口/事件归属表
    print_coverage_table(
        sub_prd_interfaces, covered_names, feature_coverage,
        "接口/事件归属"
    )

    # 实体归属表
    print_coverage_table(
        sub_prd_entities, covered_names, feature_coverage,
        "数据实体归属"
    )

    return len(all_gaps) == 0, all_gaps


def main():
    if len(sys.argv) < 2:
        print("用法: python3 verify_oma_interface_coverage.py <sub_prd_path>")
        print("示例: python3 verify_oma_interface_coverage.py sub-prds/domain-alert-engine.md")
        sys.exit(2)

    sub_prd_path = sys.argv[1]
    is_clean, gaps = verify(sub_prd_path)

    if is_clean:
        print("✅ 校验通过 — Sub PRD 所有接口/事件/实体均有 feature 归属")
        sys.exit(0)
    else:
        print(f"❌ 校验失败 — {len(gaps)} 项未归属:")
        for g in gaps:
            gtype = g.get('type', g.get('ownership', 'entity'))
            print(f"   · {g['name']} ({gtype})")
        print("\n请将未归属项追加到对应 feature 的 prd.md 后重新验证。")
        sys.exit(1)


if __name__ == '__main__':
    main()
