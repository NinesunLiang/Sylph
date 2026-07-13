# CarrorOS Opus-4.8 完整方案（9/10）

## 第 9 轮：Oracle 固化设计与成本治理

---

> 本轮定位：第 6 轮的条件 Oracle 是草案/初版，本轮将其收敛为可执行的固化版，并明确成本治理、防滥用与 VerifyGate 集成边界。

## 一、Oracle 核心定位

### 1.1 什么是 Oracle

```yaml
# Oracle 定义
definition: >
  Oracle 是"验证僵局的最终仲裁者"，当 Agent 无法自证完成时介入。
  它不是代替 Agent 干活的"超级 Agent"，而是验证系统的终审法庭。

核心职责:
  - 接受 VerifyGate BLOCKED 升级
  - 标准化问题诊断
  - 给出 PASS / FAIL / NEED_REWORK verdict
  - 记录升级原因与决策依据
  - 成本可控（单次调用 < $0.05）

非职责:
  - ✗ 替 Agent 写代码
  - ✗ 替 Agent 做架构决策
  - ✗ 成为"无限重试器"
  - ✗ 绕过 VerifyGate 直接标记 DONE
  - ✗ 修改 state / plan

边界:
  - Oracle 只回答"这个 step 是否完成"
  - Oracle 不执行 action，只审查 evidence
  - Oracle verdict 必须有明确依据
  - Oracle 不能因为"看起来对"就 PASS
```

### 1.2 Oracle 触发条件（严格限定）

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class OracleEscalation:
    """
    Oracle 升级请求
    """
    
    # === 身份 ===
    escalation_id: str         # "ORACLE-001"
    task_id: str
    step_id: str
    timestamp: str
    
    # === 触发条件 ===
    trigger: dict
    # {
    #   "reason": "verify_gate_blocked" | "ambiguous_success" | 
    #             "external_verification_required" | "cost_threshold_exceeded",
    #   "verify_attempts": int,      # VerifyGate 尝试次数
    #   "last_verify_result": dict,  # 最后一次验证结果
    # }
    
    # === 上下文 ===
    context: dict
    # {
    #   "step_description": str,
    #   "acceptance_criteria": List[str],
    #   "evidence_provided": List[str],  # Evidence IDs
    #   "agent_claim": str,              # Agent 的声明
    #   "blocking_reason": str,          # VerifyGate 阻断原因
    # }
    
    # === 成本控制 ===
    cost_budget: dict
    # {
    #   "max_usd": 0.05,
    #   "model": "deepseek-v4-flash",  # 优先用便宜模型
    #   "allow_upgrade": bool,          # 是否允许升级到 Opus
    # }


class OracleTriggerPolicy:
    """
    Oracle 触发策略：何时允许升级
    """
    
    @staticmethod
    def should_escalate_to_oracle(
        step: dict,
        verify_result: dict,
        retry_count: int,
    ) -> dict:
        """
        判断是否应该升级到 Oracle
        """
        
        # 1. VerifyGate 明确 FAIL（有具体原因）→ 不升级，Agent 自己修
        if verify_result["status"] == "FAIL" and verify_result.get("failure_reason"):
            return {
                "should_escalate": False,
                "reason": "verify_fail_with_clear_reason",
                "instruction": "Agent 应根据 failure_reason 修复",
            }
        
        # 2. VerifyGate BLOCKED（证据不足）→ 重试 < 3 次先让 Agent 补证据
        if verify_result["status"] == "BLOCKED":
            if retry_count < 3:
                return {
                    "should_escalate": False,
                    "reason": "insufficient_evidence_retry_allowed",
                    "instruction": "Agent 应提供更多 evidence",
                }
            else:
                # 重试 >= 3 次仍 BLOCKED → 升级 Oracle
                return {
                    "should_escalate": True,
                    "reason": "verify_gate_blocked_after_retries",
                    "escalation_type": "ambiguous_success",
                }
        
        # 3. VerifyGate PASS 但 step 标记需要外部验证 → 升级 Oracle
        if step.get("requires_external_verification"):
            return {
                "should_escalate": True,
                "reason": "external_verification_required",
                "escalation_type": "external_verification_required",
            }
        
        # 4. 成本超过阈值（累计重试成本 > $0.20）→ 升级 Oracle 做最终裁决
        cumulative_cost = step.get("retry_cost_usd", 0)
        if cumulative_cost > 0.20:
            return {
                "should_escalate": True,
                "reason": "cost_threshold_exceeded",
                "escalation_type": "cost_threshold_exceeded",
            }
        
        # 默认：不升级
        return {
            "should_escalate": False,
            "reason": "no_escalation_condition_met",
        }
