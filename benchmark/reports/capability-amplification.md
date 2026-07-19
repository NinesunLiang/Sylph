# CarrorOS 能力放大测试报告

> 生成时间: 2026-07-18T19:08:43.791227+00:00
> 总运行次数: 6

---

## 总体指标

| 指标 | 值 |
|------|-----|
| Verified Success Rate | 0.0% |
| Hard Task Success Rate | 0.0% |
| First Path Correct Rate | 0.0% |
| Silent False Success Rate | 0.0% |
| Regression Escape Rate | 100.0% |
| Cost / Verified Success | $inf |

## 分组对比

| 组 | N | Success Rate | Avg Cost | Cost/Success | Avg Tool Calls |
|----|---|-------------|----------|--------------|----------------|
| A_bare | 6 | 0.0% | $0.00 | $inf | 0.0 |

## 组件消融梯度

| 过渡 | 新增组件 | 回答的问题 |
|------|----------|-----------|
| A → B | AGENTS + CLAUDE.md | 入口文档是否提升协议遵守率？ |
| B → C | INDEX + kernel | 路由和约束是否提升路径正确率？ |
| C → D | Context Engine | 上下文管理是否提升持续执行能力？ |
| D → E | Harness + Hooks | 软约束转为硬执行是否提升完成率？ |

## 失败分类

| 失败类型 | 次数 | 占比 |
|----------|------|------|
| none | 6 | 100.0% |
