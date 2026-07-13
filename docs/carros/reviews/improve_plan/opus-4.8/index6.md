# CarrorOS Opus-4.8 完整方案（6/10）

## 第 6 轮：L2 严谨工作流与条件 Oracle

---

### 一、L2 工作流完整协议

```yaml
schema_version: carros.l2_workflow.v1

manifest_level: L2

triggers:
  - context > 20K tokens
  - turns > 15
  - cross_module_changes >= 3
  - irreversible_external_effect
  - risk_level: high
  - architecture_change
  - security_related

capabilities:
  checkpoint: required
  oracle: conditional  # 按需触发
  external_effect_reconciliation: required
  multi_session: supported
  autonomy_mode: supported

verification:
  method: self_verify_or_oracle
  gate: strict
  evidence_required: true
  verdict_required: true
  
  escalation_rules:
    - condition: risk.level == "high"
      action: invoke_oracle
    - condition: retry_count >= 2
      action: invoke_oracle
    - condition: complexity > 0.7 AND model == "flash"
      action: invoke_oracle
    - condition: irreversible_effect AND status == "PENDING"
      action: invoke_oracle

checkpoint_policy:
  before_irreversible: mandatory
  periodic_interval: 5_steps
  on_upgrade_from_l1: immediate
  
cost_profile:
  expected_range: $0.50 - $5.00
  oracle_budget: $0.50
  checkpoint_overhead: $0.05
  
slo:
  resume_success_rate: ">= 95%"
  state_consistency: "100%"
  verify_bypass_count: "0"
```

---

### 二、Checkpoint 完整实现

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
import hashlib
import json

@dataclass
class CheckpointMetadata:
    checkpoint_id: str
    task_id: str
    created_at: str
    created_by: str  # session_id
    reason: str
    
    # 版本快照
    state_version: int
    plan_version: int
    manifest_version: int
    working_set_version: int
    
    # Git 状态
    git_ref: str
    git_uncommitted_files: List[str]
    git_untracked_files: List[str]
    
    # 外部副作用快照
    committed_effects: List[str]  # effect_ids
    reversible_effects: List[str]
    irreversible_effects: List[str]
    
    # 文件快照
    working_files: Dict[str, str]  # path -> content_hash
    
    # 恢复元数据
    restore_order: List[str]
    warnings: List[str]


def create_checkpoint_l2(
    task_id: str,
    reason: str,
    session_id: str
) -> CheckpointMetadata:
    """
    L2 创建 Checkpoint
    在不可逆操作前必须调用
    """
    
    state = load_token(task_id)
    plan = load_plan(task_id)
    manifest = load_manifest(task_id)
    working_set = load_working_set(task_id)
    
    # === 1. Git 状态快照 ===
    git_ref = run_command("git rev-parse HEAD").strip()
    
    git_status_output = run_command("git status --porcelain")
    uncommitted = []
    untracked = []
    
    for line in git_status_output.splitlines():
        status = line[:2]
        path = line[3:]
        
        if status == "??":
            untracked.append(path)
        else:
            uncommitted.append(path)
    
    # === 2. 外部副作用分类 ===
    committed_effects = []
    reversible_effects = []
    irreversible_effects = []
    
    for effect in state.external_effects:
        if effect.status == EffectStatus.COMMITTED:
            committed_effects.append(effect.effect_id)
            
            if effect.reversible:
                reversible_effects.append(effect.effect_id)
            else:
                irreversible_effects.append(effect.effect_id)
    
    # === 3. 工作文件快照 ===
    working_files = {}
    
    for doc_ref in working_set.docs:
        # 只快照代码文件
        if doc_ref.id.startswith("src/") or doc_ref.id.startswith("tests/"):
            if os.path.exists(doc_ref.id):
                content = read_file(doc_ref.id)
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                working_files[doc_ref.id] = content_hash
    
    # === 4. 创建 Checkpoint 元数据 ===
    checkpoint = CheckpointMetadata(
        checkpoint_id=f"CHK-{task_id}-{state.version}-{now_timestamp()}",
        task_id=task_id,
        created_at=now(),
        created_by=session_id,
        reason=reason,
        state_version=state.version,
        plan_version=plan.version,
        manifest_version=manifest.version,
        working_set_version=working_set.version,
        git_ref=git_ref,
        git_uncommitted_files=uncommitted,
        git_untracked_files=untracked,
        committed_effects=committed_effects,
        reversible_effects=reversible_effects,
        irreversible_effects=irreversible_effects,
        working_files=working_files,
        restore_order=[
            "git_status_check",
            "state_file_restore",
            "plan_file_restore",
            "working_files_restore",
            "external_effects_reconcile",
        ],
        warnings=[],
    )
    
    # === 5. 持久化 Checkpoint ===
    checkpoint_dir = f".omc/task/{task_id}/checkpoints"
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    # 保存元数据
    with open(f"{checkpoint_dir}/{checkpoint.checkpoint_id}.json", "w") as f:
        json.dump(asdict(checkpoint), f, indent=2)
    
    # 保存完整状态快照
    with open(f"{checkpoint_dir}/{checkpoint.checkpoint_id}.token.json", "w") as f:
        json.dump(state, f, indent=2)
    
    with open(f"{checkpoint_dir}/{checkpoint.checkpoint_id}.plan.md", "w") as f:
        f.write(read_file(f".omc/task/{task_id}/plan.md"))
    
    # === 6. 更新 state 引用 ===
    update_state(
        task_id,
        {"last_checkpoint_id": checkpoint.checkpoint_id},
        expected_version=state.version
    )
    
    # === 7. 记录操作日志 ===
    log_operation(task_id, "checkpoint_created", {
        "checkpoint_id": checkpoint.checkpoint_id,
        "reason": reason,
        "git_ref": git_ref[:8],
    })
    
    return checkpoint