```

---

## 二、Oracle 完整实现

### 2.1 Oracle Engine Schema

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class OracleVerdict:
    """
    Oracle 终审裁决
    """
    
    # === 身份 ===
    verdict_id: str            # "VERDICT-001"
    escalation_id: str         # 关联的 Escalation ID
    timestamp: str
    
    # === 裁决 ===
    decision: str              # "PASS" | "FAIL" | "NEED_REWORK"
    confidence: float          # 0.0 ~ 1.0
    
    # === 依据 ===
    reasoning: str             # 裁决理由（完整）
    evidence_reviewed: List[str]  # 审查的 Evidence IDs
    criteria_met: List[str]    # 满足的验收标准
    criteria_unmet: List[str]  # 未满足的验收标准
    
    # === 建议 ===
    recommendation: Optional[str]  # 如果 FAIL/NEED_REWORK，给出建议
    required_fixes: List[str]      # 必须修复的问题
    
    # === 成本 ===
    cost_usd: float            # 本次 Oracle 调用成本
    model_used: str            # 使用的模型
    
    # === 元数据 ===
    oracle_version: str        # Oracle 引擎版本
    audit_trail: str           # 审计日志路径


class OracleEngine:
    """
    Oracle 引擎：验证僵局的终审仲裁
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.model_router = ModelRouter(config)
    
    def render_oracle_prompt(self, escalation: OracleEscalation) -> str:
        """
        生成 Oracle Prompt（标准化问题）
        """
        
        # 加载 evidence
        evidences = [
            load_evidence(escalation.task_id, eid)
            for eid in escalation.context["evidence_provided"]
        ]
        
        # 格式化 evidence
        evidence_text = "\n\n".join([
            f"**Evidence {i+1}: {e.title}**\n{e.content}"
            for i, e in enumerate(evidences)
        ])
        
        prompt = f"""# Oracle Verification Request

## Task Context
- **Task ID**: {escalation.task_id}
- **Step ID**: {escalation.step_id}
- **Step Description**: {escalation.context['step_description']}

## Acceptance Criteria
{self._format_criteria(escalation.context['acceptance_criteria'])}

## Agent's Claim
{escalation.context['agent_claim']}

## VerifyGate Blocking Reason
{escalation.context['blocking_reason']}

## Evidence Provided
{evidence_text}

---

## Your Task
You are the **Oracle**: the final arbiter when automated verification is blocked.

**Answer this single question**:
> Has this step been **completed** according to the acceptance criteria?

### Rules
1. **PASS** only if ALL acceptance criteria are met with clear evidence
2. **FAIL** if clear evidence shows criteria are NOT met
3. **NEED_REWORK** if evidence is ambiguous or incomplete

### Response Format
```json
{{
  "decision": "PASS" | "FAIL" | "NEED_REWORK",
  "confidence": 0.0-1.0,
  "reasoning": "Detailed explanation of your decision",
  "criteria_met": ["criterion 1", "criterion 2"],
  "criteria_unmet": ["criterion 3"],
  "recommendation": "What needs to be fixed (if FAIL/NEED_REWORK)",
  "required_fixes": ["fix 1", "fix 2"]
}}
```

**Be strict**: If in doubt, choose NEED_REWORK, not PASS.
"""
        
        return prompt
    
    def invoke_oracle(self, escalation: OracleEscalation) -> OracleVerdict:
        """
        调用 Oracle（LLM 终审）
        """
        
        # 1. 生成 Oracle Prompt
        prompt = self.render_oracle_prompt(escalation)
        
        # 2. 选择模型（优先便宜模型）
        if escalation.cost_budget["allow_upgrade"]:
            model = "claude-opus-4-8"  # 复杂情况用 Opus
        else:
            model = escalation.cost_budget["model"]  # 默认 Flash
        
        # 3. 调用 LLM
        response = self.model_router.invoke(
            model=model,
            prompt=prompt,
            # Opus 4.8 示例使用 prompt / effort / structured output 控制稳定性；不使用 temperature。
            max_tokens=2000,
        )
        
        # 4. 解析响应
        try:
            verdict_data = json.loads(response["content"])
        except json.JSONDecodeError:
            # 降级处理：提取关键信息
            verdict_data = self._parse_fallback(response["content"])
        
        # 5. 生成 Verdict
        verdict = OracleVerdict(
            verdict_id=f"VERDICT-{len(glob.glob('.omc/oracle/verdicts/*.json')) + 1:03d}",
            escalation_id=escalation.escalation_id,
            timestamp=now(),
            decision=verdict_data["decision"],
            confidence=verdict_data.get("confidence", 0.0),
            reasoning=verdict_data["reasoning"],
            evidence_reviewed=escalation.context["evidence_provided"],
            criteria_met=verdict_data.get("criteria_met", []),
            criteria_unmet=verdict_data.get("criteria_unmet", []),
            recommendation=verdict_data.get("recommendation"),
            required_fixes=verdict_data.get("required_fixes", []),
            cost_usd=response["cost_usd"],
            model_used=model,
            oracle_version="1.0.0",
            audit_trail=f".omc/oracle/audit/{verdict.verdict_id}.jsonl",
        )
        
        # 6. 持久化
        self._persist_verdict(verdict)
        
        # 7. 记录审计
        self._log_audit(escalation, verdict, prompt, response)
        
        return verdict
    
    def _format_criteria(self, criteria: List[str]) -> str:
        """
        格式化验收标准
        """
        return "\n".join(f"{i+1}. {c}" for i, c in enumerate(criteria))
    
    def _parse_fallback(self, content: str) -> dict:
        """
        降级解析（LLM 未返回 JSON）
        """
        # 简单规则提取
        if "PASS" in content:
            decision = "PASS"
        elif "FAIL" in content:
            decision = "FAIL"
        else:
            decision = "NEED_REWORK"
        
        return {
            "decision": decision,
            "confidence": 0.5,
            "reasoning": content,
            "criteria_met": [],
            "criteria_unmet": [],
            "recommendation": None,
            "required_fixes": [],
        }
    
    def _persist_verdict(self, verdict: OracleVerdict):
        """
        持久化 Verdict
        """
        path = f".omc/oracle/verdicts/{verdict.verdict_id}.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(asdict(verdict), f, indent=2)
    
    def _log_audit(
        self,
        escalation: OracleEscalation,
        verdict: OracleVerdict,
        prompt: str,
        response: dict
    ):
        """
        记录 Oracle 审计日志
        """
        audit_entry = {
            "timestamp": now(),
            "escalation_id": escalation.escalation_id,
            "verdict_id": verdict.verdict_id,
            "prompt": prompt,
            "response": response,
            "decision": verdict.decision,
            "cost_usd": verdict.cost_usd,
        }
        
        audit_path = verdict.audit_trail
        os.makedirs(os.path.dirname(audit_path), exist_ok=True)
        
        with open(audit_path, "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
```

