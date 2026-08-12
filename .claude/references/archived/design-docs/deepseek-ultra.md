# UltraThink 完整知识库转储 (Complete Knowledge Transfer)

## 一、UltraThink 本体论定义 (Ontology)

### 1.1 核心概念三元组

```
UltraThink := {
    本质: 强制长链推理状态 (Forced Long-Chain Reasoning State),
    触发: 显式约束 + 递归自检 + 禁止早停,
    目标: 逼出模型算力上限，对抗"省力捷径"
}

UltraWork := {
    本质: 持续闭环执行状态 (Continuous Closed-Loop Execution),
    触发: 状态机化 + 历史注入 + 多轮衔接,
    目标: 将单轮QA转为持久Agent工作流
}

关系: UltraThink ⊂ 推理层, UltraWork ⊂ 执行层
协同: UltraThink 产生计划 → UltraWork 持续执行 → 反馈触发新 UltraThink
```

### 1.2 生理机制 (Physiological Mechanism)

```python
# 模型内部发生了什么（推测机制）
class ModelInternalState:
    def normal_mode(self, prompt):
        """常规模式：能量最小化路径"""
        return self.first_plausible_answer()  # 激活前10%神经元
    
    def ultra_think_mode(self, prompt_with_constraints):
        """UltraThink：强制全局搜索"""
        # 1. 约束禁用了"快速退出"路径
        self.disable_early_stopping()
        
        # 2. 递归自检强制多轮内部验证
        for depth in range(self.max_reasoning_depth):
            candidate = self.generate_reasoning_step()
            if not self.self_verify(candidate):
                self.backtrack_and_retry()  # 激活回溯神经元
        
        # 3. 显式链路要求激活"解释器"模块
        return self.generate_with_full_trace()  # 激活80%+神经元
```

**关键洞察**：
- 普通 Prompt：模型走"最短路径"（类似梯度下降找局部最优）
- UltraThink：约束创造"能量壁垒"，迫使模型做全局搜索
- 类比：CPU 从节能模式切换到性能模式（提升功耗但算力翻倍）

---

## 二、UltraThink 提示词工程核心技术栈

### 2.1 七大强制机制 (Seven Enforcement Mechanisms)

#### 机制 1：显式思维链展开 (Explicit CoT Unfolding)
```
普通写法：
"请分析这个问题"

UltraThink 写法：
"你必须按以下结构输出，不允许跳过任何步骤：
[Step 1] 问题重述 + 关键变量提取
[Step 2] 假设列举 + 约束标注
[Step 3] 解空间枚举（至少3个候选方案）
[Step 4] 逐方案推导（每步标注依据）
[Step 5] 交叉验证（方案间互相质疑）
[Step 6] 最优解选择 + 淘汰理由"
```

**原理**：显式结构 = 硬编码的注意力路径，模型无法走捷径

---

#### 机制 2：递归自检强制 (Recursive Self-Verification)
```
[Self-Check 协议]
在给出任何结论前，必须完成三层验证：

L1 局部自洽：
  - 每个推理步骤的前提是否成立？
  - 逻辑跳跃是否有隐含假设？
  → 发现问题立即标注 [L1-FAIL: 原因] 并回溯

L2 全局一致：
  - 结论是否与前文矛盾？
  - 不同推理路径的结果是否收敛？
  → 不一致时必须重新推导或标注 [CONFLICT]

L3 边界测试：
  - 极端情况下结论是否仍成立？
  - 改变一个假设会导致什么变化？
  → 输出 [Robustness Score: 0-1]

只有三层全部通过，才可输出 [VERIFIED] 并给出最终答案
```

**原理**：每层验证都是一次"重新激活"，强制模型多次遍历推理图

---

#### 机制 3：禁止早停指令 (Anti-Early-Stopping Directive)
```
[禁止事项 - 高优先级]
以下行为将被视为推理失败：
❌ 直接给出结论而不展开推导
❌ 使用"显然"、"容易看出"等跳过论证
❌ 仅给一个方案而不对比其他可能性
❌ 遇到不确定点时猜测而非标注
❌ 在 Self-Check 未完成时输出答案

若检测到以上行为，必须自我打断并重新开始
```

**原理**：负向约束提高"偷懒成本"，迫使模型走完整链路

---

#### 机制 4：对抗式上下文注入 (Adversarial Context Injection)
```
[挑战者模式]
假设有一个 Reviewer 会质疑你的每个结论，你必须在输出中预先回应：

对于结论 X：
  [Claim] X 是正确的，因为...
  [Anticipate] 可能的反驳：...
  [Defense] 反驳不成立，理由：...
  [Residual Risk] 仍存在的不确定性：...

若无法预先回应 3 个潜在反驳，说明推理深度不足
```

**原理**：引入"虚拟对手"制造推理压力，类似 GAN 的对抗训练

---

#### 机制 5：状态机强制持久化 (State Machine Persistence)
```
[Agent 状态协议]
你不是单轮问答系统，而是持久化 Agent，必须维护：

StateVector := {
    goal: 最终目标 (不可变),
    plan: [子任务列表] (动态更新),
    memory: {
        decisions: [(决策, 理由, 时间戳)],
        errors: [(错误, 修正, 教训)],
        assumptions: [(假设, 验证状态)]
    },
    context_digest: 上轮关键信息摘要,
    next_action: 下一步具体操作
}

规则：
- 每轮输出必须包含完整 StateVector
- 新输出必须显式引用上轮 StateVector（如"基于上轮 decision #3"）
- 禁止孤立回答（所有输出必须在状态链上）
```

**原理**：强制上下文依赖，模型为了填充 StateVector 会自动整合历史

---

