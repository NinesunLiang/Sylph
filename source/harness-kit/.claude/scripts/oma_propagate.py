#!/usr/bin/env python3
"""
oma_propagate.py — OMA 变更传播执行器

用法:
  python3 oma_propagate.py --dry-run [--chg-id CHG-YYYYMMDD-NNN]
  python3 oma_propagate.py --execute [--chg-id CHG-YYYYMMDD-NNN]

功能:
  读取 CONSOLIDATION-LOG.md 中待传播的 CHG 条目
  → 向受影响的 feature prd.md 追加变更内容
  → 写入 sync-notes.md 同步记录（幂等：已有该 CHG-ID 则跳过）

集成:
  由 lx-oma-gov propagate 命令调用
  governance-spec.md §5 (幂等性) + §10 (dry-run)

v1: 支持 --dry-run (预览) + --execute (实际写入)
"""

import sys
import os
import re
import glob
import json
import time
from pathlib import Path
from datetime import datetime, timezone


def get_project_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent.parent


PROJECT_ROOT = get_project_root()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"
CONSOLIDATION_LOG = STATE_DIR / "CONSOLIDATION-LOG.md"


# ── CHG-ID 解析 ──────────────────────────────────────────────────

def parse_consolidation_log(log_path: Path) -> list[dict]:
    """解析 CONSOLIDATION-LOG.md，提取所有待传播的 CHG 条目。"""
    if not log_path.exists():
        return []

    entries = []
    current_entry = None

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()

            # 检测新条目: ### CL-NNN 或 ### CHG-YYYYMMDD-NNN
            m = re.match(r'^###\s+(CL-\d+|CHG-\d{8}-\d{3})', stripped)
            if m:
                if current_entry:
                    entries.append(current_entry)
                current_entry = {
                    'id': m.group(1),
                    'source': '',
                    'risk_level': '',
                    'affected_objects': [],
                    'status': '',
                    'content': '',
                    'raw_lines': [stripped]
                }
                continue

            if current_entry is None:
                continue

            current_entry['raw_lines'].append(stripped)

            # 提取字段
            if stripped.startswith('- Source:'):
                current_entry['source'] = stripped.split(':', 1)[1].strip()
            elif stripped.startswith('- Risk Level:'):
                current_entry['risk_level'] = stripped.split(':', 1)[1].strip()
            elif stripped.startswith('- Affected Objects:'):
                objs = stripped.split(':', 1)[1].strip()
                current_entry['affected_objects'] = [o.strip() for o in objs.split(',') if o.strip()]
            elif stripped.startswith('- Status:'):
                current_entry['status'] = stripped.split(':', 1)[1].strip()
            elif stripped.startswith('- Content:'):
                current_entry['content'] = stripped.split(':', 1)[1].strip()

        if current_entry:
            entries.append(current_entry)

    return entries


def get_pending_entries(entries: list[dict], chg_id: str = None) -> list[dict]:
    """过滤出待传播的条目（非 done/resolved/rejected）。"""
    pending = []
    for e in entries:
        if chg_id and e['id'] != chg_id:
            continue
        status = e.get('status', '').lower()
        if status not in ('done', 'resolved', 'rejected', 'propagated'):
            pending.append(e)
    return pending


# ── Feature 发现 ─────────────────────────────────────────────────

def discover_features() -> dict[str, Path]:
    """扫描 prd/*/feat-*/prd.md，返回 {feature_path: prd_md_path}。"""
    features = {}
    prd_dir = PROJECT_ROOT / "prd"
    if not prd_dir.exists():
        return features

    for prd_md in sorted(prd_dir.glob("*/feat-*/prd.md")):
        # prd/{sub_prd}/feat-{name}/prd.md
        feature_key = str(prd_md.parent.relative_to(PROJECT_ROOT))
        features[feature_key] = prd_md

    return features


# ── 幂等检查 ─────────────────────────────────────────────────────

def check_chg_id_in_sync_notes(feature_dir: Path, chg_id: str) -> bool:
    """检查 feature 的 sync-notes.md 中是否已存在该 CHG-ID。"""
    sync_notes = feature_dir / "sync-notes.md"
    if not sync_notes.exists():
        return False

    content = sync_notes.read_text(encoding='utf-8')
    return chg_id in content


