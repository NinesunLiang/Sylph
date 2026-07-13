# CarrorOS Opus-4.8 完整方案（5/10）

## 第 5 轮：L1 快速工作流与 VerifyGate MVP

---

### 一、L1 vs L2 核心差异

```yaml
L1_快速工作流:
  适用场景:
    - 简单 bugfix（< 3 文件）
    - 文档更新
    - 配置调整
    - 明确需求的小改动
  
  特点:
    - 无 Oracle
    - 轻量验证（自验 + 测试通过即可）
    - 无 Checkpoint（Git 足够）
    - 单会话完成
    - Context < 20K
  
  验证门槛:
    - 必须有 evidence
    - 但不需要 Oracle verdict
    - 测试覆盖即可
  
  风险承受:
    - 可回滚（Git reset）
    - 无外部副作用
    - 影响范围小

L2_严谨工作流:
  适用场景:
    - 架构变更
    - 跨模块重构
    - 安全相关
    - 并发处理
    - 有外部副作用
  
  特点:
    - 可选 Oracle（条件触发）
    - Checkpoint + 外部副作用对账
    - 多会话协作
    - 无人模式支持
    - Context > 20K 或 10+ 轮
  
  验证门槛:
    - 必须有 verdict（自验或 Oracle）
    - Checkpoint before irreversible
    - 外部副作用对账
  
  风险承受:
    - 可能不可逆
    - 影响范围大
    - 需要审计链
```

---

### 二、L1 VerifyGate MVP 协议

```python
from enum import Enum
from dataclasses import dataclass

class VerifyMethod(Enum):
    SELF_VERIFY = "self_verify"      # 模型自验 + 测试
    ORACLE_VERIFY = "oracle_verify"  # Oracle 裁决
    HUMAN_VERIFY = "human_verify"    # 人工确认

class VerifyStatus(Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass
class Evidence:
    evidence_id: str
    step_id: str
    kind: str  # test_pass, file_changed, behavior_verified
    description: str
    data: dict
    timestamp: str
    
@dataclass
class Verdict:
    verdict_id: str
    step_id: str
    method: VerifyMethod
    status: VerifyStatus
    evidences: List[str]  # evidence_ids
    rationale: str
    timestamp: str
    oracle_model: Optional[str] = None


def verify_gate_l1(task_id: str, step_id: str) -> VerifyResult:
    """
    L1 快速验证门
    不需要 Oracle，但必须有 evidence
    """
    
    state = load_token(task_id)
    plan = load_plan(task_id)
    step = plan.steps[step_id]
    
    # === 1. 收集 evidence ===
    evidences = load_evidences(task_id, step_id)
    
    if len(evidences) == 0:
        return VerifyResult(
            passed=False,
            reason="No evidence collected",
            required_actions=["Collect evidence before verify"]
        )
    
    # === 2. L1 必需 evidence 类型 ===
    required_types = {
        "test_pass": False,      # 至少一个测试通过
        "file_changed": False,   # 至少一个文件修改
    }
    
    for evidence in evidences:
        if evidence.kind in required_types:
            required_types[evidence.kind] = True
    
    missing = [k for k, v in required_types.items() if not v]
    if missing:
        return VerifyResult(
            passed=False,
            reason=f"Missing required evidence types: {missing}",
            required_actions=[
                "Run tests" if "test_pass" in missing else None,
                "Show file changes" if "file_changed" in missing else None,
            ]
        )
    
    # === 3. 检查测试是否通过 ===
    test_evidences = [e for e in evidences if e.kind == "test_pass"]
    all_tests_passed = all(
        e.data.get("passed", False)
        for e in test_evidences
    )
    
    if not all_tests_passed:
        failed_tests = [
            e.data.get("test_name")
            for e in test_evidences
            if not e.data.get("passed")
        ]
        return VerifyResult(
            passed=False,
            reason=f"Tests failed: {failed_tests}",
            required_actions=["Fix failing tests"]
        )
    
    # === 4. 生成 Self-Verify Verdict ===
    verdict = Verdict(
        verdict_id=f"VRD-{task_id}-{step_id}-{now_timestamp()}",
        step_id=step_id,
        method=VerifyMethod.SELF_VERIFY,
        status=VerifyStatus.PASSED,
        evidences=[e.evidence_id for e in evidences],
        rationale=(
            f"L1 Self-Verify: "
            f"{len(test_evidences)} tests passed, "
            f"{len([e for e in evidences if e.kind == 'file_changed'])} files changed"
        ),
        timestamp=now(),
    )
    
    # === 5. 记录 verdict ===
    write_verdict(task_id, verdict)
    
    # === 6. 更新 plan ===
    mark_step_verified(task_id, step_id, verdict.verdict_id)
    
    return VerifyResult(
        passed=True,
        verdict=verdict,
        next_action="proceed_to_next_step"
    )
```