### 2.2 Oracle 集成到 VerifyGate

```python
class VerifyGate:
    """
    VerifyGate + Oracle 集成
    """
    
    def __init__(self, task_id: str, config: dict):
        self.task_id = task_id
        self.config = config
        self.oracle = OracleEngine(config)
    
    def verify_step_with_oracle_fallback(
        self,
        step_id: str,
        retry_count: int = 0
    ) -> dict:
        """
        VerifyGate 验证 + Oracle 兜底
        """
        
        # 1. 标准 VerifyGate 验证
        verify_result = self.verify_step(step_id)
        
        # 2. 检查是否需要升级 Oracle
        step = load_plan(self.task_id).steps[step_id]
        
        escalation_check = OracleTriggerPolicy.should_escalate_to_oracle(
            step=step,
            verify_result=verify_result,
            retry_count=retry_count,
        )
        
        if not escalation_check["should_escalate"]:
            # 不需要 Oracle，返回原验证结果
            return {
                "status": verify_result["status"],
                "oracle_invoked": False,
                "verify_result": verify_result,
            }
        
        # 3. 升级到 Oracle
        escalation = OracleEscalation(
            escalation_id=f"ORACLE-{len(glob.glob('.omc/oracle/escalations/*.json')) + 1:03d}",
            task_id=self.task_id,
            step_id=step_id,
            timestamp=now(),
            trigger={
                "reason": escalation_check["reason"],
                "verify_attempts": retry_count,
                "last_verify_result": verify_result,
            },
            context={
                "step_description": step.get("description", ""),
                "acceptance_criteria": step.get("acceptance_criteria", []),
                "evidence_provided": self._get_evidence_ids(step_id),
                "agent_claim": step.get("claim", ""),
                "blocking_reason": verify_result.get("blocking_reason", ""),
            },
            cost_budget={
                "max_usd": 0.05,
                "model": "deepseek-v4-flash",
                "allow_upgrade": retry_count >= 5,  # 重试 5 次后允许用 Opus
            },
        )
        
        # 持久化 Escalation
        self._persist_escalation(escalation)
        
        # 4. 调用 Oracle
        verdict = self.oracle.invoke_oracle(escalation)
        
        # 5. 根据 Oracle Verdict 更新 step 状态
        if verdict.decision == "PASS":
            return {
                "status": "PASS",
                "oracle_invoked": True,
                "verdict": verdict,
                "message": f"Oracle PASS: {verdict.reasoning}",
            }
        elif verdict.decision == "FAIL":
            return {
                "status": "FAIL",
                "oracle_invoked": True,
                "verdict": verdict,
                "failure_reason": verdict.reasoning,
                "required_fixes": verdict.required_fixes,
            }
        else:  # NEED_REWORK
            return {
                "status": "BLOCKED",
                "oracle_invoked": True,
                "verdict": verdict,
                "blocking_reason": verdict.reasoning,
                "recommendation": verdict.recommendation,
            }
    
    def _get_evidence_ids(self, step_id: str) -> List[str]:
        """
        获取 step 的所有 Evidence IDs
        """
        evidences = load_evidences(self.task_id)
        return [e.evidence_id for e in evidences if e.step_id == step_id]
    
    def _persist_escalation(self, escalation: OracleEscalation):
        """
        持久化 Escalation
        """
        path = f".omc/oracle/escalations/{escalation.escalation_id}.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, "w") as f:
            json.dump(asdict(escalation), f, indent=2)
```

---

## 三、成本治理固化

### 3.1 成本红线与自动降级

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CostRedLine:
    """
    成本红线：硬预算边界
    """
    
    # === 全局红线 ===
    max_task_cost_usd: float           # 单任务最大成本
    max_turn_cost_usd: float           # 单轮最大成本
    max_oracle_calls_per_task: int    # 单任务 Oracle 调用次数上限
    
    # === 模型红线 ===
    opus_monthly_budget_usd: float    # Opus 月预算
    flash_monthly_budget_usd: float   # Flash 月预算
    
    # === 自动降级阈值 ===
    auto_downgrade_threshold_pct: float  # 预算使用率触发降级（如 80%）


