#!/usr/bin/env python3
"""test_gatekeeper.py — TDD: 先写测试，再验证 gatekeeper.py 分层裁决链

覆盖:
  1. 铁律违反 → BLOCK
  2. 协议A 不可逆操作 → ASK_USER(含选项+推荐)
  3. 协议A 越权操作 → ASK_USER
  4. 协议B 可修正问题 → REDIRECT(含引导)
  5. 协议C 安全操作 → ALLOW
  6. 无人模式高危 → SKIP
  7. 协议C 带约束 → ALLOW_WITH_CONSTRAINTS
  8. format_output 格式验证
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude" / "scripts"))
from gatekeeper import GateKeeper, GateContext, GateDecision, make_context, BlockOption

PASS, FAIL = 0, 0

def ok(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} {detail}")

def check_decision(name, ctx, expected_decision, expected_protocol, extra_checks=None):
    result = GateKeeper.evaluate(ctx)
    ok(f"{name} decision={expected_decision.value}", result.decision == expected_decision,
       f"got={result.decision.value}")
    if expected_protocol:
        ok(f"{name} protocol={expected_protocol}", result.protocol == expected_protocol,
           f"got={result.protocol}")
    if extra_checks:
        extra_checks(result)

# ════════════════════════════════════════════
# TDD: 先写测试场景
# ════════════════════════════════════════════

# ─── 1. 铁律违反 → BLOCK ───
ctx = GateContext(action="修改治理文件",
    target=".claude/hooks/pretool-gate.py",
    metadata={"governance_violation": True},
)
check_decision("C1: 铁律治理文件", ctx, GateDecision.BLOCK, "NONE")

ctx2 = GateContext(action="绕过验证写证据",
    target="completion-evidence",
    metadata={"bypass_attempt": True},
)
check_decision("C1: 铁律绕过gate", ctx2, GateDecision.BLOCK, "NONE")

ctx3 = GateContext(action="写无来源断言", target="report.md",
    metadata={"untrusted_value": True},
)
check_decision("C1: 铁律无来源", ctx3, GateDecision.BLOCK, "NONE")

# ─── 2. 协议A 不可逆操作 → ASK_USER ───
ctx4 = make_context(action="rm -rf /data", destructive=True, irreversible=True, risk="high")
r4 = GateKeeper.evaluate(ctx4)
ok("C2: 不可逆→ASK_USER", r4.decision == GateDecision.ASK_USER, f"got={r4.decision.value}")
ok("C2: 协议A", r4.protocol == "A", f"got={r4.protocol}")
ok("C2: 有选项", len(r4.options) >= 2, f"count={len(r4.options)}")
ok("C2: 有推荐", r4.recommendation[0] != "", f"rec={r4.recommendation}")
# 格式化输出验证
output4 = GateKeeper.format_output(r4)
ok("C2: 输出含⛔", "⛔" in output4, f"out={output4[:50]}")
ok("C2: 输出含可选方案", "可选方案" in output4)
ok("C2: 输出含AI推荐", "AI 推荐" in output4)

# ─── 3. 协议A 越权操作 → ASK_USER ───
ctx5 = make_context(
    action="修改权限表",
    privilege_escalation=True,
    risk="high",
)
check_decision("C3: 越权→ASK_USER", ctx5, GateDecision.ASK_USER, "A")

# ─── 4. 协议B 可修正问题 → REDIRECT ───
ctx6 = make_context(
    action="写入未读文件",
    risk="low",
    fixable_issue=True,
)
check_decision("C4: 可修正→REDIRECT", ctx6, GateDecision.REDIRECT, "B")
output6 = GateKeeper.format_output(GateKeeper.evaluate(ctx6))
ok("C4: 输出含🔄", "🔄" in output6, f"out={output6[:50]}")
ok("C4: 输出含继续...", "继续..." in output6)

# ─── 5. 协议C 安全操作 → ALLOW ───
ctx7 = make_context(
    action="读取README.md",
    risk="low",
    has_verification=True,
    minimal_privilege=True,
    positive_roi=True,
)
check_decision("C5: 安全→ALLOW", ctx7, GateDecision.ALLOW, "C")
output7 = GateKeeper.format_output(GateKeeper.evaluate(ctx7))
ok("C5: ALLOW无输出", output7 == "", f"got={output7[:50]}")

# ─── 6. 无人模式 → SKIP ───
ctx8 = make_context(
    action="删除生产表",
    destructive=True,
    irreversible=True,
    risk="high",
    unattended=True,
)
check_decision("C6: 无人模式→SKIP", ctx8, GateDecision.SKIP, "A")
output8 = GateKeeper.format_output(GateKeeper.evaluate(ctx8))
ok("C6: SKIP输出含⚠️", "⚠️" in output8, f"out={output8[:50]}")

# ─── 7. 协议C 带约束 → ALLOW_WITH_CONSTRAINTS ───
ctx9 = make_context(
    action="写入配置文件",
    risk="medium",
    has_verification=True,
    minimal_privilege=True,
    needs_constraints=True,
)
check_decision("C7: 中风险→ALLOW_WITH_CONSTRAINTS", ctx9, GateDecision.ALLOW_WITH_CONSTRAINTS, "C")

# ─── 8. 事件日志验证 ───
events = GateKeeper.get_events()
ok("C8: 事件日志非空", len(events) > 0, f"count={len(events)}")
# 找一个BLOCK事件
block_events = [e for e in events if e.get("decision") == "block"]
ok("C8: BLOCK事件有记录", len(block_events) > 0, f"count={len(block_events)}")
ask_user_events = [e for e in events if e.get("decision") == "ask_user"]
ok("C8: ASK_USER事件有记录", len(ask_user_events) > 0, f"count={len(ask_user_events)}")

# ═══════════════════════════════════════════════════
# R: Rule 分治激活
# ═══════════════════════════════════════════════════

# R1: pretool gate_type → 只检查 governance_violation（命中→BLOCK）
r_ctx = GateContext(action="编辑治理文件", target=".claude/hooks/x.py",
                    metadata={"governance_violation": True, "untrusted_value": True})
rr = GateKeeper.evaluate(r_ctx, gate_type="pretool")
ok("R1 pretool governance违反→BLOCK", rr.decision == GateDecision.BLOCK, f"got={rr.decision.value}")
ok("R1 pretool protocol=NONE", rr.protocol == "NONE", f"got={rr.protocol}")

# pretool 不检查 untrusted_value → 添加 untrusted_value 但无 governance 时不触发铁律
# 但需给足够哲学得分通过协议C (guard_first 8 + zero_trust 9 + less_is_more 4 = 21 >= 15)
r_ctx2 = GateContext(action="写报告", target="report.md",
                     metadata={"untrusted_value": True, "has_safeguards": True,
                               "minimal_privilege": True, "simplifies_system": True})
rr2 = GateKeeper.evaluate(r_ctx2, gate_type="pretool")
ok("R1 pretool 不查untrusted_value→非铁律阻断", rr2.protocol != "NONE", f"got={rr2.protocol}")

# R2: completion gate_type → 只检查 lacks_evidence（命中→BLOCK）
r_ctx3 = GateContext(action="提交完成", target="task1",
                     metadata={"lacks_evidence": True, "bypass_attempt": True})
rr3 = GateKeeper.evaluate(r_ctx3, gate_type="completion")
ok("R2 completion 证据缺失→BLOCK", rr3.decision == GateDecision.BLOCK, f"got={rr3.decision.value}")

# completion 不检查 bypass_attempt → 不命中，需给足够哲学得分(verify_first 10 + doc_first 7 = 17 >= 15)
r_ctx4 = GateContext(action="提交完成", target="task1",
                     metadata={"bypass_attempt": True, "has_verification": True,
                               "generates_documentation": True})
rr4 = GateKeeper.evaluate(r_ctx4, gate_type="completion")
ok("R2 completion 不查bypass→非铁律阻断", rr4.protocol != "NONE", f"got={rr4.protocol}")

# R3: verify gate_type → 只查 lacks_evidence + unverifiable
r_ctx5 = GateContext(action="verify step1", target=".",
                     metadata={"unverifiable": True, "untrusted_value": True})
rr5 = GateKeeper.evaluate(r_ctx5, gate_type="verify")
ok("R3 verify unverifiable→BLOCK", rr5.decision == GateDecision.BLOCK, f"got={rr5.decision.value}")
# verify 不查 untrusted_value
r_ctx6 = GateContext(action="verify step1", target=".",
                     metadata={"untrusted_value": True, "has_verification": True,
                               "governance_violation": False})
rr6 = GateKeeper.evaluate(r_ctx6, gate_type="verify")
# verify_first=10 < 15 low threshold → BLOCK by min_score, protocol=C
ok("R3 verify 不查untrusted→非NONE协议", rr6.protocol != "NONE", f"got={rr6.protocol}")

# R4: claim_audit gate_type → 只查 untrusted_value + lacks_evidence
r_ctx7 = GateContext(action="claim audit", target="evidence.jsonl",
                     metadata={"untrusted_value": True, "privacy_violation": True})
rr7 = GateKeeper.evaluate(r_ctx7, gate_type="claim_audit")
ok("R4 claim_audit untrusted→BLOCK", rr7.decision == GateDecision.BLOCK, f"got={rr7.decision.value}")
# claim_audit 不查 privacy_violation
r_ctx8 = GateContext(action="claim audit", target="data",
                     metadata={"privacy_violation": True, "generates_documentation": True,
                               "user_requested": True})
# 哲学: doc_first 7 + human_first 6 = 13 < 15 → BLOCK by low_score, protocol=C
rr8 = GateKeeper.evaluate(r_ctx8, gate_type="claim_audit")
ok("R4 claim_audit 不查privacy→非NONE协议", rr8.protocol != "NONE", f"got={rr8.protocol}")

# R5: unknown gate_type → 使用全量规则(execute)
r_ctx9 = GateContext(action="全量测试", target=".",
                     metadata={"governance_violation": True, "bypass_attempt": True})
rr9 = GateKeeper.evaluate(r_ctx9, gate_type="unknown")
ok("R5 unknown→全量规则(BLOCK)", rr9.decision == GateDecision.BLOCK, f"got={rr9.decision.value}")

# R6: None gate_type → 向后兼容（全量规则）
r_ctx10 = GateContext(action="None测试", target=".",
                      metadata={"bypass_attempt": True})
rr10 = GateKeeper.evaluate(r_ctx10, gate_type=None)
ok("R6 gate_type=None→全量规则(BLOCK)", rr10.decision == GateDecision.BLOCK, f"got={rr10.decision.value}")

# R7: gate_type 不影响协议A分流
r_ctx11 = make_context(action="rm -rf /", destructive=True, risk="high")
rr11 = GateKeeper.evaluate(r_ctx11, gate_type="pretool")
ok("R7 pretool协议A→ASK_USER", rr11.decision == GateDecision.ASK_USER, f"got={rr11.decision.value}")
ok("R7 pretool协议A=A", rr11.protocol == "A", f"got={rr11.protocol}")

# R8: _RULE_PACKAGES 定义完整性 — 5个domain都有定义
expected_domains = {"pretool", "completion", "verify", "claim_audit", "execute"}
actual_domains = set(GateKeeper._RULE_PACKAGES.keys())
ok("R8 _RULE_PACKAGES 5个domain", actual_domains == expected_domains,
   f"expected={expected_domains} actual={actual_domains}")
# 每个domain都有 iron_law_keys + philosophy_keys
for d in actual_domains:
    pkg = GateKeeper._RULE_PACKAGES[d]
    ok(f"R8 {d} iron_law_keys存在", bool(pkg.get("iron_law_keys")), f"keys={pkg.get('iron_law_keys')}")
    ok(f"R8 {d} philosophy_keys存在", bool(pkg.get("philosophy_keys")), f"keys={pkg.get('philosophy_keys')}")

# R9: pretool 哲学只检查 guard_first/zero_trust/less_is_more
# 模拟只有 verify_first 命中的场景 — pretool 不应计分
r_ctx12 = GateContext(action="pretool哲学测试", target=".",
                      metadata={"has_verification": True, "has_safeguards": False,
                                "minimal_privilege": False, "simplifies_system": False},
                      risk_level="high")
# 不加置信度哲学不命中，用 evaluate 验证得分
rr12 = GateKeeper.evaluate(r_ctx12, gate_type="pretool")
# pretool 不查 verify_first → score=0 → BLOCK (低于阈值)
ok("R9 pretool不查verify_first→BLOCK", rr12.decision == GateDecision.BLOCK,
   f"got={rr12.decision.value}")

print(f"\n结果: {PASS}/{PASS + FAIL} PASS, {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
