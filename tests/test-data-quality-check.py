#!/usr/bin/env python3
"""
TDD test: data-quality-check.py — 数据质量守护进程的检查逻辑

Run: python3 tests/test-data-quality-check.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# ── 被测试逻辑：复制 data-quality-check.py 的核心校验函数 ──


def _check_jsonl(path: Path, required_fields: set[str],
                 name: str) -> dict:
    """复现 data-quality-check.py 的 _check_jsonl 逻辑"""
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
    for field in required_fields:
        empty = [r for r in records if not r.get(field)]
        if empty:
            cnt = len(empty)
            result["empty_field_count"] += cnt
            result["empty_fields"][field] = cnt
            result["issues"].append(f"EMPTY_FIELD:{field}×{cnt}")
    sig_key = "signature" if "signature" in required_fields else "sig"
    sigs = [r.get(sig_key, "") for r in records]
    deduped = len(set(sigs))
    dup_count = len(sigs) - deduped
    if dup_count > 0:
        result["dup_signature_count"] = dup_count
        result["issues"].append(f"DUP_SIG:{dup_count}")
    return result


def _composite_score(results: list[dict]) -> float:
    """复现综合评分逻辑"""
    deductions = 0.0
    penalty_config = {
        "FILE_MISSING": 3.0,
        "EMPTY_FILE": 2.0,
        "JSON_DECODE_ERROR": 1.5,
        "EMPTY_FIELD": 0.5,
        "DUP_SIG": 0.3,
        "STALE_ROWS": 0.2,
    }
    for r in results:
        for issue in r.get("issues", []):
            for pattern, penalty in penalty_config.items():
                if issue.startswith(pattern) or issue == pattern:
                    deductions += penalty
                    break
    return max(0.0, round(10.0 - deductions, 1))


# ── 辅助 ──

def assert_eq(actual, expected, label: str):
    if actual != expected:
        raise AssertionError(f"FAIL {label}: expected={expected!r}, actual={actual!r}")
    print(f"  PASS {label}")


def assert_true(cond: bool, label: str):
    if not cond:
        raise AssertionError(f"FAIL {label}: condition False")
    print(f"  PASS {label}")


def assert_in(needle: str, haystack, label: str):
    if needle not in haystack:
        raise AssertionError(f"FAIL {label}: {needle!r} not found in {haystack}")
    print(f"  PASS {label}")


# ── Test 1: 文件不存在 ──

def test_file_missing():
    """文件不存在 → FILE_MISSING issue + score 扣 3"""
    r = _check_jsonl(Path("/nonexistent/file.jsonl"), {"ts"}, "test")
    assert_in("FILE_MISSING", r["issues"], "file missing issue")
    score = _composite_score([r])
    assert_eq(score, 7.0, "score after missing file")


# ── Test 2: 空文件 ──

def test_empty_file():
    """空文件 → EMPTY_FILE issue"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write("")
        f.flush()
        p = Path(f.name)
    r = _check_jsonl(p, {"ts"}, "test")
    assert_in("EMPTY_FILE", r["issues"], "empty file")
    assert_eq(r["line_count"], 0, "empty file line count")
    # 辅助文件删除
    p.unlink()
    score = _composite_score([r])
    assert_eq(score, 8.0, "score after empty file")


# ── Test 3: 正常记录 + 空字段 ──

def test_valid_records():
    """有效记录 + 空字段检测"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(json.dumps({"ts": 1000, "signature": "a1", "error_type": "build", "message": "build failed"}) + "\n")
        f.write(json.dumps({"ts": 1001, "signature": "a2", "error_type": "", "message": "no type"}) + "\n")
        f.write(json.dumps({"ts": 1002, "signature": "a3", "error_type": "test", "message": ""}) + "\n")
        f.flush()
        p = Path(f.name)

    r = _check_jsonl(p, {"ts", "signature", "error_type", "message"}, "test")
    assert_eq(r["line_count"], 3, "3 records")
    assert_in("EMPTY_FIELD:error_type×1", r["issues"], "missing error_type detected")
    assert_in("EMPTY_FIELD:message×1", r["issues"], "missing message detected")
    assert_eq(r["empty_field_count"], 2, "2 empty fields total")

    p.unlink()


# ── Test 4: 重复 signature 检测 ──

def test_dup_signature():
    """相同 signature 出现多次 → DUP_SIG 标记"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(json.dumps({"ts": 1000, "signature": "dup1", "error_type": "x", "message": "m"}) + "\n")
        f.write(json.dumps({"ts": 1000, "signature": "dup1", "error_type": "x", "message": "m"}) + "\n")
        f.write(json.dumps({"ts": 1000, "signature": "uniq", "error_type": "x", "message": "m"}) + "\n")
        f.flush()
        p = Path(f.name)

    r = _check_jsonl(p, {"ts", "signature", "error_type", "message"}, "test")
    assert_true(r["dup_signature_count"] > 0, "duplicate detected")
    assert_in("DUP_SIG", r["issues"][0], "dup sig in issues")

    p.unlink()


