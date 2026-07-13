# CarrorOS Opus-4.8 完整方案（2/10）

## 第 2 轮：MVP 核心状态模型 — token.json 正式化

### 一、为什么保留 token.json

基于知识库中已有的 CarrorOS 实践，我看到：

1. **你已经有成熟的 token.json 体系**
   - `.omc/tokens/<task-id>.json`
   - 包含 task_id、status、current_step、turns、watermark
   - 配套工具链已经围绕它构建

2. **改名成本高于收益**
   - 迁移到 state.json 需要重写所有工具
   - 历史任务需要数据迁移
   - 不改变协议本质

3. **关键是形式化，而非重命名**

**我的裁决：正式将 token.json 定义为 CarrorOS TaskState 的持久化格式。**

---

### 二、token.json 最终 Schema（v1.0）

```yaml
schema_version: carros.task_state.v1
state_id: STATE-fix-auth-001-v18
task_id: fix-auth-001
manifest_version: 2

# 核心状态机
status: RUNNING  # INIT|RUNNING|VERIFIED|BLOCKED|ARCHIVED|CANCELLED
current_step: S2
current_step_status: RUNNING  # PENDING|RUNNING|VERIFIED|BLOCKED

# 版本控制（CAS 关键）
version: 18
last_modified_at: "2026-07-12T10:30:00Z"
last_modified_by: execute-session-01

# 完成性
progress:
  total_steps: 3
  completed_steps: 1
  verified_steps: 1
  blocked_steps: 0

# 阻塞信息
blocker: null  # 或 {type, description, required_input}
question: null  # 或 {id, text, required_by}

# Context 健康度
context:
  turns: 12
  estimated_input_tokens: 8200
  watermark: CONTINUE  # CONTINUE|COMPACT_SOON|COMPACT_NOW
  last_capsule_version: 7
  compaction_count: 0

# 验证状态
verification:
  task_verdict_id: null  # 任务级 verdict
  current_step_verdict_id: null  # 当前 step verdict
  last_verified_step: S1
  last_verified_at: "2026-07-12T10:15:00Z"

# 决策记录
decisions:
  - id: D-001
    text: 保持公共 RefreshError 类型不变
    source: user_explicit
    binding: true

# 外部副作用（关键恢复信息）
external_effects:
  - effect_id: EXT-001
    kind: git_commit
    description: 修改 src/auth/refresh.ts
    status: COMMITTED  # PENDING|IN_FLIGHT|COMMITTED|UNKNOWN
    reversible: true
    checkpoint_id: CHK-007

# 风险与分级
risk:
  level: medium  # low|medium|high
  categories: [auth_change, concurrency]
  
manifest_level: L1  # L1 快速 | L2 严谨

# 模型使用记录
model_usage:
  total_input_tokens: 84200
  total_output_tokens: 9100
  estimated_cost_usd: 0.82
  primary_profile: deepseek-v4-flash
  escalation_count: 0
  oracle_calls: 0

# 关联文件版本（恢复一致性检查）
related_versions:
  plan_version: 4
  manifest_version: 2
  working_set_version: 3
  repository_commit: abc1234

# 平台特定元数据
platform:
  kind: claude_code  # or opencode
  session_id: session-20260712-01
  transcript_ref: null  # 仅审计，不用于恢复
  compaction_generation: 0

# 保留字段（兼容旧版本）
legacy:
  oracle: null  # 旧版本的 oracle 字段，已废弃
  fallback: null  # 已迁移到 model_usage
```

---

### 三、关键设计决策

#### 决策 1：CAS 版本控制

```python
def update_state(task_id: str, updates: dict, expected_version: int) -> bool:
    """Compare-And-Swap 更新"""
    current = load_token(task_id)
    
    if current["version"] != expected_version:
        # 版本冲突，拒绝更新
        return False
    
    new_state = {
        **current,
        **updates,
        "version": expected_version + 1,
        "last_modified_at": now(),
    }
    
    # 原子写入
    write_token_atomic(task_id, new_state)
    return True
```

**为什么必须 CAS**：
- 防止多 Agent/多会话同时写入
- 支持乐观并发控制
- Handoff/Resume 可检测状态漂移

#### 决策 2：status 与 current_step_status 分离

```text
任务级 status：RUNNING
步骤级 status：每个 step 独立状态

示例：
task.status = RUNNING
task.current_step = S2
plan.steps[S1].status = VERIFIED
plan.steps[S2].status = RUNNING
plan.steps[S3].status = PENDING
```

这样可以区分：
- 任务整体是否在进行
- 当前步骤是否可以继续
- 哪些步骤已经完成

#### 决策 3：watermark 是观测值，不是控制指令

```yaml
context:
  watermark: COMPACT_SOON
```

这**不是**命令模型"你应该压缩了"，而是：
- 系统观测到 Context 接近软水位
- Resume 时应考虑生成 handoff
- 但不强制触发 compact

真正的压缩由平台机制触发（Claude L1～L5、OpenCode Prune）。

#### 决策 4：external_effects 是恢复关键

