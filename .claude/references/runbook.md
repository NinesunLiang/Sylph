# CarrorOS Gate 失效人工流程 (Runbook)

> GateKeeper v1 分层裁决链上线后的应急处理手册。
> 引用: `@references/runbook.md`

## 概要

当任何 Gate 失效（误拦 / 漏放 / 崩溃）时，按此流程处理。

## 状态检测

```bash
# 1. GateKeeper 事件统计
python3 .claude/scripts/gatekeeper_digest.py

# 2. 检查是否有堆积的跳过风险
python3 .claude/scripts/gatekeeper_digest.py --check

# 3. 详细告警
python3 .claude/scripts/gatekeeper_digest.py --alert
```

## 场景处理

### 场景 A: GateKeeper 误拦截（假阳性）

**表现**: AI 被 Block/Redirect 阻止执行合法操作。

**排查**:
```bash
# 查看最近的 gatekeeper 事件
cat .omc/state/gatekeeper-events.jsonl | tail -5 | python3 -m json.tool

# 查看触发的铁律违反
rg "iron_law" .omc/state/gatekeeper-events.jsonl | tail -3
```

**处理方法**:
1. 如果属于哲学/ROI 评分误差 → 调整 `gatekeeper.py` 中的 `_generate_options()` 或 `_threshold_for_risk()`
2. 如果属于铁律误触发 → 检查 `_check_iron_rules()` 中的条件
3. 临时 bypass（需人工确认）:
   ```bash
   python3 .claude/scripts/temp-bypass.py --minutes 30 --reason "已确认安全——误拦截"
   ```
4. 记录到 anti-patterns.md 供后续调优

### 场景 B: Gate 漏放行（假阴性）

**表现**: 危险操作未被拦截，产生不良后果。

**排查**:
```bash
# 检查 pretool-gate 的 oracle 裁决
rg "oracle_gate\|BLOCK\|REDIRECT" .omc/redirects.jsonl | tail -10

# 检查是否绕过
rg "bypass\|bypass_attempt" .omc/state/gatekeeper-events.jsonl | tail -5
```

**处理方法**:
1. 加规则到 `_oracle_classify()` 或 `_check_iron_rules()`
2. 更新 `ANTI_PATTERN_REDIRECTS_PATH` 中的反模式规则
3. 提交测试覆盖漏放场景

### 场景 C: Gate 崩溃（500 / exit 非 0/2）

**表现**: 工具调用全部阻断或 CC 报 "hook stopped continuation"。

**排查**:
```bash
# 检查 hook 崩溃日志
rg -i "hook.*crash\|exit\|error" .omc/ .claude/hooks/ 2>/dev/null | tail -10
```

**处理方法**:
1. `_check_sensitive_edit()` 治理文件门有 goal 模式降级
2. 如果是 `pretool-gate.py` 崩溃，暂时禁用:
   ```yaml
   # .claude/harness.yaml
   hooks_enabled:
     permission_gate: false  # 临时禁用
   ```
3. 修复后再重新启用

### 场景 D: token.json 状态异常

**表现**: token 状态卡在 blocked/waiting_user/recovered 但不应如此。

**排查**:
```bash
cat .omc/state/token.json | python3 -m json.tool
```

**处理方法**:
1. 如果 `governance.recovery_lock = true` 且需要手动解锁:
   ```bash
   # 编辑 .omc/state/token.json，设置 recovery_lock = false
   ```
2. 如果 `recovery_required = true` 且任务已处理:
   ```bash
   # 编辑 token，设置 recovery_required = false, recovery_ack = true
   ```

## 回滚方案

### gatekeeper.py 回滚

```bash
git checkout HEAD~2 -- .claude/scripts/gatekeeper.py
```

### pretool-gate 回滚到旧 _block 格式

```bash
git checkout HEAD~3 -- .claude/hooks/pretool-gate.py
```

### 全量回滚到 GateKeeper 上线前

```bash
git revert d9bee2b  # 第一个 GateKeeper commit
# 可能需要按依赖顺序 revert 多个 commit
```

## 告警阈值

| 指标 | 阈值 | 动作 |
|------|------|------|
| skipped-risks.jsonl 条数 | >200 | 截断并告警 |
| gatekeeper BLOCK 事件数 | >10 | 检查是否误拦 |
| error-dna.jsonl 未消费条数 | >500 | 需要 review |
| token.json blocked 持续时间 | >30min | 自动清理(recovery_lock 守卫) |

## 联络

- GateKeeper 相关修改均记录在 git log
- 架构决策记录在 `.claude/references/adr/`

## 降级策略（L2→L1）（来源: 原 fallback-matrix.md）

> 当 context 过高 / 模型异常 / 连续失败时，自动降级 L2 → L1。
> 实现见 `scripts/fallback_engine.py`（已取代旧 `fallback_matrix.py`）。

### 降级触发条件

| # | 条件 | 检测方式 | 阈值 | 降级动作 |
|---|------|---------|------|---------|
| 1 | Context 过满 | context_watermark | ≥80% | L2→L1 全降级 |
| 2 | 连续 3 步未 Verify | audit 检查 | 连续 3 tick 无 verify 事件 | 暂停复杂操作 |
| 3 | 3 次 Oracle 执行时间超过 30s | Oracle 响应时间 | 单次 >30s | 跳过 Oracle（ACCEPT 默认） |
| 4 | 模型返回格式异常（非 JSON） | parse error 计数 | 连续 3 次 | 降级 L2→L1 |
| 5 | 人类长时间无介入 | last_user_message | >3600s | 不降级，但限制 L2 操作范围 |

### 降级路径

- **L2→L1**: 关闭水位检测、关闭 Oracle、关闭飞轮，回到 L1 4 步工作流（Plan→Step→Verify→Archive）
- **L1→非活跃**: session-handoff 写入后停止

### 调用方式

```bash
# 触发降级（fallback_engine 入口）
python3 .claude/scripts/fallback_engine.py <failure_type> [risk] [token_path]

# 历史接口（fallback_matrix.py 已归档）—— 不要再使用
# python3 .claude/scripts/archived/fallback_matrix.py --check <触发点ID>
```

返回示例（`should_fallback=true/false, action, reason`）。
