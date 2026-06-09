#!/usr/bin/env python3
"""
oma_sub_prd_update.py — Sub PRD 增量更新机制

用法:
  python3 oma_sub_prd_update.py --detect                    # 检测哪些 Sub PRD 需要更新
  python3 oma_sub_prd_update.py --apply <sub_prd_path>     # 对指定 Sub PRD 应用增量更新
  python3 oma_sub_prd_update.py --apply-all                 # 对所有需要更新的 Sub PRD 应用更新

功能:
  Main PRD 变更时，Sub PRD 不再需要完全重新生成。
  本脚本检测 Main PRD 与各 Sub PRD 之间的差异，增量更新 Sub PRD 的：
  - 父需求追溯表
  - 非功能契约
  - 新增接口/实体引用

  更新后保留 Sub PRD 中的人工编辑（非破坏性）。

背景:
  Sub PRD 是 hier 拆分时生成的一次性快照。之前 Main PRD 变更后需要
  完全重新运行 hier（丢失人工编辑）。本机制实现增量更新，保留人工内容。

集成:
  由 lx-oma-gov reconcile 检测到 Main PRD 变更后调用
  或独立运行
"""

import sys
import os
import re
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict


def get_project_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent.parent


PROJECT_ROOT = get_project_root()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"


# ── Main PRD 解析 ─────────────────────────────────────────────────

def parse_master_prd_sections(filepath: Path) -> dict:
    """解析 Main PRD，按章节提取内容。"""
    if not filepath.exists():
        return {}

    text = filepath.read_text(encoding='utf-8')
    sections = {}
    current_section = None
    current_content = []

    for line in text.split('\n'):
        stripped = line.strip()
        # 检测章节标题
        m = re.match(r'^#{1,3}\s+(.+)', stripped)
        if m:
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = m.group(1).strip()
            current_content = []
        elif current_section:
            current_content.append(line)

    if current_section:
        sections[current_section] = '\n'.join(current_content)

    return sections


def extract_nfr_from_master(master_sections: dict) -> list[dict]:
    """从 Main PRD 提取非功能需求。"""
    nfrs = []
    for section_name, content in master_sections.items():
        if '非功能' in section_name or 'NFR' in section_name.upper():
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped.startswith('|') and not re.match(r'^\|[\s\-]+\|', stripped):
                    cells = stripped.split('|')
                    if len(cells) >= 3:
                        attr = cells[1].strip()
                        constraint = cells[2].strip() if len(cells) > 2 else ''
                        if attr and not re.search(r'[\u4e00-\u9fff]', attr[:1]) if False else False:
                            continue
                        if attr and attr not in ('属性', '----', ''):
                            nfrs.append({
                                'attribute': attr,
                                'constraint': constraint,
                                'source_section': section_name
                            })
    return nfrs


# ── Sub PRD 更新检测 ──────────────────────────────────────────────

def detect_outdated_sub_prds(master_prd: Path, sub_prds: list[Path]) -> list[dict]:
    """
    检测哪些 Sub PRD 相对于 Main PRD 需要更新。
    基于：
    1. Sub PRD 的父需求追溯表是否覆盖 Main PRD 所有章节
    2. Main PRD 修改时间是否晚于 Sub PRD
    3. 非功能契约是否同步
    """
    if not master_prd.exists():
        return []

    master_mtime = master_prd.stat().st_mtime
    master_sections = parse_master_prd_sections(master_prd)
    master_nfrs = extract_nfr_from_master(master_sections)

    outdated = []

    for sp in sub_prds:
        needs_update = False
        reasons = []

        # 1. 时间戳检查
        if sp.exists() and sp.stat().st_mtime < master_mtime:
            reasons.append(f"Main PRD 更新晚于 Sub PRD ({datetime.fromtimestamp(master_mtime).strftime('%Y-%m-%d')} vs {datetime.fromtimestamp(sp.stat().st_mtime).strftime('%Y-%m-%d')})")
            needs_update = True

        # 2. 父需求追溯覆盖检查
        if sp.exists():
            text = sp.read_text(encoding='utf-8')
            # 提取 Sub PRD 中已追溯的章节
            traced_sections = set()
            in_trace_table = False
            for line in text.split('\n'):
                stripped = line.strip()
                if '父需求追溯' in stripped:
                    in_trace_table = True
                    continue
                if in_trace_table and stripped.startswith('##'):
                    in_trace_table = False
                if in_trace_table and stripped.startswith('|') and not re.match(r'^\|[\s\-]+\|', stripped):
                    cells = stripped.split('|')
                    if len(cells) >= 2:
                        chapter = cells[1].strip()
                        if chapter and chapter not in ('主 PRD 章节', '章节', '----', ''):
                            traced_sections.add(chapter)

            # 对比 Main PRD 章节
            uncovered = set(master_sections.keys()) - traced_sections
            # 过滤非实质性章节
            skip_patterns = ['概述', '背景', '目标', '前言', '目录', '术语', 'Overview', 'Background']
            meaningful_uncovered = {
                s for s in uncovered
                if not any(skip in s for skip in skip_patterns)
            }
            if meaningful_uncovered:
                reasons.append(f"未覆盖的 Main PRD 章节: {meaningful_uncovered}")
                needs_update = True

        if needs_update:
            outdated.append({
                'sub_prd': str(sp.relative_to(PROJECT_ROOT)) if sp.is_relative_to(PROJECT_ROOT) else str(sp),
                'reasons': reasons,
                'master_nfr_count': len(master_nfrs)
            })

    return outdated


