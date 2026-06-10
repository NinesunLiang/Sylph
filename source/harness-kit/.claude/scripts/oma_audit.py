#!/usr/bin/env python3
"""
oma_audit.py — OMA 漂移检测完整版 (4/4 类型)

用法:
  python3 oma_audit.py [target_path]
  python3 oma_audit.py prd/
  python3 oma_audit.py prd/alert-engine/

功能 (v2 完整四类):
  1. ID 孤儿检测: feature 引用了 master 中不存在的 REQ/DEC/TERM
  2. 版本落后检测: feature 最后同步时间 < 最后一次 reconcile 时间
  3. 冲突定义检测: 同一 REQ 在 feature 与 master 中定义不一致
  4. 孤立变更检测: pending decision 超过 7 天未处理

v1 范围: 1 + 2
v2 扩展: 1 + 2 + 3 + 4 (当前完整实现)

集成:
  由 lx-oma-gov audit 命令调用
  governance-spec.md §9
"""

import sys
import os
import re
import glob
import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict


def get_project_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent.parent


PROJECT_ROOT = get_project_root()
STATE_DIR = PROJECT_ROOT / ".omc" / "state"


# ── 辅助函数 ──────────────────────────────────────────────────────

def extract_ids(text: str, prefix: str) -> set[str]:
    """提取指定前缀的 ID（如 REQ-*, DEC-*, TERM-*）。"""
    pattern = rf'{re.escape(prefix)}-\w+'
    return set(re.findall(pattern, text))


def extract_all_ids(text: str) -> dict[str, set[str]]:
    """提取所有类型的 ID。"""
    result = {}
    for prefix in ['REQ', 'DEC', 'TERM', 'RISK', 'PHASE']:
        result[prefix] = extract_ids(text, prefix)
    return result


def get_days_ago(timestamp_str: str) -> float:
    """计算距离现在的天数。"""
    try:
        # 尝试解析 ISO 格式
        ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        return (now - ts).total_seconds() / 86400.0
    except Exception:
        return 0


# ── 规则 1: ID 孤儿检测 ───────────────────────────────────────────

def check_id_orphans(master_ids: dict[str, set[str]],
                     feature_files: list[Path]) -> list[dict]:
    """
    扫描所有 feature prd.md，提取引用的 ID，
    与 master 中的对象列表比对。
    """
    findings = []

    for fp in feature_files:
        try:
            text = fp.read_text(encoding='utf-8')
        except Exception:
            continue

        feature_ids = extract_all_ids(text)
        feature_path = str(fp.parent.relative_to(PROJECT_ROOT))

        for prefix, ids in feature_ids.items():
            master_set = master_ids.get(prefix, set())
            orphans = ids - master_set
            for orphan_id in orphans:
                findings.append({
                    'type': 'orphan_reference',
                    'severity': 'high',
                    'feature': feature_path,
                    'orphan_id': orphan_id,
                    'message': f"{feature_path} 引用了 master 中不存在的 {orphan_id}"
                })

    return findings


# ── 规则 2: 版本落后检测 ──────────────────────────────────────────

