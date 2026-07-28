#!/usr/bin/env python3
"""error-dna-precipitate.py — CarrorOS error-dna 沉淀引擎

角色: error-dna.jsonl 满 100 条触发，去重、合并、录入 error_rulers.json

管线:
  1. 读取 error-dna.jsonl（当前采集批）
  2. 对每条记录：匹配已有规则 → 更新频率 / 未匹配则按模式分组
  3. 高频未匹配模式 (≥3) → 自动生成新规则（auto_ 前缀，priority=50）
  4. 合并到 error_rulers.json（去重 + 更新 last_seen / frequency）
  5. 归档 processed 记录 → .omc/state/error-dna-archive/
  6. 清空 error-dna.jsonl
  7. 输出汇总

用法:
  python3 .claude/scripts/error-dna-precipitate.py
  python3 .claude/scripts/error-dna-precipitate.py --force    # 忽略阈值强制沉淀
  python3 .claude/scripts/error-dna-precipitate.py --dry-run  # 试运行不改文件
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─── 路径 ───
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (SCRIPT_DIR / '../..').resolve()
STATE_DIR = PROJECT_ROOT / '.omc' / 'state'
LEGACY_DNA_PATH = PROJECT_ROOT / '.omc' / 'error-dna.jsonl'
DNA_PATH = STATE_DIR / 'error-dna.jsonl'
RULES_PATH = PROJECT_ROOT / '.claude' / 'references' / 'error_rulers.json'
ARCHIVE_DIR = STATE_DIR / 'error-dna-archive'
PRECIP_MARKER = STATE_DIR / '.precipitated'

# ─── 阈值 ───
PRECIP_THRESHOLD = int(os.environ.get('PRECIP_THRESHOLD', '90'))
MIN_PATTERN_FREQ = int(os.environ.get('MIN_PATTERN_FREQ', '3'))  # 至少 N 次相似错误才生成规则
AUTO_PRIORITY = int(os.environ.get('AUTO_PRIORITY', '50'))       # 自动生成规则的优先级

# ═══════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════

def _load_jsonl(path: Path) -> list[dict]:
    """加载 JSONL 文件。不存在或空返回 []。"""
    if not path.exists():
        return []
    records = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def _write_jsonl(path: Path, records: list[dict]) -> None:
    """覆写 JSONL 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def _load_rules() -> list[dict]:
    """加载 error_rulers.json。不存在返回空列表。"""
    if not RULES_PATH.exists():
        return []
    try:
        data = json.loads(RULES_PATH.read_text(encoding='utf-8'))
        return data.get('rules', [])
    except (json.JSONDecodeError, OSError):
        return []


def _write_rules(rules: list[dict]) -> None:
    """覆写 error_rulers.json。"""
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        'schema_version': 1,
        'description': 'CarrorOS 错误分类规则库 — error-dna 消费该文件将 exit_code + stderr 模式映射为具体错误类型',
        'last_updated': datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%dT%H:%M%z'),
        'rules': rules,
    }
    tmp = str(RULES_PATH) + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.rename(tmp, str(RULES_PATH))