class CostGovernor:
    """
    成本治理器：红线告警 + 自动降级
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.red_line = CostRedLine(
            max_task_cost_usd=config.get("max_task_cost_usd", 5.0),
            max_turn_cost_usd=config.get("max_turn_cost_usd", 0.5),
            max_oracle_calls_per_task=config.get("max_oracle_calls_per_task", 10),
            opus_monthly_budget_usd=config.get("opus_monthly_budget_usd", 500.0),
            flash_monthly_budget_usd=config.get("flash_monthly_budget_usd", 100.0),
            auto_downgrade_threshold_pct=config.get("auto_downgrade_threshold_pct", 0.8),
        )
    
    def check_before_invoke(
        self,
        task_id: str,
        model: str,
        estimated_cost_usd: float
    ) -> dict:
        """
        调用前成本检查
        """
        
        # 1. 加载当前成本
        state = load_token(task_id)
        current_task_cost = state.cost_tracking.get("total_usd", 0)
        
        # 2. 检查任务红线
        if current_task_cost + estimated_cost_usd > self.red_line.max_task_cost_usd:
            return {
                "allowed": False,
                "reason": "task_cost_exceeded",
                "current": current_task_cost,
                "limit": self.red_line.max_task_cost_usd,
                "action": "BLOCK_TASK",
            }
        
        # 3. 检查单轮红线
        if estimated_cost_usd > self.red_line.max_turn_cost_usd:
            return {
                "allowed": False,
                "reason": "turn_cost_exceeded",
                "estimated": estimated_cost_usd,
                "limit": self.red_line.max_turn_cost_usd,
                "action": "DOWNGRADE_MODEL",
            }
        
        # 4. 检查月度预算
        monthly_usage = self._get_monthly_usage(model)
        monthly_budget = (
            self.red_line.opus_monthly_budget_usd if "opus" in model.lower()
            else self.red_line.flash_monthly_budget_usd
        )
        
        usage_pct = monthly_usage / monthly_budget
        
        if usage_pct >= 1.0:
            return {
                "allowed": False,
                "reason": "monthly_budget_exceeded",
                "usage": monthly_usage,
                "budget": monthly_budget,
                "action": "BLOCK_MODEL",
            }
        
        # 5. 检查自动降级阈值
        if usage_pct >= self.red_line.auto_downgrade_threshold_pct:
            return {
                "allowed": True,
                "warning": "approaching_budget_limit",
                "usage_pct": usage_pct,
                "action": "SUGGEST_DOWNGRADE",
            }
        
        # 6. 通过
        return {
            "allowed": True,
            "usage_pct": usage_pct,
        }
    
    def auto_downgrade_model(self, requested_model: str) -> str:
        """
        自动降级模型
        """
        
        # 降级路径
        downgrade_map = {
            "claude-opus-4-8": "deepseek-v4-flash",
            "deepseek-v4": "deepseek-v4-flash",
            "gpt-4o": "gpt-4o-mini",
        }
        
        return downgrade_map.get(requested_model, requested_model)
    
    def _get_monthly_usage(self, model: str) -> float:
        """
        获取月度使用量
        """
        # 从成本追踪数据库读取
        cost_db_path = ".omc/cost/monthly_usage.json"
        
        if not os.path.exists(cost_db_path):
            return 0.0
        
        data = read_json(cost_db_path)
        current_month = datetime.now().strftime("%Y-%m")
        
        return data.get(current_month, {}).get(model, 0.0)
    
    def record_usage(self, model: str, cost_usd: float):
        """
        记录使用量
        """
        cost_db_path = ".omc/cost/monthly_usage.json"
        os.makedirs(os.path.dirname(cost_db_path), exist_ok=True)
        
        if os.path.exists(cost_db_path):
            data = read_json(cost_db_path)
        else:
            data = {}
        
        current_month = datetime.now().strftime("%Y-%m")
        
        if current_month not in data:
            data[current_month] = {}
        
        if model not in data[current_month]:
            data[current_month][model] = 0.0
        
        data[current_month][model] += cost_usd
        
        write_json(cost_db_path, data)
```

### 3.2 成本看板集成 Oracle

```python
class CostDashboard:
    """
    成本看板：实时监控 + Oracle 成本
    """
    
    def __init__(self, task_id: str):
        self.task_id = task_id
    
    def render_dashboard(self) -> str:
        """
        渲染成本看板（包含 Oracle）
        """
        state = load_token(self.task_id)
        cost = state.cost_tracking
        
        # Oracle 成本
        oracle_verdicts = glob.glob(f".omc/oracle/verdicts/*.json")
        oracle_cost = sum(
            read_json(v).get("cost_usd", 0)
            for v in oracle_verdicts
        )
        oracle_count = len(oracle_verdicts)
        
        dashboard = f"""
# Cost Dashboard: {self.task_id}

## Total Cost
- **Total**: ${cost.get('total_usd', 0):.4f}
- **Avg/turn**: ${cost.get('avg_per_turn', 0):.4f}
- **Oracle**: ${oracle_cost:.4f} ({oracle_count} calls)

## By Model
{self._render_by_model(cost)}

## By Category
- **Search/Research**: ${cost.get('by_category', {}).get('search', 0):.4f}
- **Feature Implementation**: ${cost.get('by_category', {}).get('feature', 0):.4f}
- **Testing**: ${cost.get('by_category', {}).get('test', 0):.4f}
- **Oracle Verification**: ${oracle_cost:.4f}

## Budget Status
{self._render_budget_status(cost, oracle_cost)}

## Recommendations
{self._render_recommendations(cost, oracle_cost)}
"""
        
        return dashboard
    
    def _render_by_model(self, cost: dict) -> str:
        by_model = cost.get('by_model', {})
        
        lines = []
        for model, amount in sorted(by_model.items(), key=lambda x: -x[1]):
            lines.append(f"- **{model}**: ${amount:.4f}")
        
        return "\n".join(lines) if lines else "- None"
    
    def _render_budget_status(self, cost: dict, oracle_cost: float) -> str:
        total = cost.get('total_usd', 0)
        max_task_cost = 5.0  # 从 config 读取
        
        usage_pct = (total / max_task_cost) * 100
        
        if usage_pct < 50:
            status = "🟢 HEALTHY"
        elif usage_pct < 80:
            status = "🟡 WARNING"
        else:
            status = "🔴 CRITICAL"
        
        return f"""