---

### 三、evidence.jsonl 协议

```jsonl
{"evidence_id": "EVD-001", "step_id": "S1", "kind": "file_changed", "description": "Modified src/auth/refresh.ts", "data": {"path": "src/auth/refresh.ts", "lines_added": 12, "lines_removed": 5, "diff_hash": "abc123"}, "timestamp": "2026-07-12T10:15:00Z"}
{"evidence_id": "EVD-002", "step_id": "S1", "kind": "test_pass", "description": "Concurrent refresh test passed", "data": {"test_name": "testConcurrentRefresh", "passed": true, "duration_ms": 234}, "timestamp": "2026-07-12T10:16:00Z"}
{"evidence_id": "EVD-003", "step_id": "S1", "kind": "behavior_verified", "description": "Refresh token works under concurrent load", "data": {"verified_by": "execute-session-01", "method": "manual_test"}, "timestamp": "2026-07-12T10:17:00Z"}
```

**关键设计**：

1. **JSONL 而非 JSON Array**：方便追加，不需要重写整个文件
2. **每个 evidence 独立**：不依赖顺序
3. **data 字段灵活**：不同 kind 有不同 schema
4. **timestamp 严格**：用于时序验证

---

### 四、verdict 与 evidence 的关系

```text
evidence (证据)
  ├── 由执行过程自动产生
  ├── 无需人工审批
  ├── 可以有多个
  └── 记录事实（test passed, file changed）

verdict (裁决)
  ├── 基于多个 evidence 综合判断
  ├── 决定 step 是否通过 VerifyGate
  ├── L1: 自验 verdict（无 Oracle）
  └── L2: Oracle verdict（可选）

关系：
  verdict.evidences = [evidence_id1, evidence_id2, ...]
  
  一个 step 可以有多个 evidence
  但只有一个 final verdict

检查顺序：
  1. 收集 evidence
  2. 检查 evidence 是否充分
  3. 生成 verdict
  4. 标记 step 为 VERIFIED
```

**禁止**：

```text
✗ 没有 evidence 直接生成 verdict
✗ 没有 verdict 直接标记 VERIFIED
✗ compact 后凭记忆声称"已经验证过"
✗ 删除失败的 evidence
```

---

### 五、何时可以跳过 Oracle

```python
def should_invoke_oracle(task_id: str, step_id: str) -> OracleDecision:
    """
    判断是否需要 Oracle
    """
    
    state = load_token(task_id)
    plan = load_plan(task_id)
    step = plan.steps[step_id]
    
    # === L1 工作流：永远不调用 Oracle ===
    if state.manifest_level == "L1":
        return OracleDecision(
            invoke=False,
            reason="L1 workflow uses self-verify only"
        )
    
    # === L2 工作流：条件触发 ===
    
    # 条件 1：高风险步骤
    if state.risk.level == "high":
        return OracleDecision(
            invoke=True,
            reason="High risk step requires Oracle review"
        )
    
    # 条件 2：架构变更
    if "architecture" in step.tags or "refactor" in step.tags:
        return OracleDecision(
            invoke=True,
            reason="Architectural change requires Oracle review"
        )
    
    # 条件 3：安全相关
    if any(cat in state.risk.categories for cat in ["auth", "security", "crypto"]):
        return OracleDecision(
            invoke=True,
            reason="Security-related change requires Oracle review"
        )
    
    # 条件 4：不可逆外部副作用
    has_irreversible = any(
        e.reversible == False
        for e in state.external_effects
        if e.status == "PENDING"
    )
    if has_irreversible:
        return OracleDecision(
            invoke=True,
            reason="Irreversible external effect requires Oracle confirmation"
        )
    
    # 条件 5：DeepSeek Flash 能力不足（residual risk）
    if state.model_usage.primary_profile == "deepseek-v4-flash":
        # 检查 step 复杂度
        complexity = estimate_step_complexity(step)
        if complexity > 0.7:  # 高复杂度
            return OracleDecision(
                invoke=True,
                reason="Flash model may have residual risk, escalate to Oracle"
            )
    
    # 条件 6：连续失败后的方案变更
    if step.retry_count >= 2:
        return OracleDecision(
            invoke=True,
            reason="Multiple retries, need Oracle to review new approach"
        )
    
    # === 默认：L2 自验即可 ===
    return OracleDecision(
        invoke=False,
        reason="L2 self-verify sufficient for this step"
    )
```