def _normalize_record(record: dict) -> dict:
    """将不同版本的记录格式统一为标准格式。

    新版格式 (Python error-dna.py):
      {ts, signature, fingerprint, level, cmd, exit_code, error_type, message, ...}

    旧版格式 (error-dna.sh):
      {timestamp, step, error, artifact, retry_count, classification, _source, error_type}
    """
    # 已是最新格式
    if 'ts' in record and 'signature' in record:
        return record

    # 旧版格式
    ts = record.get('ts', record.get('timestamp', 0))
    if isinstance(ts, str):
        try:
            ts = int(datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp())
        except (ValueError, TypeError):
            ts = int(time.time())

    error_type = record.get('error_type', record.get('classification', 'runtime'))
    # 旧版格式中 error 字段是实际错误类别名（如 plan_scope_violation）
    error_field = record.get('error', '')
    classification = record.get('classification', '')
    exit_code = record.get('exit_code', record.get('retry_count', 0))
    if isinstance(exit_code, bool):
        exit_code = 1 if exit_code else 0
    exit_code = int(exit_code) if exit_code is not None else 0

    cmd = record.get('cmd', record.get('artifact', error_field or ''))
    msg = record.get('message', error_field or '')
    if not msg:
        msg = str(cmd)[:200]
    step = record.get('step', '?')

    # 旧版格式用 error/classification 作为 cmd_type
    cmd_type = classification or error_type
    if not cmd:
        cmd = error_field or 'unknown'
    cmd_family = cmd.split()[0].lower()[:32] if cmd else cmd_type[:32]
    ec_group = '0' if exit_code == 0 else '1' if exit_code == 1 else '128+' if exit_code >= 128 else '2-127'
    sig_raw = f"{error_type}:{exit_code}:{str(cmd)[:150]}:{msg[:80]}"
    sig = hashlib.md5(sig_raw.encode()).hexdigest()[:16]

    return {
        'ts': ts,
        'signature': sig,
        'fingerprint': [error_type, ec_group, step, cmd_family],
        'level': record.get('level', 'warn'),
        'resolution': record.get('resolution', 'pending'),
        'cmd': cmd,
        'exit_code': exit_code,
        'error_type': error_type,
        'message': msg,
        'session_id': record.get('session_id', 'unknown'),
        'escape_type': record.get('escape_type', ''),
        'step': step,
        'retry_count': int(record.get('retry_count', 0)),
        'error': error_field,          # 保留原始 error 字段（沉淀用）
        'classification': classification,  # 保留原始 classification
        '_source': record.get('_source', ''),  # 保留来源标记
    }


import hashlib


def _is_noise_record(record: dict) -> bool:
    """判断是否是噪声记录（应被丢弃而非沉淀）。"""
    msg = (record.get('message', '') or '').lower()
    cmd = (record.get('cmd', '') or '').lower()

    noise_keywords = [
        'shell cwd was reset',
        'narrow ',
        'could not change directory',
    ]
    for kw in noise_keywords:
        if kw in msg or kw in cmd:
            return True
    return False


def _match_rule(record: dict, rule: dict) -> bool:
    """检查一条记录是否匹配某条规则。

    条件：error_type 匹配 + exit_code 在范围内 + stderr/cmd 模式匹配。
    """
    rec_type = record.get('error_type', 'runtime')
    rule_type = rule.get('type', '')
    if rule_type == 'unknown':
        return False
    # type 匹配：规则 type 包含 auto_ 前缀时只匹配 error_type
    if rule_type.startswith('auto_'):
        # auto_ 规则用 exit_code + cmd 模式匹配
        pass
    elif rec_type != rule_type:
        return False

    exit_code = int(record.get('exit_code', 0))
    ec_ranges = rule.get('exit_code', [])
    if ec_ranges and exit_code not in ec_ranges:
        return False

    cmd = (record.get('cmd', '') or '').lower()
    stderr = record.get('message', '') or ''
    stderr_lower = stderr.lower()

    cmd_patterns = rule.get('cmd_patterns', [])
    if cmd_patterns and not any(p.lower() in cmd for p in cmd_patterns):
        return False

    stderr_patterns = rule.get('stderr_patterns', [])
    if stderr_patterns and not any(p.lower() in stderr_lower for p in stderr_patterns):
        return False

    # 如果有 cmd_patterns 或 stderr_patterns 要求，但都没命中 → 不匹配
    if cmd_patterns or stderr_patterns:
        return True

    # 如果规则没有模式要求，只匹配 type + exit_code
    return True


def _extract_pattern_group(records: list[dict]) -> dict:
    """从未分类（runtime）的错误记录中提取公共模式。

    返回: {
        'stderr_keywords': [常见 stderr 关键词],
        'cmd_families': [常见命令族],
        'exit_codes': [常见的 exit_code],
        'count': 记录数,
        'samples': [示例消息],
    }
    """
    if not records:
        return {}

    exit_codes = Counter()
    stderr_words = Counter()
    cmd_families = Counter()
    samples = []

    for r in records:
        ec = int(r.get('exit_code', 0))
        exit_codes[ec] += 1

        msg = r.get('message', '') or ''
        if msg:
            samples.append(msg[:120])
            # 提取 stderr 中的关键词（忽略标点、数字、路径）
            words = re.findall(r'[a-zA-Z_]{4,}', msg.lower())
            stderr_words.update(words)

        cmd = r.get('cmd', '') or ''
        if cmd:
            fam = cmd.strip().split()[0].lower()[:32]
            cmd_families[fam] += 1

    # 提取频率前5的关键词（排除通用词）
    stop_words = {'error', 'warning', 'info', 'debug', 'failed', 'failure',
                  'cannot', 'could', 'does', 'not', 'the', 'this', 'that',
                  'with', 'from', 'been', 'have', 'has', 'was', 'were',
                  'line', 'file', 'path', 'command', 'output'}
    sig_words = [(w, c) for w, c in stderr_words.most_common(20)
                 if w not in stop_words and len(w) > 3]

    return {
        'stderr_keywords': [w for w, _ in sig_words[:5]],
        'cmd_families': [f for f, _ in cmd_families.most_common(3)],
        'exit_codes': [ec for ec, _ in exit_codes.most_common(3)],
        'count': len(records),
        'samples': samples[:5],
    }


