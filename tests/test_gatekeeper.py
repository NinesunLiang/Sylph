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

print(f"\n结果: {PASS}/{PASS + FAIL} PASS, {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
