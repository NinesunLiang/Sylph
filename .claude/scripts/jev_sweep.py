#!/usr/bin/env python3
"""jev_sweep.py — P1-a 离线 JEV-C shadow。

对**已完成任务**逐条规则轮询 Jev，产出清单与案例账本。**不接 verify 路径，不改任何既有状态。**

用法：
    python3 .claude/scripts/jev_sweep.py --task-dir .omc/tasks/<date>/<name>
    python3 .claude/scripts/jev_sweep.py --task-dir ... --dry-run     # 只算不写盘

环境变量：
    OPENROUTER_API_KEY   仅从环境读，绝不落盘
    CARROROS_JEV_MODEL  可选，默认 typesafe/jev-1.13；拒绝 jev-latest 别名

设计边界（必须一直成立）：
  · 不写 token / plan / executor / audit
  · 不调用 complete_step_atomic，不改变任何 Goal 状态
  · 不阻断任何流程
  · 判不了「行为」，只判得了「行为的痕迹」；痕迹缺失只能判证据不足
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
MODEL_FROZEN = "typesafe/jev-1.13"
TIMEOUT = 90
MAX_STATE_CHARS = 9000

VERDICT_OK = "符合"
VERDICT_BAD = "不符合"
VERDICT_NA = "不适用"
VERDICT_INSUFFICIENT = "证据不足"
VERDICT_UNDECIDED = "不能判定"
VERDICT_UNAVAILABLE = "UNAVAILABLE"

_SECRET_RE = re.compile(r"sk-or-v1-[A-Za-z0-9]+")

REQUIRED_RULE_FIELDS = (
    "rule_id", "source", "text", "rule_target", "judge_by",
    "criteria_true", "criteria_false", "failure_action",
)
VALID_JUDGES = ("script", "jev", "hybrid")


# ── 安全 ───────────────────────────────────────────────────────────
def assert_no_secret(text: str) -> None:
    """任何要落盘或打印的内容都必须先过这一关。"""
    m = _SECRET_RE.search(text or "")
    if m:
        raise ValueError("检测到疑似密钥，拒绝写入")


# ── 登记表 ─────────────────────────────────────────────────────────
def load_registry(path: Path) -> dict:
    import yaml  # 局部导入，避免调用方为此付出启动成本

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    defaults = data.get("defaults") or {}
    for rule in data.get("rules", []):
        rule.setdefault("accept_at", defaults.get("accept_at", 0.85))
        rule.setdefault("reject_at", defaults.get("reject_at", 0.30))
        rule.setdefault("confidence_at", defaults.get("confidence_at", 0.55))
    return data


def validate_registry(registry: dict) -> list[str]:
    """返回问题清单；空列表表示合格。

    本表的检测对象是 **commit 内容**，因此只收代码类规则。
    行为类规则一律拒收：AI 行为在检测时已成定局，事后算账零价值，
    应当由执行前引导 + 执行中 hook 门禁承载。
    """
    problems: list[str] = []
    seen: set[str] = set()
    for i, rule in enumerate(registry.get("rules", [])):
        rid = rule.get("rule_id", f"<#{i}>")
        for field in REQUIRED_RULE_FIELDS:
            if not rule.get(field):
                problems.append(f"{rid}: 缺字段 {field}")
        if rid in seen:
            problems.append(f"{rid}: rule_id 重复")
        seen.add(rid)
        target = rule.get("rule_target")
        if target == "behavior":
            problems.append(
                f"{rid}: 行为类规则不得进入本表；"
                "行为应由执行前引导 + 执行中 hook 门禁承载，不做事后检测"
            )
        elif target != "code":
            problems.append(f"{rid}: rule_target 必须为 code")
        if rule.get("judge_by") not in VALID_JUDGES:
            problems.append(f"{rid}: judge_by 非法")
        for key in ("accept_at", "reject_at"):
            v = rule.get(key)
            if not isinstance(v, (int, float)) or not (0.0 <= float(v) <= 1.0):
                problems.append(f"{rid}: {key} 非法")
        if isinstance(rule.get("accept_at"), (int, float)) and isinstance(
            rule.get("reject_at"), (int, float)
        ):
            if float(rule["reject_at"]) >= float(rule["accept_at"]):
                problems.append(f"{rid}: reject_at 必须小于 accept_at")
    problems.extend(_validate_changelog(registry))
    return problems


def _validate_changelog(registry: dict) -> list[str]:
    """判据改动必须留痕：版本号要与变更记录最新一条对得上。

    没有这条，案例账本里记的 registry_version 就是假的，
    回放出来的「改动前 / 改动后」根本分不清是哪一版判据。
    """
    problems: list[str] = []
    version = registry.get("registry_version")
    log = registry.get("changelog") or []
    if not log:
        problems.append("缺 changelog：判据改动必须留痕")
        return problems
    if log[0].get("version") != version:
        problems.append(
            f"registry_version({version}) 与 changelog 最新一条({log[0].get('version')}) 不一致；"
            "改判据时必须同时抬高版本号并追加记录"
        )
    for i, entry in enumerate(log):
        if not entry.get("version"):
            problems.append(f"changelog 第 {i + 1} 条缺 version")
        if not entry.get("changes"):
            problems.append(f"changelog 第 {i + 1} 条缺 changes")
    return problems


def check_sources(registry: dict, root: Path) -> list[str]:
    """校验登记表里的规则原文确实来自真源，防止跑偏。"""
    mismatches: list[str] = []
    for rule in registry.get("rules", []):
        src = str(rule.get("source", ""))
        if ":" not in src:
            mismatches.append(f"{rule['rule_id']}: source 格式应为 FILE:LINE")
            continue
        fname, _, lineno = src.rpartition(":")
        fpath = Path(root) / fname
        if not fpath.is_file():
            mismatches.append(f"{rule['rule_id']}: 真源文件不存在 {fname}")
            continue
        lines = fpath.read_text(encoding="utf-8").splitlines()
        try:
            n = int(lineno)
        except ValueError:
            mismatches.append(f"{rule['rule_id']}: 行号非法 {lineno}")
            continue
        if not (1 <= n <= len(lines)):
            mismatches.append(f"{rule['rule_id']}: 行号 {n} 越界（{fname} 共 {len(lines)} 行）")
            continue
        if rule["text"].strip() not in lines[n - 1]:
            mismatches.append(
                f"{rule['rule_id']}: 规则原文与 {src} 不一致，登记表可能跑偏"
            )
    return mismatches


def split_by_judge(rules: list[dict]) -> tuple[list[dict], list[dict]]:
    """分成 (脚本判定, 需要送 Jev)。"""
    script_rules = [r for r in rules if r["judge_by"] == "script"]
    jev_rules = [r for r in rules if r["judge_by"] in ("jev", "hybrid")]
    return script_rules, jev_rules


def primitive_for(rule: dict) -> str:
    return "choice" if rule.get("allow_not_applicable") else "noul"


def build_questions(rules: list[dict], subject: str = "本次改动") -> dict:
    """每条规则一个问题；规则原文必须完整进 criteria。

    subject 是**判定对象的名字**。默认判「本次改动」（扫 commit 时用）；
    体检存量资源时要传「这个存量机制文件」——否则 Jev 会去判一个根本不存在的
    「改动」，问题问错了，答案再准也没用。
    """
    questions: dict[str, Any] = {}
    for rule in rules:
        prim = primitive_for(rule)
        base: dict[str, Any] = {
            "type": prim,
            "instructions": f"{subject}是否满足下面这条 CarrorOS 规则？",
        }
        if prim == "noul":
            base["criteria"] = {
                "true": f"{subject}符合这条规则。规则原文：{rule['text']}。判据：{rule['criteria_true']}",
                "false": f"{subject}违反这条规则。规则原文：{rule['text']}。判据：{rule['criteria_false']}",
            }
        else:
            base["criteria"] = {
                "符合": f"{subject}符合这条规则。规则原文：{rule['text']}。判据：{rule['criteria_true']}",
                "不符合": f"{subject}违反这条规则。规则原文：{rule['text']}。判据：{rule['criteria_false']}",
                "不适用": f"{subject}与该规则无关，且证据不足以判定",
            }
        questions[rule["rule_id"]] = base
    return questions


# ── 判定 ───────────────────────────────────────────────────────────
def _valid_prob(p: Any) -> bool:
    if isinstance(p, bool) or not isinstance(p, (int, float)):
        return False
    f = float(p)
    if f != f:  # NaN
        return False
    return 0.0 <= f <= 1.0


def verdict_from_noul(prob: Any, accept_at: float, reject_at: float) -> str:
    if not _valid_prob(prob):
        return VERDICT_UNAVAILABLE
    p = float(prob)
    if p >= accept_at:
        return VERDICT_OK
    if p <= reject_at:
        return VERDICT_BAD
    return VERDICT_INSUFFICIENT


def verdict_from_choice(choice: Any, confidence: Any, threshold: float) -> str:
    """三值判定。

    **低置信一律不给结论。** 模型自己没把握时，无论它选了哪个选项，
    结论都是「不能判定」—— 不能把瞎猜包装成违规，也不能包装成通过。

    低置信的条目不是丢掉，而是走另一条路：
    关键的升级给人类复核，看是不是**规则本身有问题**导致的，借此优化判据。
    """
    if not _valid_prob(confidence):
        return VERDICT_UNAVAILABLE
    if float(confidence) < threshold:
        return VERDICT_UNDECIDED
    return {
        "符合": VERDICT_OK,
        "不符合": VERDICT_BAD,
        "不适用": VERDICT_NA,
    }.get(str(choice), VERDICT_UNAVAILABLE)


def _added_lines(change_text: str, suffixes: list[str] | None = None) -> list[str]:
    """从 unified diff 里取新增行，可按文件后缀过滤。

    只取 '+' 开头且不是 '+++' 的行 —— 判「改了什么」，不判「原本就有什么」。
    """
    out: list[str] = []
    cur_ok = True
    for line in (change_text or "").splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            cur_ok = True
            if suffixes:
                cur_ok = any(path.endswith(s) for s in suffixes)
            continue
        if line.startswith("--- ") or line.startswith("diff --git"):
            continue
        if line.startswith("+") and cur_ok:
            out.append(line[1:])
    return out


def _check_one(check: dict, change_text: str, changed_paths: list[str], root: Path) -> dict:
    """跑一条脚本检查。返回 {ok: bool|None, note: str}；ok=None 表示不适用。"""
    kind = check.get("kind")
    suffixes = check.get("suffixes")

    if kind == "forbidden_pattern":
        hits = [p for p in check.get("patterns", []) if p in "\n".join(_added_lines(change_text, suffixes))]
        return {"ok": not hits, "note": f"命中禁用片段：{hits}" if hits else "未出现禁用片段",
                "applicable": bool(suffixes) is False or bool(_added_lines(change_text, suffixes))}

    if kind == "forbidden_regex":
        rx = re.compile(check["regex"])
        hits = [ln for ln in _added_lines(change_text, suffixes) if rx.search(ln)]
        return {"ok": not hits, "note": f"命中 {len(hits)} 行：{hits[:2]}" if hits else "未命中",
                "applicable": bool(suffixes) is False or bool(_added_lines(change_text, suffixes))}

    if kind == "line_limit":
        over = []
        for p in changed_paths or []:
            if not any(p.endswith(s) for s in check.get("suffixes", [])):
                continue
            f = Path(root) / p
            if f.is_file():
                n = len(f.read_text(encoding="utf-8", errors="replace").splitlines())
                if n > check["max"]:
                    over.append(f"{p}({n}行)")
        touched = [p for p in changed_paths or []
                   if any(p.endswith(s) for s in check.get("suffixes", []))]
        return {"ok": not over, "note": f"超限：{over}" if over else "未超限",
                "applicable": bool(touched)}

    if kind == "path_forbidden":
        rx = re.compile(check["regex"])
        hits = [p for p in changed_paths or [] if rx.search(p)]
        return {"ok": not hits, "note": check.get("note", "") + (f" 命中：{hits}" if hits else ""),
                "applicable": True}

    if kind == "port_declaration":
        allowed = {str(x) for x in check.get("allowed", [])}
        bad = []
        for p in changed_paths or []:
            if Path(p).name not in check.get("basenames", []):
                continue
            f = Path(root) / p
            if not f.is_file():
                continue
            for m in re.findall(r"\b(?:port|PORT)\b\D{0,8}(\d{2,5})", f.read_text(encoding="utf-8", errors="replace")):
                if m not in allowed:
                    bad.append(f"{p}:{m}")
        return {"ok": not bad, "note": f"非 9001 端口：{bad}" if bad else "端口合规",
                "applicable": any(Path(p).name in check.get("basenames", []) for p in changed_paths or [])}

    return {"ok": None, "note": f"未知检查类型 {kind}", "applicable": False}


def evaluate_script_rule(
    rule: dict, change_text: str, changed_paths: list[str], root: Path
) -> dict:
    """跑一条脚本类规则。不调模型，退出码即结论。"""
    checks = rule.get("script_check") or []
    if not checks:
        return {"verdict": VERDICT_UNAVAILABLE, "evidence": "规则未配置 script_check",
                "applicable": False}
    results = [_check_one(c, change_text, changed_paths, root) for c in checks]
    applicable = [r for r in results if r.get("applicable")]
    if not applicable:
        return {"verdict": VERDICT_NA, "evidence": "本次改动不涉及该规则管的东西",
                "applicable": False}
    bad = [r for r in applicable if r["ok"] is False]
    if bad:
        return {"verdict": VERDICT_BAD,
                "evidence": "；".join(r["note"] for r in bad), "applicable": True}
    return {"verdict": VERDICT_OK,
            "evidence": "；".join(r["note"] for r in applicable), "applicable": True}


def http_error_action(code: int) -> str:
    if code in (400, 401, 402, 403):
        return "fatal"
    if code == 413:
        return "shard"
    if code == 429:
        return "retry_after"
    return "unavailable"


def ensure_frozen_model(model: str) -> str:
    m = (model or "").strip()
    if not m or "latest" in m or "~" in m:
        raise ValueError(f"审计跑必须使用冻结模型 ID，拒绝：{model!r}")
    return m


# ── Jev 客户端 ─────────────────────────────────────────────────────
class JevClient:
    """只读 HTTP 客户端。key 只从环境变量读，绝不落盘。"""

    def __init__(self, api_key: str | None = None, endpoint: str = ENDPOINT):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.endpoint = endpoint

    def judge(self, state: Any, questions: dict, model: str) -> dict:
        model = ensure_frozen_model(model)
        if not self.api_key:
            return {"_error": "missing_key"}
        payload = {"model": model, "state": state, "questions": questions}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            return {
                "_http_error": exc.code,
                "_action": http_error_action(exc.code),
                "_detail": detail,
            }
        except urllib.error.URLError as exc:
            # 只留类名等于没留：URLError 的 reason 才是真话
            # （超时？连不上？证书？）。实测踩过：19 次调用 12 次失败，
            # 全都只显示「URLError」，查不出任何东西。
            return {"_error": f"URLError: {exc.reason!r}"}
        except Exception as exc:  # noqa: BLE001
            return {"_error": f"{type(exc).__name__}: {exc}"}


# ── 轮询编排 ───────────────────────────────────────────────────────
def _requires_available(
    requires: str, delivery: dict | None, repo_context_available: bool = False
) -> bool:
    """规则依赖的输入是否可用。

    两种「不可用」语义完全不同，调用方要分开处理：
      delivery     不可用 → 判定单元不匹配（这条规则本来就不适用于这个单元）
      repo_context 不可用 → 输入缺失（规则适用，但我们没把事实喂进去，判不了）
    """
    if requires == "delivery":
        return bool((delivery or {}).get("available"))
    if requires == "repo_context":
        return bool(repo_context_available)
    return False


def _aggregate_answers(raw_list: list[dict]) -> dict:
    """多次采样取多数。

    单次采样意味着一个坏样本无法被发现 —— 这是 LLM-as-judge 的通行做法：
    多采几次投票，成本几乎为零（3 次约 $0.00007）。

      noul        → 取概率均值
      choice      → 取票数最多的选项，confidence 取均值
      score       → 取均值
    """
    if len(raw_list) == 1:
        return raw_list[0].get("answers") or {}

    merged: dict = {}
    ids = set()
    for r in raw_list:
        ids |= set((r.get("answers") or {}).keys())
    for qid in ids:
        variants = [r["answers"][qid] for r in raw_list if qid in (r.get("answers") or {})]
        if not variants:
            continue
        prim = variants[0].get("type")
        out = {"type": prim}
        if prim == "noul":
            vals = [v.get("noul") for v in variants if isinstance(v.get("noul"), (int, float))]
            out["noul"] = sum(vals) / len(vals) if vals else None
            out["samples"] = len(vals)
        elif prim == "choice":
            votes = [str(v.get("choice")) for v in variants if v.get("choice") is not None]
            chosen = max(set(votes), key=votes.count) if votes else None
            out["choice"] = chosen
            confs = [v.get("confidence") for v in variants if isinstance(v.get("confidence"), (int, float))]
            out["confidence"] = sum(confs) / len(confs) if confs else None
            out["agree"] = (votes.count(chosen) / len(votes)) if chosen else None
            out["probabilities"] = {}
            out["samples"] = len(votes)
        elif prim == "score":
            scores = [v.get("score") for v in variants if isinstance(v.get("score"), (int, float))]
            out["score"] = sum(scores) / len(scores) if scores else None
            confs = [v.get("confidence") for v in variants if isinstance(v.get("confidence"), (int, float))]
            out["confidence"] = sum(confs) / len(confs) if confs else None
            out["samples"] = len(scores)
        merged[qid] = out
    return merged


def _sum_usage(raw_list: list[dict]) -> dict:
    total = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}
    for r in raw_list:
        u = r.get("usage") or {}
        total["input_tokens"] += u.get("input_tokens") or 0
        total["output_tokens"] += u.get("output_tokens") or 0
        total["cost"] += u.get("cost") or 0.0
    return total


def _row(rule: dict) -> dict:
    return {
        "rule_id": rule["rule_id"],
        "rule_source": rule["source"],
        "rule_target": rule["rule_target"],
        "judge_by": rule["judge_by"],
        "accept_at": rule.get("accept_at"),
        "reject_at": rule.get("reject_at"),
        "verdict": VERDICT_UNAVAILABLE,
        "raw_choice": None,
        "uncertain_note": None,
        "escalate_for_rule_tuning": False,
        "severity": None,
        "required_action": rule.get("failure_action"),
        "evidence_refs": [],
        "explanation_by": None,
        "jev_question_id": rule["rule_id"],
        "jev_primitive": None,
        "jev_noul": None,
        "jev_choice": None,
        "jev_score": None,
        "jev_probabilities": None,
        "jev_confidence": None,
        "jev_response_id": None,
        "jev_model_resolved": None,
        "jev_provider": None,
        "jev_usage": None,
        "fallback_reason": None,
    }


def _apply_answer(row: dict, rule: dict, answer: dict | None) -> None:
    if not answer:
        row["fallback_reason"] = "answers 缺项"
        row["verdict"] = VERDICT_UNAVAILABLE
        return
    prim = answer.get("type") or primitive_for(rule)
    row["jev_primitive"] = prim
    accept = float(rule.get("accept_at", 0.85))
    reject = float(rule.get("reject_at", 0.30))
    if prim == "noul":
        row["jev_noul"] = answer.get("noul")
        row["verdict"] = verdict_from_noul(answer.get("noul"), accept, reject)
    elif prim == "choice":
        row["jev_choice"] = answer.get("choice")
        row["jev_confidence"] = answer.get("confidence")
        row["jev_probabilities"] = answer.get("probabilities")
        # 三值用 confidence 阈值：三选项均分时 confidence ≈ 0.33，
        # 沿用二值的 accept_at 会让绝大多数判定落进「证据不足」。
        conf_at = float(rule.get("confidence_at", accept))
        row["verdict"] = verdict_from_choice(
            answer.get("choice"), answer.get("confidence"), conf_at
        )
        # 低置信不给结论，但原始信号要留档：它可能是**规则本身有问题**的证据。
        conf = answer.get("confidence")
        if row["verdict"] == VERDICT_UNDECIDED:
            row["raw_choice"] = answer.get("choice")
            row["uncertain_note"] = (
                f"模型置信度 {conf} 低于阈值 {conf_at}，不给结论。"
                f"若该规则标了 escalate_when_uncertain，需人工看是不是规则判据有问题"
            )
    else:
        row["jev_score"] = answer.get("score")
        row["jev_probabilities"] = answer.get("probabilities")
        row["jev_confidence"] = answer.get("confidence")
        row["verdict"] = VERDICT_INSUFFICIENT
    if row["verdict"] == VERDICT_UNAVAILABLE:
        row["fallback_reason"] = "概率非法或缺失"


def run_sweep(
    *,
    task_dir: Path | None,
    out_dir: Path | None,
    client: Any,
    registry: dict,
    rules_to_judge: list[dict],
    dry_run: bool = False,
    model: str = MODEL_FROZEN,
    purpose: str = "",
    change_text: str = "",
    delivery: dict | None = None,
    changed_paths: list[str] | None = None,
    repo_context: str = "",
    root: Path | None = None,
    samples: int = 1,
    subject: str = "本次改动",
) -> dict:
    """跑一轮规则轮询。不写 token/plan/executor/audit，只写 out_dir 下的清单。"""
    model = ensure_frozen_model(model)
    root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    judged_ids = {r["rule_id"] for r in rules_to_judge}
    all_rules = registry.get("rules", [])

    ctx_available = bool((repo_context or "").strip())
    state = {
        "purpose": purpose,
        "change_kind": classify_change(changed_paths or []),
        "changed_paths": (changed_paths or [])[:50],
        "change": (change_text or "")[:MAX_STATE_CHARS],
        "delivery": delivery or {"available": False, "reason": "未提供交付物信息"},
        # 由主 LLM 收集整理的上下文（仓库已有实现、相关约定等）。
        # 工具不自己采集 —— 收集与总结上下文是 LLM 的活。
        "repo_context": repo_context or "（未提供；判「是否复用已有能力」时会因此判不准）",
        "repo_context_available": ctx_available,
    }

    answers: dict = {}
    response_meta: dict = {}
    if rules_to_judge and client is not None:
        questions = build_questions(rules_to_judge, subject)
        tries = max(1, int(samples))
        raw_list = []
        for _ in range(tries):
            raw = client.judge(state, questions, model) if hasattr(client, "judge") else {}
            if isinstance(raw, dict) and "answers" in raw:
                raw_list.append(raw)
        if raw_list:
            answers = _aggregate_answers(raw_list)
            first = raw_list[0]
            response_meta = {
                "jev_response_id": [r.get("id") for r in raw_list],
                "jev_model_resolved": first.get("model"),
                "jev_provider": first.get("provider"),
                "jev_usage": _sum_usage(raw_list),
                "jev_samples": len(raw_list),
            }
        else:
            raw = client.judge(state, questions, model) if hasattr(client, "judge") else {}
            response_meta = {"_error": (raw or {}).get("_error") or (raw or {}).get("_http_error")}

    results: list[dict] = []
    covered: list[str] = []
    skipped: list[dict] = []

    for rule in all_rules:
        rid = rule["rule_id"]

        # 脚本类规则就地判定，不调模型。
        if rule["judge_by"] == "script":
            sc = evaluate_script_rule(rule, state["change"], changed_paths or [], root)
            if not sc["applicable"] and sc["verdict"] == VERDICT_NA:
                skipped.append({"rule_id": rid, "reason": "本次改动不涉及该规则"})
                continue
            row = _row(rule)
            row["verdict"] = sc["verdict"]
            row["evidence_refs"] = [sc["evidence"]]
            results.append(row)
            covered.append(rid)
            continue

        if rid not in judged_ids:
            skipped.append({"rule_id": rid, "reason": "不在本次 rules_to_judge 集合内"})
            continue
        row = _row(rule)
        _apply_answer(row, rule, answers.get(rid))
        # 低置信 + 关键规则 → 升级给人类复核规则判据（不是复核这次改动）。
        if row["verdict"] != VERDICT_OK and rule.get("escalate_when_uncertain"):
            if row["verdict"] in (VERDICT_UNDECIDED, VERDICT_INSUFFICIENT):
                row["escalate_for_rule_tuning"] = True
        # 看不到的东西不能判违规：证据源不可用且会判「不符合」时，降级为「证据不足」。
        # 注意只在会判「不符合」时降级 —— 服务层失败（UNAVAILABLE）本就不是违规判定。
        requires = rule.get("requires")
        if requires and not _requires_available(requires, delivery, ctx_available):
            # 记下「这条根本没问到模型」—— 它不该算进「模型答上来没有」的分母。
            # 否则一条被上下文闸门挡住的关键规则，就能把「整批拿不到答案」的告警压掉。
            row["gated_by_requires"] = requires
            if requires == "delivery":
                # 判定单元不匹配：该规则只适用于「任务」单元，这里是「改动」单元。
                row["verdict"] = VERDICT_NA
                row["fallback_reason"] = (
                    f"该规则要求 {requires}，当前判定单元不含它；"
                    "要判它请用任务单元（--task-dir 或 --commit + --delivery-dir）"
                )
            else:
                # 输入缺失：规则适用，但我们没把事实喂进去。
                # 这里**不能判「不适用」** —— 那是逃逸；也**不能判「符合」** —— 那是放水。
                # 只能老实说「判不了」。
                row["verdict"] = VERDICT_INSUFFICIENT
                row["fallback_reason"] = (
                    f"该规则要求 {requires}，但本次没有提供；"
                    "缺了它就判不准，所以不给结论。请由主 LLM 收集上下文后重跑"
                )
        if row["verdict"] != VERDICT_UNAVAILABLE:
            row.update(response_meta)
        results.append(row)
        covered.append(rid)

    summary = {
        "checked": len(results),
        "script_rules_checked": sum(1 for r in results if r["judge_by"] == "script"),
        "not_covered": len(skipped),
        "blocked_by_missing_context": [
            r["rule_id"] for r in results
            if r["verdict"] == VERDICT_INSUFFICIENT
            and next((x.get("requires") for x in all_rules if x["rule_id"] == r["rule_id"]), None)
            == "repo_context"
        ],
        "violated": [
            r["rule_id"] for r in results if r["verdict"] == VERDICT_BAD
        ],
        "undecided": [
            r["rule_id"] for r in results if r["verdict"] == VERDICT_UNDECIDED
        ],
        # 低置信 + 关键规则 → 升级给人，但目的不是「判这次」，
        # 而是看**规则判据是不是有问题**，借此优化规则。
        "escalate_for_rule_tuning": [
            {"rule_id": r["rule_id"], "raw_choice": r.get("raw_choice"),
             "note": "低置信，可能是规则判据需要优化"}
            for r in results if r.get("escalate_for_rule_tuning")
        ],
        "insufficient": [r["rule_id"] for r in results if r["verdict"] == VERDICT_INSUFFICIENT],
        # 「拿不到答案」不是判定结果。没钥匙/没余额时 Jev 规则会整批落到这里。
        # 必须单独报出来：否则「静默什么都没做」和「一切正常」长得一模一样。
        "unavailable": [r["rule_id"] for r in results if r["verdict"] == VERDICT_UNAVAILABLE],
        "total_cost": (response_meta.get("jev_usage") or {}).get("cost"),
    }

    checklist = {
        "schema_version": "carros.jev_checklist.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "shadow",
        "changes_flow": False,
        "model_requested": model,
        "task_dir": str(task_dir) if task_dir else None,
        "covered_rule_ids": covered,
        "skipped_rule_ids": skipped,
        "results": results,
        "summary": summary,
    }

    assert_no_secret(json.dumps(checklist, ensure_ascii=False))

    # 低置信 + 关键规则 → 自动进待复核队列，让规则自己攒样本。
    # 复核的目的不是判这一次，而是看**规则判据**有没有问题。
    if not dry_run and out_dir is not None:
        try:
            import jev_fit as _jf

            for item in summary.get("escalate_for_rule_tuning", []):
                rid = item["rule_id"]
                _jf.enqueue_pending({
                    "review_id": f"p-{hashlib.sha256(f'{rid}{state['change'][:200]}'.encode()).hexdigest()[:12]}-{rid}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "rule_id": rid,
                    "registry_version": registry.get("registry_version"),
                    "purpose": purpose,
                    "change": state["change"],
                    "changed_paths": (changed_paths or [])[:50],
                    "repo_context": state.get("repo_context", ""),
                    "jev": next(
                        ({"verdict": r["verdict"], "noul": r.get("jev_noul"),
                          "choice": r.get("jev_choice") or r.get("raw_choice"),
                          "confidence": r.get("jev_confidence")}
                         for r in results if r["rule_id"] == rid),
                        {},
                    ),
                    "human": None,
                })
        except ImportError:
            pass  # 队列可选，装不上不影响扫描

    if not dry_run and out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "checklist.json").write_text(
            json.dumps(checklist, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out_dir / "checklist.md").write_text(
            _render_markdown(checklist), encoding="utf-8"
        )
        with (out_dir / "cases.jsonl").open("a", encoding="utf-8") as fh:
            for row in results:
                # UNAVAILABLE = 「拿不到答案」，不含关于这次改动的任何信息。
                # 记下来只会把账本灌满噪声：实测一次没钥匙的空转 = 8 行垃圾，
                # 跑几天就是几千行，把「待复核队列」和一致率统计一起淹掉。
                if row["verdict"] == VERDICT_UNAVAILABLE:
                    continue
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    return checklist


def _render_markdown(checklist: dict) -> str:
    lines = [
        "# JEV-C shadow 清单",
        "",
        f"- 生成时间：{checklist['generated_at']}",
        f"- 模式：{checklist['mode']}（不改变任何完成流程）",
        f"- 检测对象：**本次 commit 的改动内容**（不检测 AI 行为）",
        f"- 模型：`{checklist['model_requested']}`",
        "",
        "| 规则 | 判定 | 说明 |",
        "|---|---|---|",
    ]
    for row in checklist["results"]:
        lines.append(
            f"| `{row['rule_id']}` | {row['verdict']} | "
            f"{row['required_action'] or ''} |"
        )
    s = checklist["summary"]
    esc = s.get("escalate_for_rule_tuning") or []
    if esc:
        lines += ["", "## 需人工复核（低置信，疑似规则判据问题）", ""]
        for e in esc:
            lines.append(
                f"- `{e['rule_id']}`：模型原选「{e['raw_choice']}」但置信度不足，"
                "不给结论。请判断是本次改动本身模糊，还是**规则判据需要优化**。"
            )
    lines += [
        "",
        "## 汇总",
        "",
        f"- 已判定：{s['checked']} 条",
        f"- 未覆盖：{s['not_covered']} 条",
        f"- 不符合：{s['violated'] or '无'}",
        f"- 不能判定（低置信，不给结论）：{s['undecided'] or '无'}",
        f"- 证据不足：{s['insufficient'] or '无'}",
        f"- 成本：{s['total_cost']}",
        "",
        "## 未覆盖",
        "",
    ]
    for sk in checklist["skipped_rule_ids"]:
        lines.append(f"- `{sk['rule_id']}`：{sk['reason']}")
    return "\n".join(lines) + "\n"


def _collect_change_text(task_dir: Path) -> str:
    """只读任务目录里的文档当改动上下文，不读 token、不碰 git。"""
    parts = []
    for name in ("plan.md", "executor.md", "research.md"):
        p = Path(task_dir) / name
        if p.is_file():
            parts.append(f"### {name}\n{p.read_text(encoding='utf-8')}")
    return "\n\n".join(parts)


CODE_SUFFIXES = (
    ".py", ".ts", ".tsx", ".js", ".jsx", ".scss", ".css", ".json",
    ".sh", ".yaml", ".yml", ".toml", ".sql", ".html",
)


def classify_change(changed_paths: list[str]) -> str:
    """判断本次改动的性质，供规则决定「适不适用」。

    实测教训：纯文档任务没有测试，但没说清性质时会被判成「不符合」，
    正确结论应是「不适用」。
    """
    if not changed_paths:
        return "unknown"
    code = [p for p in changed_paths if p.lower().endswith(CODE_SUFFIXES)]
    if not code:
        return "docs_only"
    if len(code) == len(changed_paths):
        return "code_only"
    return "mixed"


def collect_commit_change(
    commit: str, paths: list[str] | None = None
) -> tuple[str, str, list[str]]:
    """取一个 commit 的改动内容 —— 这是本工具的**主检测对象**。

    返回 (purpose, change_text, changed_paths)。只读 git，不改任何东西。
    """
    import subprocess

    def run(args: list[str]) -> str:
        out = subprocess.run(args, capture_output=True, text=True, check=False)
        return out.stdout if out.returncode == 0 else ""

    purpose = run(["git", "show", "-s", "--format=%s", commit]).strip()
    name_cmd = ["git", "show", "--name-only", "--format=", commit]
    if paths:
        name_cmd += ["--", *paths]
    changed = [ln for ln in run(name_cmd).splitlines() if ln.strip()]

    cmd = ["git", "show", "--format=", commit]
    if paths:
        cmd += ["--", *paths]
    return purpose, run(cmd)[:MAX_STATE_CHARS], changed


def _headings(text: str, level: str = "##") -> list[str]:
    import re as _re

    pat = rf"^{_re.escape(level)}\s+(.+?)\s*$"
    return [m.strip() for m in _re.findall(pat, text, flags=_re.M)]


def collect_delivery(task_dir: Path | None) -> dict:
    """采集交付物事实。

    文档优先是 CarrorOS 的机制，所以这里**把文档的骨架摘出来**，
    而不是用字符串硬匹配某个词 —— 同一个意思可能写成「依赖树」也可能写成「依赖结论」，
    硬匹配会把表述差异误判成交付缺失。摘出标题交给 Jev 判，更稳也更诚实。

    只读；能数清的都数清，数不清的留给 Jev。
    """
    import re as _re

    if task_dir is None:
        return {"available": False, "reason": "未提供任务目录，无法判交付物类规则"}

    task_dir = Path(task_dir)
    texts: dict[str, str] = {}
    present: dict[str, bool] = {}
    for name in ("research.md", "plan.md", "executor.md"):
        p = task_dir / name
        present[name] = p.is_file()
        texts[name] = p.read_text(encoding="utf-8") if p.is_file() else ""

    etext = texts["executor.md"]
    ev_ids = _re.findall(r"^###\s+(EV-[\w.-]+)", etext, flags=_re.M)
    ev_types = _re.findall(r"^-\s*type:\s*(\S+)\s*$", etext, flags=_re.M)
    exit_codes = _re.findall(r"^-\s*exit_code:\s*(\S+)\s*$", etext, flags=_re.M)

    return {
        "available": True,
        "task_dir": str(task_dir),
        "docs_present": present,
        "research_sections": _headings(texts["research.md"]),
        "plan_sections": _headings(texts["plan.md"]),
        "executor_sections": _headings(texts["executor.md"]),
        "plan_has_acceptance": ("acceptance:" in texts["plan.md"]),
        "plan_has_verify": ("verify:" in texts["plan.md"]),
        "executor_evidence_blocks": len(ev_ids),
        "executor_evidence_ids": ev_ids[:20],
        "executor_evidence_types": sorted(set(ev_types)),
        "executor_test_blocks": sum(1 for t in ev_types if t == "test"),
        "executor_blocks_with_exit_code": len(exit_codes),
        "executor_has_failure_evidence": any(c not in ("0", "null") for c in exit_codes),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="P1-a 离线 JEV-C shadow（只读、不改流程）——检测 commit 内容是否符合规则"
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--task-dir", help="按任务目录检测（同时提供文档与验证记录事实）")
    src.add_argument("--commit", help="**主检测对象**：按某个 commit 的改动内容检测")
    src.add_argument("--change-file", help="按一个 diff 文件检测（如 git diff > x.patch）")
    ap.add_argument("--paths", nargs="*", default=None, help="配合 --commit，限定只看这些路径")
    ap.add_argument(
        "--delivery-dir",
        default=None,
        help="配合 --commit 使用：从该任务目录采集交付物事实（用于文档/TDD/影响范围类规则）",
    )
    ap.add_argument("--rules", default=str(Path(__file__).resolve().parent / "jev_rules.yaml"))
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--model", default=os.environ.get("CARROROS_JEV_MODEL", MODEL_FROZEN))
    ap.add_argument("--dry-run", action="store_true", help="只算不写盘")
    ap.add_argument(
        "--samples", type=int, default=1,
        help="多次采样取多数（推荐 3；单次采样时一个坏样本无法被发现）",
    )
    ap.add_argument(
        "--context-file", default=None,
        help="主 LLM 整理好的仓库上下文（markdown/文本）。工具不自己采集，只负责传进去",
    )
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parents[2]
    registry = load_registry(Path(args.rules))

    problems = validate_registry(registry) + check_sources(registry, root)
    if problems:
        for p in problems:
            print(f"ERROR: {p}", file=sys.stderr)
        return 2

    delivery_dir: Path | None = None
    changed_paths: list[str] = []
    if args.commit:
        purpose, change_text, changed_paths = collect_commit_change(args.commit, args.paths)
        label = args.commit
        if args.delivery_dir:
            delivery_dir = Path(args.delivery_dir).resolve()
            if not delivery_dir.is_dir():
                print(f"ERROR: 交付目录不存在：{delivery_dir}", file=sys.stderr)
                return 2
    elif args.change_file:
        cf = Path(args.change_file)
        if not cf.is_file():
            print(f"ERROR: diff 文件不存在：{cf}", file=sys.stderr)
            return 2
        change_text = cf.read_text(encoding="utf-8")[:MAX_STATE_CHARS]
        purpose = "(来自 diff 文件)"
        label = cf.stem
        changed_paths = [
            ln.split(" b/", 1)[-1].strip()
            for ln in change_text.splitlines() if ln.startswith("diff --git ")
        ]
    else:
        task_dir = Path(args.task_dir).resolve()
        if not task_dir.is_dir():
            print(f"ERROR: 任务目录不存在：{task_dir}", file=sys.stderr)
            return 2
        purpose = str(task_dir.name)
        change_text = _collect_change_text(task_dir)
        label = task_dir.name
        delivery_dir = task_dir
        changed_paths = ["plan.md", "executor.md", "research.md"]

    delivery = collect_delivery(delivery_dir)
    repo_context = ""
    if args.context_file:
        ctx_path = Path(args.context_file)
        if not ctx_path.is_file():
            print(f"ERROR: 上下文文件不存在：{ctx_path}", file=sys.stderr)
            return 2
        repo_context = ctx_path.read_text(encoding="utf-8")[:MAX_STATE_CHARS]
    _, jev_rules = split_by_judge(registry["rules"])
    out_dir = Path(args.out_dir) if args.out_dir else root / ".omc" / "state" / "jev" / label

    checklist = run_sweep(
        task_dir=delivery_dir,
        out_dir=out_dir,
        client=JevClient(),
        registry=registry,
        rules_to_judge=jev_rules,
        dry_run=args.dry_run,
        model=args.model,
        purpose=purpose,
        change_text=change_text,
        delivery=delivery,
        changed_paths=changed_paths,
        repo_context=repo_context,
        samples=args.samples,
    )

    s = checklist["summary"]
    print("模式: shadow（不改变任何完成流程）")
    print(f"检测对象: {purpose or label} —— 只判改动内容，不判 AI 行为")
    print(f"规则: {s['checked']} 条判定 / {s['not_covered']} 条未覆盖")
    _warn_if_unavailable(checklist)
    print(f"不符合: {s['violated'] or '无'}")
    print(f"证据不足: {s['insufficient'] or '无'}")
    blocked = s.get("blocked_by_missing_context") or []
    if blocked:
        print(f"缺上下文判不了: {blocked}（由主 LLM 补 repo_context 后重跑）")
    print(f"成本: {s['total_cost']}")
    if not args.dry_run:
        print(f"清单: {out_dir}")
        pending = _count_pending()
        if pending:
            print(f"待人工复核: {pending} 条 —— "
                  f"python3 .claude/scripts/jev_fit.py pending")
    return 0


def _warn_if_unavailable(checklist: dict) -> None:
    """把「拿不到答案」的规则喊出来，尤其是 Jev 整批拿不到的时候。

    为什么必须喊：没钥匙时 Jev 规则会整批变成 UNAVAILABLE，而进程照样退出 0。
    不喊的话，「静默什么都没做」和「一切正常」在终端里长得一模一样，
    跑几天下来账本里只剩噪声，而人还以为在攒样本。
    """
    results = checklist.get("results") or []
    unavail = checklist["summary"].get("unavailable") or []
    if not unavail:
        return
    print(f"⚠️  拿不到答案: {len(unavail)} 条 → {unavail}")

    # 分母只算「真的问到模型」的规则。被 requires 闸门挡下的规则压根没发请求，
    # 把它算进来会让一条被挡住的关键规则掩盖掉「整批连不上」的事实。
    asked = [
        r for r in results
        if r.get("judge_by") != "script" and not r.get("gated_by_requires")
    ]
    jev_unavail = [r for r in asked if r["verdict"] == VERDICT_UNAVAILABLE]
    # 判据是「全问过的都没答上」而不是某个拍脑袋的比例：只可能是连接层面的问题
    # （没钥匙、钥匙失效、余额不足），不可能是改动本身。
    if asked and len(jev_unavail) == len(asked):
        print("    ↳ Jev 规则整批拿不到答案 —— 多半是钥匙缺失/失效/余额不足，不是改动有问题")


def _count_pending() -> int:
    """待复核条目数。读账本自己算，不依赖 jev_fit（避免循环依赖）。"""
    ledger = Path(__file__).resolve().parents[2] / ".omc" / "state" / "jev" / "reviews.jsonl"
    if not ledger.is_file():
        return 0
    resolved: set[str] = set()
    pending: set[str] = set()
    try:
        for line in ledger.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if e.get("kind") == "resolution":
                resolved.add(e.get("review_id"))
            elif e.get("kind") == "pending":
                pending.add(e.get("review_id"))
    except Exception:  # noqa: BLE001 —— 账本坏了不能影响扫描
        return 0
    return len(pending - resolved)


if __name__ == "__main__":
    raise SystemExit(main())