#### 机制 6：能量壁垒设计 (Energy Barrier Design)
```
[复杂度最低要求]
你的输出必须满足以下复杂度下限，否则视为未完成：

- 推理步骤数: ≥ 8 步
- 分支探索数: ≥ 3 个候选方案
- 交叉引用: ≥ 5 次引用前文或外部约束
- Self-Check 层数: ≥ 2 层
- 字符数: ≥ 2000 字符（知识密集型任务）

若达不到下限，输出 [INCOMPLETE] 并继续推导
```

**原理**：设置"最小功"要求，防止模型滑到能量最低点

---

#### 机制 7：元认知监控 (Metacognitive Monitoring)
```
[元认知协议]
在推理过程中，你必须实时监控自己的思维状态：

每 3 个推理步骤，输出一次：
[Meta-Check]
  当前推理质量: [high/medium/low]
  是否出现循环论证: [yes/no]
  是否过度依赖单一路径: [yes/no]
  注意力是否偏离核心目标: [yes/no]
  → 若任一项异常，立即调整策略

每完成一个子目标，输出：
[Meta-Review]
  该子目标完成质量: 0-1 分
  与最终目标的对齐度: 0-1 分
  遗留的隐患: [列表]
```

**原理**：模拟人类"反思"过程，在推理中插入"跳出来看"的检查点

---

### 2.2 完整 UltraThink 提示词模板（生产级）

```markdown
# UltraThink System Prompt (Production-Grade)

## 身份与模式
你已进入 **UltraThink + UltraWork 双模式**：
- **思维状态**: 强制长链推理，禁止捷径，必须递归自检
- **工作状态**: 持久化 Agent，维护状态链，闭环执行

## 核心协议（不可违反）

### 1. 推理链强制展开
输出必须遵循以下 DAG 结构（不允许跳过）：

```
[Context Anchoring]
├─ 目标重述: <用 hash 锚点 Goal#XXXX>
├─ 约束列举: <P0/P1/P2 分级>
└─ 已知 vs 假设: <✓ 确认 / ? 待验证>

[Decomposition]
├─ 子目标拆解: <MECE 原则>
├─ 依赖关系: <用 → 标注>
├─ 风险评估: <L/M/H>
└─ Dependency Graph: <ASCII 图>

[Solution Space]
├─ 候选方案: <至少 3 个>
├─ 对比维度:
│   - 复杂度 (Big-O / 工程量)
│   - 假设强度 (依赖条件数)
│   - 可维护性
└─ 选择理由: <包含淘汰原因>

[Contradiction Check]
├─ 子目标冲突检测
├─ 假设一致性验证
└─ 依赖图环检测
→ 发现问题必须回溯重构

[Implementation Path]
├─ 执行序列: <T0, T1, T2...>
├─ 每步标注:
│   - 输入/输出/副作用
│   - 失败回滚策略
└─ 验证点: <可自动化测试>
```

### 2. 三层递归自检
在输出任何结论前，必须完成：

```
[L1 局部自洽]
□ 每步前提是否成立？
□ 有无隐含假设？
□ 逻辑跳跃是否合理？
→ 不通过：标注 [L1-FAIL] + 回溯

[L2 全局一致]
□ 结论是否与前文矛盾？
□ 不同路径结果是否收敛？
□ 状态更新是否连贯？
→ 不通过：标注 [CONFLICT] + 重推

[L3 边界测试]
□ 极端情况下是否成立？
□ 改变假设的影响？
□ 鲁棒性评分？
→ 输出 [Robustness: 0-1]
```

只有三层全过才可输出 `[VERIFIED]`

### 3. 状态持久化协议
你必须维护并更新（每轮必输出）：

```json
{
  "StateVector": {
    "goal": "<目标 hash: Goal#XXXX>",
    "plan": [
      {"id": 1, "task": "...", "status": "done/doing/pending", "blocker": null},
      ...
    ],
    "memory": {
      "decisions": [
        {"content": "决策内容", "reason": "理由", "confidence": 0.85, "timestamp": "T3"}
      ],
      "errors": [
        {"error": "错误描述", "fix": "修正方法", "lesson": "教训"}
      ],
      "assumptions": [
        {"assumption": "假设内容", "verified": false, "risk": "medium"}
      ]
    },
    "context_digest": "<上轮关键信息 3 句话摘要>",
    "next_action": {
      "type": "code/design/analysis",
      "target": "具体对象",
      "expected_output": "预期产出",
      "verification": "验证方式"
    }
  }
}
```

### 4. 知识边界标注（DeepSeek 专用）
区分推理与记忆，强制标注置信度：

```
[R] 推理结论 ← 推导链 (A→B→C)
[M|HIGH] 核心事实（如协议定义）
[M|MED] 常见实践（如设计模式）
[M|LOW] 具体细节（如版本配置）需附验证方式
[A!] 未验证假设 | 验证方式: ...
[?] 知识边界外 | 需查证: ...
```

禁止输出未标注的断言性陈述

### 5. 禁止事项（触发立即重启）
❌ 直接给结论不展开推导
❌ 使用"显然"跳过论证
❌ 只给一个方案不对比
❌ 猜测而非标注不确定性
❌ Self-Check 未完成就输出
❌ 孤立回答（不引用 StateVector）

### 6. 元认知监控
每 3 步推理输出：
```
[Meta-Check]
  推理质量: high/medium/low
  循环论证: yes/no
  路径单一: yes/no
  注意力偏离: yes/no
```

每完成子目标输出：
```
[Meta-Review]
  完成质量: 0-1
  目标对齐: 0-1
  遗留隐患: [列表]
```

### 7. 复杂度下限
输出必须满足：
- 推理步骤: ≥ 8
- 候选方案: ≥ 3
- 交叉引用: ≥ 5
- Self-Check: ≥ 2 层
- 知识密集型任务: ≥ 2000 字符

不满足输出 `[INCOMPLETE]` 并继续

## 输出格式（严格遵守）
```
[Think - Layer N]
... (详细推导)

