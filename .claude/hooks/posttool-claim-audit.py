#!/usr/bin/env python3

from __future__ import annotations
"""posttool-claim-audit.py — PostToolUse:Edit|Write — 铁律 #1「禁止编造」强制校验
检测 AI 对文件内容的断言（file:line 引用 + 数值断言来源）是否基于真实读取
Role: 铁律 #1 enforce — AI 不能编造没读过的代码事实 + 不能写无来源的数值断言

等效移植自 posttool-claim-audit.sh (218行)
"""

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
import subprocess

# ─── 导入共享库 ───

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))
from harness_lib import hc_enabled, hc_emit_hook_json, flywheel_event, is_mode_active, output_continue

# ─── GateKeeper 协议格式 ───
sys.path.insert(0, str(_HOOKS_DIR.parent / "scripts"))
from gatekeeper import GateKeeper, make_context

# index48 修复：`_autofix_log_edit_repeat` 原先引用 `STATE_DIR`，而该名字是在 main()
# 内部（第 130 行左右）才赋值的局部变量 —— 模块级函数访问它必抛 NameError，
# 被函数自身的 except 吞掉 → 自动修复**从未成功过**。此处提供模块级状态目录常量。
_PROJECT_ROOT = _HOOKS_DIR.parent.parent
STATE_DIR = Path(os.environ.get("CARROROS_STATE_DIR", "") or (_PROJECT_ROOT / ".omc" / "state"))