def _generate_rule_name(stderr_kw: list[str], cmd_families: list[str], records: list[dict] | None = None) -> str:
    """根据模式自动生成规则名。优先用已有的 classification/error 字段。"""
    # 优先从记录中提取已有的分类名
    if records:
        error_types = Counter()
        classifications = Counter()
        for r in records:
            et = r.get('_source', '') or ''
            if et:
                classifications[et] += 1
            error_field = r.get('error', '') or ''
            if error_field and error_field != 'test error':
                error_types[error_field] += 1
        # 如果有高频 error 字段（如 plan_scope_violation），用它作规则名
        if error_types:
            top_error = error_types.most_common(1)[0][0]
            # 清理路径前缀
            clean = top_error.replace('/', '_').replace('\\', '_').replace(' ', '_')
            # 如果不是路径格式，直接用它
            if not any(c in clean for c in [':', '.py', '.json', '.md']):
                return f"auto_{clean}"
        # 用 classification
        if classifications:
            top_cls = classifications.most_common(1)[0][0]
            if top_cls != 'unknown':
                return f"auto_{top_cls}"

    if cmd_families and cmd_families[0]:
        base = cmd_families[0].replace('-', '_').replace('.', '_').replace('/', '_')
        if len(base) < 40:
            return f"auto_{base}"
    if stderr_kw:
        base = stderr_kw[0].replace('-', '_').replace('.', '_')
        return f"auto_{base}"
    return f"auto_unknown_{int(time.time())}"


def _generate_rule_pattern(records: list[dict]) -> dict | None:
    """从一组相似记录生成新规则。

    规则：
    - 少于 MIN_PATTERN_FREQ 条 → 噪声，丢弃
    - 所有 exit_code 相同 → 固定 exit_code 列表
    - 提取 stderr_patterns 和 cmd_patterns
    - 严重级别按 exit_code 推断
    - 建议修复从 sample 消息推断
    """
    if len(records) < MIN_PATTERN_FREQ:
        return None

    group = _extract_pattern_group(records)
    if not group['stderr_keywords'] and not group['cmd_families']:
        return None

    # 检查是否已存在匹配该模式的auto规则
    existing = _load_rules()
    ec = group['exit_codes'][0] if group['exit_codes'] else 1

    # 推断严重级别
    severity = 'warn'
    if ec == 137 or ec == 139:
        severity = 'error'
    elif ec == 127 or ec == 126:
        severity = 'error'
    elif ec >= 128:
        severity = 'error'

    # 生成建议修复
    cmd_hint = group['cmd_families'][0] if group['cmd_families'] else ''
    ec_hint = f"exit_code={ec}" if ec else ""
    suggested_fix = f"检查 {cmd_hint} 相关错误" if cmd_hint else "检查命令输出"
    if ec == 127:
        suggested_fix = "安装缺失的命令或检查 PATH"
    elif ec == 126:
        suggested_fix = "检查文件权限"
    elif ec == 137 or ec == 139:
        suggested_fix = "减少内存使用或增加资源限制"

    return {
        'type': _generate_rule_name(group['stderr_keywords'], group['cmd_families'], records),
        'priority': AUTO_PRIORITY,
        'exit_code': [ec] if ec else [],
        'stderr_patterns': group['stderr_keywords'],
        'cmd_patterns': group['cmd_families'],
        'severity': severity,
        'action': 'investigate',
        'suggested_fix': suggested_fix,
        'auto_generated': True,
        'first_seen': int(records[0].get('ts', time.time())),
        'last_seen': int(records[-1].get('ts', time.time())),
        'frequency': len(records),
    }