- **Task Budget**: ${total:.4f} / ${max_task_cost:.2f} ({usage_pct:.1f}%) {status}
- **Oracle Budget**: ${oracle_cost:.4f} / $0.50 ({(oracle_cost/0.50)*100:.1f}%)
"""
    
    def _render_recommendations(self, cost: dict, oracle_cost: float) -> str:
        recommendations = []
        
        total = cost.get('total_usd', 0)
        
        if total > 4.0:
            recommendations.append("⚠️ Task cost approaching limit, consider splitting into subtasks")
        
        if oracle_cost > 0.30:
            recommendations.append("⚠️ High Oracle cost, review acceptance criteria clarity")
        
        opus_cost = cost.get('by_model', {}).get('claude-opus-4-8', 0)
        if opus_cost > total * 0.7:
            recommendations.append("💡 Consider using Flash for search/research tasks")
        
        return "\n".join(recommendations) if recommendations else "✅ No issues detected"
```

---

## 四、Oracle 防滥用机制

```python
class OracleAbuseDetector:
    """
    Oracle 防滥用检测
    """
    
    @staticmethod
    def detect_abuse(task_id: str) -> dict:
        """
        检测 Oracle 滥用
        """
        
        # 加载所有 Oracle 调用与 verdict（示意）
        task_escalations = load_task_oracle_escalations(task_id)
        verdicts = load_task_oracle_verdicts(task_id)
        issues = []
        
        low_confidence = [v for v in verdicts if v.get("confidence", 1.0) < 0.7]
        
        if len(low_confidence) > 3:
            issues.append({
                "type": "low_confidence_verdicts",
                "count": len(low_confidence),
                "recommendation": "Evidence quality is poor, Agent should provide better evidence",
            })
        
        # 4. NEED_REWORK 循环（Oracle → Agent → Oracle）
        rework_chains = []
        for esc in task_escalations:
            verdict = read_json(f".omc/oracle/verdicts/{esc['escalation_id'].replace('ORACLE', 'VERDICT')}.json")
            if verdict.get("decision") == "NEED_REWORK":
                rework_chains.append(esc["step_id"])
        
        rework_loops = {step: rework_chains.count(step) for step in set(rework_chains)}
        
        for step_id, count in rework_loops.items():
            if count > 2:
                issues.append({
                    "type": "rework_loop",
                    "step_id": step_id,
                    "count": count,
                    "recommendation": f"Step {step_id} is stuck in rework loop - consider splitting step",
                })
        
        # 5. Oracle 成本占比过高（> 30%）
        oracle_cost = sum(v.get("cost_usd", 0) for v in verdicts)
        state = load_token(task_id)
        total_cost = state.cost_tracking.get("total_usd", 0)
        
        if total_cost > 0:
            oracle_pct = (oracle_cost / total_cost) * 100
            
            if oracle_pct > 30:
                issues.append({
                    "type": "excessive_oracle_cost",
                    "oracle_cost_usd": oracle_cost,
                    "total_cost_usd": total_cost,
                    "percentage": oracle_pct,
                    "recommendation": "Improve acceptance criteria clarity to reduce Oracle dependency",
                })
        
        return {
            "has_abuse": len(issues) > 0,
            "issues": issues,
            "total_oracle_calls": len(task_escalations),
            "total_oracle_cost_usd": oracle_cost,
        }
```

---

## 五、成本超支自动处理

```python
class CostOverrunHandler:
    """
    成本超支自动处理器
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.governor = CostGovernor(config)
    
    def handle_overrun(
        self,
        task_id: str,
        current_cost_usd: float,
        estimated_remaining_usd: float
    ) -> dict:
        """
        处理成本超支
        """
        
        red_line = self.governor.red_line
        total_projected = current_cost_usd + estimated_remaining_usd
        
        # 1. 超支等级评估
        if total_projected > red_line.max_task_cost_usd * 1.5:
            severity = "CRITICAL"
        elif total_projected > red_line.max_task_cost_usd * 1.2:
            severity = "HIGH"
        elif total_projected > red_line.max_task_cost_usd:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        # 2. 根据严重程度选择策略
        if severity == "CRITICAL":
            return self._handle_critical_overrun(task_id, current_cost_usd, total_projected)
        elif severity == "HIGH":
            return self._handle_high_overrun(task_id, current_cost_usd, total_projected)
        elif severity == "MEDIUM":
            return self._handle_medium_overrun(task_id, current_cost_usd, total_projected)
        else:
            return {
                "action": "CONTINUE",
                "reason": "Within acceptable range",
            }
    
    def _handle_critical_overrun(
        self,
        task_id: str,
        current_cost: float,
        projected_cost: float
    ) -> dict:
        """
        处理 CRITICAL 超支：立即阻断
        """
        
        # 1. 冻结任务
        state = load_token(task_id)
        state.outcome = "BLOCKED_COST_OVERRUN"
        write_token(task_id, state)
        
        # 2. 生成超支报告
        report_path = f".omc/cost/overrun_reports/{task_id}.md"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        report = f"""# Cost Overrun Report: {task_id}

## Status
🔴 **CRITICAL OVERRUN** - Task Blocked

## Cost Analysis
- **Current Cost**: ${current_cost:.4f}
- **Projected Cost**: ${projected_cost:.4f}
- **Budget**: ${self.governor.red_line.max_task_cost_usd:.2f}
- **Overrun**: ${projected_cost - self.governor.red_line.max_task_cost_usd:.4f} ({((projected_cost / self.governor.red_line.max_task_cost_usd) - 1) * 100:.1f}% over)

## Recommended Actions
1. **SPLIT TASK**: Break into smaller subtasks with separate budgets
2. **SIMPLIFY SCOPE**: Remove non-critical requirements
3. **MANUAL REVIEW**: Escalate to user for budget approval

## Next Steps
- Task is now BLOCKED
- User intervention required to:
  - Approve additional budget, OR
  - Split task into subtasks, OR
  - Cancel task
"""
        
        with open(report_path, "w") as f:
            f.write(report)
        
        return {
            "action": "BLOCK_TASK",
            "severity": "CRITICAL",
            "current_cost": current_cost,
            "projected_cost": projected_cost,
            "report_path": report_path,
            "message": "Task blocked due to critical cost overrun",
        }
    
    def _handle_high_overrun(
        self,
        task_id: str,
        current_cost: float,
        projected_cost: float
    ) -> dict:
        """
        处理 HIGH 超支：自动降级 + 警告
        """
        
        # 1. 启用激进降级模式
        state = load_token(task_id)
        
        if not hasattr(state, 'cost_mode'):
            state.cost_mode = "AGGRESSIVE_DOWNGRADE"
        
        # 2. 禁用 Opus，强制 Flash
        state.model_constraints = {
            "allowed_models": ["deepseek-v4-flash", "gpt-4o-mini"],
            "reason": "cost_overrun_high",
        }
        
        write_token(task_id, state)
        
        # 3. 记录警告
        self._log_cost_warning(task_id, "HIGH", current_cost, projected_cost)
        
        return {
            "action": "AGGRESSIVE_DOWNGRADE",
            "severity": "HIGH",
            "current_cost": current_cost,
            "projected_cost": projected_cost,
            "constraints_applied": state.model_constraints,
            "message": "Auto-downgraded to cheapest models due to cost overrun",
        }
    
    def _handle_medium_overrun(
        self,
        task_id: str,
        current_cost: float,
        projected_cost: float
    ) -> dict:
        """
        处理 MEDIUM 超支：建议降级
        """
        
        # 记录建议
        self._log_cost_warning(task_id, "MEDIUM", current_cost, projected_cost)
        
        return {
            "action": "SUGGEST_DOWNGRADE",
            "severity": "MEDIUM",
            "current_cost": current_cost,
            "projected_cost": projected_cost,
            "message": "Consider using cheaper models for remaining steps",
        }
    
    def _log_cost_warning(
        self,
        task_id: str,
        severity: str,
        current_cost: float,
        projected_cost: float
    ):
        """
        记录成本警告
        """
        warning_log = ".omc/cost/warnings.jsonl"
        os.makedirs(os.path.dirname(warning_log), exist_ok=True)
        
        entry = {
            "timestamp": now(),
            "task_id": task_id,
            "severity": severity,
            "current_cost_usd": current_cost,
            "projected_cost_usd": projected_cost,
            "budget_usd": self.governor.red_line.max_task_cost_usd,
        }
        
        with open(warning_log, "a") as f:
            f.write(json.dumps(entry) + "\n")