def rollback_to_checkpoint_l2(checkpoint_id: str) -> RollbackResult:
    """
    L2 回滚到 Checkpoint
    """
    
    # === 1. 加载 Checkpoint ===
    checkpoint_path = find_checkpoint_path(checkpoint_id)
    with open(checkpoint_path) as f:
        checkpoint = CheckpointMetadata(**json.load(f))
    
    current_state = load_token(checkpoint.task_id)
    
    # === 2. 安全性检查 ===
    
    # 检查 2.1: Git 是否有新 commit
    current_git_ref = run_command("git rev-parse HEAD").strip()
    
    if current_git_ref != checkpoint.git_ref:
        return RollbackResult(
            success=False,
            reason=(
                f"Git moved from {checkpoint.git_ref[:8]} "
                f"to {current_git_ref[:8]}. "
                f"Use 'git reset {checkpoint.git_ref}' manually first."
            ),
            action="manual_git_reset_required",
        )
    
    # 检查 2.2: 新产生的不可逆副作用
    new_irreversible = []
    
    for effect in current_state.external_effects:
        if (
            effect.status == EffectStatus.COMMITTED and
            not effect.reversible and
            effect.effect_id not in checkpoint.committed_effects
        ):
            new_irreversible.append(effect)
    
    if new_irreversible:
        return RollbackResult(
            success=False,
            reason="New irreversible external effects detected",
            effects=[e.effect_id for e in new_irreversible],
            action="cannot_rollback_must_continue_forward",
        )
    
    # === 3. 执行回滚 ===
    
    restored_files = []
    warnings = []
    
    # 3.1 恢复状态文件
    state_snapshot_path = checkpoint_path.replace(".json", ".token.json")
    with open(state_snapshot_path) as f:
        state_snapshot = json.load(f)
    
    write_token(checkpoint.task_id, state_snapshot)
    restored_files.append("token.json")
    
    # 3.2 恢复 plan
    plan_snapshot_path = checkpoint_path.replace(".json", ".plan.md")
    with open(plan_snapshot_path) as f:
        plan_snapshot = f.read()
    
    write_file(f".omc/task/{checkpoint.task_id}/plan.md", plan_snapshot)
    restored_files.append("plan.md")
    
    # 3.3 恢复工作文件（谨慎）
    for path, expected_hash in checkpoint.working_files.items():
        if not os.path.exists(path):
            warnings.append(f"{path} not found, skipping restore")
            continue
        
        current_hash = compute_file_hash(path)
        
        if current_hash == expected_hash:
            # 文件未修改，无需恢复
            continue
        
        # 文件已修改，需要确认
        warnings.append(
            f"{path} was modified after checkpoint "
            f"(expected: {expected_hash[:8]}, current: {current_hash[:8]})"
        )
        
        # 默认不自动恢复，需要人工决策
        # 可以在这里添加交互式确认
    
    # === 4. 对账外部副作用 ===
    reconcile_result = reconcile_external_effects(
        checkpoint.task_id,
        checkpoint_id=checkpoint.checkpoint_id
    )
    
    if not reconcile_result.consistent:
        warnings.extend([
            f"Effect mismatch: {m}"
            for m in reconcile_result.mismatches
        ])
    
    # === 5. 记录回滚操作 ===
    log_operation(checkpoint.task_id, "rollback_executed", {
        "checkpoint_id": checkpoint_id,
        "restored_files": restored_files,
        "warnings": warnings,
    })
    
    return RollbackResult(
        success=True,
        checkpoint_id=checkpoint_id,
        restored_files=restored_files,
        warnings=warnings,
        next_action="resume_from_checkpoint",
    )