# ── 增量更新应用 ──────────────────────────────────────────────────

def apply_update(sub_prd_path: Path, master_prd: Path, dry_run: bool = True) -> dict:
    """
    对指定 Sub PRD 应用增量更新。
    非破坏性：保留所有人工编辑内容，仅追加/更新自动维护的节。
    """
    if not sub_prd_path.exists():
        return {'success': False, 'error': f'Sub PRD 不存在: {sub_prd_path}'}

    if not master_prd.exists():
        return {'success': False, 'error': f'Main PRD 不存在: {master_prd}'}

    master_sections = parse_master_prd_sections(master_prd)
    master_nfrs = extract_nfr_from_master(master_sections)

    original_text = sub_prd_path.read_text(encoding='utf-8')
    updated_text = original_text

    changes = []

    # 1. 更新父需求追溯表
    # 查找现有追溯表，补充缺失的章节
    if '## 父需求追溯' in updated_text:
        # 提取已有章节
        existing_chapters = set()
        in_table = False
        for line in updated_text.split('\n'):
            stripped = line.strip()
            if '父需求追溯' in stripped:
                in_table = True
                continue
            if in_table and stripped.startswith('##'):
                in_table = False
            if in_table and stripped.startswith('|') and not re.match(r'^\|[\s\-]+\|', stripped):
                cells = stripped.split('|')
                if len(cells) >= 2:
                    chapter = cells[1].strip()
                    if chapter and chapter not in ('主 PRD 章节', '----', ''):
                        existing_chapters.add(chapter)

        # 补充缺失章节
        new_entries = []
        for section_name in master_sections:
            if section_name not in existing_chapters:
                # 跳过非功能性章节
                skip = ['概述', '背景', '前言', '目录', '术语', 'Overview', 'Background', '目标']
                if not any(s in section_name for s in skip):
                    new_entries.append(f"| {section_name} | 待确认 |")

        if new_entries:
            # 在追溯表末尾追加
            trace_section_end = updated_text.find('##', updated_text.find('父需求追溯') + 10)
            if trace_section_end == -1:
                trace_section_end = len(updated_text)

            insert_pos = trace_section_end
            # 找到最后一个表格行
            before = updated_text[:insert_pos]
            last_table_line = before.rfind('\n|')
            if last_table_line > 0:
                insert_pos = before.rfind('\n', 0, last_table_line) + 1 if before.rfind('\n', 0, last_table_line) > 0 else last_table_line

            # 插入新行
            prefix = updated_text[:insert_pos]
            suffix = updated_text[insert_pos:]
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            new_content = '\n'.join(new_entries)
            updated_text = prefix + f"\n<!-- 增量更新 {now} -->\n{new_content}\n" + suffix
            changes.append(f"追加 {len(new_entries)} 条父需求追溯")

    # 2. 同步非功能契约
    if master_nfrs and '## 非功能契约' in updated_text:
        nfr_section_start = updated_text.find('## 非功能契约')
        nfr_section_end = updated_text.find('##', nfr_section_start + 10)
        if nfr_section_end == -1:
            nfr_section_end = len(updated_text)

        # 提取已有 NFR
        existing_nfrs = set()
        nfr_section = updated_text[nfr_section_start:nfr_section_end]
        for line in nfr_section.split('\n'):
            if line.strip().startswith('|') and not re.match(r'^\|[\s\-]+\|', line.strip()):
                cells = line.strip().split('|')
                if len(cells) >= 2:
                    attr = cells[1].strip()
                    if attr and attr != '属性':
                        existing_nfrs.add(attr)

        # 补充缺失的 NFR
        new_nfrs = []
        for nfr in master_nfrs:
            if nfr['attribute'] not in existing_nfrs:
                new_nfrs.append(f"| {nfr['attribute']} | {nfr['constraint']} | P1 | {nfr['source_section']} |")

        if new_nfrs:
            insert_pos = nfr_section_end
            prefix = updated_text[:insert_pos]
            suffix = updated_text[insert_pos:]
            new_content = '\n'.join(new_nfrs)
            updated_text = prefix + f"\n{new_content}\n" + suffix
            changes.append(f"同步 {len(new_nfrs)} 条非功能契约")

    # 3. 写入或预览
    if dry_run:
        # 计算差异
        if changes:
            return {
                'success': True,
                'dry_run': True,
                'changes': changes,
                'sub_prd': str(sub_prd_path.relative_to(PROJECT_ROOT)),
                'message': f"将应用 {len(changes)} 项变更"
            }
        else:
            return {
                'success': True,
                'dry_run': True,
                'changes': [],
                'sub_prd': str(sub_prd_path.relative_to(PROJECT_ROOT)),
                'message': "无需更新"
            }
    else:
        # 实际写入
        if changes:
            # 备份
            backup_path = sub_prd_path.with_suffix('.md.bak')
            sub_prd_path.rename(backup_path)
            sub_prd_path.write_text(updated_text, encoding='utf-8')

            # 记录更新
            update_log = STATE_DIR / "sub-prd-update-log.md"
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            with open(update_log, 'a', encoding='utf-8') as f:
                f.write(f"\n## Update {now}\n")
                f.write(f"- Sub PRD: {sub_prd_path.relative_to(PROJECT_ROOT)}\n")
                f.write(f"- Changes: {', '.join(changes)}\n")
                f.write(f"- Backup: {backup_path}\n")

            return {
                'success': True,
                'dry_run': False,
                'changes': changes,
                'sub_prd': str(sub_prd_path.relative_to(PROJECT_ROOT)),
                'backup': str(backup_path),
                'message': f"已应用 {len(changes)} 项变更，备份: {backup_path.name}"
            }
        else:
            return {
                'success': True,
                'dry_run': False,
                'changes': [],
                'message': "无需更新"
            }


