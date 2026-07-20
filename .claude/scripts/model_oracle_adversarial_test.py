#!/usr/bin/env python3
# DEPRECATED - 保留向后兼容，建议迁移到 meta_oracle.py (adversarial-test)
"""
model_oracle_adversarial_test.py — 对抗性烟雾测试。

覆盖 GPT-5.5 审查中指出的缺失测试（S9）：
- 破坏性 JSON 解析
- 多余文字 JSON
- 假 file:line 验证
- 降级行为
- 硬门禁优先验证
- 未验证 finding 降级
"""

import sys
import json
import os
import tempfile
from pathlib import Path

# 固定 CWD 到脚本目录，保证相对路径解析正确
_SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(str(_SCRIPT_DIR))

sys.path.insert(0, str(_SCRIPT_DIR))

from carros_oracle_base import (
    Finding, OracleReview, Evidence, Severity, RiskType,
    parse_llm_json_output_strict,
    validate_evidence_local, verify_file_line,
    downgrade_unverified_findings, llm_finding_to_finding,
    make_input_hash, check_proxy_health, reset_circuit,
    call_llm_oracle, write_oracle_verdict, audit_log,
    LLM_AVAILABLE, CIRCUIT_CLOSED,
    policy_to_gate_config, RiskPolicy,
)

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}: {detail}")


# ═══════════════════════════════════════════════
# Test 1: 严格 JSON 解析 — 正常有效
# ═══════════════════════════════════════════════
print("\n=== T1: 严格 JSON 解析 (正常) ===")
t1 = json.dumps({
    "decision": "allow",
    "severity": "low",
    "confidence": 0.9,
    "score": 9.5,
    "findings": []
})
r = parse_llm_json_output_strict(t1)
check("裸 JSON OK", r is not None and r["decision"] == "allow")

# code block
t1b = "```json\n" + t1 + "\n```"
r = parse_llm_json_output_strict(t1b)
check("```json code block OK", r is not None and r["decision"] == "allow")

# ═══════════════════════════════════════════════
# Test 2: fail-close — 多余文字
# ═══════════════════════════════════════════════
print("\n=== T2: Fail-Close (多余文字) ===")
r = parse_llm_json_output_strict("Some prefix text " + t1)
check("前缀文字 → fail-close", r is None)

r = parse_llm_json_output_strict(t1 + " some suffix")
check("后缀文字 → fail-close", r is None)

r = parse_llm_json_output_strict("```json\n" + t1 + "\n```\ntrailing")
check("code block + 尾部文字 → fail-close", r is None)

r = parse_llm_json_output_strict("")
check("空字符串 → fail-close", r is None)

r = parse_llm_json_output_strict("not json at all")
check("纯文本 → fail-close", r is None)

# ═══════════════════════════════════════════════
# Test 3: fail-close — Schema 违规
# ═══════════════════════════════════════════════
print("\n=== T3: Fail-Close (Schema 违规) ===")
r = parse_llm_json_output_strict(json.dumps({"decision": "INVALID", "score": 5}))
check("invalid decision → fail-close", r is None)

r = parse_llm_json_output_strict(json.dumps({"decision": "allow", "score": -1}))
check("score < 0 → fail-close", r is None)

r = parse_llm_json_output_strict(json.dumps({"decision": "allow", "score": 99}))
check("score > 10 → fail-close", r is None)

r = parse_llm_json_output_strict(json.dumps({"decision": "allow", "score": "not_a_number"}))
check("score 非数字 → fail-close", r is None)

# ═══════════════════════════════════════════════
# Test 4: 证据本地验证
# ═══════════════════════════════════════════════
print("\n=== T4: 证据本地验证 (file:line) ===")

# 当前目录有 carros_oracle_base.py，验证 line 1
valid, detail = verify_file_line("carros_oracle_base.py:1")
check("真实 file:line → valid", valid)
check("   detail 含 'valid:'", "valid" in detail)

valid2, detail2 = verify_file_line("/nonexistent/deadbeef.py:100")
check("不存在 file → invalid", not valid2)
check("   detail 含 file_not_found", "file_not_found" in detail2)

valid3, detail3 = verify_file_line("carros_oracle_base.py:999999")
check("超出行号 → invalid", not valid3)
check("   detail 含 line_out_of_range", "line_out_of_range" in detail3)