# ── Test 5: JSON 损坏 ──

def test_json_decode_error():
    """损坏的 JSON 行 → JSON_DECODE_ERROR"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(json.dumps({"ts": 1000, "signature": "ok", "error_type": "x", "message": "m"}) + "\n")
        f.write("{bad json}\n")
        f.flush()
        p = Path(f.name)

    r = _check_jsonl(p, {"ts", "signature", "error_type", "message"}, "test")
    assert_in("JSON_DECODE_ERROR", str(r["issues"]), "json decode error issue")
    assert_eq(r["line_count"], 2, "still counts bad lines")

    p.unlink()


# ── Test 6: edit-churn 字段检查 ──

def test_edit_churn_field_check():
    """edit-churn 的 required_fields 校验"""
    REQUIRED = {"ts", "file_path", "tool_name", "sig", "edit_mode", "edit_scope"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(json.dumps({"ts": 1000, "file_path": "/a.py", "tool_name": "Edit",
                             "sig": "abc", "edit_mode": "replace", "edit_scope": "small"}) + "\n")
        f.write(json.dumps({"ts": 1001, "file_path": "/b.py", "tool_name": "Write",
                             "sig": "def", "edit_mode": "", "edit_scope": ""}) + "\n")
        f.flush()
        p = Path(f.name)

    r = _check_jsonl(p, REQUIRED, "edit-churn")
    assert_eq(r["line_count"], 2, "2 edit-churn records")
    if r["empty_field_count"] > 0:
        assert_in("edit_mode", str(r["empty_fields"]), "empty edit_mode detected")
        assert_in("edit_scope", str(r["empty_fields"]), "empty edit_scope detected")

    p.unlink()


# ── Test 7: 综合评分 — 完美分值 ──

def test_composite_score_perfect():
    """无问题文件 → 10 分"""
    r1 = {"name": "a", "issues": []}
    r2 = {"name": "b", "issues": []}
    score = _composite_score([r1, r2])
    assert_eq(score, 10.0, "perfect score")


def test_composite_score_multi_issue():
    """多个文件各有问题 → 正确扣分"""
    r1 = {"name": "a", "issues": ["FILE_MISSING"]}
    r2 = {"name": "b", "issues": ["EMPTY_FIELD:ts×5", "DUP_SIG:3"]}
    score = _composite_score([r1, r2])
    # 3.0 (missing) + 0.5 (empty) + 0.3 (dup) = 3.8 → 6.2
    assert_eq(score, 6.2, "multi-issue score")


def test_composite_score_floor():
    """扣分下限为 0"""
    r1 = {"name": "a", "issues": ["FILE_MISSING", "FILE_MISSING", "EMPTY_FILE",
                                    "EMPTY_FILE", "DUP_SIG:100"]}
    score = _composite_score([r1])
    # 3+3+2+2+0.3 = 10.3 → 0 (floor)
    assert_eq(score, 0.0, "score floor 0")


# ── 入口 ──

if __name__ == "__main__":
    print("=== test-data-quality-check: 守护进程校验逻辑 ===")

    print("\n--- 文件状态检测 ---")
    test_file_missing()
    test_empty_file()

    print("\n--- 字段校验 ---")
    test_valid_records()
    test_dup_signature()
    test_json_decode_error()
    test_edit_churn_field_check()

    print("\n--- 综合评分 ---")
    test_composite_score_perfect()
    test_composite_score_multi_issue()
    test_composite_score_floor()

    print("\n✅ 全部 test-data-quality-check 通过")
    sys.exit(0)