def _dedup_new_rules(new_rules: list[dict], existing_rules: list[dict]) -> list[dict]:
    """新规则与已有规则去重。

    规则：如果新规则的 type 与已有规则一致，或是已有规则的相似变体，跳过。
    """
    existing_types = {r['type'] for r in existing_rules}
    deduped = []
    for rule in new_rules:
        rtype = rule['type']
        if rtype in existing_types:
            # 更新已有规则的 frequency/last_seen
            for existing in existing_rules:
                if existing['type'] == rtype:
                    existing['frequency'] = existing.get('frequency', 0) + rule.get('frequency', 0)
                    existing['last_seen'] = rule.get('last_seen', existing.get('last_seen', ''))
            continue
        # 检查是否与已有规则有相同的 stderr_patterns
        rule_stderr = set(rule.get('stderr_patterns', []))
        if rule_stderr:
            overlap = False
            for existing in existing_rules:
                existing_stderr = set(existing.get('stderr_patterns', []))
                if rule_stderr & existing_stderr:
                    overlap = True
                    break
            if overlap:
                continue
        deduped.append(rule)
    return deduped


def _archive_records(records: list[dict], archive_dir: Path) -> None:
    """归档记录：按日期分片存储。"""
    archive_dir.mkdir(parents=True, exist_ok=True)
    now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_path = archive_dir / f'precipitate-{now_str}.jsonl'
    _write_jsonl(archive_path, records)


def run_precipitation(force: bool = False, dry_run: bool = False) -> dict[str, Any]:
    """执行沉淀主流程。

    返回汇总信息。
    """
    now = time.time()
    summary = {
        'status': 'ok',
        'total_records': 0,
        'classified': 0,
        'new_rules': 0,
        'noise_dropped': 0,
        'archived': 0,
        'rule_updates': 0,
        'errors': [],
    }

    # ─── Step 1: 读取并统一格式 ───
    records = _load_jsonl(DNA_PATH)
    legacy_records = _load_jsonl(LEGACY_DNA_PATH)

    if not records and not legacy_records:
        summary['status'] = 'no_data'
        return summary

    # 统一格式
    all_records = [_normalize_record(r) for r in records]
    all_records.extend(_normalize_record(r) for r in legacy_records)
    summary['total_records'] = len(all_records)

    if not all_records:
        summary['status'] = 'no_data'
        return summary

    # ─── Step 2: 检查阈值 ───
    if not force and len(all_records) < PRECIP_THRESHOLD:
        summary['status'] = 'below_threshold'
        summary['threshold'] = PRECIP_THRESHOLD
        return summary

    # ─── Step 3: 过滤噪声 ───
    clean_records = [r for r in all_records if not _is_noise_record(r)]
    summary['noise_dropped'] = len(all_records) - len(clean_records)

    # ─── Step 4: 加载现有规则 ───
    existing_rules = _load_rules()
    summary['existing_rules'] = len(existing_rules)

    # ─── Step 5: 匹配规则 → 分组 → 生成新规则 ───
    classified_records = []
    unclassified_records = []
    matched_rule_types = Counter()

    for record in clean_records:
        matched = False
        for rule in existing_rules:
            if _match_rule(record, rule):
                matched = True
                matched_rule_types[rule['type']] += 1
                # 更新已有规则的 last_seen 和 frequency
                break
        if matched:
            classified_records.append(record)
        else:
            unclassified_records.append(record)

    summary['classified'] = len(classified_records)
    if matched_rule_types:
        summary['matched_rule_stats'] = dict(matched_rule_types.most_common(10))

    # ─── Step 6: 按 fingerprint 分组未匹配记录 ───
    if unclassified_records:
        # 按 fingerprint 分组
        fp_groups: dict[str, list[dict]] = defaultdict(list)
        for record in unclassified_records:
            fp = '|'.join(record.get('fingerprint', ['unknown']))
            fp_groups[fp].append(record)

        summary['unclassified_groups'] = len(fp_groups)
        summary['unclassified_details'] = {
            fp: len(group)
            for fp, group in sorted(fp_groups.items(), key=lambda x: -len(x[1]))
        }

        # 生成新规则
        new_rules = []
        for fp, group in fp_groups.items():
            rule = _generate_rule_pattern(group)
            if rule:
                new_rules.append(rule)

        if new_rules:
            # 去重：先合并同 type 的新规则
            merged: dict[str, dict] = {}
            for rule in new_rules:
                rtype = rule['type']
                if rtype in merged:
                    # 合并频率和模式
                    merged[rtype]['frequency'] = merged[rtype].get('frequency', 0) + rule.get('frequency', 0)
                    existing_pat = set(merged[rtype]['stderr_patterns'])
                    new_pat = set(rule.get('stderr_patterns', []))
                    merged_pat = existing_pat | new_pat
                    merged[rtype]['stderr_patterns'] = sorted(merged_pat, key=lambda x: -len(x))[:8]
                    existing_cmd = set(merged[rtype]['cmd_patterns'])
                    new_cmd = set(rule.get('cmd_patterns', []))
                    merged[rtype]['cmd_patterns'] = sorted(existing_cmd | new_cmd)[:5]
                    ec = set(merged[rtype]['exit_code']) | set(rule.get('exit_code', []))
                    merged[rtype]['exit_code'] = sorted(ec)
                else:
                    merged[rtype] = dict(rule)
            # 再与已有规则去重
            new_rules = _dedup_new_rules(list(merged.values()), existing_rules)
            if new_rules:
                if not dry_run:
                    existing_rules.extend(new_rules)
                    _write_rules(existing_rules)
                summary['new_rules'] = len(new_rules)
                summary['new_rule_names'] = [r['type'] for r in new_rules]
                summary['new_rule_details'] = [
                    {
                        'type': r['type'],
                        'exit_code': r['exit_code'],
                        'stderr_patterns': r['stderr_patterns'],
                        'cmd_patterns': r['cmd_patterns'],
                        'frequency': r.get('frequency', 0),
                    }
                    for r in new_rules
                ]

    # ─── Step 7: 更新已有规则的 frequency ───
    rule_updates = 0
    for rule_type, count in matched_rule_types.items():
        for rule in existing_rules:
            if rule['type'] == rule_type:
                old_freq = rule.get('frequency', 0)
                new_freq = old_freq + count
                if new_freq != old_freq:
                    rule['frequency'] = new_freq
                    rule_updates += 1
                break

    if rule_updates > 0 and not dry_run:
        _write_rules(existing_rules)
    summary['rule_updates'] = rule_updates

    # ─── Step 8: 归档清空 ───
    if dry_run:
        return summary

    # 归档本次沉淀的记录
    _archive_records(all_records, ARCHIVE_DIR)
    summary['archived'] = len(all_records)

    # 清空主文件
    _write_jsonl(DNA_PATH, [])

    # 如果 legacy 文件存在，也清空
    if LEGACY_DNA_PATH.exists():
        _write_jsonl(LEGACY_DNA_PATH, [])

    # 标记沉淀时间
    PRECIP_MARKER.parent.mkdir(parents=True, exist_ok=True)
    PRECIP_MARKER.write_text(str(int(now)))

    return summary