valid4, detail4 = verify_file_line("bad_format_without_colon")
check("无冒号格式 → invalid", not valid4)
check("   detail 含 invalid_format", "invalid_format" in detail4)

# ═══════════════════════════════════════════════
# Test 5: Finding 降级 (unverified)
# ═══════════════════════════════════════════════
print("\n=== T5: 未验证 Finding 降级 ===")

f_critical = Finding(oracle="test", severity=Severity.CRITICAL, confidence=0.9,
                      risk_type=RiskType.DESTRUCTIVE_COMMAND, verified=False)
f_high = Finding(oracle="test", severity=Severity.HIGH, confidence=0.8,
                 risk_type=RiskType.SCOPE_VIOLATION, verified=False)
f_medium = Finding(oracle="test", severity=Severity.MEDIUM, confidence=0.6,
                   risk_type=RiskType.UNKNOWN, verified=False)

down = downgrade_unverified_findings([f_critical, f_high, f_medium])
check("critical→HIGH", down[0].severity == Severity.HIGH)
check("HIGH→MEDIUM", down[1].severity == Severity.MEDIUM)
check("MEDIUM→不变", down[2].severity == Severity.MEDIUM)
check("critical reason 含 'downgraded'", "downgraded" in down[0].reason)
check("HIGH reason 含 'downgraded'", "downgraded" in down[1].reason)

# 已验证的不降级
f_verified = Finding(oracle="test", severity=Severity.CRITICAL, confidence=0.9,
                     risk_type=RiskType.DESTRUCTIVE_COMMAND, verified=True,
                     evidence=[Evidence(type="file_line", location="carros_oracle_base.py:1", content="x")])
down2 = downgrade_unverified_findings([f_verified])
check("已验证 critical → 不降级 (保持 CRITICAL)", down2[0].severity == Severity.CRITICAL)

# ═══════════════════════════════════════════════
# Test 6: validate_evidence_local
# ═══════════════════════════════════════════════
print("\n=== T6: validate_evidence_local ===")

f_valid = Finding(oracle="test", severity=Severity.HIGH, confidence=0.8,
                  risk_type=RiskType.SCOPE_VIOLATION,
                  evidence=[Evidence(type="file_line", location="carros_oracle_base.py:1", content="test")])
f_valid = validate_evidence_local(f_valid)
check("有效证据 → verified=True", f_valid.verified)

f_invalid = Finding(oracle="test", severity=Severity.HIGH, confidence=0.8,
                    risk_type=RiskType.SCOPE_VIOLATION,
                    evidence=[Evidence(type="file_line", location="/nonexistent.py:1", content="fake")])
f_invalid = validate_evidence_local(f_invalid)
check("无效证据 → verified=False", not f_invalid.verified)
check("  evidence 含 UNVERIFIED", "UNVERIFIED" in f_invalid.evidence[0].content)

# ═══════════════════════════════════════════════
# Test 7: 硬门禁优先级 (模拟 meta oracle)
# ═══════════════════════════════════════════════
print("\n=== T7: 硬门禁优先级验证 (S4/S6) ===")
# 用 model_meta_oracle 的 aggregate 验证门禁
from model_meta_oracle import aggregate_verdict

# 先写一个测试裁决文件来测试
test_task = "adversarial_test_s9_" + str(os.getpid())
from carros_oracle_base import VERDICT_DIR

# 创建静态 REJECT 裁决
verdict_dir = VERDICT_DIR / test_task
verdict_dir.mkdir(parents=True, exist_ok=True)

# 模拟验证过的 critical 发现 → 应 REJECT
reject_verdict = {
    "version": 5, "agent": "model_static", "task_id": test_task,
    "model": "test", "prompt_version": "v1", "timestamp": "now",
    "decision": "block", "verdict": "REJECT", "risk": "CRITICAL", "score": 3.0,
    "degraded": False, "degraded_reason": "", "missing_oracles": [], "fallback_oracles": [],
    "findings": [{
        "oracle": "model_static", "severity": "critical", "confidence": 0.95,
        "risk_type": "destructive_command", "evidence": [{"type": "file_line", "location": "carros_oracle_base.py:1", "content": "rm -rf found", "hash": "aaa"}],
        "reason": "destructive command detected", "recommendation": "remove", "verified": True
    }]
}
(verdict_dir / "latest.json").write_text(json.dumps(reject_verdict) + "\n")
(verdict_dir / "20260710T000000Z-model_static.json").write_text(json.dumps(reject_verdict) + "\n")

