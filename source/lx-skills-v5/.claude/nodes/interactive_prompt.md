# 交互式参数引导 — 所有 skill 通用

> 当用户调用 skill 但未提供完整参数时，自动进入引导式问答。
> 本文件被所有 lx-* skill 引用。

## 触发条件

用户调用 skill 时：- 有参数 → 直接执行（向后兼容）- 无参数 → 进入引导式问答

## 引导式问答流程

### 第 1 问：目标

```📋 {skill_name} 已启动。
问题 1/3：{目标提示}示例：{示例1} {示例2}```

### 第 2 问：深度/范围

```问题 2/3：{深度提示}
1. 快速扫描 — 仅检测，不修复
2. 深度分析 — 检测 + 自动修复 P0/P1
3. 全量 + 验证 — 检测 + 修复 + re-scan 验证```

### 第 3 问：重点关注（可选）

```问题 3/3：有重点关注的问题类别吗？（直接回车跳过）示例：{重点关注示例}```

### 构建 task_input

用户回答完成后，自动构建：
```yamltask_input
: name: "{skill_name} - {目标}" role: "{从 skill 声明推断}" target: "{用户输入的目标}" scope: "{用户选择的深度}" criteria: "{skill 内置完成标准}" focus_areas: "[{用户输入的重点关注}]"
```
然后按 skill 的执行流程继续。

## 各 skill 的引导配置

| Skill | Q1 目标提示 | Q2 深度选项 | Q3 重点关注示例 |
|-------|-----------|------------|----------------|
| lx-code-review | 审查什么？（文件/目录/git ref/函数名） | 快速扫描 / 深度+修复 / 全量+验证 | "重点看并发安全和 error 处理" |
| lx-security-review | 扫描什么？（文件/目录/git ref） | 快速扫描 / 深度+修复 / 全量+govulncheck | "重点看 SQL 注入和硬编码密钥" |
| lx-react-review | 审查什么？（组件文件/目录/组件名） | 快速扫描 / 深度+修复 / 全量+类型检查 | "重点看 hooks 规则和 re-render" |
| lx-style-guide | 检查什么？（样式文件/目录/组件名） | 快速扫描 / 深度+修复 / 全量+可访问性 | "重点看 Design Token 一致性" |
| lx-web-perf | 审查什么？（文件/目录/路由/组件名） | 快速扫描 / 深度+修复 / 全量+Lighthouse | "重点看 Bundle 大小和 Web Vitals" |
| lx-browser-verify | 验证什么？（URL/组件名/页面路由/流程描述） | 截图验证 / 交互流程 / 全量+暗色模式 | "重点看移动端响应式" |
| lx-frontend-test | 测试什么？（组件文件/目录/组件名） | 单元测试 / E2E 测试 / 全量+覆盖率 | "重点看表单交互和 API Mock" |
| lx-golang-test | 测试什么？（函数名/handler 名/接口名） | 单元测试 / 基准测试 / 全量+race | "重点看 table-driven 和 mock" |
| lx-perf-analysis | 分析什么？（函数名/包路径/性能症状描述） | CPU / 内存 / Goroutine / 全域 | "重点看内存分配和逃逸" |
| lx-todo | 做什么？（描述 todo 项） | 快速修复 / 完整流程 | — |
| lx-tdd-spec | 什么功能/API？（描述） | 完整 Spec / 轻量版 | — |
| lx-pre-commit | 提交什么？（自动检测） | 自动 | — |
| lx-pre-push | 推送什么？（自动检测） | 自动 | — |
| lx-debug-spec | 什么错误？（错误描述/测试失败/CI 报错） | 快速定位 / 深度根因 / 修复+回归 | — |
| lx-root-cause-analysis | 什么 recurring bug？（症状+历史） | 5-Why 分析 / 完整免疫 | — |
| lx-rpe | 什么功能？（RPE 任务项） | 完整 RPE 流程 | — |
| lx-prd | 什么产品/功能？（描述） | 完整 PRD / 轻量版 | — |
