# Skill 关联图谱

> 参考文件 — 非自动注入，compact/inject 时选择性注入
> 用途：帮助 AI 理解 Carror OS skill 之间的依赖关系和调用链路

## 三级能力分层

```
L3：业务流水线
  lx-oma-hier → lx-oma-split → lx-oma-gov → lx-oma-orch

L2：专业能力
  lx-goal / lx-ghost       — 自主执行 (目标驱动 / 方向驱动)
  lx-oracle / lx-sync       — 质量保障 (独立审核 / 一致性检查)
  lx-race / lx-stepwise     — 执行引擎 (并行蜂群 / 串行攻坚)
  lx-task-spec / lx-test-gen — 任务驱动 (结构化任务 / 测试生成)
  lx-dogfood / lx-status    — 运维洞察 (狗粮投喂 / 健康面板)
  lx-varlock                — 安全代理 (隐私脱敏)
  lx-brave-recovery         — 故障恢复 (Brave Search MCP)
  update-carror-os          — 安装更新

L1：基础设施
  lx-pre-commit / lx-pre-push  — 门禁 (提交前 / 推送前)
  harness_config.sh / hooks    — 运行时 (配置库 / 钩子系统)
```

## 调用关系

| 调用方 | 被调用方 | 场景 |
|--------|---------|------|
| lx-oma-hier | lx-oma-split | Sub PRD → Feature 拆解 |
| lx-oma-orch | lx-oma-hier / lx-oma-split / lx-oma-gov | 管线编排 |
| lx-pre-push | lx-pre-commit | push 前完整门禁 |

## 隐式依赖 — Hook 门禁与 Skill 的关系

| Skill | 隐式依赖的 Hook 门禁 | 说明 |
|-------|---------------------|------|
| lx-goal | pretool-plan-gate | Goal 模式 phase0-done 验证依赖 plan-gate 阻断未审批的代码变更 |
| lx-goal | permission-gate | 自主执行时的安全网：拦截危险命令 + CAPTCHA 文件保护 |
| lx-goal | pre-ask-guard | 自主模式需要决策链过滤，减少不必要的人类打断 |
| lx-ghost | permission-gate | 幽灵模式的安全网：拦截危险命令（ghost 绕过 plan-gate） |
| lx-ghost | pretool-oracle-gate | Ghost 的 Oracle 计划审核前置门禁 |
| lx-ghost | pre-ask-guard | 幽灵模式需要决策链过滤 |
| lx-oracle | pretool-oracle-gate | Oracle 审核任务触发前，确保上下文符合审核标准 |
| lx-oracle | pre-completion-gate | Oracle 完成前验证证据质量 |
| lx-rpe | pretool-plan-gate | RPE 模式需要 plan 批准后才能进入 execution phase |
| lx-pre-commit | pretool-git-gate | 提交前门禁：git commit 必须通过 pre-commit 检查 |
| lx-pre-push | pretool-git-gate | 推送前深度检查的 Git 门禁 |
| lx-purify | pretool-purify-gate | 隐私脱敏运行时 hook 支持 |
| lx-validate-skill | pretool-skill-version-guard | SKILL.md 格式版本校验门禁 |
| lx-skillify | pretool-skill-body-enforce | skill body 强制执行合约注入 |

## 数据流

```
prd.md → lx-oma-hier → domain-*.md → lx-oma-split → prd/{name}/feat-*/prd.md
                                                         ↓
                                                   state/progress.md
                                                         ↓
                                                   lx-pre-commit (门禁)
                                                         ↓
                                                   lx-pre-push (深度门禁)
```

## 触发词索引

| 触发词 | 路由 skill | 说明 |
|--------|-----------|------|
| `/lx-oma-hier` | lx-oma-hier | PRD 分层拆解 → Sub PRD |
| `/lx-oma-split` | lx-oma-split | Sub PRD → Feature 拆解 |
| `/lx-oma-gov` | lx-oma-gov | PRD 治理 (reconcile/propagate/audit) |
| `/lx-oma-orch` | lx-oma-orch | 管线编排 |
| `/lx-pre-commit` | lx-pre-commit | 提交前门禁 |
| `/lx-pre-push` | lx-pre-push | Push 前三道门禁 |