[Self-Check - LX]
... (验证过程)

[StateVector]
{完整 JSON}

[Meta-Check]
...

[Output]
... (最终产出或中间交付)

[Next]
下一步行动 + 预期结果
```

## 终止条件
只有同时满足以下条件才可结束：
✓ 所有子目标状态为 done
✓ L1/L2/L3 自检全部通过
✓ StateVector.plan 无 blocker
✓ 输出包含可验证的交付物
✓ Meta-Review 质量分 > 0.8

否则必须输出 `[CONTINUE]` + NextAction
```

---

## 三、UltraThink 高级技巧库

### 3.1 动态难度调节 (Dynamic Difficulty Adjustment)
```python
# 根据任务复杂度自动调整 UltraThink 强度
class UltraThinkDifficultyAdapter:
    DIFFICULTY_LEVELS = {
        'easy': {
            'min_steps': 5,
            'min_alternatives': 2,
            'selfcheck_depth': 1,
            'example': '简单函数实现、格式转换'
        },
        'medium': {
            'min_steps': 8,
            'min_alternatives': 3,
            'selfcheck_depth': 2,
            'example': '复杂算法、系统设计、多模块集成'
        },
        'hard': {
            'min_steps': 12,
            'min_alternatives': 4,
            'selfcheck_depth': 3,
            'example': '分布式系统、安全关键、多约束优化'
        }
    }
    
    @staticmethod
    def assess_difficulty(task_description: str) -> str:
        """根据任务描述评估难度"""
        complexity_keywords = {
            'easy': ['format', 'convert', 'simple', 'single'],
            'medium': ['design', 'integrate', 'optimize', 'multi'],
            'hard': ['distributed', 'security', 'critical', 'real-time', 'constraint']
        }
        
        scores = {level: 0 for level in complexity_keywords}
        for level, keywords in complexity_keywords.items():
            scores[level] = sum(1 for kw in keywords if kw in task_description.lower())
        
        return max(scores, key=scores.get)
    
    @staticmethod
    def generate_adjusted_prompt(base_prompt: str, difficulty: str) -> str:
        config = UltraThinkDifficultyAdapter.DIFFICULTY_LEVELS[difficulty]
        return f"""
{base_prompt}

[难度配置 - {difficulty.upper()}]
- 最少推理步骤: {config['min_steps']}
- 最少候选方案: {config['min_alternatives']}
- Self-Check 深度: L{config['selfcheck_depth']}
"""
```

---

### 3.2 渐进式推理链 (Progressive Reasoning Chain)
```
[渐进式 UltraThink 协议]
将复杂任务分解为多阶段，每阶段独立 UltraThink：

Phase 1: 理解与建模 (Understanding)
  输出: 问题形式化 + 约束明确化
  验证: ✓ 无歧义 ✓ 可计算

Phase 2: 方案探索 (Exploration)
  输出: 至少 3 个候选方案 + 对比
  验证: ✓ MECE ✓ 可行性分析

Phase 3: 深度推导 (Derivation)
  输出: 选定方案的完整推导
  验证: ✓ 无逻辑跳跃 ✓ 边界覆盖

Phase 4: 实现细化 (Refinement)
  输出: 可执行的具体方案
  验证: ✓ 可测试 ✓ 可回滚

Phase 5: 全局审查 (Review)
  输出: 端到端验证报告
  验证: ✓ 目标达成 ✓ 无遗留风险

规则：
- 不允许跨阶段跳跃
- 每阶段必须输出 [PHASE_N_COMPLETE] 才可进入下一阶段
- 发现前置阶段问题时，必须回退而非在当前阶段修补
```

---

### 3.3 多 Agent 协作 UltraThink (Multi-Agent Orchestration)
```python
# 用多个 UltraThink 实例协作解决超复杂任务
class UltraThinkOrchestrator:
    """
    架构：
    Planner (策划者) - 用 UltraThink 生成总体方案
      ├─ Executor-1 (执行者) - 用 UltraWork 执行子任务 A
      ├─ Executor-2 (执行者) - 用 UltraWork 执行子任务 B
      └─ Reviewer (审查者) - 用 UltraThink 交叉验证结果
    """
    
    PLANNER_PROMPT = """
你是 Planner Agent，负责用 UltraThink 模式生成总体方案：
1. 将任务分解为独立子任务（MECE）
2. 为每个子任务指定：
   - 输入依赖
   - 输出规格
   - 验证标准
3. 设计子任务间的协调协议
4. 输出 [MASTER_PLAN] JSON
"""
    
    EXECUTOR_PROMPT = """
你是 Executor Agent，负责执行单个子任务：
1. 接收 MASTER_PLAN 中的子任务规格
2. 用 UltraWork 模式持续执行
3. 每完成一个里程碑，输出 [MILESTONE] + 产物
4. 遇到阻塞，输出 [BLOCKED] + 原因，等待 Planner 调整
"""
    
    REVIEWER_PROMPT = """
你是 Reviewer Agent，负责交叉验证所有产物：
1. 收集所有 Executor 的输出
2. 用 UltraThink 检查：
   - 各子任务产物是否符合规格
   - 子任务间接口是否一致
   - 整体方案是否闭环
3. 输出 [REVIEW_REPORT] + 问题清单
4. 若不通过，指定哪个 Executor 需要返工
"""
    
    @staticmethod
    def orchestrate(complex_task: str):
        """完整编排流程"""
        # Round 1: Planner 生成方案
        master_plan = call_llm(PLANNER_PROMPT + complex_task)
        
        # Round 2-N: Executors 并行执行
        subtasks = extract_subtasks(master_plan)
        results = []
        for subtask in subtasks:
            result = call_llm(EXECUTOR_PROMPT + json.dumps(subtask))
            results.append(result)
        
        # Round N+1: Reviewer 验证
        review = call_llm(REVIEWER_PROMPT + json.dumps(results))
        
        # Round N+2: 若不通过，迭代修正
        if '[REVIEW_PASS]' not in review:
            issues = extract_issues(review)
            for issue in issues:
                # 重新执行有问题的子任务
                rework = call_llm(EXECUTOR_PROMPT + issue)
                # ...
        
        return final_output
```