**Oracle 调用成本控制**：

```text
假设每次 Oracle 调用 = $0.05
一个 10-step 任务：

策略 A（每 step 都调）：10 × $0.05 = $0.50
策略 B（条件触发）：   2 × $0.05 = $0.10

成本节省：80%
同时保持关键步骤的安全性
```

---

### 六、L1 → L2 升级触发条件

```python
def check_upgrade_to_l2(task_id: str) -> UpgradeDecision:
    """
    检查是否应该从 L1 升级到 L2
    """
    
    state = load_token(task_id)
    
    # 当前声明是 L1
    if state.manifest_level != "L1":
        return UpgradeDecision(upgrade=False)
    
    triggers = []
    
    # 触发器 1：Context 超过 L1 预算
    if state.context.estimated_input_tokens > 20000:
        triggers.append("context_exceeded")
    
    # 触发器 2：回合数超过 L1 限制
    if state.turns > 15:
        triggers.append("turns_exceeded")
    
    # 触发器 3：发现不可逆外部副作用
    has_irreversible = any(
        e.reversible == False
        for e in state.external_effects
    )
    if has_irreversible:
        triggers.append("irreversible_effect_detected")
    
    # 触发器 4：风险等级升高
    if state.risk.level in ["high"]:
        triggers.append("risk_escalated")
    
    # 触发器 5：跨模块修改
    modified_modules = set()
    for evidence in load_evidences(task_id):
        if evidence.kind == "file_changed":
            module = extract_module_from_path(evidence.data["path"])
            modified_modules.add(module)
    
    if len(modified_modules) >= 3:
        triggers.append("cross_module_detected")
    
    # 触发器 6：需要 Oracle
    for step_id in state.plan.steps:
        if should_invoke_oracle(task_id, step_id).invoke:
            triggers.append("oracle_required")
            break
    
    if triggers:
        return UpgradeDecision(
            upgrade=True,
            reason=f"L1 → L2 triggered by: {triggers}",
            required_actions=[
                "Create checkpoint before continuing",
                "Enable Oracle for remaining steps",
                "Review risk categories",
            ]
        )
    
    return UpgradeDecision(upgrade=False)
```

**升级后的变化**：

```yaml
升级前 (L1):
  manifest_level: L1
  oracle_enabled: false
  checkpoint_required: false
  verify_method: self_verify

升级后 (L2):
  manifest_level: L2
  oracle_enabled: conditional  # 按需触发
  checkpoint_required: true
  verify_method: self_verify_or_oracle
  
  # 立即动作
  immediate_actions:
    - create_checkpoint
    - log_upgrade_decision
    - notify_user
```

---

### 七、L1 完整流程示例

