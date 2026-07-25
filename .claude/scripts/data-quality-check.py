#!/usr/bin/env python3
"""
data-quality-check.py — CarrorOS 数据质量守护进程

运行频率: 每小时 (由 cron 或 /lx-goal 任务触发)
用途: 检查 error-dna.jsonl + edit-churn-log.jsonl 的数据质量并输出报告
产出: .omc/state/data-quality-report.json + flywheel 事件

借鉴: Sentry fingerprint 精确去重 + OpenTelemetry batch processor
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# ── 路径 ──
ROOT = Path(__file__).resolve().parents[2]
OMC_STATE = ROOT / ".omc" / "state"

ERROR_DNA_PATH = OMC_STATE / "error-dna.jsonl"
EDIT_CHURN_PATH = OMC_STATE / "edit-churn-log.jsonl"
RETRY_BUDGET_PATH = OMC_STATE / "retry-budget.json"
REPORT_PATH = OMC_STATE / "data-quality-report.json"

REQUIRED_ERROR_DNA_FIELDS = {"ts", "signature", "exit_code", "error_type", "message"}
REQUIRED_EDIT_CHURN_FIELDS = {"ts", "file_path", "tool_name", "sig", "edit_mode", "edit_scope"}


def _check_jsonl(path: Path, required_fields: set[str],
                 name: str) -> dict:
    """检查一个 jsonl 文件的质量"""
    result: dict = {
        "name": name,
        "exists": path.exists(),
        "line_count": 0,
        "empty_field_count": 0,
        "empty_fields": {},
        "dup_signature_count": 0,
        "stale_count": 0,
        "issues": [],
        "metrics": {},
    }
    if not path.exists():
        result["issues"].append("FILE_MISSING")
        return result

    try:
        lines_raw = path.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        result["issues"].append(f"READ_ERROR: {e}")
        return result

    lines = [l.strip() for l in lines_raw if l.strip()]
    result["line_count"] = len(lines)

    if not lines:
        result["issues"].append("EMPTY_FILE")
        return result

    records: list[dict] = []
    for i, line in enumerate(lines):
        try:
            rec = json.loads(line)
            records.append(rec)
        except json.JSONDecodeError:
            result["issues"].append(f"JSON_DECODE_ERROR at line {i + 1}")
            continue

    # 1. 空字段检测
    for field in required_fields:
        empty = [r for r in records if not r.get(field)]
        if empty:
            cnt = len(empty)
            result["empty_field_count"] += cnt
            result["empty_fields"][field] = cnt
            result["issues"].append(f"EMPTY_FIELD:{field}×{cnt}")

    # 2. 重复 signature/sig 检测
    sig_key = "signature" if "signature" in required_fields else "sig"
    sigs = [r.get(sig_key, "") for r in records]
    deduped = len(set(sigs))
    dup_count = len(sigs) - deduped
    if dup_count > 0:
        result["dup_signature_count"] = dup_count
        result["issues"].append(f"DUP_SIG:{dup_count}")

    # 3. 过期数据（>7天）
    now = int(time.time())
    SEVEN_DAYS = 7 * 86400
    stale = [r for r in records if isinstance(r.get("ts"), (int, float)) and (now - r["ts"]) > SEVEN_DAYS]
    if stale:
        result["stale_count"] = len(stale)
        result["issues"].append(f"STALE_ROWS:{len(stale)}")

    # 4. 特有指标
    if name == "error-dna":
        types = set(r.get("error_type", "?") for r in records)
        result["metrics"]["unique_error_types"] = len(types)
        result["metrics"]["error_types"] = sorted(types)

        levels = {}
        for r in records:
            lv = r.get("level", "unknown")
            levels[lv] = levels.get(lv, 0) + 1
        result["metrics"]["levels"] = levels

        resolutions = {}
        for r in records:
            rv = r.get("resolution", "unknown")
            resolutions[rv] = resolutions.get(rv, 0) + 1
        result["metrics"]["resolutions"] = resolutions

        # 平均 message 长度
        msg_lens = [len(r.get("message", "")) for r in records]
        result["metrics"]["avg_message_len"] = round(sum(msg_lens) / max(1, len(msg_lens)), 1)

        # fingerprint 多样性
        fprints = set()
        for r in records:
            fp = r.get("fingerprint", [])
            if fp:
                fprints.add(tuple(fp))
        result["metrics"]["unique_fingerprints"] = len(fprints)

    elif name == "edit-churn":
        modes = {}
        for r in records:
            m = r.get("edit_mode", "unknown")
            modes[m] = modes.get(m, 0) + 1
        result["metrics"]["edit_modes"] = modes

        scopes = {}
        for r in records:
            s = r.get("edit_scope", "unknown")
            scopes[s] = scopes.get(s, 0) + 1
        result["metrics"]["edit_scopes"] = scopes

        # patience_score 分布
        patience_scores = [r.get("patience_score", 1.0) for r in records if isinstance(r.get("patience_score"), (int, float))]
        if patience_scores:
            result["metrics"]["patience_avg"] = round(sum(patience_scores) / len(patience_scores), 2)
            result["metrics"]["patience_min"] = round(min(patience_scores), 2)
            result["metrics"]["patience_max"] = round(max(patience_scores), 2)

        # revert_rate
        revert_count = sum(1 for r in records if r.get("revert_of"))
        result["metrics"]["revert_rate"] = round(revert_count / max(1, len(records)), 3)

    return result


def _check_retry_budget() -> dict:
    """检查 retry-budget.json"""
    result: dict = {
        "name": "retry-budget",
        "exists": RETRY_BUDGET_PATH.exists(),
        "signature_count": 0,
        "top_retries": [],
    }
    if not RETRY_BUDGET_PATH.exists():
        result["issues"] = ["FILE_MISSING"]
        return result
    try:
        data = json.loads(RETRY_BUDGET_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        result["issues"] = [f"PARSE_ERROR: {e}"]
        return result
    sigs = data.get("signatures", {})
    result["signature_count"] = len(sigs)
    # 取 retry_count 最高的5条
    sorted_sigs = sorted(sigs.items(), key=lambda x: x[1].get("retry_count", 0), reverse=True)
    result["top_retries"] = [
        {"sig": sig[:16], "retry_count": info.get("retry_count", 0),
         "label": info.get("label", "")[:60],
         "error_type": info.get("error_type", "?")}
        for sig, info in sorted_sigs[:5]
    ]
    result["issues"] = []
    return result


def _composite_score(results: list[dict]) -> float:
    """计算数据质量综合分（0-10），基于各文件检查结果"""
    deductions = 0.0
    penaltiy_config = {
        "FILE_MISSING": 3.0,
        "EMPTY_FILE": 2.0,
        "JSON_DECODE_ERROR": 1.5,
        "EMPTY_FIELD": 0.5,
        "DUP_SIG": 0.3,
        "STALE_ROWS": 0.2,
    }
    for r in results:
        for issue in r.get("issues", []):
            for pattern, penalty in penaltiy_config.items():
                if issue.startswith(pattern) or issue == pattern:
                    deductions += penalty
                    break
    return max(0.0, round(10.0 - deductions, 1))


def main():
    # 检查各文件
    error_dna_result = _check_jsonl(ERROR_DNA_PATH, REQUIRED_ERROR_DNA_FIELDS, "error-dna")
    edit_churn_result = _check_jsonl(EDIT_CHURN_PATH, REQUIRED_EDIT_CHURN_FIELDS, "edit-churn")
    retry_result = _check_retry_budget()

    score = _composite_score([error_dna_result, edit_churn_result, retry_result])

    report = {
        "ts": int(time.time()),
        "score": score,
        "checks": [error_dna_result, edit_churn_result, retry_result],
        "summary": {
            "total_issues": sum(len(r.get("issues", [])) for r in [error_dna_result, edit_churn_result, retry_result]),
            "total_lines": error_dna_result["line_count"] + edit_churn_result["line_count"],
        },
    }

    # 写入报告
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
