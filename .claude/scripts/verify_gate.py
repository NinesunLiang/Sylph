#!/usr/bin/env python3
"""
CarrorOS VerifyGate

Purpose:
  Match executor.md evidence against plan.md verify rules to decide step completion.
  Only VerifyGate VERIFIED allows plan.md [x].

Commands:
  verify --step <step_id> --plan <path> --executor <path> [--token <path>]

Output:
  VERIFIED / WARN / BLOCKED / REJECTED

Constraints:
  - Python 3.10+ standard library only
  - Does not execute fixes
  - Does not alter executor evidence
  - Evidence-level enforcement:
    E3 command exit=0 > E2 file_assertion > E1 user_confirmation > E0 narrative (rejected)
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_step_evidence_validator():
    """Load validate_step_evidence via importlib from sibling step_contracts.py.
    Fail-closed: returns no-op function on any import failure."""
    try:
        _script_dir = Path(__file__).resolve().parent
        _spec = importlib.util.spec_from_file_location(
            "_verify_gate_step_contracts",
            str(_script_dir / "step_contracts.py"),
        )
        if _spec is None or _spec.loader is None:
            raise ImportError("spec_from_file_location failed")
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules["_verify_gate_step_contracts"] = _mod
        _spec.loader.exec_module(_mod)
        return _mod.validate_step_evidence
    except Exception:
        def _unavailable(*args, **kwargs):
            return ["evidence_validator_unavailable"]
        return _unavailable


validate_step_evidence = _load_step_evidence_validator()

# 降噪（index15）：中英同义词归一化映射。
# 目的不是放宽标准，而是移除「rule 英文 / EV 断言中文」时的强制双语书写负担，
# 让 AI 把 token 花在正确产出上。核心防线（soft-completion/占位）不受影响。
_I18N_SYNONYMS = [
    ("baseline", "基线"),
    ("snapshot", "快照"),
    ("exists", "存在|落盘"),
    ("evidence", "证据"),
    ("error attribution table", "报错归因表"),
    ("attribution", "归因"),
    ("old task states untouched", "未改动任何旧任务状态"),  # 复合短语整词
    ("old task states", "旧任务状态"),  # 拆解原子，允许中文侧部分命中
    ("untouched", "未改动|未改"),
    ("verified", "验证"),
    ("passed", "通过"),
    ("failed", "失败"),
    ("completed", "完成"),
    ("scorecard", "评分卡"),
    ("report generated", "报告生成"),
    ("generated", "生成"),
    ("archived", "归档"),
    ("artifacts exist", "产物落盘"),
    ("artifacts", "产物"),
    ("under artifacts", "产物目录"),
    ("regression", "回归"),
    ("cleanup script idempotent", "清理脚本幂等"),
    ("idempotent", "幂等"),
    ("backup exists", "备份存在"),
    ("backup", "备份"),
    ("green", "绿"),
    ("red", "红"),
]


def _normalize_i18n(text: str) -> str:
    """中英同义词归一化：将文本中的中英关键术语映射为统一 token，便于跨语言比对。

    仅做术语映射，不改动其余字符；soft-completion 检测走独立短语表，不受此影响。
    """
    lowered = text.lower()
    # 两阶段替换，避免术语嵌套穿透（如 "untouched" ⊂ "old task states untouched"）：
    # 阶段 1：所有术语 → 不可碰撞占位符（P0,P1,...），按英文长度降序先替换长短语；
    # 阶段 2：占位符 → ⟨术语⟩ 标记。这样替换互不干扰，杜绝二次穿透。
    placeholders: list[tuple[str, str]] = []
    for idx, (en, zh) in enumerate(_I18N_SYNONYMS):
        token = f"\x00D{idx}\x00"
        placeholders.append((en, token))
        # 中文侧可能用 | 提供多个同义变体（如 "未改动|未改"），逐个替换
        for variant in zh.split("|"):
            if variant and variant in lowered:
                lowered = lowered.replace(variant, token)
    # 英文侧按长度降序替换（长短语优先，避免短术语先命中产生穿透）
    for en, token in sorted(placeholders, key=lambda p: len(p[0]), reverse=True):
        if en in lowered:
            lowered = lowered.replace(en, token)
    # 阶段 2：占位符 → 术语标记（复合短语拆为原子标记，便于术语集覆盖比较）
    for idx, (en, _zh) in enumerate(_I18N_SYNONYMS):
        token = f"\x00D{idx}\x00"
        marker = en if " " not in en else en  # 复合短语保留整词标记（由覆盖逻辑处理）
        lowered = lowered.replace(token, f"⟨{marker}⟩")
    return lowered


def _canonical_atom(word: str) -> str:
    """Normalize English morphological forms for core-term comparison.

    Strips a trailing 's' (noun plurals / 3rd-person -s) while guarding 'ss'
    suffixes and short words, so 'exists'=='exist', 'artifacts'=='artifact'.
    '-ed/-ing' inflections are NOT stripped, keeping distinct lexemes distinct
    and avoiding false-positive matches. (index17 M1)
    """
    w = word.lower().strip()
    if w.endswith("ss") or len(w) <= 4:
        return w
    if w.endswith("s"):
        return w[:-1]
    return w


def _extract_core_terms(normalized: str) -> set[str]:
    """从归一化文本提取核心术语集（⟨...⟩ 标记的映射术语）。

    复合短语（含空格的 ⟨old task states untouched⟩）按空格拆成单词原子，
    使「术语集覆盖」比较能跨同义短语成立（rule 的原子词全在断言侧即可），
    同时保留单术语原子。用于断言匹配的判断：rule 原子词 ⊆ 断言原子词。
    原子词经 _canonical_atom 词形归一（index17 M1：exist/exists 拦截修复）。
    """
    terms: set[str] = set()
    for marked in re.findall(r"⟨([^⟩]+)⟩", normalized):
        if " " in marked:
            terms.update(_canonical_atom(w) for w in marked.split())
        else:
            terms.add(_canonical_atom(marked))
    return terms


SOFT_COMPLETION_PHRASES = [
    "应该好了", "看起来可以", "基本完成", "大概没问题",
    "已经处理", "完成了",
    "looks good", "should work", "probably fixed",
    "可以了", "没问题",
]


@dataclass
class VerifyDecision:
    decision: str  # VERIFIED | WARN | BLOCKED | REJECTED
    reason: str
    step: str
    matched: list[str]
    missing: list[str]
    warnings: list[str]
    required_action: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    # H10: 与 carros_base/carros_utils 审计文件名格式统一(%Y%m%d)
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return default or {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def parse_verify_rules(plan_text: str, step: str) -> list[str]:
    """Extract verify rules for a given step from plan.md."""
    rules: list[str] = []
    in_step = False
    step_prefixes = [f"- [ ] {step}:", f"- [x] {step}:", f"- [X] {step}:", f"- [a] {step}:", f"- [A] {step}:"]

    for line in plan_text.splitlines():
        stripped = line.strip()
        # Check if we're entering the target step
        if any(stripped.startswith(p) for p in step_prefixes):
            in_step = True
            continue
        # Exit step on next step heading or step marker
        if in_step and (stripped.startswith("- [") or stripped.startswith("## ")):
            if stripped.startswith("- [") and not any(stripped.startswith(p) for p in step_prefixes):
                break
        if in_step:
            m = re.match(r"- verify:\s*(.+)$", stripped)
            if m:
                raw = m.group(1).strip()
                # 支持一行多规则: `file: A contains "x"; file: B contains "y"` 拆成两条。
                # 顶层分号拆分, 忽略引号内分号(避免拆坏 contains "a;b")。
                parts, cur, in_q, qch = [], "", False, None
                for ch in raw:
                    if ch in ("'", '"'):
                        if in_q and ch == qch:
                            in_q = False
                        elif not in_q:
                            in_q, qch = True, ch
                    if ch == ";" and not in_q:
                        if cur.strip():
                            parts.append(cur.strip())
                        cur = ""
                    else:
                        cur += ch
                if cur.strip():
                    parts.append(cur.strip())
                rules.extend(p for p in parts if p)
    return rules


def parse_evidence(executor_text: str, step: str) -> list[dict[str, Any]]:
    """Extract only exact step evidence entries from executor.md."""
    evidence: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    include_current = False
    in_entry = False
    target_headers = {f"EV-{step}", f"FAIL-{step}"}

    def flush() -> None:
        if include_current and current.get("step") == step:
            evidence.append(dict(current))

    for line in executor_text.splitlines():
        stripped = line.strip()
        m = re.match(r"^###\s+(EV-\S+|FAIL-\S+)\s*$", stripped)
        if m:
            flush()
            header = m.group(1)
            current = {"id": header}
            include_current = header in target_headers
            if header.startswith("FAIL-"):
                current["type"] = "failure"
            in_entry = True
            continue
        if in_entry:
            for key in ("step", "type", "source", "exit_code", "file", "assertion",
                        "evidence_level", "confirmation", "change_summary", "output_tail"):
                kv = re.match(rf"- {key}:\s*(.+)$", stripped)
                if kv:
                    val = kv.group(1).strip()
                    if key == "exit_code":
                        try:
                            val = int(val)
                        except ValueError:
                            pass
                    current[key] = val
            if stripped.startswith("## "):
                flush()
                current = {}
                include_current = False
                in_entry = False

    flush()
    return evidence


def is_soft_completion(text: str) -> bool:
    lowered = text.lower().strip()
    return any(phrase.lower() in lowered for phrase in SOFT_COMPLETION_PHRASES)


# ── 真实文件验证（还债升级）：file: 规则直接读仓库内文件，不信任 AI 自述 ──
VERIFY_ROOT = Path(__file__).resolve().parents[2]


def _resolve_verified_path(expected_file: str, base_dir: Path | None = None) -> Path | None:
    """将 file: 规则路径解析为仓库内绝对路径；越界（.. 逃逸 / 仓库外）返回 None。

    index19 F1：plan.md 的 file: 规则常用任务目录相对路径（如 artifacts/xxx）。
    base_dir 存在时先尝试从 base_dir（任务目录）解析；文件在 repo 根则照旧。
    两条路径都必须在 VERIFY_ROOT 内，否则按越界拒绝。
    """
    p = Path(expected_file)
    try:
        root = VERIFY_ROOT.resolve()
    except OSError:
        return None
    candidates: list[Path] = []
    if p.is_absolute():
        candidates.append(p)
    else:
        if base_dir is not None and base_dir.exists():
            candidates.append(base_dir / p)
        candidates.append(VERIFY_ROOT / p)
    first_in_repo = None
    for cand in candidates:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved == root or root in resolved.parents:
            if resolved.exists():
                return resolved
            if first_in_repo is None:
                first_in_repo = resolved  # 仓库内但暂不存在：供调用方报 missing
    return first_in_repo


def match_verify_rule(rule: str, evidence: list[dict[str, Any]],
                      base_dir: Path | None = None) -> tuple[bool, str, list[str]]:
    """Match a single verify rule against available evidence.

    base_dir: 任务目录（executor.md 所在目录），file: 相对路径的第二解析基点。
    """
    warnings: list[str] = []

    # command: rule
    cm = re.match(r"^command:(.+)$", rule)
    if cm:
        expected_cmd = cm.group(1).strip()
        for ev in evidence:
            if ev.get("type") == "failure":
                continue
            src = str(ev.get("source", "")).strip()
            ec = ev.get("exit_code")
            el = str(ev.get("evidence_level", ""))
            if src and (src == expected_cmd or src.endswith("/" + expected_cmd) or expected_cmd.endswith(src)):
                if ec == 0 and el == "E3":
                    return True, f"command match: {src} exit=0", []
                elif ec == 0:
                    warnings.append(f"command {src} exit=0 but evidence_level={el} (expected E3)")
        return False, f"no matching command evidence for: {expected_cmd}", warnings

    # file: rule — 真实读文件验证（还债升级：不信任 AI 自述的 file/assertion 字段）
    fm = re.match(r"^file:(.+?)\s+contains\s+(.+)$", rule)
    if fm:
        expected_file = fm.group(1).strip()
        expected_assertion = fm.group(2).strip()
        # 剥离包裹引号（plan.md 里 `contains "index19"` 引号是书写习惯，非字面量）
        if len(expected_assertion) >= 2 and expected_assertion[0] == expected_assertion[-1] \
                and expected_assertion[0] in ("'", '"'):
            expected_assertion = expected_assertion[1:-1]
        resolved = _resolve_verified_path(expected_file, base_dir)
        if resolved is None:
            return False, f"file rule path outside repo: {expected_file}", warnings
        if not resolved.exists():
            return False, f"verified file missing: {expected_file}", warnings
        try:
            content = resolved.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            return False, f"cannot read verified file {expected_file}: {exc}", warnings
        # 注：真实文件读取不做 soft-completion 检测（那是防 AI 自述敷衍的，
        # 真实代码/文档内容含"should be ok"等词是正常现象，不应误判）。
        if expected_assertion.lower() in content.lower():
            return True, f"real file match: {expected_file} contains '{expected_assertion}'", []
        return False, f"real file does not contain '{expected_assertion}': {expected_file}", warnings

    # assertion: rule
    am = re.match(r"^assertion:(.+)$", rule)
    if am:
        expected_raw = am.group(1).strip().lower()
        # 降噪（index15）：中英同义词归一化 + 核心术语集匹配。
        # 目标不是放宽标准，而是移除「rule 英文 / EV 断言中文」的强制双语书写负担。
        # 匹配语义 = rule 的核心术语集必须全被断言侧覆盖（不要求结构词/顺序），
        # 保持防编造强度：soft-completion 仍拒，术语缺失仍拒。
        expected_norm = _normalize_i18n(expected_raw)
        expected_terms = _extract_core_terms(expected_norm)
        segments = [s.strip() for s in re.split(r"[;；,，。\n]+", expected_raw) if len(s.strip()) > 3]
        segments_norm = [_normalize_i18n(s) for s in segments]
        for ev in evidence:
            if ev.get("type") == "failure":
                continue
            assertion_text = str(ev.get("assertion", "")).lower()
            if is_soft_completion(assertion_text):
                warnings.append("assertion contains soft completion")
                continue
            assertion_norm = _normalize_i18n(assertion_text)
            assertion_terms = _extract_core_terms(assertion_norm)
            # 1) 整段字面子串（向后兼容，含中英归一化后）
            if expected_norm in assertion_norm or expected_raw in assertion_text:
                return True, f"assertion match: '{expected_raw}'", []
            # 2) 多数实质性分段命中（容忍插入/换序 + 中英归一化；降噪还债：all→majority，对齐 index12 文档原意）
            if segments_norm:
                hits = sum(1 for s in segments_norm if s in assertion_norm)
                if hits * 2 > len(segments_norm):
                    return True, f"assertion segment match ({hits}/{len(segments_norm)}): '{'; '.join(segments)}'", []
            # 3) 核心术语集覆盖（rule 术语 ⊆ 断言术语）——跨语言语义匹配主路径
            if expected_terms and assertion_terms and expected_terms <= assertion_terms:
                return True, f"assertion core-term match: {expected_terms}", []
            txt = str(ev.get("output_tail", "")).lower()
            txt_norm = _normalize_i18n(txt)
            if (expected_raw in txt or expected_norm in txt_norm) and ev.get("exit_code") == 0:
                return True, f"assertion in command output: '{expected_raw}'", []
            if segments_norm and ev.get("exit_code") == 0 and all(s in txt_norm for s in segments_norm):
                return True, f"assertion segments in command output: '{'; '.join(segments)}'", []
        return False, f"no matching assertion for: {expected_raw}", warnings

    return False, f"unrecognized verify rule: {rule}", warnings


def parse_spec_acs(spec_path: Path, step: str | None = None) -> list[str]:
    """Parse Acceptance Criteria from spec.md — returns list of AC rules

    spec.md 格式:
        - AC1 [command:] <desc>
        - AC2 [file:] <desc>
        - AC3 [assertion:] <desc>
    """
    spec_text = read_text(spec_path)
    if not spec_text:
        return []

    rules = []
    for line in spec_text.splitlines():
        stripped = line.strip()
        # Match: - AC1 [command:] description
        m = re.match(r"^\s*-\s*(AC\d+)\s*\[(command:|file:|assertion:)\]\s*(.+)", stripped)
        if m:
            prefix = m.group(2)  # e.g. "command:"
            desc = m.group(3).strip()
            rules.append(f"{prefix}{desc}")
            continue
        # Match: - AC1: description (no type prefix, default assertion:)
        m2 = re.match(r"^\s*-\s*(AC\d+):\s*(.+)", stripped)
        if m2:
            desc = m2.group(2).strip()
            rules.append(f"assertion:{desc}")

    return rules


def verify_step(step: str, plan_path: Path, executor_path: Path, token_path: Path | None = None,
                spec_path: Path | None = None) -> VerifyDecision:
    plan_text = read_text(plan_path)
    executor_text = read_text(executor_path)

    plan_text = read_text(plan_path)
    if not plan_text:
        return VerifyDecision("REJECTED", "plan_missing", step, [], [], [])

    executor_text = read_text(executor_path)
    if not executor_text:
        return VerifyDecision("BLOCKED", "executor_missing", step, [], [], [])

    # Parse verify rules for this step
    verify_rules = parse_verify_rules(plan_text, step)

    # Also merge AC rules from spec.md (if available)
    spec_acs = []
    if spec_path and spec_path.exists():
        spec_acs = parse_spec_acs(spec_path, step)
    all_rules = verify_rules + [r for r in spec_acs if r not in verify_rules]

    if not all_rules:
        return VerifyDecision("REJECTED", "no_verify_rules", step, [], [], [],
                              "Plan step must have verify rules or spec.md must have ACs.")
    verify_rules = all_rules

    # Check for invalid rule syntax
    valid_prefixes = ("command:", "file:", "assertion:", "user:")
    for rule in verify_rules:
        if not any(rule.startswith(p) for p in valid_prefixes):
            return VerifyDecision("REJECTED", f"invalid_verify_prefix: {rule}", step, [], [], [],
                                  "Verify rule must start with command:/file:/assertion:/user:")

    # Parse evidence
    evidence = parse_evidence(executor_text, step)
    if not evidence:
        return VerifyDecision("BLOCKED", "no_evidence_for_step", step, [], verify_rules, [])

    # Check for soft completion in evidence assertions
    for ev in evidence:
        assertion = str(ev.get("assertion", ""))
        confirmation = str(ev.get("confirmation", ""))
        if is_soft_completion(assertion) or is_soft_completion(confirmation):
            return VerifyDecision("REJECTED", "soft_completion_in_evidence", step, [], verify_rules, [])

    # Check for unresolved failures
    failures = [ev for ev in evidence if ev.get("type") == "failure"]
    # Remove failures that have subsequent covering success evidence
    for fail in failures:
        fail_action = str(fail.get("action", ""))
        # Check if there's a successful command evidence with same source
        covered = False
        for ev in evidence:
            if ev.get("type") == "failure":
                continue
            if ev.get("exit_code") == 0:
                src = str(ev.get("source", ""))
                if src and fail_action.endswith(src):
                    covered = True
                    break
        if not covered:
            return VerifyDecision("BLOCKED", f"unresolved_failure:{fail.get('id', 'unknown')}",
                                  step, [], verify_rules, [])

    # Task75: Validate evidence section completeness (Conditions, Key Changes, Decisions, AC, TDD)
    ev_structure_errors = validate_step_evidence(executor_text, step)
    if ev_structure_errors:
        return VerifyDecision("BLOCKED",
                              f"evidence_structure_incomplete: {'; '.join(ev_structure_errors[:3])}",
                              step, [], verify_rules, ev_structure_errors)

    # Match each verify rule
    matched_rules: list[str] = []
    missing_rules: list[str] = []
    all_warnings: list[str] = []

    for rule in verify_rules:
        ok, reason, warns = match_verify_rule(rule, evidence, base_dir=executor_path.parent)
        all_warnings.extend(warns)
        if ok:
            matched_rules.append(reason)
        else:
            missing_rules.append(reason)

    # Check user confirmation rules separately (weaker match needed)
    user_rules = [r for r in missing_rules if r.startswith("no matching")]
    user_verify = [r for r in verify_rules if r.startswith("user:")]
    for vr in user_verify:
        expected = vr[5:].strip().lower()
        for ev in evidence:
            if ev.get("type") != "user_confirmation":
                continue
            conf = str(ev.get("confirmation", "")).lower()
            if is_soft_completion(conf):
                all_warnings.append(f"user confirmation contains soft completion: '{conf}'")
                continue
            if len(conf) >= 8 and expected in conf:
                matched_rules.append(f"user confirmation match: '{expected}'")
                user_rules_to_remove = [r for r in missing_rules if "user:" in r]
                for rr in user_rules_to_remove:
                    if rr in missing_rules:
                        missing_rules.remove(rr)

    # Decision
    if not missing_rules and not all_warnings:
        return VerifyDecision("VERIFIED", "all_verify_rules_matched", step, matched_rules, [], [])
    elif not missing_rules and all_warnings:
        return VerifyDecision("WARN", "all_verify_matched_with_warnings", step, matched_rules, [], all_warnings)
    elif missing_rules:
        return VerifyDecision("BLOCKED", "evidence_missing", step, matched_rules, missing_rules, all_warnings)

    return VerifyDecision("BLOCKED", "unknown", step, matched_rules, missing_rules, all_warnings)


def write_audit(decision: VerifyDecision, token: dict[str, Any] | None = None) -> None:
    event = {
        "event_type": "verify_decision",
        "timestamp": now_iso(),
        "step": decision.step,
        "decision": decision.decision,
        "reason": decision.reason,
        "matched": decision.matched,
        "missing": decision.missing,
        "warnings": decision.warnings,
        "required_action": decision.required_action,
        # Round7 PKG-4(E7 校准账): claim 语义字段——每条 verify_decision 是一条
        # "本步已验证"断言,claim_id 稳定可索引,evidence_ids 回溯支撑证据,
        # status 供 jq 统计 overturn(verified→后被推翻率)。
        "claim_id": f"verify:{decision.step}",
        "evidence_ids": [f"matched:{m}" for m in decision.matched],
        "status": "verified" if decision.decision == "VERIFIED" else "unverified",
    }
    if token:
        event["task_id"] = (token.get("session", {}) or {}).get("id") \
            or token.get("task", {}).get("id", "unknown")
        event["level"] = token.get("session", {}).get("level", "unknown")
    append_jsonl(Path(".omc/audit") / f"{today()}.jsonl", event)


def self_check() -> list[str]:
    """内建自检（index19 M: 测试内建到机制能力）。

    验证 VerifyGate 自身的不变量，无需外部测试矫正：
    - 词形归一（_canonical_atom：exist/exists、ss 守卫、不同词拒匹配）
    - file 规则引号剥离（contains "x" 不按字面量含引号比较）
    启动时调用，fail-closed。返回违规列表（空 = 通过）。
    """
    violations: list[str] = []

    # 1. 词形归一不变量
    canonical_cases = {
        "exists": "exist", "artifacts": "artifact", "files": "file",
        "verify": "verify", "class": "class", "process": "process",
    }
    for word, expected in canonical_cases.items():
        got = _canonical_atom(word)
        if got != expected:
            violations.append(f"self_check canonical({word})={got} expected {expected}")

    # 2. 断言匹配：exist/exists 应匹配；不同词应拒绝（经 match_verify_rule）
    ev_match = {"type": "test", "assertion": "artifacts exists（10/10 exit 0）",
                "evidence_level": "E3", "exit_code": 0}
    ok, _, _ = match_verify_rule("assertion: artifacts exist", [ev_match])
    if not ok:
        violations.append("self_check: exist/exists core-term match failed")
    ok_reject, _, _ = match_verify_rule(
        "assertion: artifacts exist",
        [{"type": "test", "assertion": "artifacts removed from workspace",
          "evidence_level": "E3", "exit_code": 0}])
    if ok_reject:
        violations.append("self_check: distinct lexeme should not match")

    return violations


def _assert_self_check():
    """启动时调用；违规即抛错（fail-closed）。"""
    v = self_check()
    if v:
        raise RuntimeError("VerifyGate self_check failed: " + "; ".join(v))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--executor", required=True)
    parser.add_argument("--token", required=False)
    parser.add_argument("--spec", required=False,
                       help="spec.md 路径 — 可选，提供 AC 规则以增强验证")
    args = parser.parse_args()

    _assert_self_check()  # 内建自检 fail-closed（机制自身不变量）

    token = read_json(Path(args.token)) if args.token else None
    spec_path = Path(args.spec) if args.spec else None
    result = verify_step(args.step, Path(args.plan), Path(args.executor),
                         Path(args.token) if args.token else None, spec_path)

    write_audit(result, token)

    # E7: 校准日志 — 每条 VERIFIED 断言留痕,供后续 overturn 追踪
    if result.decision == "VERIFIED":
        try:
            _cal_dir = Path(__file__).resolve().parent.parent.parent / ".omc" / "state"
            _cal_dir.mkdir(parents=True, exist_ok=True)
            _cal_path = _cal_dir / "calibration-log.jsonl"

            # E7增强1: 计算置信度 confidence（规则匹配率）
            total_rules = len(result.matched) + len(result.missing)
            confidence = round(len(result.matched) / max(total_rules, 1), 3) if total_rules > 0 else 0.0

            # E7增强2: overturn 检测 — 读取审计中该 step 的决策历史
            _prev_decisions = []
            _audit_dir = _cal_dir.parent / "audit"  # .omc/audit/ — parent of .omc/state/
            if _audit_dir.exists():
                for _f in sorted(_audit_dir.glob("*.jsonl")):
                    try:
                        for _line in _f.read_text(encoding="utf-8").splitlines():
                            try:
                                _ev = json.loads(_line)
                            except json.JSONDecodeError:
                                continue
                            if (_ev.get("event_type") == "verify_decision"
                                    and _ev.get("step") == args.step):
                                past = _ev.get("decision", "")
                                if past in ("BLOCKED", "REJECTED", "WARN"):
                                    _prev_decisions.append(past)
                    except OSError:
                        continue

            _overturn = len(_prev_decisions) > 0
            if _overturn:
                _cal_record = {
                    "event_type": "calibration_overturn",
                    "timestamp": now_iso(),
                    "step": args.step,
                    "decision": "VERIFIED",
                    "overturn": True,
                    "previous_decisions": _prev_decisions,
                    "assertion": f"step {args.step} overturn alert: 此前 {len(_prev_decisions)} 次非通过({','.join(_prev_decisions)})→VERIFIED",
                    "confidence": confidence,
                    "matched_rules": result.matched,
                    "missing_rules": result.missing,
                }
                with _cal_path.open("a", encoding="utf-8") as _cal_f:
                    _cal_f.write(json.dumps(_cal_record, ensure_ascii=False, sort_keys=True) + "\n")
                    _cal_f.flush()
                print(f"⚠️ [E7:calibration_overturn] step={args.step} 此前 {len(_prev_decisions)} 次非通过 -> 当前 VERIFIED —— 过度自信风险，建议回溯验证断言有效性",
                      file=sys.stderr, flush=True)
            else:
                _cal_record = {
                    "event_type": "calibration_assertion",
                    "timestamp": now_iso(),
                    "step": args.step,
                    "decision": "VERIFIED",
                    "matched_rules": result.matched,
                    "confidence": confidence,
                    "assertion": f"step {args.step} 全部规则通过（置信度={confidence}）",
                }
                with _cal_path.open("a", encoding="utf-8") as _cal_f:
                    _cal_f.write(json.dumps(_cal_record, ensure_ascii=False, sort_keys=True) + "\n")
                    _cal_f.flush()
        except Exception:
            pass

    # GateKeeper protocol output for consistency (BLOCKED/REJECTED -> stderr guidance)
    try:
        _gk_script = Path(__file__).resolve().parent
        sys.path.insert(0, str(_gk_script))
        from gatekeeper import GateKeeper, make_context
        if result.decision in ("BLOCKED", "REJECTED"):
            _gk_ctx = make_context(
                action="verify: " + result.reason, target=result.step,
                risk="medium", has_verification=True,
            )
            _gk_r = GateKeeper.evaluate(_gk_ctx)
            _gk_msg = GateKeeper.format_output(_gk_r)
            if _gk_msg:
                sys.stderr.write(_gk_msg + "\n")
    except Exception:
        pass

    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.decision == "VERIFIED" else 1



if __name__ == "__main__":
    raise SystemExit(main())