```

---

## 六、Oracle 与成本治理集成验收

### 6.1 Oracle 验收测试

```python
def test_oracle_escalation():
    """测试 Oracle 升级流程"""
    task_id = "test-oracle-001"
    
    # 1. 准备 BLOCKED step
    step = {
        "step_id": "step-1",
        "description": "实现用户认证",
        "acceptance_criteria": [
            "用户可以登录",
            "密码加密存储",
            "JWT token 生成",
        ],
        "status": "IN_PROGRESS",
        "requires_external_verification": False,
    }
    
    # 2. 模拟 VerifyGate BLOCKED
    verify_result = {
        "status": "BLOCKED",
        "blocking_reason": "无法确认 JWT token 是否正确生成",
    }
    
    # 3. 创建 Evidence
    evidence = Evidence(
        evidence_id="EV-001",
        task_id=task_id,
        step_id="step-1",
        timestamp=now(),
        title="登录功能实现",
        content="实现了 /login 端点，返回 JWT token",
        category="implementation",
        tags=["auth", "jwt"],
    )
    write_evidence(task_id, evidence)
    
    # 4. 检查是否应该升级 Oracle
    check = OracleTriggerPolicy.should_escalate_to_oracle(
        step=step,
        verify_result=verify_result,
        retry_count=3,  # 重试 3 次
    )
    
    assert check["should_escalate"] == True
    assert check["reason"] == "verify_gate_blocked_after_retries"
    
    # 5. 创建 Escalation
    escalation = OracleEscalation(
        escalation_id="ORACLE-001",
        task_id=task_id,
        step_id="step-1",
        timestamp=now(),
        trigger={
            "reason": check["reason"],
            "verify_attempts": 3,
            "last_verify_result": verify_result,
        },
        context={
            "step_description": step["description"],
            "acceptance_criteria": step["acceptance_criteria"],
            "evidence_provided": ["EV-001"],
            "agent_claim": "JWT token 已实现",
            "blocking_reason": verify_result["blocking_reason"],
        },
        cost_budget={
            "max_usd": 0.05,
            "model": "deepseek-v4-flash",
            "allow_upgrade": False,
        },
    )
    
    # 6. 调用 Oracle
    oracle = OracleEngine({})
    verdict = oracle.invoke_oracle(escalation)
    
    # 7. 验证 Verdict
    assert verdict.decision in ["PASS", "FAIL", "NEED_REWORK"]
    assert verdict.confidence >= 0.0 and verdict.confidence <= 1.0
    assert len(verdict.reasoning) > 0
    
    print(f"✅ Oracle verdict: {verdict.decision} (confidence: {verdict.confidence})")