# ── 影响分析 ─────────────────────────────────────────────────────

def match_features_to_objects(
    features: dict[str, Path],
    affected_objects: list[str]
) -> list[str]:
    """
    分析哪些 feature 受 affected_objects 影响。
    策略：扫描 feature prd.md 内容，检查是否引用了受影响的对象 ID。
    """
    matched = []
    for feature_key, prd_path in features.items():
        try:
            content = prd_path.read_text(encoding='utf-8')
        except Exception:
            continue
        for obj_id in affected_objects:
            if obj_id in content:
                matched.append(feature_key)
                break
    return matched


# ── 传播执行 ──────────────────────────────────────────────────────

def generate_append_content(entry: dict, feature_key: str) -> str:
    """生成要追加到 feature prd.md 的内容块。"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""
<!-- CHG:{entry['id']} :: propagated {now} -->

> 📋 上游变更同步: {entry.get('source', 'unknown')}
> 风险级别: {entry.get('risk_level', 'L2')}
> 受影响对象: {', '.join(entry.get('affected_objects', []))}
> 变更内容: {entry.get('content', 'see CONSOLIDATION-LOG.md')}

"""


def write_sync_record(feature_dir: Path, entry: dict):
    """向 feature 的 sync-notes.md 追加同步记录。"""
    sync_notes = feature_dir / "sync-notes.md"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # 确保 sync-notes.md 存在
    if not sync_notes.exists():
        sync_notes.write_text(
            f"# Sync Notes — {feature_dir.name}\n\n"
            f"> 由 lx-oma-gov propagate 自动维护\n\n",
            encoding='utf-8'
        )

    record = f"""
## Sync Record {entry['id']}

- CHG-ID: {entry['id']}
- Propagated At: {now}
- Propagated By: oma_propagate.py
- Source Change: {entry.get('source', 'unknown')}
- Sync Type: prd
- Content Added: {entry.get('content', 'see CONSOLIDATION-LOG.md')}
- Status: done
"""
    with open(sync_notes, 'a', encoding='utf-8') as f:
        f.write(record)


def update_consolidation_log_status(entry_id: str, new_status: str):
    """更新 CONSOLIDATION-LOG.md 中条目的状态。"""
    if not CONSOLIDATION_LOG.exists():
        return

    content = CONSOLIDATION_LOG.read_text(encoding='utf-8')
    # 替换状态行
    pattern = re.compile(
        rf'(###\s+{re.escape(entry_id)}.*?\n.*?- Status:\s*).*',
        re.DOTALL
    )
    replacement = rf'\1{new_status}'

    # 更简单的方法：追加状态更新
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open(CONSOLIDATION_LOG, 'a', encoding='utf-8') as f:
        f.write(f"\n#状态更新: {entry_id}\n")
        f.write(f"- New Status: {new_status}\n")
        f.write(f"- Updated At: {now}\n")
        f.write(f"- Updated By: oma_propagate.py\n")


# ── 主流程 ────────────────────────────────────────────────────────