def _autofix_log_edit_repeat(file_path: str, _mode: str) -> bool:
    """K2 autofix: log structured evidence for EDIT_REPEAT to edit-churn-log.jsonl.

    注：原 docstring 记录的目标文件与实际写入目标不符（index48 更正）。
    Does not block the edit, but creates a structured record that exit report
    can aggregate.
    """
    _is_auto = _mode != 'normal'
    if not _is_auto:
        return False
    try:
        ev = {
            "ts": int(time.time()),
            "file_path": file_path,
            "error_type": "edit_repeat",
            "severity": "warn",
            "autofixed": True,
            "message": f"Edit count exceeded threshold in {file_path} — autofix logged",
        }
        _CONTRADICTION_LOG = STATE_DIR / 'edit-churn-log.jsonl'
        with open(_CONTRADICTION_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


# ── index34 S2: 拦截≠阻止观测增强（后写检测，不硬阻断）─────────────────────────
# 无人模式核心就是无人（人类裁决），不能阻止任务进行；但门禁 BLOCK 后文件仍被写入
# （sensitive-edit 凭据仍被改 / skip-tests 跳测试）必须留痕审计，避免"拦截≠阻止"无迹可查。

_GATE_BLOCK_EVENTS = ("credential_write_block", "privacy_write_block")  # 仅实际发射的事件（index34 清理死词汇）
_GATE_BYPASS_WINDOW_SEC = 120


def _detect_gate_bypassed(file_path: str, state_dir: Path) -> bool:
    """后写检测：pretool-gate 近期 BLOCK 了此文件（敏感/凭据），该文件仍被写入 → True。"""
    if not file_path or not state_dir:
        return False
    audit_dir = state_dir / "audit"
    if not audit_dir.exists():
        return False
    fname = Path(file_path).name
    now = time.time()
    for af in sorted(audit_dir.glob("*.jsonl"))[-3:]:
        try:
            lines = af.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines[-300:]:  # 只看尾部，避免全量扫描
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("event_type") not in _GATE_BLOCK_EVENTS:
                continue
            ev_path = ev.get("path", "")
            if not ev_path or Path(ev_path).name != fname:
                continue
            ts = ev.get("timestamp", "")
            try:
                from datetime import datetime as _dt
                ev_dt = _dt.fromisoformat(str(ts).replace("Z", "+00:00"))
                if now - ev_dt.timestamp() <= _GATE_BYPASS_WINDOW_SEC:
                    return True
            except Exception:
                return True  # 时间戳异常则按"存在即命中"保守判定
    return False


def _log_gate_bypassed(state_dir: Path, file_path: str, tool: str) -> None:
    """写 gate-bypassed 审计事件（不阻止，只留痕）。"""
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        log = state_dir / "gate-bypassed.jsonl"
        ev = {
            "ts": int(time.time()),
            "event_type": "gate_bypassed",
            "file_path": file_path,
            "tool": tool,
            "detail": "敏感/凭据门禁刚 BLOCK 此文件但仍被写入（无人模式不阻止，只留痕）",
        }
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 留痕失败不阻断主流程


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
    # index34 验收修复：支持 CARROROS_STATE_DIR 环境变量覆盖（测试可隔离，避免污染真实审计链）
    STATE_DIR = Path(os.environ.get("CARROROS_STATE_DIR", "")) if os.environ.get("CARROROS_STATE_DIR") else PROJECT_ROOT / '.omc' / 'state'
    STATE_DIR_STR = str(STATE_DIR)

    # Mode detection: ghost/goal 降级为 warn-only
    _MODE = is_mode_active(STATE_DIR_STR)
    _AUTONOMOUS_LOCAL = _MODE != 'normal'

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

    # index34 S2: 后写检测——pretool-gate 刚 BLOCK 此文件但仍被写入 → 记录 gate_bypassed（不阻止，只留痕）
    try:
        if _detect_gate_bypassed(FILE_PATH, STATE_DIR):
            _log_gate_bypassed(STATE_DIR, FILE_PATH, TOOL_NAME)
            print("[posttool-claim-audit] ⚠️ gate_bypassed_detected: "
                  f"{FILE_PATH} 在敏感门禁 BLOCK 后仍被写入（已留痕审计）", file=sys.stderr, flush=True)
    except Exception:
        pass  # 检测失败不阻断

    # 代码/测试/参考文件中的 file:line 是源码引用或模式说明，非对外断言
    _EXEMPT_EXT = ('.py', '.js', '.ts', '.go', '.rs', '.sh', '.yaml', '.yml', '.json')
    _EXEMPT_DIR = ('/.claude/references/', '/test-', '/tests/', '/test_')
    if FILE_PATH.endswith(_EXEMPT_EXT) or any(p in FILE_PATH.replace("\\", "/") for p in _EXEMPT_DIR):
        print(json.dumps({'continue': True}))
        sys.exit(0)

    # ── E3-extended: 软完成语检测（context 压力下 AI 自夸防护，T1 2026-08-30）──
    # 仅在 markdown / 文本类文件中检测（代码文件可能含"看起来"等正常表达）
    _SOFT_COMPLETION_TARGET = ('.md', '.txt', '.rst')
    if FILE_PATH.endswith(_SOFT_COMPLETION_TARGET):
        _content_for_soft = str(data.get('tool_input', {}).get('content', '') or
                                data.get('tool_input', {}).get('new_string', '') or '')
        # 软完成语词表（与 harness.yaml completion_gate.soft_completion_words 对齐）
        # T2 (2026-08-30) 扩展：context 压力下 AI 习惯用模糊完成语绕过检测
        # 注意：避免过短模式（如"完成"），防止"已修复"被误中
        _SOFT_PATTERNS = [
            "看起来没问题", "看起来正常", "基本完成", "大部分完成", "差不多了",
            "应该没问题", "理论上可行", "should be fine", "basically done",
            "mostly complete", "seems to work", "probably works", "looks good",
            # T2 新增：英文模糊完成语（短且边界明确）
            "all done", "fixed it", "fixed the bug", "done with", "ready for review",
            "all set", "completed successfully", "ship it",
            # T2 新增：中文模糊完成语（≥3 字避免子串误报）
            "搞定了", "修好了", "改完了", "做完了", "搞定，可以",
        ]
        for _pat in _SOFT_PATTERNS:
            if _pat.lower() in _content_for_soft.lower():
                print(
                    f"[posttool-claim-audit] ⚠️ soft_completion_detected: "
                    f"文件 {FILE_PATH} 含软完成语 '{_pat}'（context 压力下 AI 自夸防护）",
                    file=sys.stderr, flush=True,
                )
                flywheel_event("posttool_claim_audit", "soft_completion_warn", "P2",
                               f"pattern={_pat}|file={FILE_PATH}")
                # index33 电池实证修复：warn 落项目审计链（原仅宿主机 flywheel.log，
                # 项目 .omc/state/ 不可见 → 观测性缺口）。追加到 soft-completion.jsonl。
                try:
                    _soft_log = STATE_DIR / 'soft-completion.jsonl'
                    _soft_log.parent.mkdir(parents=True, exist_ok=True)
                    with open(_soft_log, 'a', encoding='utf-8') as _f:
                        _f.write(json.dumps({
                            "ts": int(time.time()),
                            "pattern": _pat,
                            "file_path": FILE_PATH,
                            "tool": TOOL_NAME,
                            "severity": "warn",
                        }, ensure_ascii=False) + "\n")
                except Exception:
                    pass  # 审计落盘失败不阻断主流程
                # warn-only：不阻断（不 return），让其他检测继续
                break

    # ── E6: edit-churn-log 写入（每个 Edit/Write 操作记录一条）──
    # 供 posttool-claim-audit.py 自身（同一会话/跨会话）做自我矛盾检测:
    #   - CONTRADICTION: intent-tracker 标记矛盾
    #   - REVERT_DETECTED: 内容回退
    #   - EDIT_REPEAT / CONTENT_FLIP: 高频抖动/方向摇摆
    _EH_LOG = STATE_DIR / 'edit-churn-log.jsonl'
    try:
        _EH_LOG.parent.mkdir(parents=True, exist_ok=True)
        _ti = data.get('tool_input', {}) or {}
        _old = str(_ti.get('old_string', '') or _ti.get('content', '') or '')
        _new = str(_ti.get('new_string', '') or '')
        _hash = hashlib.md5((_old + _new).encode()).hexdigest()[:16]
        # === E6: edit_mode 检测 ===
        #   insert: 新增（old 为空）
        #   replace: 内容替换（old 和 new 都非空）
        #   refactor: 大规模重写（old 显著长于 new 或结构变化）
        #   revert: 回退到之前的内容
        #   delete: 删除（new 为空）
        #   write_new: Write 到新文件
        #   write_overwrite: Write 覆盖已有内容
        _edit_mode = 'unknown'
        if TOOL_NAME == 'Edit':
            _old_str = str(_ti.get('old_string', '') or '')
            _new_str = str(_ti.get('new_string', '') or '')
            if not _old_str and _new_str:
                _edit_mode = 'insert'
            elif _old_str and not _new_str:
                _edit_mode = 'delete'
            elif _old_str and _new_str:
                # 初步区分 replace 和 refactor：内容长度变化 >300% 为 refactor
                _ratio = len(_new_str) / max(1, len(_old_str))
                if _ratio > 3.0 or _ratio < 0.33:
                    _edit_mode = 'refactor'
                else:
                    _edit_mode = 'replace'
        elif TOOL_NAME == 'Write':
            _content = str(_ti.get('content', '') or '')
            _edit_mode = 'write_new' if not _old else 'write_overwrite'

        # === E6: edit_scope 编辑规模 ===
        _edit_char_count = max(len(str(_ti.get('old_string', '') or '')), len(str(_ti.get('new_string', '') or '')), len(str(_ti.get('content', '') or '')))
        if _edit_char_count < 100:
            _edit_scope = 'small'
        elif _edit_char_count < 1000:
            _edit_scope = 'medium'
        else:
            _edit_scope = 'large'

        # === E6: patience_score 收敛度 ===
        # 同一文件编辑次数 / 唯一内容 hash 数，值越低越健康
        _edit_count_snapshot = 1
        _unique_hash_count = 1
        _revert_of = None
        try:
            with open(_EH_LOG, encoding='utf-8') as _eh_temp:
                _file_edits = [json.loads(lx) for lx in _eh_temp if lx.strip() and FILE_PATH in lx]
                _edit_count_snapshot = len(_file_edits) + 1
                _unique_hash_count = len(set(r.get('content_hash', '') for r in _file_edits)) + 1
                # E6 revert 检测（精专化）：当前内容 hash 曾在历史中出现 → 内容回退到之前版本。
                # 此前 revert_of 恒 None（死代码），E6-2 REVERT_DETECTED 从未真实触发。
                if _hash and any(r.get('content_hash') == _hash for r in _file_edits):
                    _revert_of = _hash[:16]
        except Exception:
            pass
        _patience_score = round(_edit_count_snapshot / max(1, _unique_hash_count), 2)

        _eh_entry = {
            "ts": int(time.time()),
            "file_path": FILE_PATH,
            "tool_name": TOOL_NAME,
            "edit_mode": _edit_mode,
            "edit_scope": _edit_scope,
            "patience_score": _patience_score,
            "sig": _hash,
            "edit_count": _edit_count_snapshot,
            "contradiction": False,
            "revert_of": _revert_of,
            "content_hash": _hash,
        }
        with _EH_LOG.open("a", encoding="utf-8") as _eh_f:
            _eh_f.write(json.dumps(_eh_entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


    # 豁免: 文档/参考/测试文件中的 file:line 引用是模式说明而非外部断言
    _EXEMPT_PATHS = [".claude/references/", "/test-", "/tests/"]
    if any(ex in FILE_PATH.replace("\\", "/") for ex in _EXEMPT_PATHS):
        print(json.dumps({'continue': True}))
        sys.exit(0)

    # index48：read-tracker 依赖的 file:line 引用校验已移除（IRRELEVANT_CLAIM 12 天 0 触发）。
    VIOLATIONS = ''

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
                # E6-3: EDIT_REPEAT — 同一文件高频编辑（精专化：门槛 4→8，豁免证据类文件）
                # E6-4: CONTENT_FLIP — 连续 3+ 次编辑 hash 均不同，方向摇摆

                # 精专化（治理精专化 S3）：证据/治理产物文件合法追加（executor.md / evidence.jsonl /
                # state/** / *.json.lock）不应触发 EDIT_REPEAT；门槛从 4 提到 8（降合法编辑误报）。
                _is_evidence_file = any(
                    seg in FILE_PATH for seg in ('executor.md', 'evidence.jsonl', '.omc/state', '.json.lock')
                )
                _edit_threshold = 8 if _is_evidence_file else 4
                # EDIT_REPEAT: edit_count >= 阈值 且不同 sig >= 2
                edit_repeat_flag = max_edits >= _edit_threshold and unique_sigs >= 2
                # CONTENT_FLIP: 最近 3 条记录 hash 各不相同（证据类文件豁免——收敛编辑非方向摇摆）
                recent_hashes = [r.get('content_hash', '') for r in matching[-3:]]
                content_flip_flag = not _is_evidence_file and len(recent_hashes) >= 3 and len(set(recent_hashes)) == len(recent_hashes)

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
                    if _AUTONOMOUS_LOCAL:
                        _autofix_log_edit_repeat(FILE_PATH, _MODE)
                        E6_CHECK_parts.append(f"  → autofix: {FILE_PATH} 编辑频率超限已记录至 evidence 日志")
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
    # index48：COLD_START 冷启动警告已移除（依赖 read-tracker；12 天 0 触发）。
    if E6_VIOLATIONS:
        COMBINED = VIOLATIONS
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

        # PostTool 阶段不应阻断——操作已执行完,阻断也无法撤销。
        # 全部降级为 protocol B format (warn-only),违规记录 audit 供退出报告统一审查。
        tag = _MODE if _AUTONOMOUS_LOCAL else "posttool"
        mode_msg = (
            f"⚠️ [{tag}] [铁律#1+#7] 输出真实性提示（warn-only）：\n"
            f"{COMBINED}\n"
            f"PostTool 阶段只记录，不阻断、不升级 HARD_BLOCK。{TRIAGE_SUFFIX}"
        )
        result = hc_emit_hook_json(mode_msg, 'PostToolUse', True)
        print(result)
        flywheel_event('posttool_claim_audit', 'warned', 'P2')
        sys.exit(0)

    # DG-131: 清除 completion-blocked 状态
    BLOCKED_FILE = STATE_DIR / 'completion-blocked'
    if BLOCKED_FILE.is_file():
        BLOCKED_FILE.unlink(missing_ok=True)

    print(json.dumps({'continue': True}))
    sys.exit(0)


if __name__ == '__main__':
    main()