```

---

### 三、条件 Oracle 触发逻辑（草案）

```python
from dataclasses import dataclass
from enum import Enum

class OracleReason(Enum):
    HIGH_RISK = "high_risk"
    ARCHITECTURE = "architecture_change"
    SECURITY = "security_related"
    IRREVERSIBLE = "irreversible_effect"
    COMPLEXITY = "complexity_exceeds_flash_capability"
    RETRY_LIMIT = "retry_limit_exceeded"
    CONCURRENCY = "concurrency_critical"
    DATA_LOSS_RISK = "potential_data_loss"

@dataclass
class OracleDecision:
    invoke: bool
    reason: OracleReason
    priority: str  # low, medium, high, critical
    estimated_cost: float
    alternative: Optional[str] = None


def should_invoke_oracle_l2(
    task_id: str,
    step_id: str,
    force: bool = False
) -> OracleDecision:
    """
    L2 条件 Oracle 触发逻辑
    """
    
    if force:
        return OracleDecision(
            invoke=True,
            reason=OracleReason.HIGH_RISK,
            priority="critical",
            estimated_cost=0.05,
            alternative=None,
        )
    
    state = load_token(task_id)
    plan = load_plan(task_id)
    step = plan.steps[step_id]
    
    # === L1 工作流不调用 Oracle ===
    if state.manifest_level == "L1":
        return OracleDecision(
            invoke=False,
            reason=None,
            priority="none",
            estimated_cost=0,
            alternative="L1 uses self-verify only",
        )
    
    # === 触发器 1：高风险等级 ===
    if state.risk.level == "high":
        return OracleDecision(
            invoke=True,
            reason=OracleReason.HIGH_RISK,
            priority="high",
            estimated_cost=0.05,
        )
    
    # === 触发器 2：架构变更 ===
    if any(tag in ["architecture", "refactor", "design_change"] for tag in step.tags):
        return OracleDecision(
            invoke=True,
            reason=OracleReason.ARCHITECTURE,
            priority="high",
            estimated_cost=0.05,
        )
    
    # === 触发器 3：安全相关 ===
    security_categories = ["auth", "security", "crypto", "access_control"]
    if any(cat in state.risk.categories for cat in security_categories):
        return OracleDecision(
            invoke=True,
            reason=OracleReason.SECURITY,
            priority="critical",
            estimated_cost=0.05,
        )
    
    # === 触发器 4：不可逆外部副作用 ===
    pending_irreversible = [
        e for e in state.external_effects
        if e.status == EffectStatus.PENDING and not e.reversible
    ]
    
    if pending_irreversible:
        return OracleDecision(
            invoke=True,
            reason=OracleReason.IRREVERSIBLE,
            priority="critical",
            estimated_cost=0.05,
        )
    
    # === 触发器 5：Flash 能力不足（residual risk）===
    if state.model_usage.primary_profile == "deepseek-v4-flash":
        complexity = estimate_step_complexity(step)
        
        # 复杂度阈值
        if complexity > 0.7:
            return OracleDecision(
                invoke=True,
                reason=OracleReason.COMPLEXITY,
                priority="medium",
                estimated_cost=0.05,
                alternative="Consider escalating to Opus-4.8",
            )
    
    # === 触发器 6：连续失败 ===
    if step.retry_count >= 2:
        return OracleDecision(
            invoke=True,
            reason=OracleReason.RETRY_LIMIT,
            priority="high",
            estimated_cost=0.05,
        )
    
    # === 触发器 7：并发处理 ===
    if any(cat in state.risk.categories for cat in ["concurrency", "race_condition"]):
        return OracleDecision(
            invoke=True,
            reason=OracleReason.CONCURRENCY,
            priority="high",
            estimated_cost=0.05,
        )
    
    # === 触发器 8：潜在数据丢失 ===
    if any(tag in ["data_migration", "schema_change", "destructive"] for tag in step.tags):
        return OracleDecision(
            invoke=True,
            reason=OracleReason.DATA_LOSS_RISK,
            priority="critical",
            estimated_cost=0.05,
        )
    
    # === 默认：L2 自验即可 ===
    return OracleDecision(
        invoke=False,
        reason=None,
        priority="none",
        estimated_cost=0,
        alternative="Self-verify sufficient for this step",
    )