def propagate(chg_id: str = None, dry_run: bool = True) -> dict:
    """
    执行传播。返回执行报告。
    """
    entries = parse_consolidation_log(CONSOLIDATION_LOG)
    pending = get_pending_entries(entries, chg_id)

    if not pending:
        return {
            'result': 'no_changes',
            'message': '没有待传播的变更',
            'entries': [],
            'dry_run': dry_run
        }

    features = discover_features()
    if not features:
        return {
            'result': 'error',
            'message': '未发现 feature PRD 文件（prd/*/feat-*/prd.md）',
            'entries': [],
            'dry_run': dry_run
        }

    report_entries = []

    for entry in pending:
        entry_id = entry['id']
        affected_objects = entry.get('affected_objects', [])

        # 影响分析：哪些 feature 引用了受影响的对象
        if affected_objects:
            matched_features = match_features_to_objects(features, affected_objects)
        else:
            # 无明确受影响对象 → 默认影响所有 feature
            matched_features = list(features.keys())

        feature_actions = []
        for feature_key in matched_features:
            prd_path = features[feature_key]
            feature_dir = prd_path.parent

            # 幂等检查
            already_synced = check_chg_id_in_sync_notes(feature_dir, entry_id)

            if already_synced:
                feature_actions.append({
                    'feature': feature_key,
                    'action': 'skip',
                    'reason': f'CHG-ID {entry_id} 已同步'
                })
                continue

            # 生成追加内容
            append_text = generate_append_content(entry, feature_key)

            if dry_run:
                feature_actions.append({
                    'feature': feature_key,
                    'action': 'would_append',
                    'preview': append_text[:200] + '...' if len(append_text) > 200 else append_text
                })
            else:
                # 实际写入
                try:
                    with open(prd_path, 'a', encoding='utf-8') as f:
                        f.write(append_text)
                    write_sync_record(feature_dir, entry)
                    feature_actions.append({
                        'feature': feature_key,
                        'action': 'appended',
                        'file': str(prd_path)
                    })
                except Exception as e:
                    feature_actions.append({
                        'feature': feature_key,
                        'action': 'error',
                        'error': str(e)
                    })

        report_entries.append({
            'chg_id': entry_id,
            'source': entry.get('source', ''),
            'risk_level': entry.get('risk_level', ''),
            'affected_objects': affected_objects,
            'features': feature_actions
        })

        # 标记传播完成
        if not dry_run:
            update_consolidation_log_status(entry_id, 'propagated')

    # 检查是否有内容被实际追加
    any_appended = any(
        fa['action'] in ('appended', 'would_append')
        for e in report_entries
        for fa in e['features']
    )

    return {
        'result': 'success' if any_appended else 'no_changes',
        'dry_run': dry_run,
        'entries': report_entries
    }


def print_report(report: dict):
    """格式化输出传播报告。"""
    mode = "DRY-RUN (预览)" if report['dry_run'] else "EXECUTE (实际写入)"
    print(f"{'='*60}")
    print(f"OMA Propagate Report — {mode}")
    print(f"{'='*60}")

    if report['result'] == 'no_changes':
        print(report.get('message', '无变更'))
        return

    if report['result'] == 'error':
        print(f"❌ {report.get('message', '错误')}")
        return

    total_features = 0
    skipped = 0
    appended = 0

    for entry in report.get('entries', []):
        print(f"\n── {entry['chg_id']} — {entry['source']} ({entry['risk_level']})")
        print(f"   受影响对象: {', '.join(entry['affected_objects']) if entry['affected_objects'] else '(全部)'}")
        for fa in entry['features']:
            total_features += 1
            if fa['action'] == 'skip':
                skipped += 1
                print(f"   ⏭️  {fa['feature']} — {fa['reason']}")
            elif fa['action'] == 'would_append':
                print(f"   📋 {fa['feature']} — 将追加")
            elif fa['action'] == 'appended':
                appended += 1
                print(f"   ✅ {fa['feature']} — 已写入 ({fa['file']})")
            elif fa['action'] == 'error':
                print(f"   ❌ {fa['feature']} — {fa['error']}")

    print(f"\n{'='*60}")
    print(f"汇总: {len(report['entries'])} CHG, {total_features} feature 目标")
    if report['dry_run']:
        print(f"      将追加 {total_features - skipped} 处, 跳过 {skipped} 处 (已同步)")
    else:
        print(f"      已追加 {appended} 处, 跳过 {skipped} 处 (已同步)")
    print()


def main():
    if len(sys.argv) < 2:
        print("用法: python3 oma_propagate.py --dry-run|--execute [--chg-id CHG-YYYYMMDD-NNN]")
        print()
        print("  --dry-run   预览传播内容，不写入文件")
        print("  --execute   实际写入 feature prd.md + sync-notes.md")
        print("  --chg-id    仅传播指定 CHG-ID（可选，默认传播所有待处理条目）")
        sys.exit(2)

    dry_run = True
    chg_id = None

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--dry-run':
            dry_run = True
        elif arg == '--execute':
            dry_run = False
        elif arg == '--chg-id':
            if i + 1 < len(sys.argv):
                chg_id = sys.argv[i + 1]

    report = propagate(chg_id=chg_id, dry_run=dry_run)
    print_report(report)

    if report['result'] == 'error':
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