```yaml
external_effects:
  - effect_id: EXT-002
    kind: api_call
    description: 调用上游认证服务
    status: UNKNOWN  # Resume 时不能重放
    reversible: false
    checkpoint_id: null
```

Resume 算法必须检查：
- 所有 `status: IN_FLIGHT` 或 `UNKNOWN` 的副作用
- 不可逆操作是否需要人工确认
- checkpoint 是否仍然有效

---

### 四、与 handoff.md 的协作关系

```text
token.json
  机器可解析的状态真相
  Resume 引擎的唯一输入
  版本控制与 CAS

handoff.md
  人类可读的恢复导航
  建议从哪里开始
  记录上次为什么停止
  
关系：
  token.json → 生成 → handoff.md
  handoff.md ✗ 解析回 → token.json
```

**禁止从 handoff.md 提取状态的理由**：

```python
# 错误做法 ✗
def resume_from_handoff(task_id: str):
    handoff = load_markdown("handoff.md")
    current_step = extract_step_from_text(handoff)  # 容易出错
    status = infer_status_from_description(handoff)  # 更容易出错
    return {"current_step": current_step, "status": status}

# 正确做法 ✓
def resume_from_state(task_id: str):
    state = load_token(task_id)  # 机器可靠
    handoff = load_handoff(task_id)  # 仅用于上下文
    
    # handoff 只用于：
    # 1. 告诉用户"上次在做什么"
    # 2. 建议读取哪些文件
    # 3. 警告哪些路径可能相关
    
    return state  # 状态仍来自 token.json
```

---

### 五、兼容旧版本的迁移策略

如果现有 token.json 缺少某些字段：

```python
def migrate_legacy_token(old_token: dict) -> dict:
    """将旧 token 迁移到 v1.0"""
    
    # 必需字段
    new_token = {
        "schema_version": "carros.task_state.v1",
        "task_id": old_token["task_id"],
        "status": normalize_status(old_token.get("status", "RUNNING")),
        "current_step": old_token["current_step"],
        "version": old_token.get("version", 1),
    }
    
    # 可选字段，提供默认值
    new_token["blocker"] = old_token.get("blocker")
    new_token["question"] = old_token.get("question")
    
    # 重建字段
    new_token["progress"] = infer_progress(old_token)
    new_token["verification"] = extract_verification_state(old_token)
    
    # 废弃字段保留在 legacy 中
    new_token["legacy"] = {
        "oracle": old_token.get("oracle"),
        "fallback": old_token.get("fallback"),
    }
    
    return new_token
```

迁移时机：
- 首次运行新版本工具时自动迁移
- 保留旧文件为 `token.legacy.json`
- 迁移日志写入 audit

---

### 六、验收测试

```python
def test_token_cas_prevents_concurrent_write():
    """CAS 阻止并发写入"""
    state_v1 = create_task("test-001")
    assert state_v1["version"] == 1
    
    # Agent A 和 Agent B 同时读取
    state_a = load_token("test-001")
    state_b = load_token("test-001")
    
    # Agent A 先写入
    ok_a = update_state("test-001", {"current_step": "S2"}, expected_version=1)
    assert ok_a is True
    
    # Agent B 尝试基于旧版本写入
    ok_b = update_state("test-001", {"current_step": "S3"}, expected_version=1)
    assert ok_b is False  # 版本冲突，写入失败
    
    # Agent B 必须重新读取并重试
    state_latest = load_token("test-001")
    assert state_latest["version"] == 2
    assert state_latest["current_step"] == "S2"


def test_handoff_does_not_override_token_state():
    """handoff 不能覆盖 token 状态"""
    # 初始状态
    update_state("test-002", {"status": "RUNNING", "current_step": "S1"}, 1)
    
    # 写入 handoff，故意包含错误信息
    write_handoff("test-002", """
    # Handoff
    Current Step: S3  # 错误！实际是 S1
    Status: VERIFIED  # 错误！实际是 RUNNING
    """)
    
    # Resume 不应从 handoff 解析状态
    state = resume_task("test-002")
    assert state["current_step"] == "S1"  # 来自 token.json
    assert state["status"] == "RUNNING"   # 来自 token.json


def test_unknown_external_effect_blocks_resume():
    """未知外部副作用阻止恢复"""
    state = {
        "task_id": "test-003",
        "status": "RUNNING",
        "external_effects": [
            {
                "effect_id": "EXT-001",
                "kind": "api_call",
                "status": "UNKNOWN",  # 不知道是否完成
                "reversible": False,
            }
        ],
    }
    
    result = check_resume_safety(state)
    assert result["safe"] is False
    assert "UNKNOWN external effect" in result["reason"]
```

---

## 第 3 轮预告

下一轮我将输出：
- **渐进式披露（D0～D5）与 Hot Tail 生成**
- working-set.yaml 与每轮 Context 重建
- "每 5 轮注入"改为"每轮 Hot Tail"的具体实现
- U 型注意力的头部、中部、尾部组成

现在准备第 3 轮。