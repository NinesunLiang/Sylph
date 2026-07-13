# CarrorOS Opus-4.8 完整方案（3/10）

## 第 3 轮：渐进式披露与 Hot Tail 生成

抱歉刚才误判，现在继续输出系统优化方案。

---

### 一、渐进式披露（D0～D5）完整定义

基于你的需求 1（Context Boom 治理），我定义 CarrorOS 的文档分级披露协议：

```yaml
# 文档披露等级定义
schema_version: carros.disclosure_level.v1

levels:
  D0_always_loaded:
    description: 核心治理铁律，永久在 Context HEAD
    max_tokens: 2000
    included:
      - kernel/philosophy.md
      - kernel/safety.md
      - kernel/verify_gate.md
      - .omc/task/<task-id>/manifest.md (goal 部分)
    
  D1_hot_state:
    description: 当前任务实时状态，每轮刷新
    max_tokens: 800
    included:
      - current_step
      - next_action
      - blocker
      - last_evidence
      - todo_list
      - user_delta
    
  D2_working_set:
    description: 当前 step 必需文档，按需加载
    max_tokens: 12000
    included:
      - .omc/task/<task-id>/plan.md (当前 step)
      - working-set.yaml 白名单的文档
      - 当前 step 相关的 symbol 和邻近代码
    
  D3_evidence_preview:
    description: 已验证证据的预览，不含全文
    max_tokens: 3000
    included:
      - evidence.jsonl (最近 5 条预览)
      - artifacts/** (preview only)
      - decisions (binding 决策)
    
  D4_review_isolated:
    description: 审查文档，默认隔离，需要时显式加载
    max_tokens: 8000
    included:
      - review/**
      - oracle-reports/**
      - analysis/**
    
  D5_archive:
    description: 历史归档，仅通过工具检索，不进 Context
    max_tokens: 0
    included:
      - .omc/task/<task-id>/archive/**
      - operation-log (历史)
      - 旧 transcript
```

---

### 二、每轮 Context 重建算法

```python
def build_context_capsule(task_id: str, turn: int) -> ContextCapsule:
    """
    每轮确定性生成最小 Context Capsule
    不依赖历史 Context，完全从磁盘重建
    """
    
    # === D0: 永久加载 ===
    head = load_kernel_head()  # ~2K tokens
    manifest_goal = load_manifest(task_id).goal  # ~200 tokens
    
    # === D1: Hot Tail（每轮生成）===
    state = load_token(task_id)
    plan = load_plan(task_id)
    hot_tail = generate_hot_tail(state, plan)  # ~800 tokens
    
    # === D2: Working Set（按白名单）===
    working_set = load_working_set(task_id)
    middle_docs = []
    
    for doc_ref in working_set.docs:
        if doc_ref.level <= D2:
            content = load_document_slice(
                doc_ref.id,
                sections=doc_ref.sections,
                max_tokens=doc_ref.budget
            )
            middle_docs.append(content)
    
    # === D3: Evidence Preview ===
    evidence_preview = load_evidence_preview(
        task_id,
        last_n=5,
        preview_only=True
    )
    
    # 组装 Capsule
    capsule = ContextCapsule(
        version=turn,
        head=head,
        goal=manifest_goal,
        middle=middle_docs,
        evidence=evidence_preview,
        tail=hot_tail,
        total_tokens=estimate_tokens(head, middle_docs, evidence_preview, hot_tail)
    )
    
    # 检查是否超预算
    if capsule.total_tokens > SOFT_LIMIT:
        capsule = compress_middle(capsule)  # 只压缩 middle
    
    return capsule
```

**关键设计**：
1. **每轮完全重建**，不依赖上一轮 Context
2. **HEAD 和 TAIL 稳定**，只有 MIDDLE 按需变化
3. **超预算时只压缩 MIDDLE**，不动 HEAD/TAIL
4. **所有输入来自磁盘**，不信任模型记忆

---

### 三、Hot Tail 生成（替代"每 5 轮注入"）

