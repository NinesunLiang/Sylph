# 面向专家

> **你来这里不是为了护栏，而是为了力量倍增器。**

## 变化了什么

**进阶版**解锁完整的 Carror OS — 主动工作流、多智能体盲审、DLP 透明代理和 RPE 开发管线。

安装方式：

```bash
curl -fsSL https://raw.githubusercontent.com/NinesunLiang/Sylph/main/install.sh | bash -s -- enhanced
```

## 你将获得（超越基础版）

### 主动工作流技能

| 技能 | 功能 |
| :--- | :--- |
| `/lx-rpe` | 研究→规划→执行管线，支持 50% 上下文交接和 A/B 盲审 |
| `/lx-task-spec` | 中复杂度任务，由精确验收标准驱动（无需 PRD） |
| `/lx-todo` | 轻量 5 步 bug 修复循环，适用于小型任务（≤3 个文件） |
| `/lx-prd` | 自动化产品需求文档生成 |
| `/lx-tdd-spec` | 从行为矩阵生成 TDD 测试场景 |
| `/lx-browser-verify` | Playwright E2E 可视化验收测试 |
| `/lx-root-cause-analysis` | 5-Why 根因追踪深度调试 |
| `/lx-debug-spec` | 深度并发问题调试 |
| `/lx-golang-test` | Go 专属测试框架 |
| `/lx-frontend-test` | 前端测试框架 |
| `/lx-varlock` | DLP 透明代理 — AI 使用脱敏凭据；本地保险库在执行时替换 |
| `/lx-status` | 健康看板：显示 Token 节省、自愈率、执行效率 |

### RPE 工作流

核心专家工作流是**研究→规划→执行**：

1. **研究**：调查问题空间、记录约束、读取受影响代码
2. **规划**：设计架构、定义接口、设定验收标准
3. **执行**：每一步都有证据门禁的增量实现，50% 时自动上下文交接

### 高级工作流

- **竞赛** (`/lx-race`)：并行候选生成，由评审者选择最佳方案
- **OMA** (`/lx-oma`)：优化的多智能体并发开发，带锁管理

## 何时升级

当你满足以下条件时从基础版升级到进阶版：

- 正在承担跨多个模块的复杂重构
- 需要多智能体盲审来发现自己的盲区
- 希望为大型功能开发建立结构化的 RPE 规范
- 需要管理同时在代码库不同部分工作的并发 AI 智能体

升级是安全的，原地进行。你现有的配置和记忆将被保留：

```bash
bash install.sh enhanced
```

降级也同样安全：

```bash
bash install.sh base
```

## 下一步

| 目标 | 路径 |
| :--- | :--- |
| RPE 深度了解 | [工作流概念](../concepts/workflow.md) |
| 完整功能参考 | [功能特性](../governance/features.md) |
| 升级说明 | [版本选择](../governance/editions.md) |