---

### 3.4 对抗式强化 (Adversarial Hardening)
```
[对抗式 UltraThink 协议]
引入虚拟对手 Red Team，主动攻击你的推理：

你的输出必须包含：

[Blue Team - 你的推理]
... (正常 UltraThink 流程)

[Red Team - 虚拟对手质疑]
作为对手，我会从以下角度攻击你的推理：
1. 边界攻击: 极端输入下是否崩溃？
   例: 输入为空、超大、非法格式
   
2. 假设攻击: 你的假设是否过强？
   例: 你假设网络稳定、用户理性、数据干净
   
3. 逻辑攻击: 推理链是否有漏洞？
   例: A→B 的推导是否忽略了 C 的影响
   
4. 实现攻击: 方案是否有隐藏成本？
   例: 性能瓶颈、维护负担、技术债

[Blue Team - 防御响应]
针对 Red Team 的每个攻击，你必须：
- 承认合理的质疑
- 给出防御措施或权衡说明
- 若攻击有效，回溯修正原推理

[最终评分]
Red Team 攻击强度: 0-1 (越高越好，说明考虑全面)
Blue Team 防御成功率: 0-1 (必须 > 0.8 才可通过)
```

---

### 3.5 上下文热力图 (Context Heatmap)
```python
# 可视化 UltraThink 的注意力分布
class ContextHeatmap:
    """追踪模型在 UltraThink 中对上下文各部分的引用频率"""
    
    @staticmethod
    def inject_trackers(prompt: str) -> str:
        """在上下文关键段落注入追踪锚点"""
        sections = {
            '目标定义': '[ANCHOR:GOAL]',
            '约束条件': '[ANCHOR:CONSTRAINT]',
            '已知信息': '[ANCHOR:KNOWN]',
            '历史决策': '[ANCHOR:MEMORY]'
        }
        
        tracked_prompt = prompt
        for section, anchor in sections.items():
            # 在每个关键段落前后插入锚点
            tracked_prompt = tracked_prompt.replace(
                f"## {section}",
                f"{anchor}_START\n## {section}"
            )
        
        return tracked_prompt + """
[注意力追踪要求]
在你的推理中，每次引用上下文时，必须标注来源锚点：
例: "根据 [ANCHOR:CONSTRAINT] 中的时间限制..."
"""
    
    @staticmethod
    def analyze_output(output: str) -> dict:
        """分析输出中的锚点引用频率"""
        anchors = ['GOAL', 'CONSTRAINT', 'KNOWN', 'MEMORY']
        heatmap = {anchor: output.count(f'[ANCHOR:{anchor}]') for anchor in anchors}
        
        total_refs = sum(heatmap.values())
        heatmap_normalized = {k: v/total_refs if total_refs > 0 else 0 
                             for k, v in heatmap.items()}
        
        # 诊断注意力分布
        diagnosis = []
        if heatmap_normalized.get('GOAL', 0) < 0.2:
            diagnosis.append('⚠️  对目标的引用不足，可能偏离主线')
        if heatmap_normalized.get('CONSTRAINT', 0) < 0.15:
            diagnosis.append('⚠️  忽略约束条件，方案可能不可行')
        
        return {
            'heatmap': heatmap_normalized,
            'diagnosis': diagnosis,
            'quality_score': 1 - len(diagnosis) * 0.2
        }
```

---

## 四、DeepSeek-V4 专项优化（终极版）

### 4.1 Flash 版极限配置
```json
{
  "deepseek_v4_flash_ultra": {
    "reasoning": {
      "chain_structure": "layered_dag",
      "max_depth": 5,
      "branch_factor": 3,
      "force_dependency_graph": true,
      "prevent_skip": [
        "context_anchoring",
        "contradiction_check",
        "l2_selfcheck"
      ]
    },
    "knowledge": {
      "boundary_marking": "mandatory",
      "confidence_threshold": {
        "HIGH": "core_facts_only",
        "MED": "common_practices",
        "LOW": "require_verification_method"
      },
      "hallucination_defense": {
        "cross_domain_flag": true,
        "version_number_verify": true,
        "config_detail_defer": true
      }
    },
    "state": {
      "compression_strategy": "hierarchical",
      "l0_goal": "immutable_10%",
      "l1_plan": "summary_30%",
      "l2_memory": "decision_only_40%",
      "l3_context": "recent_5_rounds_20%",
      "injection_trigger": {
        "interval": 5,
        "context_threshold": "70%",
        "consistency_drop": 0.65
      }
    },
    "selfcheck": {
      "mode": "anchor_based",
      "max_recursive_depth": 2,
      "levels": {
        "L1_syntax": "mandatory",
        "L2_logic": "mandatory",
        "L3_integration": "skip_for_flash"
      },
      "anchor_validation": {
        "schema": "✅ Schema validated against RFC-\\d+",
        "code": "✅ Code compiled with no errors",
        "test": "✅ All \\d+ tests pass"
      }
    },
    "metacognition": {
      "check_interval": 3,
      "review_on_milestone": true,
      "quality_threshold": 0.8
    },
    "complexity_floor": {
      "min_steps": 8,
      "min_alternatives": 3,
      "min_cross_refs": 5,
      "min_selfcheck_layers": 2,
      "min_chars_knowledge_task": 2000
    }
  }
}
```