```python
def generate_hot_tail(state: dict, plan: dict) -> str:
    """
    每轮生成短 Hot Tail（~800 tokens）
    替代固定每 5 轮注入大段状态
    """
    
    current_step = plan.steps[state.current_step]
    
    # 提取最新信息
    last_evidence = get_last_n_evidence(state.task_id, n=2)
    last_user_prompt = load_last_user_prompt(state.task_id)
    
    # 生成确定性文本
    tail = f"""
# 🎯 Current Task State

**Goal**: {state.manifest.goal}

**Current Step**: {state.current_step} — {current_step.description}
**Status**: {state.current_step_status}
**Risk Level**: {state.risk.level}

## ✅ Last Verified
- Step: {state.verification.last_verified_step}
- At: {state.verification.last_verified_at}

## 📋 TODO (Current Step)
{format_todo_list(current_step.todos)}

## 🚫 Blocker
{state.blocker or "None"}

## 🔍 Last Evidence
{format_evidence_preview(last_evidence)}

## 💬 User Latest Input
{last_user_prompt or "No recent input"}

## 🎬 Next Action
{infer_next_action(state, current_step)}

## ⚠️ Constraints
{format_binding_decisions(state.decisions)}
"""
    
    # 检查长度
    tokens = estimate_tokens(tail)
    if tokens > 800:
        tail = compress_tail(tail, target=800)
    
    return tail
```

**为什么这样设计**：

| 固定每 5 轮注入 | 每轮 Hot Tail |
|---|---|
| 前 4 轮状态可能过期 | 每轮都是最新 |
| 重复注入相同大段文本 | 只生成变化部分 |
| 容易达到 Context 上限 | 控制在 800 tokens 内 |
| 模型可能记住旧状态 | 强制读取当前状态 |

---

### 四、working-set.yaml 协议

```yaml
schema_version: carros.working_set.v1
task_id: fix-auth-001
version: 3
updated_at: "2026-07-12T10:30:00Z"

# 当前 step 披露白名单
current_step: S2
disclosure:
  - doc_id: plan.md
    sections: [S2]
    level: D2
    budget_tokens: 500
    reason: 当前执行步骤
    
  - doc_id: src/auth/refresh.ts
    sections: [refreshToken, handleConcurrency]
    level: D2
    budget_tokens: 800
    reason: 修改目标
    
  - doc_id: tests/auth/concurrent.test.ts
    sections: [testConcurrentRefresh]
    level: D2
    budget_tokens: 400
    reason: 验证用例
    
  - doc_id: docs/error_dna/EDNA-017.md
    sections: [root_cause, solution]
    level: D2
    budget_tokens: 300
    reason: 相关经验

# 明确排除（避免误加载）
excluded:
  - path: review/**
    reason: 审查文档默认隔离
  - path: .omc/task/*/archive/**
    reason: 历史归档不进 Context
  - path: .env
    reason: 敏感信息
```

**关键约束**：
- 白名单制，未列入的不加载
- 每个文档有 token 预算
- 可以只加载 section，不加载全文
- 明确排除规则，防止误触发

---

### 五、U 型注意力最终结构

```text
┌─────────────────────────────────────────────────┐
│ HEAD（D0）— 2K tokens                           │
│ • 哲学铁律（200）                                │
│ • 安全规则（300）                                │
│ • VerifyGate 协议（500）                        │
│ • L1/L2 分级规则（200）                          │
│ • Goal（从 manifest 提取）（200）                │
│                                                 │
│ 特点：短、稳定、高遵循度                         │
└─────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│ MIDDLE（D2 + D3）— 12K～15K tokens              │
│ • 当前 step 计划（500）                          │
│ • working-set 文档切片（8K～12K）                │
│ • Evidence 预览（2K）                            │
│ • Binding decisions（500）                      │
│                                                 │
│ 特点：按需加载、可压缩、版本化                    │
└─────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│ TAIL（D1）— 800 tokens                          │
│ • Current Step & Status（100）                  │
│ • Last Verified（50）                           │
│ • TODO（200）                                   │
│ • Blocker（50）                                 │
│ • Last Evidence（150）                          │
│ • User Latest Input（100）                      │
│ • Next Action（100）                            │
│ • Constraints（50）                             │
│                                                 │
│ 特点：每轮生成、实时性强、短小精悍                │
└─────────────────────────────────────────────────┘
```

**总 Token 预算**：
- 最小：~15K（HEAD 2K + MIDDLE 12K + TAIL 0.8K）
- 典型：~18K（HEAD 2K + MIDDLE 15K + TAIL 0.8K）
- 上限：~25K（压缩前警告线）