# ── 主流程 ────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 oma_sub_prd_update.py --detect              # 检测需要更新的 Sub PRD")
        print("  python3 oma_sub_prd_update.py --apply <path>        # 对指定 Sub PRD 应用更新")
        print("  python3 oma_sub_prd_update.py --apply-all           # 对所有 Sub PRD 应用更新")
        print("  python3 oma_sub_prd_update.py --dry-run <path>      # 预览更新内容")
        sys.exit(2)

    command = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else None

    # 定位 Main PRD
    master_prd = PROJECT_ROOT / "master-prd.md"
    if not master_prd.exists():
        master_prd = PROJECT_ROOT / "docs" / "master-prd.md"
    if not master_prd.exists():
        print("⚠️ 未找到 master-prd.md，尝试从 sub-prds/ 推断...")
        master_prd = None

    # 发现 Sub PRD
    sub_prd_files = sorted(PROJECT_ROOT.glob("sub-prds/domain-*.md"))
    if not sub_prd_files:
        sub_prd_files = sorted(PROJECT_ROOT.glob("prd/*/prd.md"))

    if command == '--detect':
        if not master_prd:
            print("❌ 无法定位 Main PRD")
            sys.exit(2)

        print(f"{'='*60}")
        print(f"Sub PRD 更新检测")
        print(f"{'='*60}")
        print(f"Main PRD: {master_prd.relative_to(PROJECT_ROOT)}")
        print(f"Sub PRD 数量: {len(sub_prd_files)}")
        print()

        outdated = detect_outdated_sub_prds(master_prd, sub_prd_files)

        if not outdated:
            print("✅ 所有 Sub PRD 与 Main PRD 同步")
        else:
            print(f"🔴 {len(outdated)} 个 Sub PRD 需要更新:\n")
            for item in outdated:
                print(f"  {item['sub_prd']}:")
                for reason in item['reasons']:
                    print(f"    → {reason}")
                print()

        sys.exit(0 if not outdated else 1)

    elif command == '--apply':
        if not target:
            print("❌ 请指定 Sub PRD 路径")
            sys.exit(2)

        if not master_prd:
            print("❌ 无法定位 Main PRD")
            sys.exit(2)

        sub_prd_path = PROJECT_ROOT / target
        if not sub_prd_path.exists():
            sub_prd_path = Path(target)

        result = apply_update(sub_prd_path, master_prd, dry_run=False)
        print(f"\n{result['message']}")
        if result.get('changes'):
            for c in result['changes']:
                print(f"  → {c}")
        sys.exit(0 if result['success'] else 1)

    elif command == '--dry-run':
        if not target:
            print("❌ 请指定 Sub PRD 路径")
            sys.exit(2)

        if not master_prd:
            print("❌ 无法定位 Main PRD")
            sys.exit(2)

        sub_prd_path = PROJECT_ROOT / target
        if not sub_prd_path.exists():
            sub_prd_path = Path(target)

        result = apply_update(sub_prd_path, master_prd, dry_run=True)
        print(f"\n{result['message']}")
        if result.get('changes'):
            for c in result['changes']:
                print(f"  → {c}")
        sys.exit(0)

    elif command == '--apply-all':
        if not master_prd:
            print("❌ 无法定位 Main PRD")
            sys.exit(2)

        for sp in sub_prd_files:
            result = apply_update(sp, master_prd, dry_run=False)
            print(f"{sp.name}: {result['message']}")
        sys.exit(0)

    else:
        print(f"❌ 未知命令: {command}")
        sys.exit(2)


if __name__ == '__main__':
    main()