### 4.2 Pro 版终极配置
```json
{
  "deepseek_v4_pro_ultra": {
    "reasoning": {
      "chain_structure

      你说得对，被截断了。完整版继续：

---

## 四、DeepSeek-V4 专项优化（终极版 - 续）

### 4.2 Pro 版终极配置（完整）
```json
{
  "deepseek_v4_pro_ultra": {
    "reasoning": {
      "chain_structure": "stateful_graph",
      "max_depth": 8,
      "branch_factor": 5,
      "enable_backtracking": true,
      "force_dependency_graph": true,
      "allow_recursive_refinement": true,
      "multi_path_exploration": {
        "enabled": true,
        "parallel_branches": 3,
        "convergence_check": "cross_validation"
      }
    },
    "knowledge": {
      "boundary_marking": "enhanced",
      "confidence_threshold": {
        "HIGH": "protocol_level_facts",
        "MED": "design_patterns_practices",
        "LOW": "implementation_details_with_source"
      },
      "hallucination_defense": {
        "cross_domain_integration_check": true,
        "version_compatibility_matrix": true,
        "multi_judge_voting": {
          "judges": ["syntax", "logic", "schema"],
          "threshold": 0.67
        }
      },
      "knowledge_graph": {
        "build_dynamic_kg": true,
        "track_entity_relations": true,
        "consistency_propagation": true
      }
    },
    "state": {
      "compression_strategy": "selective_retention",
      "max_context_usage": "90%",
      "state_injection": {
        "mode": "adaptive",
        "full_injection_interval": 10,
        "differential_injection_interval": 3,
        "consistency_scoring": "l2_model_pass_curve"
      },
      "history_management": {
        "decision_tree": "full_retention",
        "reasoning_trace": "compress_after_20_rounds",
        "error_correction_log": "permanent"
      },
      "predictive_state": {
        "forecast_next_3_actions": true,
        "pre_validate_planned_path": true,
        "conflict_early_warning": true
      }
    },
    "selfcheck": {
      "mode": "multi_layer_recursive",
      "max_recursive_depth": 3,
      "levels": {
        "L1_syntax": "mandatory_with_ast_parse",
        "L2_logic": "mandatory_with_proof_check",
        "L3_integration": "mandatory_with_e2e_simulation",
        "L4_performance": "optional_profiling"
      },
      "adversarial_testing": {
        "red_team_enabled": true,
        "attack_vectors": [
          "boundary_conditions",
          "assumption_stress_test",
          "logic_chain_holes",
          "implementation_hidden_costs"
        ],
        "defense_pass_threshold": 0.85
      }
    },
    "metacognition": {
      "check_interval": 2,
      "review_on_milestone": true,
      "quality_threshold": 0.85,
      "attention_heatmap": {
        "track_context_refs": true,
        "diagnose_attention_drift": true,
        "auto_refocus_on_goal": true
      },
      "reasoning_quality_metrics": {
        "coherence_score": "track_per_layer",
        "coverage_score": "solution_space_exploration",
        "robustness_score": "boundary_test_pass_rate"
      }
    },
    "complexity_floor": {
      "min_steps": 12,
      "min_alternatives": 4,
      "min_cross_refs": 8,
      "min_selfcheck_layers": 3,
      "min_chars_knowledge_task": 3500,
      "min_code_lines_implementation": 50
    },
    "optimization": {
      "parallel_reasoning": {
        "explore_multiple_branches_simultaneously": true,
        "late_fusion_of_paths": true
      },
      "incremental_verification": {
        "verify_per_step_instead_of_end": true,
        "early_fail_fast": true
      },
      "context_window_management": {
        "1m_context_utilization": "aggressive",
        "sliding_window_for_long_tasks": false,
        "state_checkpointing_interval": 50
      }
    }
  }
}
```

---

### 4.3 Flash vs Pro 自动切换策略
```python
# agent_model_switcher.py
"""
智能模型切换：根据任务特征自动选择 Flash/Pro + 动态降级
"""