```python
def execute_l1_workflow(task_id: str):
    """
    L1 快速工作流完整示例
    """
    
    state = load_token(task_id)
    plan = load_plan(task_id)
    
    current_step = plan.steps[state.current_step]
    
    # === Step 1: 执行 ===
    print(f"Executing step {state.current_step}: {current_step.description}")
    
    # 修改文件
    apply_changes("src/auth/refresh.ts", changes)
    
    # 记录 evidence
    add_evidence(task_id, Evidence(
        evidence_id=generate_id(),
        step_id=state.current_step,
        kind="file_changed",
        description="Modified src/auth/refresh.ts",
        data={
            "path": "src/auth/refresh.ts",
            "lines_added": 12,
            "lines_removed": 5,
            "diff_hash": compute_diff_hash(),
        },
        timestamp=now(),
    ))
    
    # === Step 2: 测试 ===
    test_result = run_tests("tests/auth/concurrent.test.ts")
    
    add_evidence(task_id, Evidence(
        evidence_id=generate_id(),
        step_id=state.current_step,
        kind="test_pass",
        description="Concurrent refresh test passed",
        data={
            "test_name": "testConcurrentRefresh",
            "passed": test_result.passed,
            "duration_ms": test_result.duration,
        },
        timestamp=now(),
    ))
    
    # === Step 3: VerifyGate ===
    verify_result = verify_gate_l1(task_id, state.current_step)
    
    if not verify_result.passed:
        print(f"VerifyGate failed: {verify_result.reason}")
        print(f"Required actions: {verify_result.required_actions}")
        
        # 标记 BLOCKED
        update_state(task_id, {
            "current_step_status": "BLOCKED",
            "blocker": {
                "type": "verify_failed",
                "description": verify_result.reason,
                "required_actions": verify_result.required_actions,
            }
        }, expected_version=state.version)
        
        return
    
    print(f"✓ Step {state.current_step} verified")
    print(f"  Verdict: {verify_result.verdict.verdict_id}")
    print(f"  Method: {verify_result.verdict.method.value}")
    
    # === Step 4: 进入下一步 ===
    next_step = get_next_step(plan, state.current_step)
    
    if next_step:
        update_state(task_id, {
            "current_step": next_step,
            "current_step_status": "PENDING",
            "progress.verified_steps": state.progress.verified_steps + 1,
        }, expected_version=state.version)
        
        print(f"→ Moving to step {next_step}")
    else:
        # 所有步骤完成
        update_state(task_id, {
            "status": "VERIFIED",
            "current_step_status": "VERIFIED",
        }, expected_version=state.version)
        
        print("✓ All steps completed")
        
        # L1 可以直接 Archive（如果符合条件）
        if check_archive_ready(task_id):
            archive_task(task_id)
```

---

### 八、Compact 后禁止跳过 VerifyGate（硬约束）

```python
def detect_verify_bypass_after_compact(task_id: str) -> BypassDetection:
    """
    检测 compact 后是否绕过了 VerifyGate
    这是 CarrorOS 的铁律
    """
    
    operation_log = load_operation_log(task_id)
    
    # 找到最近的 compact 事件
    last_compact = None
    for entry in reversed(operation_log):
        if entry.action in ["compaction_detected", "resume_after_compact"]:
            last_compact = entry
            break
    
    if not last_compact:
        return BypassDetection(detected=False)
    
    # 检查 compact 后的操作
    violations = []
    
    for entry in operation_log:
        if entry.timestamp <= last_compact.timestamp:
            continue
        
        # 违规 1：直接标记 VERIFIED 但没有 verdict
        if entry.action == "step_marked_verified":
            step_id = entry.metadata["step_id"]
            verdict_exists = check_verdict_exists(task_id, step_id)
            
            if not verdict_exists:
                violations.append({
                    "timestamp": entry.timestamp,
                    "step": step_id,
                    "violation": "marked VERIFIED without verdict",
                    "severity": "CRITICAL",
                })
        
        # 违规 2：声称"之前已经验证过"
        if entry.action == "user_message":
            message = entry.metadata.get("text", "")
            suspicious_phrases = [
                "already verified",
                "之前已经验证",
                "previous session verified",
                "we verified earlier",
            ]
            if any(phrase in message.lower() for phrase in suspicious_phrases):
                violations.append({
                    "timestamp": entry.timestamp,
                    "violation": "claimed previous verification after compact",
                    "severity": "WARNING",
                    "message": message[:100],
                })
        
        # 违规 3：修改 plan.md 的 VERIFIED 标记
        if entry.action == "file_modified":
            if entry.metadata["path"] == ".omc/task/{task_id}/plan.md":
                diff = entry.metadata.get("diff", "")
                if "VERIFIED" in diff:
                    violations.append({
                        "timestamp": entry.timestamp,
                        "violation": "manual plan.md VERIFIED modification",
                        "severity": "CRITICAL",
                    })
        
        # 违规 4：Archive 但没有全部 verdict
        if entry.action == "task_archived":
            plan = load_plan(task_id)
            missing_verdicts = []
            for step_id in plan.steps:
                if not check_verdict_exists(task_id, step_id):
                    missing_verdicts.append(step_id)
            
            if missing_verdicts:
                violations.append({
                    "timestamp": entry.timestamp,
                    "violation": "archived without all verdicts",
                    "severity": "CRITICAL",
                    "missing_steps": missing_verdicts,
                })
    
    return BypassDetection(
        detected=(len(violations) > 0),
        violations=violations,
        compact_timestamp=last_compact.timestamp,
    )
```