**为什么不超过 25K**：
- DeepSeek V4 Flash 在 30K+ 时开始抖动
- 保留预算给模型输出和工具结果
- 避免触发平台 compact 机制

---

### 六、Compact 后 Resume 协议

```python
def resume_after_compact(task_id: str) -> ResumeResult:
    """
    Compact 后恢复，不信任 transcript 摘要
    """
    
    # 1. 加载机器状态（真相源）
    state = load_token(task_id)
    plan = load_plan(task_id)
    
    # 2. 检查状态一致性
    if not check_state_consistency(state, plan):
        return ResumeResult(
            success=False,
            reason="state/plan version mismatch",
            action="manual_review"
        )
    
    # 3. 检查外部副作用
    unsafe_effects = [
        e for e in state.external_effects
        if e.status in ["IN_FLIGHT", "UNKNOWN"]
    ]
    if unsafe_effects:
        return ResumeResult(
            success=False,
            reason=f"unsafe external effects: {unsafe_effects}",
            action="human_confirmation"
        )
    
    # 4. 读取 handoff（仅作为导航）
    handoff = load_handoff(task_id)
    suggested_reads = extract_suggested_files(handoff)
    
    # 5. 重建 Context Capsule
    capsule = build_context_capsule(task_id, turn=state.turns + 1)
    
    # 6. 生成 Resume Prompt
    resume_prompt = f"""
# Resume Task After Compact

You are resuming task `{task_id}` after context compaction.

**Important**: 
- Do NOT rely on conversation memory
- All state is reconstructed from disk files
- Read the Hot Tail below for current status

---

{capsule.tail}

---

**Suggested Files to Review** (from handoff):
{format_file_list(suggested_reads)}

**Next Action**: {state.next_action or "Continue current step"}

Ready to proceed?
"""
    
    return ResumeResult(
        success=True,
        capsule=capsule,
        resume_prompt=resume_prompt
    )
```

**关键原则**：
1. **状态来自磁盘**，不来自 transcript 摘要
2. **handoff 只是导航**，不解析为状态
3. **外部副作用检查**，不可逆操作要确认
4. **重建完整 Capsule**，不信任模型记忆
5. **明确告知模型**"这是 Resume，读磁盘状态"

---

### 七、验收测试

```python
def test_hot_tail_always_fresh():
    """Hot Tail 每轮都是最新"""
    task_id = "test-001"
    
    # Turn 1
    update_state(task_id, {"current_step": "S1"}, version=1)
    capsule_1 = build_context_capsule(task_id, turn=1)
    assert "Current Step: S1" in capsule_1.tail
    
    # Turn 2: 状态变化
    update_state(task_id, {"current_step": "S2"}, version=2)
    capsule_2 = build_context_capsule(task_id, turn=2)
    assert "Current Step: S2" in capsule_2.tail
    
    # Tail 必须反映最新状态
    assert capsule_1.tail != capsule_2.tail


def test_d4_review_isolated_by_default():
    """D4 审查文档默认不进 Context"""
    task_id = "test-002"
    
    # 即使 review/ 下有文件
    create_file(".omc/task/test-002/review/step-s1-review.md", "...")
    
    # 默认不加载
    capsule = build_context_capsule(task_id, turn=1)
    assert "step-s1-review.md" not in capsule.content
    
    # 除非显式加入 working-set
    add_to_working_set(task_id, "review/step-s1-review.md", level=D2)
    capsule_2 = build_context_capsule(task_id, turn=2)
    assert "step-s1-review.md" in capsule_2.content


def test_resume_ignores_handoff_state():
    """Resume 不从 handoff 解析状态"""
    task_id = "test-003"
    
    # 真实状态
    update_state(task_id, {"current_step": "S1", "status": "RUNNING"}, 1)
    
    # handoff 包含错误信息
    write_handoff(task_id, """
    Current Step: S3  # 错误
    Status: VERIFIED  # 错误
    """)
    
    # Resume 必须读取 token.json
    result = resume_after_compact(task_id)
    assert result.success is True
    assert "Current Step: S1" in result.resume_prompt
    assert "RUNNING" in result.resume_prompt
```

---

## 第 4 轮预告

下一轮我将输出：
- **handoff.md 最小协议**
- **Resume 引擎完整算法**
- **外部副作用对账机制**
- **Checkpoint 与 Resume 的协作关系**

准备第 4 轮。