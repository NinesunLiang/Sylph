#!/usr/bin/env python3
"""posttool-claim-audit.py — PostToolUse:Edit|Write — 铁律 #1「禁止编造」强制校验
检测 AI 对文件内容的断言（file:line 引用 + 数值断言来源）是否基于真实读取
Role: 铁律 #1 enforce — AI 不能编造没读过的代码事实 + 不能写无来源的数值断言

等效移植自 posttool-claim-audit.sh (218行)
"""

import json
import os
import re
import sys
from pathlib import Path

# ─── 导入共享库 ───

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, is_mode_active, output_continue


def main():
    # ─── hc_enabled 门禁 ───
    if not hc_enabled('posttool_claim_audit'):
        output_continue()
        return

    # 读取 stdin
    INPUT = sys.stdin.read()

    # ─── 路径初始化 ───
    SCRIPT_DIR = _HOOKS_DIR
    PROJECT_ROOT = (SCRIPT_DIR / '../..').resolve()
    STATE_DIR = PROJECT_ROOT / '.omc' / 'state'
    STATE_DIR_STR = str(STATE_DIR)

    # Mode detection: ghost/goal 降级为 warn-only
    _MODE = is_mode_active(STATE_DIR_STR)
    _AUTONOMOUS = _MODE != 'normal'

    # ─── 解析 JSON ───
    try:
        data = json.loads(INPUT)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"continue": True}))
        sys.exit(0)
    TOOL_NAME = data.get('tool_name', '') or ''

    # 仅审计 Edit/Write
    if TOOL_NAME not in ('Edit', 'Write'):
        print(json.dumps({'continue': True}))
        sys.exit(0)

    # 提取 file_path
    FILE_PATH = data.get('tool_input', {}).get('file_path', '') or ''
    if not FILE_PATH:
        FILE_PATH = data.get('args', {}).get('filePath', '') or ''

    # 无路径 → 放行
    if not FILE_PATH:
        print(json.dumps({'continue': True}))
        sys.exit(0)

    READ_LOG = STATE_DIR / 'read-tracker.txt'

    # 提取所有 file:line 引用（AGENTS.md:42, kernel.go:15 等）
    CLAIMED_FILES = re.findall(r'(?:\.?/)?[a-zA-Z0-9_./-]+\.[a-z]+:[0-9]+', INPUT)
    # Apply sed cleanup similar to original: strip leading ./
    CLAIMED_FILES = [f.lstrip('./') for f in CLAIMED_FILES]

    # 读取 read-tracker
    read_files = ''
    _READ_TRACKER_EXISTS = True
    if READ_LOG.is_file():
        read_files = READ_LOG.read_text(encoding='utf-8', errors='replace')
    else:
        _READ_TRACKER_EXISTS = False

    # 检测 claim 文件是否在 read-tracker 中
    CLAIMED_BASENAMES = set()
    CLAIMED_DIRS = set()
    for cf in CLAIMED_FILES:
        cf_path = cf.split(':')[0]
        CLAIMED_BASENAMES.add(os.path.basename(cf_path))
        CLAIMED_DIRS.add(os.path.dirname(cf_path))

    VIOLATIONS = ''
    for claimed in CLAIMED_FILES:
        if not claimed:
            continue

        claimed_path = re.sub(r':[0-9]*$', '', claimed)

        # 检查1: read-tracker 中有完整路径匹配
        try:
            resolved = os.path.realpath(os.path.join('.', claimed_path))
        except Exception:
            resolved = claimed_path
        if read_files and resolved in read_files.splitlines():
            continue

        # 检查2: basename 匹配
        basename = os.path.basename(claimed_path)
        if read_files and '/' + basename in read_files:
            continue

        # 检查3: dirname 下有同名文件被 Read
        claim_dir = os.path.dirname(claimed_path)
        found = False
        for d in CLAIMED_DIRS:
            if not d:
                continue
            candidate = d + '/' + basename
            if read_files and candidate in read_files:
                found = True
                break
        if found:
            continue

        VIOLATIONS += '⚠️ IRRELEVANT_CLAIM: ' + claimed + '\n'

    # === G1 数值断言来源强制检查 ===
    G1_VIOLATIONS = ''
    NUM_CLAIMS = re.findall(
        r'[0-9]{1,3}\.[0-9]+%|[0-9]{1,3}%|通过率|[0-9]+%[-~][0-9]+%|减少\s*[0-9]+%?|提升\s*[0-9]+%?|'
        r'节省\s*[0-9]+%?|降低\s*[0-9]+%?|1/[0-9]+|[0-9]+倍|[0-9]+/[0-9]+\s*(?:passed|通过|pass)|'
        r'[0-9]+\s*(?:out of|of|项|个)\s*[0-9]+|\+[0-9]+\.[0-9]+|\+[0-9]+%|[0-9]+\s*分|'
        r'得分\s*[0-9]+|[0-9]+\s*轮|[0-9]+\s*次|[0-9]{2,}\s*条',
        INPUT
    )

    if NUM_CLAIMS:
        HAS_SOURCE = bool(re.search(
            r'(ASVS|OWASP|NIST|ISO|CWE|CVE|ATLAS|benchmark\.report|benchmark-report|'
            r'baseline|cross-platform-gain|pass-rate-summary|\[已验证|\[已测试|\[内部自检|'
            r'VERIFIED|https?://|[a-zA-Z0-9_./-]+\.[a-z]+:[0-9]+|source:|ref:|來源|'
            r'出处|根据.*统计|harness\.smoke|production\.verify|audit\.hooks|auto\.score|'
            r'flywheel\.log|\d+/\d+\s*(?:passed|通过)|实测|实测数据)',
            INPUT
        ))
        if not HAS_SOURCE:
            NUM_SAMPLE = ' '.join(NUM_CLAIMS[:5])
            if 'docs/marketing/' in FILE_PATH:
                G1_VIOLATIONS = ('⚠️ G1_MARKETING_CLAIM: 营销文档中的数值断言(' + NUM_SAMPLE +
                                 ')无来源引用。\n  营销文案中的任何百分比/倍数/增减数字必须附带验证来源。'
                                 '失去真实感，99% 的前面努力都浪费了。\n  修复: 在数字后标注来源，如 '
                                 "'(20 轮实测数据，benchmark-report.md:291)' 或 '[内部自检，非行业标准]'。\n")
            else:
                G1_VIOLATIONS = ('⚠️ G1_PSEUDO_INTEGRITY: 数值断言(' + NUM_SAMPLE +
                                 ')无来源。请标注 [内部自检，非行业标准] 或附加来源 URL/file:line。\n')

    # === E6 自我矛盾检测 ===
    E6_VIOLATIONS = ''
    CONTRADICTION_LOG = STATE_DIR / 'edit-churn-log.jsonl'
    if CONTRADICTION_LOG.is_file() and FILE_PATH:
        E6_CHECK = ''
        try:
            matching = []
            with open(CONTRADICTION_LOG, encoding='utf-8') as f:
                for line in f:
                    if FILE_PATH in line:
                        try:
                            matching.append(json.loads(line.strip()))
                        except Exception:
                            pass
            if len(matching) >= 2:
                contradicted = [r for r in matching if r.get('contradiction') is True]
                reverted = [r for r in matching if r.get('revert_of') is not None]
                max_edits = max((r.get('edit_count', 0) for r in matching), default=0)
                unique_sigs = len(set(r.get('sig', '') for r in matching))

                # E6-1: CONTRADICTION — intent-tracker 显式标记矛盾
                # E6-2: REVERT_DETECTED — 内容回退（revert_of 非空）
                # E6-3: EDIT_REPEAT — 同一文件高频编辑 ≥4 次，可能未收敛
                # E6-4: CONTENT_FLIP — 连续 3+ 次编辑 hash 均不同，方向摇摆

                # EDIT_REPEAT: edit_count >= 4 且不同 sig >= 2
                edit_repeat_flag = max_edits >= 4 and unique_sigs >= 2
                # CONTENT_FLIP: 最近 3 条记录 hash 各不相同
                recent_hashes = [r.get('content_hash', '') for r in matching[-3:]]
                content_flip_flag = len(recent_hashes) >= 3 and len(set(recent_hashes)) == len(recent_hashes)

                if contradicted:
                    E6_CHECK_parts = [f"[E6] CONTRADICTION: {FILE_PATH} — {len(contradicted)} 条标记为 contradiction=true"]
                    for c in contradicted[:2]:
                        E6_CHECK_parts.append(f"  · sig={c.get('sig','')[:16]}... type={c.get('type','?')}")
                    E6_CHECK = '\n'.join(E6_CHECK_parts)
                elif reverted:
                    E6_CHECK_parts = [f"[E6] REVERT_DETECTED: {FILE_PATH} — {len(reverted)} 条 revert_of 非空"]
                    for r in reverted[:2]:
                        E6_CHECK_parts.append(f"  · revert_of={r.get('revert_of','')[:16]}...")
                    E6_CHECK = '\n'.join(E6_CHECK_parts)
                elif edit_repeat_flag:
                    E6_CHECK_parts = [f"[E6] EDIT_REPEAT: {FILE_PATH} — 编辑{max_edits}次，{unique_sigs}个签名，可能未收敛"]
                    E6_CHECK = '\n'.join(E6_CHECK_parts)
                elif content_flip_flag:
                    E6_CHECK_parts = [f"[E6] CONTENT_FLIP: {FILE_PATH} — 最近3次编辑hash均不同，方向摇摆"]
                    E6_CHECK = '\n'.join(E6_CHECK_parts)
                elif max_edits > 10 and unique_sigs > 3:
                    # HIGH_CHURN: only stderr, not a violation
                    print(f"[E6] HIGH_CHURN: {FILE_PATH} — {len(matching)} 条编辑, {unique_sigs} 个签名, 最高 {max_edits} 次 (非矛盾)", file=sys.stderr, flush=True)
            else:
                pass
        except Exception:
            pass

        if E6_CHECK:
            if 'CONTRADICTION' in E6_CHECK or 'REVERT_DETECTED' in E6_CHECK or 'EDIT_REPEAT' in E6_CHECK or 'CONTENT_FLIP' in E6_CHECK:
                E6_VIOLATIONS = '⚠️ E6_SELF_CONTRADICTION: ' + E6_CHECK + '\n'
                flywheel_event('posttool_claim_audit', 'e6_pattern_detected', 'P2')
            else:
                # HIGH_CHURN: stderr only
                print(E6_CHECK, file=sys.stderr, flush=True)

    # ─── 组合违规 ───
    if VIOLATIONS or G1_VIOLATIONS or E6_VIOLATIONS:
        if not _READ_TRACKER_EXISTS and CLAIMED_FILES:
            VIOLATIONS = ('⚠️ NO_READ_HISTORY: zero files read this session — all file:line claims are unverifiable. '
                          'Read the referenced file before claiming its content.\n' + VIOLATIONS)

        COMBINED = VIOLATIONS
        if G1_VIOLATIONS:
            COMBINED += '\n' + G1_VIOLATIONS
        if E6_VIOLATIONS:
            COMBINED += '\n' + E6_VIOLATIONS

        # ── issue-triage 集成 ──
        TRIAGE_SUFFIX = ''
        triage_script = SCRIPT_DIR / '..' / 'scripts' / 'issue-triage.sh'
        if triage_script.exists():
            import subprocess
            try:
                # issue-triage.sh uses `source` so we run it via bash -c
                triage_cmd = ('source ' + str(triage_script) +
                              ' && triage_for_hook "posttool-claim-audit" "' +
                              '铁律#1虚假断言: ' + COMBINED.replace('"', '\\"').replace('$', '\\$') +
                              '" "P0" "{}" 2>/dev/null || echo ""')
                result = subprocess.run(
                    ['bash', '-c', triage_cmd],
                    capture_output=True, text=True, timeout=10
                )
                TRIAGE_MSG = result.stdout.strip()
                if TRIAGE_MSG:
                    TRIAGE_SUFFIX = '\n' + TRIAGE_MSG
            except Exception:
                pass

        if _AUTONOMOUS:
            # 自主模式: 降级为 warn-only
            mode_msg = f'⚠️ [{_MODE}] [铁律#1+#7] AI 输出真实性违规 (warn-only):\n{COMBINED}\n自主模式下降级为 warn — 违规已记录，退出报告时统一审查.{TRIAGE_SUFFIX}'
            result = hc_emit_hook_json(mode_msg, 'PostToolUse', True)
            print(result)
            flywheel_event('posttool_claim_audit', 'blocked', 'P2')
            sys.exit(0)
        else:
            block_msg = f'⛔ [铁律#1+#7] AI 输出真实性违规:\n{COMBINED}\n宪法: "禁止编造" + "任何数值断言必须有可验证来源"\n请修复以上违规项后重试.{TRIAGE_SUFFIX}'
            result = hc_emit_hook_json(block_msg, 'PostToolUse', False)
            print(result)
            flywheel_event('posttool_claim_audit', 'blocked', 'P2')
            sys.exit(2)

    # DG-131: 清除 completion-blocked 状态
    BLOCKED_FILE = STATE_DIR / 'completion-blocked'
    if BLOCKED_FILE.is_file():
        BLOCKED_FILE.unlink(missing_ok=True)

    print(json.dumps({'continue': True}))
    sys.exit(0)


if __name__ == '__main__':
    main()