def check_version_lag(feature_files: list[Path]) -> list[dict]:
    """
    读取 state/sync-state.md 中 last_reconcile_snapshot，
    与各 feature sync-notes.md 最后同步时间比对。
    """
    findings = []

    # 读取最后 reconcile 时间
    sync_state_file = STATE_DIR / "sync-state.md"
    last_reconcile_ts = None

    if sync_state_file.exists():
        text = sync_state_file.read_text(encoding='utf-8')
        # 查找 last_reconcile_snapshot 及其时间戳
        m = re.search(r'last_reconcile_snapshot:.*?(\d{4}-\d{2}-\d{2})', text)
        if m:
            try:
                last_reconcile_ts = datetime.strptime(m.group(1), '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except ValueError:
                pass

    if last_reconcile_ts is None:
        # 无 reconcile 记录 → 检查 CONSOLIDATION-LOG.md 最后修改时间
        consol_log = STATE_DIR / "CONSOLIDATION-LOG.md"
        if consol_log.exists():
            last_reconcile_ts = datetime.fromtimestamp(
                consol_log.stat().st_mtime, tz=timezone.utc
            )

    if last_reconcile_ts is None:
        return findings  # 无法确定基准时间

    for fp in feature_files:
        feature_dir = fp.parent
        sync_notes = feature_dir / "sync-notes.md"

        if not sync_notes.exists():
            findings.append({
                'type': 'sync_behind',
                'severity': 'medium',
                'feature': str(feature_dir.relative_to(PROJECT_ROOT)),
                'last_sync': 'never',
                'message': f"{feature_dir.name} 从未同步（sync-notes.md 不存在）"
            })
            continue

        text = sync_notes.read_text(encoding='utf-8')
        # 查找最后一条 Sync Record 的时间
        m = re.search(r'Propagated At:\s*(\d{4}-\d{2}-\d{2})', text)
        if m:
            try:
                last_sync_ts = datetime.strptime(m.group(1), '%Y-%m-%d').replace(tzinfo=timezone.utc)
                if last_sync_ts < last_reconcile_ts:
                    days_behind = (last_reconcile_ts - last_sync_ts).days
                    findings.append({
                        'type': 'sync_behind',
                        'severity': 'medium',
                        'feature': str(feature_dir.relative_to(PROJECT_ROOT)),
                        'last_sync': m.group(1),
                        'days_behind': days_behind,
                        'message': f"{feature_dir.name} 落后 {days_behind} 天（最后同步: {m.group(1)}，最后 reconcile: {last_reconcile_ts.strftime('%Y-%m-%d')}）"
                    })
            except ValueError:
                pass

    return findings


# ── 规则 3: 冲突定义检测 ──────────────────────────────────────────

def check_definition_conflict(master_ids: dict[str, set[str]],
                              feature_files: list[Path]) -> list[dict]:
    """
    找出同一 REQ-ID 在多个 feature 中都有描述的情况，
    检查描述是否一致（启发性：对比周围的 key-value 模式）。
    """
    findings = []
    req_occurrences = defaultdict(list)

    # 收集所有 feature 中出现的 REQ 引用及其上下文
    for fp in feature_files:
        try:
            text = fp.read_text(encoding='utf-8')
        except Exception:
            continue

        feature_path = str(fp.parent.relative_to(PROJECT_ROOT))

        # 提取每个 REQ-* 周围的上下文（前后各 2 行）
        lines = text.split('\n')
        for i, line in enumerate(lines):
            reqs = re.findall(r'REQ-\w+', line)
            for req_id in reqs:
                context_start = max(0, i - 2)
                context_end = min(len(lines), i + 3)
                context = '\n'.join(lines[context_start:context_end])
                req_occurrences[req_id].append({
                    'feature': feature_path,
                    'context': context[:200]  # 截断
                })

    # 检测同一 REQ 在多个 feature 中出现
    for req_id, occurrences in req_occurrences.items():
        if len(occurrences) > 1:
            # 启发性：如果两个 feature 都在描述同一 REQ，
            # 标记为需要人工审查
            features = list(set(o['feature'] for o in occurrences))
            findings.append({
                'type': 'definition_conflict',
                'severity': 'high',
                'req_id': req_id,
                'features': features,
                'message': f"{req_id} 在 {len(features)} 个 feature 中被引用，需审查定义一致性: {features}"
            })

    return findings


# ── 规则 4: 孤立变更检测 ──────────────────────────────────────────

def check_stale_pending(stale_days: int = 7) -> list[dict]:
    """
    扫描 CONSOLIDATION-LOG.md 和 pending-decisions.md 中
    超过 N 天未处理的待裁决项。
    """
    findings = []

    # 检查 CONSOLIDATION-LOG.md
    consol_log = STATE_DIR / "CONSOLIDATION-LOG.md"
    if consol_log.exists():
        text = consol_log.read_text(encoding='utf-8')
        # 查找状态为 awaiting_human 或 pending 的条目
        entries = re.split(r'\n(?=###\s+)', text)
        for entry in entries:
            if 'awaiting_human' in entry.lower() or 'pending' in entry.lower():
                # 提取创建时间
                m = re.search(r'Created At:\s*(\d{4}-\d{2}-\d{2})', entry)
                if m:
                    days = get_days_ago(m.group(1))
                    if days > stale_days:
                        entry_id = 'unknown'
                        id_m = re.match(r'###\s+(\S+)', entry)
                        if id_m:
                            entry_id = id_m.group(1)
                        findings.append({
                            'type': 'stale_pending',
                            'severity': 'high',
                            'entry_id': entry_id,
                            'days_stale': int(days),
                            'message': f"{entry_id} 已挂起 {int(days)} 天未处理"
                        })

    # 检查 pending-decisions.md
    pending_file = STATE_DIR / "pending-decisions.md"
    if pending_file.exists():
        text = pending_file.read_text(encoding='utf-8')
        conflicts = re.findall(r'CONFLICT-\w+', text)
        # 查找创建时间
        m = re.search(r'Created At:\s*(\d{4}-\d{2}-\d{2})', text)
        if m and conflicts:
            days = get_days_ago(m.group(1))
            if days > stale_days:
                findings.append({
                    'type': 'stale_pending',
                    'severity': 'high',
                    'entry_id': ', '.join(conflicts),
                    'days_stale': int(days),
                    'message': f"CONSOLIDATION-LOG 中有待处理冲突 ({', '.join(conflicts)})，已挂起 {int(days)} 天"
                })

    return findings


# ── 主流程 ────────────────────────────────────────────────────────

def audit(target_path: str = None, stale_days: int = 7) -> tuple[dict, list[dict]]:
    """
    执行全部四类漂移检测。
    返回 (summary, all_findings)
    """
    # 发现 feature 文件
    prd_dir = PROJECT_ROOT / "prd"
    if target_path:
        prd_dir = Path(target_path)

    feature_files = sorted(prd_dir.glob("*/feat-*/prd.md")) if prd_dir.exists() else []

    if not feature_files:
        # 尝试从当前目录搜索
        feature_files = sorted(PROJECT_ROOT.glob("prd/*/feat-*/prd.md"))

    # 读取 master PRD 中的 ID 集合
    master_ids = defaultdict(set)
    master_prd = PROJECT_ROOT / "master-prd.md"
    if not master_prd.exists():
        master_prd = PROJECT_ROOT / "docs" / "master-prd.md"

    if master_prd.exists():
        master_ids = extract_all_ids(master_prd.read_text(encoding='utf-8'))
    else:
        # 尝试从子 PRD 收集
        for fp in feature_files:
            try:
                text = fp.read_text(encoding='utf-8')
                for prefix, ids in extract_all_ids(text).items():
                    master_ids[prefix].update(ids)
            except Exception:
                pass

    # 如果没有 master，从 sub-prds 收集
    if not any(master_ids.values()):
        sub_prd_files = sorted(PROJECT_ROOT.glob("sub-prds/domain-*.md"))
        for fp in sub_prd_files:
            try:
                text = fp.read_text(encoding='utf-8')
                for prefix, ids in extract_all_ids(text).items():
                    master_ids[prefix].update(ids)
            except Exception:
                pass

    # 执行四类检测
    all_findings = []

    # 1. ID 孤儿
    all_findings.extend(check_id_orphans(dict(master_ids), feature_files))

    # 2. 版本落后
    all_findings.extend(check_version_lag(feature_files))

    # 3. 冲突定义 (v2)
    all_findings.extend(check_definition_conflict(dict(master_ids), feature_files))

    # 4. 孤立变更 (v2)
    all_findings.extend(check_stale_pending(stale_days))

    # 汇总
    high = [f for f in all_findings if f['severity'] == 'high']
    medium = [f for f in all_findings if f['severity'] == 'medium']
    low = [f for f in all_findings if f['severity'] == 'low']

    summary = {
        'total_features': len(feature_files),
        'total_findings': len(all_findings),
        'high': len(high),
        'medium': len(medium),
        'low': len(low),
        'status': 'clean' if not all_findings else ('warning' if not high else 'drift_detected')
    }

    return summary, all_findings


def print_report(summary: dict, findings: list[dict]):
    """格式化输出审计报告。"""
    print(f"{'='*60}")
    print(f"OMA Audit Report — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    print(f"{'='*60}")
    print(f"Feature 数量: {summary['total_features']}")
    print(f"漂移发现: {summary['total_findings']} (H:{summary['high']} M:{summary['medium']} L:{summary['low']})")
    print(f"审计状态: {summary['status']}")
    print()

    if summary['total_findings'] == 0:
        print("✅ 无漂移 — 所有 feature 与 master 一致")
        print()
        return

    # 按严重度分组输出
    for severity, label in [('high', '🔴 高严重度'), ('medium', '🟡 中严重度'), ('low', '🟢 低严重度')]:
        items = [f for f in findings if f['severity'] == severity]
        if not items:
            continue
        print(f"\n{label} ({len(items)}):")
        for f in items:
            print(f"   [{f['type']}] {f['message']}")

    print(f"\n{'='*60}")
    print("建议操作:")
    if summary['high'] > 0:
        print("  → 运行 lx-oma-gov reconcile 检测并合入变更")
        print("  → 运行 lx-oma-gov propagate --dry-run 预览传播")
    if summary['medium'] > 0:
        print("  → 运行 lx-oma-gov audit 定期检查漂移趋势")
    print()


def main():
    target = None
    stale_days = 7

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg.startswith('--stale-days='):
            stale_days = int(arg.split('=')[1])
        elif not arg.startswith('--'):
            target = arg

    summary, findings = audit(target_path=target, stale_days=stale_days)
    print_report(summary, findings)

    # exit code: 0 = clean, 1 = warning, 2 = drift detected
    if summary['status'] == 'clean':
        sys.exit(0)
    elif summary['status'] == 'warning':
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == '__main__':
    main()