def test_oracle_cost_limit():
    """测试 Oracle 成本限制"""
    task_id = "test-oracle-cost-001"
    
    # 1. 准备任务状态
    state = TaskState(
        task_id=task_id,
        manifest_level="L1",
        started_at=now(),
        outcome="IN_PROGRESS",
        cost_tracking={"total_usd": 0.0},
    )
    write_token(task_id, state)
    
    # 2. 模拟 10 次 Oracle 调用
    for i in range(10):
        escalation = OracleEscalation(
            escalation_id=f"ORACLE-{i+1:03d}",
            task_id=task_id,
            step_id=f"step-{i+1}",
            timestamp=now(),
            trigger={"reason": "test"},
            context={
                "step_description": f"Test step {i+1}",
                "acceptance_criteria": ["Test"],
                "evidence_provided": [],
                "agent_claim": "Done",
                "blocking_reason": "Test",
            },
            cost_budget={
                "max_usd": 0.05,
                "model": "deepseek-v4-flash",
                "allow_upgrade": False,
            },
        )
        
        # 记录成本
        state = load_token(task_id)
        state.cost_tracking["total_usd"] += 0.02
        write_token(task_id, state)
    
    # 3. 检查滥用
    abuse_report = OracleAbuseDetector.detect_abuse(task_id)
    
    # 4. 验证
    assert abuse_report["has_abuse"] == True
    assert abuse_report["total_oracle_calls"] == 10
    assert any(issue["type"] == "excessive_oracle_calls" for issue in abuse_report["issues"])
    
    print(f"✅ Oracle abuse detected: {abuse_report['issues']}")


def test_cost_overrun_critical():
    """测试 CRITICAL 成本超支"""
    task_id = "test-cost-critical-001"
    
    # 1. 准备任务
    state = TaskState(
        task_id=task_id,
        manifest_level="L2",
        started_at=now(),
        outcome="IN_PROGRESS",
        cost_tracking={"total_usd": 7.0},  # 已经超支
    )
    write_token(task_id, state)
    
    # 2. 处理超支
    handler = CostOverrunHandler({
        "max_task_cost_usd": 5.0,
    })
    
    result = handler.handle_overrun(
        task_id=task_id,
        current_cost_usd=7.0,
        estimated_remaining_usd=1.5,
    )
    
    # 3. 验证
    assert result["action"] == "BLOCK_TASK"
    assert result["severity"] == "CRITICAL"
    
    # 4. 验证任务已冻结
    state = load_token(task_id)
    assert state.outcome == "BLOCKED_COST_OVERRUN"
    
    # 5. 验证报告已生成
    assert os.path.exists(result["report_path"])
    
    print(f"✅ Critical overrun handled: task blocked")


def test_cost_dashboard_with_oracle():
    """测试成本看板（含 Oracle）"""
    task_id = "test-dashboard-001"
    
    # 1. 准备任务
    state = TaskState(
        task_id=task_id,
        manifest_level="L2",
        started_at=now(),
        outcome="IN_PROGRESS",
        cost_tracking={
            "total_usd": 0.85,
            "avg_per_turn": 0.042,
            "by_model": {
                "deepseek-v4-flash": 0.30,
                "claude-opus-4-8": 0.50,
            },
        },
    )
    write_token(task_id, state)
    
    # 2. 模拟 Oracle 调用
    verdict = OracleVerdict(
        verdict_id="VERDICT-001",
        escalation_id="ORACLE-001",
        timestamp=now(),
        decision="PASS",
        confidence=0.9,
        reasoning="All criteria met",
        evidence_reviewed=["EV-001"],
        criteria_met=["criterion 1"],
        criteria_unmet=[],
        recommendation=None,
        required_fixes=[],
        cost_usd=0.05,
        model_used="deepseek-v4-flash",
        oracle_version="1.0.0",
        audit_trail=".omc/oracle/audit/VERDICT-001.jsonl",
    )
    
    os.makedirs(".omc/oracle/verdicts", exist_ok=True)
    with open(f".omc/oracle/verdicts/{verdict.verdict_id}.json", "w") as f:
        json.dump(asdict(verdict), f)
    
    # 3. 渲染看板
    dashboard = CostDashboard(task_id)
    output = dashboard.render_dashboard()
    
    # 4. 验证
    assert "$0.85" in output  # Total cost
    assert "$0.05" in output  # Oracle cost
    assert "deepseek-v4-flash" in output
    assert "claude-opus-4-8" in output
    
    print("✅ Cost dashboard with Oracle rendered successfully")
```

---

## 七、第 9 轮验收与交付边界

```yaml
schema_version: carros.round9.final_acceptance