def invoke_oracle_verification(
    task_id: str,
    step_id: str,
    evidences: List[Evidence]
) -> Verdict:
    """
    调用 Oracle 进行验证
    """
    
    state = load_token(task_id)
    plan = load_plan(task_id)
    step = plan.steps[step_id]
    
    # === 1. 构建 Oracle Prompt ===
    oracle_prompt = f"""
# Oracle Verification Request

You are reviewing step completion for a critical task.

## Task Context
- **Goal**: {state.manifest.goal}
- **Current Step**: {step_id} — {step.description}
- **Risk Level**: {state.risk.level}
- **Risk Categories**: {state.risk.categories}

## Step Definition
{step.definition}

## Collected Evidence
{format_evidences_for_oracle(evidences)}

## Your Task
Review the evidence and determine:
1. Does the evidence prove the step is complete?
2. Are there any overlooked risks or edge cases?
3. Should this step be marked as VERIFIED?

**Output Format**:
```yaml
verdict: PASSED | FAILED | NEEDS_MORE_EVIDENCE
rationale: |
  Your detailed reasoning (2-4 sentences)
concerns: 
  - Any risks or missing coverage
recommendations:
  - Suggestions for improvement (if any)
```
"""
    
    # === 2. 调用 Oracle Model（通常用 Opus-4.8）===
    oracle_model = "claude-opus-4-8"
    
    response = call_llm(
        model=oracle_model,
        prompt=oracle_prompt,
        max_tokens=1000,
        # Opus 4.8 示例使用 prompt / effort / structured output 控制稳定性；不使用 temperature。
    )
    
    # === 3. 解析 Oracle 响应 ===
    oracle_output = parse_yaml_from_response(response)
    
    verdict_status = VerifyStatus.PASSED if oracle_output["verdict"] == "PASSED" else VerifyStatus.FAILED
    
    # === 4. 创建 Verdict ===
    verdict = Verdict(
        verdict_id=f"VRD-{task_id}-{step_id}-oracle-{now_timestamp()}",
        step_id=step_id,
        method=VerifyMethod.ORACLE_VERIFY,
        status=verdict_status,
        evidences=[e.evidence_id for e in evidences],
        rationale=oracle_output["rationale"],
        timestamp=now(),
        oracle_model=oracle_model,
    )
    
    # === 5. 记录成本 ===
    log_operation(task_id, "oracle_invoked", {
        "step_id": step_id,
        "verdict_id": verdict.verdict_id,
        "model": oracle_model,
        "cost_usd": 0.05,  # 估算
        "concerns": oracle_output.get("concerns", []),
        "recommendations": oracle_output.get("recommendations", []),
    })
    
    # === 6. 持久化 Verdict ===
    write_verdict(task_id, verdict)
    
    return verdict
```

---

### 四、模型路由（Flash → Opus 升级）

```python
@dataclass
class ModelProfile:
    name: str
    provider: str
    cost_per_1m_input: float
    cost_per_1m_output: float
    context_window: int
    recommended_for: List[str]
    max_complexity: float

# 模型配置
PROFILES = {
    "deepseek-v4-flash": ModelProfile(
        name="deepseek-chat",
        provider="deepseek",
        cost_per_1m_input=0.27,
        cost_per_1m_output=1.10,
        context_window=128000,
        recommended_for=["L1_fast", "simple_bugfix", "documentation"],
        max_complexity=0.7,
    ),
    "claude-opus-4-8": ModelProfile(
        name="claude-opus-4-8",
        provider="anthropic",
        cost_per_1m_input=15.00,
        cost_per_1m_output=75.00,
        context_window=200000,
        recommended_for=["L2_complex", "architecture", "oracle", "high_risk"],
        max_complexity=1.0,
    ),
}


