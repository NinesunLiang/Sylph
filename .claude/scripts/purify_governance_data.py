#!/usr/bin/env python3
"""purify_governance_data.py — 治理数据统一提纯管道（提纯后删除原始）。

铁律：产生数据先提纯再入库，提纯后删除原始信息。
覆盖原始源：
  - hook-evidence.jsonl  → 提纯为 hook 健康度（exit 分布、异常率）
  - edit-churn-log.jsonl → 提纯为编辑热点（高频文件、revert/矛盾率）
  - error-dna.jsonl      → 提纯为错误模式频率（复用 error_rulers）
  - calibration-log.jsonl→ 提纯为校准分布

产物：.omc/knowledge/governance-purified.json（结构化摘要，保留原始信息不可恢复）
清理：各原始源清空（保留文件骨架），写入 .omc/state/.purified 标记。

用法:
  python3 .claude/scripts/purify_governance_data.py
  python3 .claude/scripts/purify_governance_data.py --dry-run   # 只提纯不清理
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / '../..').resolve()
STATE_DIR = PROJECT_ROOT / '.omc' / 'state'
KNOWLEDGE_DIR = PROJECT_ROOT / '.omc' / 'knowledge'
PURIFIED_PATH = KNOWLEDGE_DIR / 'governance-purified.json'
PURIFIED_MARKER = STATE_DIR / '.purified'

SOURCES = {
    'hook_evidence': STATE_DIR / 'hook-evidence.jsonl',
    'edit_churn': STATE_DIR / 'edit-churn-log.jsonl',
    'error_dna': STATE_DIR / 'error-dna.jsonl',
    'calibration': STATE_DIR / 'calibration-log.jsonl',
    # 高 ROI 源（量大，提纯回收磁盘 + 健康度）：recovery-ledger 2.4M、completion-failures 5.5万
    'recovery_ledger': STATE_DIR / 'recovery-ledger.jsonl',
    'completion_failures': STATE_DIR / 'completion-gate-failures.jsonl',
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_jsonl(path: Path, limit: int = 0) -> list[dict]:
    records = []
    if not path.exists():
        return records
    with path.open(encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if limit and len(records) >= limit:
                break
    return records


def _purify_hook_evidence(records: list[dict]) -> dict:
    """提纯 hook-evidence → hook 健康度。"""
    if not records:
        return {'count': 0, 'status': 'empty'}
    hooks = Counter(r.get('hook', '?') for r in records)
    exits = Counter(int(r.get('exit', 0)) for r in records)
    nonzero = sum(v for e, v in exits.items() if e != 0)
    return {
        'count': len(records),
        'status': 'purified',
        'hook_calls': dict(hooks.most_common(10)),
        'exit_distribution': dict(sorted(exits.items())),
        'anomaly_rate': round(nonzero / len(records), 4),
    }


def _purify_edit_churn(records: list[dict]) -> dict:
    """提纯 edit-churn → 编辑热点 + 矛盾率。"""
    if not records:
        return {'count': 0, 'status': 'empty'}
    files = Counter(r.get('file_path', '?').split('/')[-1] for r in records)
    modes = Counter(r.get('edit_mode', 'unknown') for r in records)
    reverts = sum(1 for r in records if r.get('revert_of'))
    contradictions = sum(1 for r in records if r.get('contradiction'))
    return {
        'count': len(records),
        'status': 'purified',
        'top_files': dict(files.most_common(10)),
        'edit_modes': dict(modes),
        'revert_rate': round(reverts / len(records), 4),
        'contradiction_rate': round(contradictions / len(records), 4),
    }


def _purify_error_dna(records: list[dict]) -> dict:
    """提纯 error-dna → 错误模式频率。"""
    if not records:
        return {'count': 0, 'status': 'empty'}
    types = Counter(r.get('type', r.get('classification', 'unknown')) for r in records)
    return {
        'count': len(records),
        'status': 'purified',
        'error_types': dict(types.most_common(10)),
    }


def _purify_calibration(records: list[dict]) -> dict:
    """提纯 calibration-log → 校准分布。"""
    if not records:
        return {'count': 0, 'status': 'empty'}
    fields = Counter()
    for r in records:
        for k in list(r.keys())[:6]:
            fields[k] += 1
    return {
        'count': len(records),
        'status': 'purified',
        'field_frequency': dict(fields),
    }


def _purify_recovery_ledger(records: list[dict]) -> dict:
    """提纯 recovery-ledger（2.4M 高 ROI）→ 恢复协议决策分布 + 失败率。"""
    if not records:
        return {'count': 0, 'status': 'empty'}
    decisions = Counter(str(r.get('decision', '?')) for r in records)
    outcomes = Counter(str(r.get('actual_outcome', '?')) for r in records)
    events = Counter(str(r.get('event', '?')) for r in records)
    fails = sum(1 for r in records if r.get('decision') in ('BLOCKED', 'FAIL'))
    return {
        'count': len(records),
        'status': 'purified',
        'decision_distribution': dict(decisions),
        'outcome_distribution': dict(outcomes),
        'event_distribution': dict(events),
        'failure_rate': round(fails / len(records), 4),
    }


def _purify_completion_failures(records: list[dict]) -> dict:
    """提纯 completion-gate-failures（5.5万 高 ROI）→ 完成门禁失败原因分布。"""
    if not records:
        return {'count': 0, 'status': 'empty'}
    decisions = Counter(str(r.get('decision', '?')) for r in records)
    gates = Counter(str(r.get('gate', '?')) for r in records)
    reasons = Counter(str(r.get('reason', '?'))[:40] for r in records)
    return {
        'count': len(records),
        'status': 'purified',
        'decision_distribution': dict(decisions),
        'gate_distribution': dict(gates),
        'top_reasons': dict(reasons.most_common(10)),
    }


def purify(dry_run: bool = False) -> dict:
    """执行提纯：聚合各源 → 写入 knowledge → 清理原始（非 dry-run）。"""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    purified = {
        'schema': 'carroros.governance.purified.v1',
        'purified_at': _now(),
        'sources': {},
    }
    for name, path in SOURCES.items():
        records = _read_jsonl(path)
        fn = {
            'hook_evidence': _purify_hook_evidence,
            'edit_churn': _purify_edit_churn,
            'error_dna': _purify_error_dna,
            'calibration': _purify_calibration,
            'recovery_ledger': _purify_recovery_ledger,
            'completion_failures': _purify_completion_failures,
        }[name]
        purified['sources'][name] = fn(records)

    # 合并历史提纯（与已沉淀数据去重，避免重复入库）
    history: dict = {}
    if PURIFIED_PATH.exists():
        try:
            history = json.loads(PURIFIED_PATH.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            history = {}
    rounds = history.get('rounds', []) if isinstance(history, dict) else []
    # 去重：与最近轮比较各源指纹（count + 关键聚合），无变化则标记 deduped
    last_round = rounds[-1]['sources'] if rounds else {}
    deduped = {}
    for name, src in purified['sources'].items():
        prev = last_round.get(name)
        if prev and prev.get('status') == src.get('status') and prev.get('count') == src.get('count'):
            deduped[name] = True
        else:
            deduped[name] = False
    purified['deduped'] = deduped
    # 仅当有实质变化（非全 deduped）时 append 新轮次
    has_change = not all(deduped.values())
    if has_change or not rounds:
        rounds.append({'ts': _now(), 'sources': purified['sources']})
    purified['rounds'] = rounds[-20:]  # 保留最近 20 轮

    PURIFIED_PATH.write_text(json.dumps(purified, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    if not dry_run:
        # 提纯后清理原始信息（保留文件骨架，清空内容）
        for path in SOURCES.values():
            if path.exists():
                path.write_text('', encoding='utf-8')
        PURIFIED_MARKER.write_text(_now() + '\n', encoding='utf-8')
    return purified


def main() -> int:
    dry_run = '--dry-run' in sys.argv
    result = purify(dry_run=dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not dry_run:
        print(f'✅ 提纯完成: {PURIFIED_PATH}；原始数据已清空（marker: {PURIFIED_MARKER}）')
    else:
        print(f'🔍 dry-run: 提纯完成但原始数据未清理')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