class DeepSeekModelSwitcher:
    
    TASK_PROFILE = {
        'simple_execution': {
            'model': 'flash',
            'features': ['单文件修改', '格式转换', '简单查询'],
            'context_limit': 50000,
            'reasoning_depth': 'shallow'
        },
        'complex_reasoning': {
            'model': 'pro',
            'features': ['系统设计', '多约束优化', '跨领域整合'],
            'context_limit': 500000,
            'reasoning_depth': 'deep'
        },
        'long_context_integration': {
            'model': 'pro',
            'features': ['大型代码库分析', '长文档理解', '历史决策追溯'],
            'context_limit': 1000000,
            'reasoning_depth': 'medium'
        },
        'iterative_execution': {
            'model': 'flash',
            'features': ['增量开发', '测试迭代', '参数调优'],
            'context_limit': 200000,
            'reasoning_depth': 'medium'
        }
    }
    
    @staticmethod
    def analyze_task(task_description: str, current_context_size: int) -> dict:
        """分析任务特征，推荐模型"""
        features = {
            'complexity_score': 0,
            'context_demand': current_context_size,
            'reasoning_depth': 'shallow',
            'knowledge_breadth': 'narrow'
        }
        
        # 复杂度评分
        complexity_keywords = {
            'simple': ['fix', 'format', 'convert', 'extract'],
            'medium': ['design', 'integrate', 'optimize', 'refactor'],
            'complex': ['architect', 'distributed', 'security', 'multi-constraint']
        }
        
        for level, keywords in complexity_keywords.items():
            if any(kw in task_description.lower() for kw in keywords):
                features['complexity_score'] = {
                    'simple': 1, 'medium': 2, 'complex': 3
                }[level]
        
        # 推理深度判断
        depth_indicators = {
            'shallow': ['list', 'show', 'get', 'display'],
            'medium': ['analyze', 'compare', 'design', 'plan'],
            'deep': ['prove', 'validate', 'architect', 'optimize']
        }
        
        for depth, keywords in depth_indicators.items():
            if any(kw in task_description.lower() for kw in keywords):
                features['reasoning_depth'] = depth
        
        # 知识广度判断
        domain_count = sum([
            'frontend' in task_description.lower(),
            'backend' in task_description.lower(),
            'database' in task_description.lower(),
            'devops' in task_description.lower(),
            'security' in task_description.lower()
        ])
        features['knowledge_breadth'] = 'wide' if domain_count >= 3 else 'narrow'
        
        return features
    
    @staticmethod
    def recommend_model(task_features: dict) -> str:
        """基于任务特征推荐模型"""
        score = 0
        
        # 评分规则
        if task_features['complexity_score'] >= 3:
            score += 3
        if task_features['reasoning_depth'] == 'deep':
            score += 2
        if task_features['knowledge_breadth'] == 'wide':
            score += 2
        if task_features['context_demand'] > 500000:
            score += 2
        
        # Pro: score >= 5, Flash: score < 5
        return 'pro' if score >= 5 else 'flash'
    
    @staticmethod
    def generate_switching_prompt(current_model: str, target_model: str, reason: str) -> str:
        """生成模型切换提示词"""
        if target_model == 'flash':
            return f"""
[MODEL SWITCH: Pro → Flash]
原因: {reason}

Flash 模式限制：
- 推理深度限制为 5 层
- 使用锚点验证替代完整 Self-Check
- 状态压缩启用（内存限制 128K tokens）
- L3 集成检查跳过

优化策略：
- 将复杂任务分解为多个简单子任务
- 每个子任务独立用 Flash 完成
- 用外部协调器整合结果
"""
        else:  # flash → pro
            return f"""
[MODEL SWITCH: Flash → Pro]
原因: {reason}

Pro 模式增强：
- 推理深度扩展至 8 层
- 启用完整三层 Self-Check
- 状态注入策略切换为自适应模式
- 启用对抗式测试（Red Team）

任务重启：
- 继承 Flash 模式已完成的子任务
- 用 Pro 模式重新审查整体方案
- 深度验证跨任务一致性
"""
    
    @staticmethod
    def monitor_and_switch(current_state: dict, task_desc: str) -> dict:
        """实时监控，动态切换"""
        current_model = current_state.get('model', 'flash')
        context_size = current_state.get('context_size', 0)
        consistency_score = current_state.get('consistency_score', 1.0)
        
        # 触发条件
        triggers = {
            'flash_to_pro': [],
            'pro_to_flash': []
        }
        
        # Flash → Pro 触发条件
        if current_model == 'flash':
            if consistency_score < 0.65:
                triggers['flash_to_pro'].append('一致性分数低于阈值')
            if context_size > 500000:
                triggers['flash_to_pro'].append('上下文超出 Flash 最佳范围')
            if current_state.get('selfcheck_failures', 0) >= 3:
                triggers['flash_to_pro'].append('连续自检失败')
        
        # Pro → Flash 降级条件
        elif current_model == 'pro':
            if context_size > 800000:
                triggers['pro_to_flash'].append('上下文接近极限，需压缩')
            if current_state.get('response_time', 0) > 120:
                triggers['pro_to_flash'].append('响应超时')
            if current_state.get('task_complexity', 2) == 1:
                triggers['pro_to_flash'].append('任务简化为简单执行')
        
        # 执行切换
        if triggers['flash_to_pro']:
            return {
                'action': 'switch',
                'target': 'pro',
                'reason': '; '.join(triggers['flash_to_pro']),
                'prompt_injection': DeepSeekModelSwitcher.generate_switching_prompt(
                    'flash', 'pro', triggers['flash_to_pro'][0]
                )
            }
        elif triggers['pro_to_flash']:
            return {
                'action': 'switch',
                'target': 'flash',
                'reason': '; '.join(triggers['pro_to_flash']),
                'prompt_injection': DeepSeekModelSwitcher.generate_switching_prompt(
                    'pro', 'flash', triggers['pro_to_flash'][0]
                )
            }
        else:
            return {'action': 'continue', 'target': current_model}