def route_model_for_step(
    task_id: str,
    step_id: str
) -> str:
    """
    为 step 选择模型
    """
    
    state = load_token(task_id)
    plan = load_plan(task_id)
    step = plan.steps[step_id]
    
    # === L1 始终用 Flash ===
    if state.manifest_level == "L1":
        return "deepseek-v4-flash"
    
    # === L2 按复杂度路由 ===
    complexity = estimate_step_complexity(step)
    
    # 高复杂度 → Opus
    if complexity > 0.7:
        return "claude-opus-4-8"
    
    # 高风险 → Opus
    if state.risk.level == "high":
        return "claude-opus-4-8"
    
    # 架构变更 → Opus
    if any(tag in ["architecture", "refactor"] for tag in step.tags):
        return "claude-opus-4-8"
    
    # 连续失败 → 升级到 Opus
    if step.retry_count >= 2:
        return "claude-opus-4-8"
    
    # 默认 Flash
    return "deepseek-v4-flash"


def estimate_step_complexity(step: dict) -> float:
    """
    估算 step 复杂度（0.0～1.0）
    """
    
    complexity = 0.0
    
    # 因子 1：涉及文件数量
    file_count = len(step.get("related_files", []))
    complexity += min(file_count / 10, 0.3)
    
    # 因子 2：tags
    complex_tags = ["architecture", "refactor", "concurrency", "async", "distributed"]
    tag_score = sum(1 for tag in step.tags if tag in complex_tags) * 0.15
    complexity += min(tag_score, 0.3)
    
    # 因子 3：描述长度（粗略指标）
    description_length = len(step.description)
    complexity += min(description_length / 500, 0.2)
    
    # 因子 4：外部副作用
    if step.get("external_effects"):
        complexity += 0.2
    
    return min(complexity, 1.0)
```

---

### 五、Residual Risk 处理（Flash 的局限性）

```python
def handle_flash_residual_risk(
    task_id: str,
    step_id: str,
    flash_result: dict
) -> ResidualRiskDecision:
    """
    处理 Flash 完成后的 residual risk
    """
    
    state = load_token(task_id)
    step = load_plan(task_id).steps[step_id]
    
    # === 1. 检查是否需要升级验证 ===
    oracle_decision = should_invoke_oracle_l2(task_id, step_id)
    
    if oracle_decision.invoke:
        # Flash 执行 + Opus 验证
        return ResidualRiskDecision(
            action="escalate_to_oracle",
            reason=oracle_decision.reason.value,
            estimated_additional_cost=0.05,
        )
    
    # === 2. 检查 Flash 输出质量 ===
    quality_issues = analyze_flash_output_quality(flash_result)
    
    if quality_issues:
        return ResidualRiskDecision(
            action="retry_with_opus",
            reason=f"Flash output quality issues: {quality_issues}",
            estimated_additional_cost=0.30,
        )
    
    # === 3. 通过自验 ===
    return ResidualRiskDecision(
        action="accept_flash_result",
        reason="Flash result meets quality threshold",
        estimated_additional_cost=0,
    )


def analyze_flash_output_quality(result: dict) -> List[str]:
    """
    分析 Flash 输出质量
    """
    issues = []
    
    # 检查 1：是否有语法错误
    if result.get("syntax_errors"):
        issues.append("syntax_errors_detected")
    
    # 检查 2：是否有测试失败
    if result.get("test_failures"):
        issues.append("test_failures")
    
    # 检查 3：输出是否完整
    if result.get("truncated"):
        issues.append("output_truncated")
    
    # 检查 4：是否有逻辑漏洞（启发式）
    if detect_potential_logic_bugs(result):
        issues.append("potential_logic_bugs")
    
    return issues
```

---

### 六、无人模式 Autonomy Contract（基础）

```python
@dataclass
class AutonomyContract:
    """
    无人模式合约
    定义模型可以自主决策的边界
    """
    
    task_id: str
    max_steps: int
    max_cost_usd: float
    max_duration_minutes: int
    
    # 允许的自主动作
    allowed_actions: List[str]  # ["read_file", "write_file", "run_test", "git_commit"]
    
    # 禁止的动作
    forbidden_actions: List[str]  # ["git_push", "api_call", "db_write"]
    
    # 人工介入条件
    human_intervention_triggers: List[str]
    
    # 停止条件
    stop_conditions: List[str]


