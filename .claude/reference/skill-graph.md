# Skill 关联图谱

> 参考文件 — 非自动注入，compact/inject 时选择性注入
> 用途：帮助 AI 理解 Carror OS skill 之间的依赖关系、调用链路和替代选择

## 三级能力分层

```
L3：业务流水线
  lx-rpe → lx-prd → lx-oma-hier → lx-oma-split → lx-oma-gov → lx-oma-orch

L2：专业能力
  lx-code-review / lx-react-review / lx-security-review
  lx-golang-test / lx-tdd-spec / lx-debug-spec
  lx-root-cause-analysis / lx-race / lx-web-perf
  lx-browser-verify / lx-varlock

L1：基础设施
  lx-pre-commit / lx-pre-push
  lx-todo / lx-task-spec / lx-validate-skill / lx-status
```

## 调用关系

| 调用方 | 被调用方 | 场景 |
|--------|---------|------|
| lx-rpe Step 3 | lx-pre-commit | 编码后门禁（编译+测试+代码审查） |
| lx-rpe Step 3 | lx-code-review / lx-react-review | 代码质量审查（按项目类型路由） |
| lx-rpe Step 4 | lx-security-review | 安全扫描 |
| lx-rpe Step 3 | lx-golang-test | Go 测试缺口补测 |
| lx-oma-hier | lx-oma-split | Sub PRD → Feature 拆解 |
| lx-oma-orch | lx-oma-hier / lx-oma-split / lx-oma-gov / lx-rpe | 管线编排 |
| lx-pre-push | lx-pre-commit | push 前完整门禁 |
| lx-race | 全部 L2 skills | 蜂群并行协调 |
| lx-status | 全部 hook + skill | 健康面板聚合 |
| lx-task-spec | lx-rpe / lx-pre-commit | 任务驱动闭环 |

## 数据流

```
prd.md → lx-oma-hier → domain-*.md → lx-oma-split → prd/{name}/feat-*/prd.md
                                                                    ↓
                                                              lx-rpe research.md
                                                                    ↓
                                                              plan.md → executor.md
                                                                    ↓
                                                              state/progress.md
                                                                    ↓
                                                              lx-pre-commit (门禁)
                                                                    ↓
                                                              lx-pre-push (深度门禁)
```

## 替代与回退

| 主技能 | 替代方案 | 降级条件 |
|--------|---------|---------|
| lx-code-review | 人工审查 | 非 Go 项目或 skill 不可用 |
| lx-security-review | security-reviewer agent | skill 不可用 |
| lx-golang-test | 手动 `go test ./...` | skill 不可用 |
| lx-oma-orch | 手动逐 skill 调用 | pipeline.yaml 不存在 |

## 触发词索引

| 触发词 | 路由 skill | 说明 |
|--------|-----------|------|
| `/lx-rpe` | lx-rpe | 特性开发主入口（9 步闭环） |
| `/lx-oma-hier` | lx-oma-hier | PRD 分层拆解 → Sub PRD |
| `/lx-oma-split` | lx-oma-split | Sub PRD → Feature 拆解 |
| `/lx-oma-gov` | lx-oma-gov | PRD 治理 (reconcile/propagate/audit) |
| `/lx-oma-orch` | lx-oma-orch | 管线编排 |
| `/lx-todo` | lx-todo | 轻量开发模式 |
| `/lx-status` | lx-status | 系统健康面板 |
| `TDD` / `测试驱动` | lx-tdd-spec | 测试需求生成 |
| `debug` / `调试` | lx-debug-spec | 系统化调试 |
| 根因分析 / RCA | lx-root-cause-analysis | 五层 Why + 免疫 |
| `/lx-pre-commit` | lx-pre-commit | 提交前门禁 |
| `/lx-pre-push` | lx-pre-push | Push 前三道门禁 |
| `/lx-validate-skill` | lx-validate-skill | Skill 原子化校验 |