# ═══════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════

def main():
    force = '--force' in sys.argv
    dry_run = '--dry-run' in sys.argv

    result = run_precipitation(force=force, dry_run=dry_run)

    # 输出汇总
    print('=== error-dna 沉淀结果 ===')
    if result['status'] == 'no_data':
        print('  无数据可沉淀')
        sys.exit(0)

    if result['status'] == 'below_threshold':
        print(f'  低于阈值 ({result["total_records"]}/{result["threshold"]})，跳过沉淀')
        sys.exit(0)

    print(f'  总记录: {result["total_records"]}')
    print(f'  噪声丢弃: {result["noise_dropped"]}')
    print(f'  已有规则匹配: {result["classified"]}')
    print(f'  新增规则: {result["new_rules"]}')
    print(f'  已有规则更新: {result["rule_updates"]}')
    print(f'  归档: {result["archived"]}')

    if result.get('new_rule_names'):
        print('  ── 新规则 ──')
        for r in result.get('new_rule_details', []):
            print(f'    + {r["type"]}: exit_code={r["exit_code"]}, patterns={r["stderr_patterns"]}, freq={r["frequency"]}')

    if result.get('matched_rule_stats'):
        print('  ── 命中频率前 5 的规则 ──')
        for rule_type, count in list(result['matched_rule_stats'].items())[:5]:
            print(f'    {rule_type}: ×{count}')

    if dry_run:
        print('  [DRY RUN — 未修改任何文件]')
    else:
        print(f'  沉淀标记: {PRECIP_MARKER}')


if __name__ == '__main__':
    main()