def execute_autonomy_loop(
    task_id: str,
    contract: AutonomyContract
) -> AutonomyResult:
    """
    无人模式执行循环
    """
    
    start_time = now()
    steps_executed = 0
    total_cost = 0.0
    
    while True:
        # === 1. 检查停止条件 ===
        if steps_executed >= contract.max_steps:
            return AutonomyResult(
                status="max_steps_reached",
                steps_executed=steps_executed,
                total_cost=total_cost,
            )
        
        elapsed_minutes = (now() - start_time).total_seconds() / 60
        if elapsed_minutes >= contract.max_duration_minutes:
            return AutonomyResult(
                status="max_duration_reached",
                steps_executed=steps_executed,
                total_cost=total_cost,
            )
        
        if total_cost >= contract.max_cost_usd:
            return AutonomyResult(
                status="max_cost_reached",
                steps_executed=steps_executed,
                total_cost=total_cost,
            )
        
        # === 2. 观察当前状态 ===
        state = load_token(task_id)
        
        # 检查是否需要人工介入
        for trigger in contract.human_intervention_triggers:
            if check_trigger(state, trigger):
                return AutonomyResult(
                    status="human_intervention_required",
                    reason=trigger,
                    steps_executed=steps_executed,
                    total_cost=total_cost,
                )
        
        # === 3. 决策下一步 ===
        next_action = decide_next_action(state, contract)
        
        if next_action.action_type not in contract.allowed_actions:
            return AutonomyResult(
                status="forbidden_action_blocked",
                reason=f"Attempted: {next_action.action_type}",
                steps_executed=steps_executed,
                total_cost=total_cost,
            )
        
        # === 4. 执行动作 ===
        action_result = execute_action(next_action)
        total_cost += action_result.cost
        
        # === 5. 验证不变式 ===
        if not verify_local_invariant(task_id):
            return AutonomyResult(
                status="invariant_violated",
                steps_executed=steps_executed,
                total_cost=total_cost,
            )
        
        # === 6. 检查进展 ===
        progress_fingerprint = compute_progress_fingerprint(state)
        
        # 检测空转
        if is_no_progress_loop(task_id, progress_fingerprint):
            return AutonomyResult(
                status="no_progress_detected",
                steps_executed=steps_executed,
                total_cost=total_cost,
            )
        
        steps_executed += 1
        
        # === 7. 检查是否完成 ===
        if check_task_completed(task_id):
            return AutonomyResult(
                status="completed",
                steps_executed=steps_executed,
                total_cost=total_cost,
            )
```

**硬规则**：

```text
无人模式必须：
✓ 一次循环只执行一个可回滚 action
✓ 每次循环都有进展度量
✓ 连续无进展时停止
✓ compact/resume 后不能盲目重放 action
✓ 所有停止都生成 handoff

无人模式禁止：
✗ 自动扩大 scope
✗ 执行不可逆操作（除非明确授权）
✗ 无限思考循环
✗ 跳过 VerifyGate
```

---

### 七、验收测试

```python
def test_l2_requires_checkpoint_before_irreversible():
    """L2 不可逆操作前必须 checkpoint"""
    task_id = "test-001"
    update_state(task_id, {"manifest_level": "L2"}, 1)
    
    # 添加不可逆副作用
    add_external_effect(task_id, {
        "effect_id": "EXT-001",
        "kind": "api_call",
        "status": "PENDING",
        "reversible": False,
    })
    
    # 检查是否要求 checkpoint / Oracle
    decision = should_invoke_oracle(task_id)
    assert decision["should_invoke"] is True
    assert decision["reason"] in {"irreversible_effect", "high_risk"}


def test_l2_autonomy_has_stop_conditions():
    """L2 无人模式必须有停止条件"""
    config = AutonomyConfig(max_cycles=3, max_cost_usd=1.0, require_progress=True)
    result = validate_autonomy_config(config)
    assert result["allowed"] is True
    assert result["stop_conditions"]
```

---

### 八、本轮结论

第 6 轮定义了 L2 的核心边界：高风险任务必须先 checkpoint，再执行可审计动作；Oracle 在本轮仅作为条件触发草案，用于标记高风险、验证僵局、连续失败或不可逆副作用前的仲裁入口；无人模式必须有成本、轮次、进展度量和停止条件。

### 九、第 7 轮预告

第 7 轮进入 Context Compiler、Claude Code Hook、OpenCode 适配、模型路由与成本看板，将第 6 轮的 L2 边界落到可观测、可编译、可双栈适配的工程化上下文层。