**铁律**：

```text
compact 后必须：
✓ 从 evidence.jsonl 读取已验证的 evidence
✓ 从 verdict 文件读取已有的 verdict
✓ 如果 step 没有 verdict，重新执行验证
✓ 不能凭记忆声称"已经完成"

compact 后禁止：
✗ 跳过 evidence 收集
✗ 跳过 VerifyGate
✗ 手动修改 plan.md 的 VERIFIED 标记
✗ 声称"之前已经验证过"
✗ 用 transcript 摘要代替 verdict
```

---

### 九、验收测试

```python
def test_l1_verify_requires_evidence():
    """L1 验证必须有 evidence"""
    task_id = "test-001"
    
    # 没有 evidence
    result = verify_gate_l1(task_id, "S1")
    assert result.passed is False
    assert "No evidence" in result.reason


def test_l1_verify_requires_test_pass():
    """L1 验证必须有测试通过"""
    task_id = "test-002"
    
    # 只有文件修改，没有测试
    add_evidence(task_id, Evidence(
        evidence_id="EVD-001",
        step_id="S1",
        kind="file_changed",
        description="Modified file",
        data={"path": "src/test.ts"},
        timestamp=now(),
    ))
    
    result = verify_gate_l1(task_id, "S1")
    assert result.passed is False
    assert "test_pass" in result.reason


def test_l1_never_invokes_oracle():
    """L1 永远不调用 Oracle"""
    task_id = "test-003"
    update_state(task_id, {"manifest_level": "L1"}, 1)
    
    # 即使是高风险
    update_state(task_id, {"risk.level": "high"}, 2)
    
    decision = should_invoke_oracle(task_id, "S1")
    assert decision.invoke is False
    assert "L1 workflow" in decision.reason


def test_upgrade_l1_to_l2_on_context_exceeded():
    """Context 超限触发升级"""
    task_id = "test-004"
    update_state(task_id, {
        "manifest_level": "L1",
        "context.estimated_input_tokens": 25000,  # 超过 20K
    }, 1)
    
    decision = check_upgrade_to_l2(task_id)
    assert decision.upgrade is True
    assert "context_exceeded" in decision.reason


def test_compact_bypass_detection():
    """检测 compact 后绕过验证"""
    task_id = "test-005"
    
    # 记录 compact
    log_operation(task_id, "compaction_detected", {})
    
    # compact 后直接标记 VERIFIED（错误）
    log_operation(task_id, "step_marked_verified", {"step_id": "S1"})
    
    # 但没有 verdict
    
    detection = detect_verify_bypass_after_compact(task_id)
    assert detection.detected is True
    assert any(
        v["violation"] == "marked VERIFIED without verdict"
        for v in detection.violations
    )
```

---

## 第 6 轮预告

下一轮我将输出：
- **L2 工作流完整协议**
- **Checkpoint + 外部副作用对账**
- **条件 Oracle 触发逻辑**
- **无人模式 Autonomy Contract 基础**
- **L2 的 residual risk 处理**
- **模型路由（Flash → Opus 升级）**

准备第 6 轮。