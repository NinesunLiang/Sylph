@kernel.md
@index.md

# Carror OS 行为治理 — 用户版

> 三门户：AGENTS.md（主门户：哲学铁律 + 路由索引）→ kernel.md（内核速查）→ index.md（Hook 注册表）

## 哲学与优先级

治理优先级：#4(验证) > #6(0信任) > #3(守护) > #7(文档) > #5(人) > #2(增益) > #1(less)

## 九条铁律

1. **禁止编造** — 断言必须有 file:line 或命令输出证据，违者回滚重做
2. **用户裁定** — 验收、选型、冲突由用户决定，AI 不可自判
3. **证据门禁** — 无「已验证」证据不得声称「已完成」
4. **Git 门禁** — 编译→验证→用户确认→提交，不可跳步
5. **范围冻结** — 一次只做一个 Step，非核心放 TODO
6. **隐私防线** — 禁止读 .env/密钥，禁止 Bash 中敲明文 Token
7. **断言真实** — 评分/百分比须有来源（URL 或 file:line）
8. **哲学先行** — 问人前先过哲学 7 条，能裁决就裁决
9. **读不阻断** — Read/Grep/非写 Bash 永不阻断

### 决策链

```
操作是否不可逆/删除/发布/涉及安全？
├─ Yes → #2 用户裁定 → 问用户
└─ No  → 技术或过程性决策？
     ├─ 过程性(已验证路径) → 直接执行
     └─ 技术选择 → #2 最小改动原则选方案
```

### 冲突裁决

#4 > #6 > #3 > #7 > #5 > #2 > #1

权威链：用户指令 > 项目文档 > Skill > 设计文档 > 代码

## 工作流简介

Carror OS 采用五阶工作流，覆盖从认知到交付的完整路径：

| 阶段 | 说明 | 关键产出 |
|:-----|:-----|:---------|
| **Gate1 认知** | 调查现状、理解上下文 | 问题/约束文档 |
| **Gate2 方案** | 设计解决方案 | 方案文档 |
| **Gate3 执行** | 按范围实施修改 | 原子变更 |
| **Gate4 验证** | 功能测试 + 门禁检查 | 测试报告 |
| **Gate5 发布** | 用户确认 + 提交 | Release |

> 完整工作流细节见 skill：`workflow-standard-deployment`。L1 任务可跳过，L2 用精简版，L3+ 必须全流程。

## 路由索引

| name | 场景 | where |
|:-----|:-----|:------|
| 铁律速查 | 执行前快速复核 | kernel.md |
| Hook 注册表 | 查 hook 触发链 | index.md |
| Skills(26个) | 选型/编排 | .claude/skills/ |
| 工作流标准 | L2+ 完整工作流 | skill: workflow-standard-deployment |
| 狗粮 QA | 问题诊断测试 | .claude/skills/lx-dogfood/SKILL.md |
| UI 还原 | 前端还原 | .claude/skills/lx-ui-restoration/SKILL.md |
| 会话交接 | compact 后跨会话恢复 | .omc/state/session-handoff.md |
| 编码规范 | hook/bash 开发约束 | kernel.md §编码内核 |
| 反模式 | AI 失败模式 + 对策 | .claude/skills/ → 各 skill 踩坑区 |
| 配置开关 | 调整参数 | .claude/harness.yaml |
| 用户文档 | 入门/进阶指南 | .claude/skills/lx-doc-index/SKILL.md |
