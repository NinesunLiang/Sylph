---
name: lx-oracle
version: v2.0.0
description: "Oracle 独立第三方审核 — 环境自适应路由: 有 Agent 时物理隔离 spawn, 无 Agent 时本地 prompt。裁决留痕 oracle-verdicts.md。"
role: "Independent third-party auditor for autonomous decision chains"
when_to_use: "Use when autonomous execution hits a decision gate requiring independent review: dangerous operations, architecture decisions, direction drift, hard-boundary pre-checks, or true-blockage judgments. Trigger: '/lx-oracle', 'oracle:review'."
harness_version: ">=6.3.0"
status: stable
execution_mode: stepwise
triggers:
  - "/lx-oracle"
  - "oracle:review"
  - "oracle:approve"
  - "oracle:reject"
nodes:
  - behavior_rules          # 自洽检查 + 哲学先行
  - target_resolver         # 解析审核目标
  - gate_checker            # 门禁判定(approved/rejected/escalated)
  - report_generator        # 裁决报告生成
schemas:
  - atomic/verdict
  - atomic/gate_result
  - output/review_report
---
# lx-oracle — Oracle 独立第三方审核 (v2.0)

**v2.0**: 原 lx-oracle (本地 prompt) 和 lx-oracle-v2 (Agent 隔离) 合并。自动检测环境：有 Agent → spawn 独立进程；无 → 本地 prompt。

## 裁决范围

| 类型 | 裁决 | 示例 |
|------|------|------|
| 危险操作 | approved / rejected | `git push --force` |
| 架构决策 | approved / rejected | 重构是否符合 Philosophy |
| 方向漂移 | confirmed / diverted | 工作是否在目标范围内 |
| 硬边界预检 | safe / blocked | 操作是否触碰硬边界 |
| 真阻断判断 | blocked / workaround | 核心路径是否被堵死 |

## 输出格式

```
[Oracle: approved] — 理由: ...
[Oracle: rejected] — 理由: ...
[Oracle: escalated] — 理由: ..., 建议: Level 3 人类裁决
```

判定由 gate_checker 执行门禁检查，出 gate_result.yaml。

## 环境自适应路由

```text
检测环境
  ├─ .omc/ 存在 → agent_omc (物理隔离 Agent spawn)
  ├─ .opencode/plugins/ 存在 → agent_omo (跨平台 Agent)
  └─ 无 → local_prompt (AI 本地扮演 Oracle)
```

**路由优先级**: OMC Agent > OMO Agent > 本地 prompt

## 执行流程

### 路径 A: Agent spawn

```text
1. prepare: bash oracle-spawn.sh prepare --mode d|v --target <path>
2. spawn:   Agent(subagent_type="critic", prompt=<oracle-request.json + oracle-protocol.md>)
3. record:  oracle-spawn.sh record --mode d|v --verdict "<agent output>"
```

### 路径 B: 本地 prompt

AI 直接按审核原则做 Oracle 审查，结果写入 oracle-verdicts.md。

## 调用方式

```text
/lx-oracle review "操作描述" --context "相关上下文"   # 自动路由
/lx-oracle review "操作描述" --local                    # 强制本地
```

## 审核原则

1. Philosophy 不可违背
2. Iron Rules 不可绕过
3. 0 信任 — 独立验证所有前提
4. 裁决留痕 — 每条裁决写入 oracle-verdicts.md

## 降级策略

Agent spawn 超时 (120s): 记录 pending-decisions.md → 降级放行 → flywheel 告警 → 下次重试