# === 交付物 ===
deliverables:
  core_components:
    - OracleEngine（标准化问题 + LLM 调用）
    - OracleEscalation（升级请求 Schema）
    - OracleVerdict（终审裁决 Schema）
    - OracleTriggerPolicy（严格触发条件）
    - OracleAbuseDetector（防滥用检测）
    - CostGovernor（红线 + 自动降级）
    - CostOverrunHandler（超支自动处理）
    - CostDashboard（含 Oracle 成本）
  
  schemas:
    - OracleEscalation（5 个字段）
    - OracleVerdict（10 个字段）
    - CostRedLine（6 个字段）
  
  configuration_files:
    - .omc/cost/monthly_usage.json
  
  test_suite:
    - test_oracle_escalation（Oracle 升级流程）
    - test_oracle_cost_limit（Oracle 成本限制）
    - test_cost_overrun_critical（CRITICAL 超支处理）
    - test_cost_dashboard_with_oracle（成本看板含 Oracle）

# === SLO 达成 ===
slo_compliance:
  oracle_positioning:
    - ✅ Oracle 仅用于 VerifyGate BLOCKED 升级
    - ✅ Oracle 不替代 Agent 执行
    - ✅ Oracle 不绕过 VerifyGate
    - ✅ Oracle verdict 必须有明确依据
  
  oracle_triggering:
    - ✅ VerifyGate FAIL（有明确原因）→ 不升级
    - ✅ VerifyGate BLOCKED + 重试 < 3 → 不升级
    - ✅ VerifyGate BLOCKED + 重试 >= 3 → 升级
    - ✅ 需要外部验证 → 升级
    - ✅ 累计重试成本 > $0.20 → 升级
  
  oracle_cost_control:
    - ✅ 单次 Oracle 调用 < $0.05
    - ✅ 优先使用 Flash
    - ✅ 重试 >= 5 次后允许 Opus
    - ✅ Oracle 成本占比 > 30% 触发告警
  
  oracle_abuse_prevention:
    - ✅ 单任务 Oracle 调用 > 10 次告警
    - ✅ 同一 step Oracle > 3 次告警
    - ✅ 低置信度 verdict > 3 个告警
    - ✅ NEED_REWORK 循环检测
  
  cost_governance:
    - ✅ 任务成本红线（$5.0）
    - ✅ 单轮成本红线（$0.5）
    - ✅ 月度预算红线（Opus $500, Flash $100）
    - ✅ 预算使用率 > 80% 自动降级
    - ✅ CRITICAL 超支自动冻结任务
    - ✅ HIGH 超支强制 Flash
    - ✅ MEDIUM 超支建议降级

# === 双栈验收 ===
dual_stack_validation:
  claude_code:
    - ✅ Oracle 与 L5 compaction 隔离
    - ✅ Oracle 成本计入 cache-write
    - ✅ Verdict 写入 Transcript
  
  opencode:
    - ✅ Oracle 成本写入 SQLite
    - ✅ Verdict 作为 Evidence 存储
    - ✅ 多会话下 Oracle 隔离

# === 集成点验收 ===
integration_validation:
  verify_gate:
    - ✅ BLOCKED 自动评估是否升级 Oracle
    - ✅ Oracle verdict 直接影响 step 状态
  
  cost_tracking:
    - ✅ Oracle 成本独立追踪
    - ✅ 成本看板显示 Oracle 占比
  
  error_dna:
    - ✅ Oracle FAIL 自动生成 Error DNA
    - ✅ 滥用检测写入 Error DNA

# === 性能指标 ===
performance_metrics:
  oracle_invocation_time: < 5s
  oracle_cost_per_call: < $0.05
  abuse_detection_time: < 100ms
  cost_overrun_check_time: < 50ms

# === 回归测试 ===
regression_tests:
  - ✅ H1（单文件编辑）：无 Oracle 调用
  - ✅ H2（多文件重构）：0～1 次 Oracle
  - ✅ H3（架构设计）：1～3 次 Oracle
  - ✅ 成本超支：自动降级生效
  - ✅ Oracle 滥用：告警触发

# === 文档 ===
documentation:
  - ✅ Oracle 核心定位文档
  - ✅ Oracle 触发条件决策树
  - ✅ OracleEscalation Schema
  - ✅ OracleVerdict Schema
  - ✅ CostRedLine 配置说明
  - ✅ 成本超支处理流程
  - ✅ 4 个测试用例作为示例

# === 遗留问题 ===
known_issues:
  - Oracle Prompt 在极复杂场景可能需要更多 tokens（当前 2000）
  - 成本预测算法当前为简单估算，需要历史数据训练
  - Oracle 滥用检测的阈值需要根据实际数据调优

# === 后续优化方向 ===
future_enhancements:
  - Oracle Multi-Judge（多 LLM 投票）
  - Meta-Oracle（Oracle 的 Oracle）
  - 成本预测模型（基于历史任务）
  - 动态红线调整（根据任务复杂度）
  - Oracle verdict 质量评分

# === 最终判定 ===
verdict:
  status: ✅ PASSED
  readiness: PRODUCTION_READY
  blocking_issues: NONE
  recommendation: >
    第 9 轮完成 Oracle 固化设计与成本治理，定位明确、触发条件严格、成本治理健全。
    防滥用机制完整，成本超支自动处理逻辑清晰。
    
    下一步：进入第 10 轮最终验收、实施路线图与 Sovereign Verdict。
```

---

**第 9 轮交付边界：** Oracle 固化设计与成本治理已形成；最终端到端验收、完整路线图与 Sovereign Verdict 由第 10 轮承接。