# 运行 meta aggregate（默认 policy=balanced）
try:
    r = aggregate_verdict(test_task, "balanced")
    check("验证过的 critical → REJECT", r.verdict == "REJECT", f"got {r.verdict}")
except Exception as e:
    check(f"aggregate critical: exception {e}", False)

# ═══════════════════════════════════════════════
# Test 8: 降级 + llm_required → ESCALATE（不能 ACCEPT）
# ═══════════════════════════════════════════════
print("\n=== T8: 降级状态门禁 (S5) ===")

test_task2 = "adversarial_degraded_" + str(os.getpid())
verdict_dir2 = VERDICT_DIR / test_task2
verdict_dir2.mkdir(parents=True, exist_ok=True)

# 如果只有一个 oracle 且 llm_required=false（balanced 默认 llm_required=false）→ degraded_allow
# 用 security_strict 测试（llm_required=true）
# 只有一个 static，无 runtime → missing_oracles 包含 runtime
static_only = {
    "version": 5, "agent": "model_static", "task_id": test_task2,
    "model": "test", "prompt_version": "v1", "timestamp": "now",
    "decision": "allow", "verdict": "ACCEPT", "risk": "LOW", "score": 9.5,
    "degraded": False, "degraded_reason": "", "missing_oracles": [], "fallback_oracles": [],
    "findings": [{
        "oracle": "model_static", "severity": "info", "confidence": 0.3,
        "risk_type": "evidence_missing", "evidence": [], "verified": True,
        "reason": "", "recommendation": ""
    }]
}
(verdict_dir2 / "latest.json").write_text(json.dumps(static_only) + "\n")
(verdict_dir2 / "20260710T000001Z-model_static.json").write_text(json.dumps(static_only) + "\n")

try:
    r2 = aggregate_verdict(test_task2, "security_strict")
    # security_strict: min_oracles=2, llm_required=true, runtime_missing 应触发 REJECT
    check("security_strict + runtime 缺失 → REJECT", r2.verdict == "REJECT", f"got {r2.verdict}")
    check("  degraded=True", r2.degraded, f"got degraded={r2.degraded}")
    check("  missing_oracles 含 model_runtime", "model_runtime" in r2.missing_oracles, str(r2.missing_oracles))
except Exception as e:
    check(f"aggregate degraded: exception {e}", False)

# ═══════════════════════════════════════════════
# Test 9: 9998 代理健康检查
# ═══════════════════════════════════════════════
print("\n=== T9: 健康检查 ===")
health = check_proxy_health()
check(f"health endpoint: {health['proxy_endpoint'][:30]}...", health["proxy_endpoint"] != "")
check(f"circuit state: {health['circuit']['state']}", health["circuit"]["state"] in ("closed", "open", "half_open"))
# 实际可用性依赖于 9998
print(f"  proxy status: {health['status']}")

# ═══════════════════════════════════════════════
# Test 10: 原子写入
# ═══════════════════════════════════════════════
print("\n=== T10: 写入 ===")
from carros_oracle_base import _atomic_write

with tempfile.TemporaryDirectory() as tmpdir:
    test_file = Path(tmpdir) / "test_atomic.json"
    _atomic_write(test_file, '{"test": "data"}\n')
    check("原子写入文件存在", test_file.exists())
    content = test_file.read_text(encoding="utf-8")
    check("写入内容正确", json.loads(content)["test"] == "data")

# ═══════════════════════════════════════════════
# 清理
# ═══════════════════════════════════════════════
import shutil
for task in [test_task, test_task2]:
    p = VERDICT_DIR / task
    if p.exists():
        shutil.rmtree(p)

# ═══════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"RESULT: {PASS}/{PASS+FAIL} passed")
if FAIL == 0:
    print("🎉 ALL CLEAR")
else:
    print(f"⚠️  {FAIL} failures")
sys.exit(0 if FAIL == 0 else 1)
