## 原子化声明

> 本 skill 无私有 references，共享能力引用 @../references/oma/。


# lx-oracle — Oracle 独立第三方审核 (v2.0 合并版)

> **v2.0 说明**: 原 lx-oracle (本地 prompt) 和 lx-oracle-v2 (Agent 物理隔离) 已合并为一个 skill。
> 现在 `/lx-oracle` 自动检测环境: 有 OMC/OMO Agent → spawn 独立进程; 无 → 本地 prompt。

## 裁决范围

| 类型 | 裁决 | 示例 |
|------|------|------|
| **危险操作** | approved / rejected | `git push --force` |
| **架构决策** | approved / rejected | 重构是否符合 Philosophy |
| **方向漂移** | confirmed / diverted | 工作是否在目标范围内 |
| **硬边界预检** | safe / blocked | 操作是否触碰硬边界 |
| **真阻断判断** | blocked / workaround | 核心路径是否被堵死 |

## 输出格式

```
[Oracle: approved] — 理由: ...
[Oracle: rejected] — 理由: ...
[Oracle: escalated] — 理由: ..., 建议: Level 3 人类裁决
```

## 环境自适应路由

```
检测环境 (detect-oracle-env.sh)
  ├─ .omc/ 存在 → agent_omc (物理隔离 Agent spawn)
  ├─ .opencode/plugins/ 存在 → agent_omo (跨平台 Agent)
  └─ 无 → local_prompt (AI 本地扮演 Oracle)
```

**路由优先级**: OMC Agent > OMO Agent > 本地 prompt

## 执行流程

### 路径 A: Agent spawn (OMC/OMO 可用)

```
1. prepare: bash .claude/skills/lx-oracle-v2/scripts/oracle-spawn.sh prepare --mode d|v --target <path>
   → 输出 JSON 含 oracle_path + agent_available
2. spawn:   Agent(subagent_type="critic", prompt=<oracle-request.json + oracle-protocol.md>)
3. record:  bash .claude/skills/lx-oracle-v2/scripts/oracle-spawn.sh record --mode d|v --verdict "<agent output>"
   → 追加 oracle-verdicts.md + flywheel 事件
```

### 路径 B: 本地 prompt (无 Agent)

```
AI 直接按审核原则 + 输出格式做 Oracle 审查，结果写入 oracle-verdicts.md
```

## 调用方式

```
# 自动路由（推荐）
/lx-oracle review "操作描述" --context "相关上下文"

# 强制本地
/lx-oracle review "操作描述" --local

# 决策链引用
→ Level 1: AGENTS.md 无覆盖
→ Level 2: /lx-oracle → [Oracle: approved/rejected] — ...
→ 执行并记录
```

## 审核原则

1. **Philosophy 不可违背** — 违反哲学的操作必须 rejected
2. **Iron Rules 不可绕过** — AI workaround 必须 rejected
3. **0 信任** — 独立验证所有前提，不假设已做尽职调查
4. **裁决留痕** — 每条裁决附带理由，写入 `oracle-verdicts.md`

## 详细协议

Oracle-D (决策审核) / Oracle-V (验证审核) 完整协议 → `references/oracle-protocol.md`

## 降级策略

Agent spawn 超时 (120s): 记录 `pending-decisions.md` → 降级放行 → flywheel 告警 → 下次重试