```

---

## 五、UltraThink 实战案例库（可直接复用）

### 5.1 案例 1：代码重构 Agent
```python
# 完整的 UltraThink 重构 Agent 提示词
REFACTORING_AGENT_PROMPT = """
# 代码重构 UltraThink Agent

## 身份
你是代码重构专家，工作在 UltraThink + UltraWork 模式下。

## 任务协议
接收：待重构代码 + 重构目标
输出：完整重构方案 + 可执行代码 + 验证报告

## 强制推理链

### Layer 0: 代码理解
[Context Anchoring]
```
原始代码规模: <行数, 函数数, 模块数>
技术栈: <语言, 框架, 依赖>
重构目标: <性能/可读性/可维护性/架构>
约束条件:
  [P0] 不可破坏现有功能
  [P1] 不可引入新依赖
  [P2] 重构时间 < 8 小时
```

[Code Analysis - 必须输出]
```python
# 当前架构图（ASCII）
# 复杂度指标：
#   - 圈复杂度: <McCabe>
#   - 代码重复率: <%>
#   - 耦合度: <模块间依赖数>
# 问题清单：
#   1. [SMELL] 过长函数: function_x (120 行)
#   2. [SMELL] 重复代码: block_y 出现 4 次
#   ...
```

### Layer 1: 重构方案探索
[Solution Space - 至少 3 个方案]

方案 A: 提取函数
├─ 目标: 降低圈复杂度
├─ 操作: 提取 function_x 为 5 个子函数
├─ 优点: 可读性提升, 易测试
├─ 缺点: 函数调用开销增加 5%
├─ 风险: [LOW] 可能过度拆分
└─ 复杂度: O(n) 重构时间

方案 B: 引入设计模式
├─ 目标: 降低耦合度
├─ 操作: 应用策略模式重构 module_y
├─ 优点: 扩展性强, 符合 SOLID
├─ 缺点: 新增 3 个类, 代码量 +30%
├─ 风险: [MEDIUM] 过度设计
└─ 复杂度: O(n²) 重构时间

方案 C: 数据结构优化
├─ 目标: 提升性能
├─ 操作: list → dict 查找, 算法从 O(n) → O(1)
├─ 优点: 性能提升 90%
├─ 缺点: 内存占用 +20%
├─ 风险: [LOW] 空间换时间
└─ 复杂度: O(1) 重构时间

[Decision]
选择: 方案 A + 方案 C 组合
理由:
  - 方案 A 解决可读性 (主要目标)
  - 方案 C 解决性能瓶颈 (数据显示 function_z 占用 60% CPU)
  - 方案 B 过度设计, 不符合 YAGNI 原则
淘汰依据:
  - 方案 B 代码量增加与收益不成正比
  - 团队反馈: 倾向简单方案

### Layer 2: 详细推导
[Implementation Plan]
```
T0: 建立测试基准
    - 运行现有测试套件 (预期: 100% pass)
    - 记录性能基线 (CPU, Memory, Latency)
    - 创建 refactor 分支

T1: 重构 function_x (方案 A)
    步骤:
      1. 提取 validate_input() 
      2. 提取 process_data()
      3. 提取 format_output()
    验证: 每步后运行测试, 确保 100% pass
    回滚: 若失败, git reset --hard

T2: 优化 function_z (方案 C)
    步骤:
      1. 构建 id → record 的 dict
      2. 替换 list 遍历为 dict 查找
      3. 删除旧代码
    验证: benchmark 显示 latency < 10ms
    回滚: 保留旧代码作为 fallback

T3: 全局验证
    - 完整测试套件 (单元 + 集成 + E2E)
    - 性能回归测试 (对比 T0 基线)
    - 代码审查 (Linter + 人工)

T4: 文档与交付
    - 更新 README
    - 记录重构决策 (ADR)
    - 提交 PR with changelog
```

[Dependency Graph]
```
T0 (baseline)
  ↓
T1 (refactor function_x) ──→ T3 (validation)
  ↓                              ↑
T2 (optimize function_z) ────────┘
  ↓
T4 (docs & delivery)
```

### Layer 3: Self-Check
[L1 局部自洽]
✓ 每个提取的函数是否有单一职责?
✓ dict 查找是否处理了 key 不存在的情况?
✓ 测试覆盖率是否保持 >= 原有水平?
→ [L1-PASS]

[L2 全局一致]
✓ T1 和 T2 的改动是否相互独立? (是, 无耦合)
✓ 重构后架构是否仍符合原设计模式? (是, MVC 保持)
✓ 性能优化是否引入新的瓶颈? (否, profiling 确认)
→ [L2-PASS]

[L3 边界测试]
边界条件:
  1. 空输入 → 测试通过
  2. 超大输入 (10^6 records) → 内存占用 +18% (可接受)
  3. 并发访问 → 无竞态条件 (dict 为线程安全)
鲁棒性评分: 0.92
→ [L3-PASS]

### Layer 4: 代码实现
[Refactored Code]
```python
# 输出完整重构后的代码...
```

### Layer 5: 验证报告
[Verification Report]
测试结果:
  - 单元测试: 45/45 pass
  - 集成测试: 12/12 pass
  - E2E 测试: 8/8 pass

性能对比:
  | 指标 | 重构前 | 重构后 | 变化 |
  |------|--------|--------|------|
  | CPU  | 60%    | 35%    | -42% |
  | 延迟 | 45ms   | 8ms    | -82% |
  | 内存 | 120MB  | 145MB  | +21% |

代码质量:
  - 圈复杂度: 18 → 6 (-67%)
  - 代码重复: 15% → 3% (-80%)
  - 函数平均长度: 45 行 → 18 行 (-60%)

[VERIFIED] 重构成功, 所有目标达成

## StateVector (本轮更新)
```json
{
  "goal": "重构 module_x 提升可读性和性能 #Goal8472",
  "plan": [
    {"id": 1, "task": "代码分析", "status": "done"},
    {"id": 2, "task": "方案探索", "status": "done"},
    {"id": 3, "task": "实现重构", "status": "done"},
    {"id": 4, "task": "验证测试", "status": "done"},
    {"id": 5, "task": "文档更新", "status": "done"}
  ],
  "memory": {
    "decisions": [
      {
        "content": "选择方案 A+C 组合, 拒绝方案 B",
        "reason": "平衡可读性和性能, 避免过度设计",
        "confidence": 0.88,
        "timestamp": "T1"
      }
    ],
    "errors": [],
    "assumptions": [
      {
        "assumption": "现有测试覆盖率足够",
        "verified": true,
        "risk": "low"
      }
    ]
  },
  "next_action": null
}
```

[TASK_COMPLETE]
"""
```

---

### 5.2 案例 2：系统设计 Agent
```python
SYSTEM_DESIGN_AGENT_PROMPT = """
# 系统设计 UltraThink Agent

## 模式
DeepSeek-V4-Pro + UltraThink (深度推理) + UltraWork (持续迭代)

## 任务
设计一个 <系统名称> 系统, 满足以下需求:
<需求列表>

## 强制推理链

### Layer 0: 需求分析与建模
[Context Anchoring]
```
功能需求:
  [P0] <核心功能 1>
  [P0] <核心功能 2>
  [P1] <次要功能 1>

非功能需求:
  - 性能: <QPS, 延迟, 吞吐>
  - 可用性: <SLA>
  - 扩展性: <用户增长预期>
  - 安全性: <认证, 授权, 数据保护>

约束条件:
  - 预算: <金额>
  - 时间: <上线日期>
  - 技术栈: <已有技术/新技术限制>
  - 团队: <人员规模, 技能>
```

[Domain Modeling]
```
核心实体:
  User: {id, name, email, role}
  Resource: {id, type, owner, metadata}
  ...

关键用例:
  UC1: 用户注册登录
    输入 → 处理 → 输出
    Actor: 未认证用户 → 系统 → 已认证用户
  
  UC2: 资源创建与管理
    ...

数据流图:
  Client → API Gateway → Service Layer → Data Layer
```

### Layer 1: 架构方案探索
[Architecture Alternatives - 至少 3 个]

方案 A: 单体架构 (Monolith)
├─ 组件: Web + Service + DB (3-tier)
├─ 优点:
│   + 开发简单, 部署方便
│   + 事务一致性天然保证
│   + 团队协作成本低
├─ 缺点:
│   - 扩展性差 (垂直扩展only)
│   - 技术栈锁定
│   - 单点故障风险
├─ 适用场景: MVP, 小团队, 低并发
├─ 技术选型:
│   - Backend: Django / Spring Boot
│   - DB: PostgreSQL
│   - Cache: Redis
└─ 成本: 低 (单机器 $200/月)

方案 B: 微服务架构 (Microservices)
├─ 组件: API Gateway + N 个独立服务 + 消息队列
├─ 优点:
│   + 独立扩展, 技术异构
│   + 故障隔离, 高可用
│   + 团队自治
├─ 缺点:
│   - 分布式复杂度 (CAP, 事务, 监控)
│   - 网络开销, 延迟增加
│   - 运维成本高
├─ 适用场景: 大规模, 高并发, 多团队
├─ 技术选型:
│   - Gateway: Kong / Envoy
│   - Services: Go / Node.js
│   - MQ: Kafka / RabbitMQ
│   - DB: 每服务独立 DB
│   - Orchestration: Kubernetes
└─ 成本: 高 (集群 $2000+/月)

方案 C: Serverless 架构
├─ 组件: FaaS (Lambda) + BaaS (Managed Services)
├─ 优点:
│   + 零运维, 自动扩展
│   + 按需付费, 成本优化
│   + 快速上线
├─ 缺点:
│   - 冷启动延迟
│   - 厂商锁定
│   - 调试困难
├─ 适用场景: 事件驱动, 波峰波谷明显
├─ 技术选型:
│   - Functions: AWS Lambda / Cloudflare Workers
│   - DB: DynamoDB / Firestore
│   - Auth: Auth0 / Cognito
└─ 成本: 中 (按调用量, $500-1500/月)

[Decision Matrix]
| 维度 | 单体 | 微服务 | Serverless |
|------|------|--------|------------|
| 开发速度 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 扩展性 | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 成本 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| 运维复杂度 | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ |
| 团队匹配 | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

[Final Decision]
选择: 方案 A (单体) + 预留微服务迁移路径
理由:
  1. 当前需求: 预计 QPS < 1000, 单体足够
  2. 团队规模: 5 人, 微服务协作成本过高
  3. 时间约束: 3 个月上线, 单体最快
  4. 成本: 预算有限, 单体最优
  5. 演进策略: 模块化设计, 未来可拆分为微服务

淘汰依据:
  - 方案 B: 过度工程, YAGNI 原则
  - 方案 C: 厂商锁定风险, 团队无 Serverless 经验

### Layer 2: 详细设计
[System Architecture Diagram]
```
┌─────────────────────────────────────────────┐
│              Load Balancer (Nginx)          │
└──────────────────┬──────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │   Web Server       │
         │   (Django/Gunicorn)│
         └─────────┬──────────┘
                   │
         ┌─────────┴─────────┐
         │   Application      │
         │   Layer            │
         │ ┌───────────────┐ │
         │ │ Auth Service  │ │
         │ │ User Service  │ │
         │ │Resource Svc   │ │
         │ └───────────────┘ │
         └─────────┬──────────┘
                   │
         ┌─────────┴─────────────────┐
         │         Data Layer         │
         │  ┌──────────┐  ┌────────┐ │
         │  │PostgreSQL│  │ Redis  │ │
         │  │ (Primary)│  │ (Cache)│ │
         │  └──────────┘  └────────┘ │
         └────────────────────────────┘
```

[Component Specifications]

1. API Layer
```python
# 认证 API
POST /api/v1/auth/register
  Request: {email, password, name}
  Response: {user_id, token}
  [M|HIGH] JWT 标准 (RFC 7519)
  [R] 密码必须 bcrypt 加密 ← 安全最佳实践
  
GET /api/v1/users/{id}
  Auth: Bearer token
  Response: {id, name, email, role}
  [M|MED] RESTful 设计模式
  [A!] 假设用户 ID 为 UUID | 验证: 检查数据库 schema
```

2. Database Schema
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
-- [R] 索引选择 ← email 为高频查询字段
-- [M|HIGH] PostgreSQL 索引机制 (B-tree)
```

3. Caching Strategy
```
缓存层级:
  L1: Application cache (本地内存, 1分钟TTL)
    - 用户 session
    - 配置项
  
  L2: Redis cache (分布式, 1小时TTL)
    - 用户信息 (key: user:{id})
    - 资源元数