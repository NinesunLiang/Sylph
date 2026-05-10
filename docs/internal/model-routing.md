# Carror OS 模型路由策略

> 版本：v1 | 2026-05-10
> 描述：三档模型（haiku/sonnet/opus）分配策略与当前技能映射表

---

## 三档模型能力矩阵

| 档次 | 能力 | 适用场景 | 性价比 |
|------|------|---------|--------|
| **haiku** | 轻量快速 | 状态面板、简单校验、确定性脚本 | 低成本，高吞吐 |
| **sonnet** | 标准开发 | 编码、审查、测试、安全分析、RCA | 默认选择 |
| **opus** | 复杂架构 | 架构决策、跨系统分析、安全策略设计 | 按需调用 |

---

## 当前技能模型分配

### model: haiku（轻量技能）
| Skill | 行数 | 复杂度 | 理由 |
|-------|------|--------|------|
| lx-status | 64 | beginner | 面板聚合，仅读取状态文件+格式化输出 |
| lx-validate-skill | — | beginner | 11 项确定性合规检查 |

### model: sonnet（标准技能 — 默认档位）
| Skill | 行数 | 复杂度 | 理由 |
|-------|------|--------|------|
| lx-browser-verify | — | intermediate | 浏览器端到端验证 |
| lx-code-review | — | intermediate | 代码审查，标准分析 |
| lx-debug-spec | — | intermediate | Debug 流程引导 |
| lx-golang-test | — | intermediate | Go 测试执行 |
| lx-oma-gov | — | intermediate | PRD 治理 |
| lx-oma-hier | — | intermediate | 分层拆解 |
| lx-oma-orch | — | intermediate | 管线编排 |
| lx-oma-split | — | intermediate | OMA 拆解 |
| lx-prd | — | intermediate | PRD 管理 |
| lx-pre-commit | — | intermediate | 预提交门禁 |
| lx-pre-push | — | intermediate | 推送前门禁 |
| lx-race | — | intermediate | 竞态检测 |
| lx-react-review | — | intermediate | React 审查 |
| lx-root-cause-analysis | 212 | intermediate | 根因分析，标准 RCA |
| lx-rpe | 212 | intermediate | 9 步闭环（重构后已精简） |
| lx-security-review | — | intermediate | 安全审查 |
| lx-task-spec | — | intermediate | 结构化任务 |
| lx-tdd-spec | — | intermediate | TDD 流程 |
| lx-todo | — | intermediate | Todo 管理 |
| lx-web-perf | — | intermediate | Web 性能分析 |

---

## 模型选择原则

1. **默认 sonnet**：除非明确理由，所有 skill 默认 `model: sonnet`
2. **降级 haiku 条件**：
   - 行数 < 80 行
   - 复杂度 = beginner
   - 无架构决策/安全分析需求
3. **升级 opus 条件**（当前无 skill 满足）：
   - 涉及跨系统架构决策
   - 安全策略/加密协议设计
   - 多人团队代码的深层重构分析

---

## 在 SKILL.md 中使用

每个 SKILL.md 在 YAML frontmatter 中声明：

```yaml
---
name: lx-example
model: sonnet  # haiku | sonnet | opus
complexity: intermediate  # beginner | intermediate | advanced
---
```

CLI 工具或 orchestrator 在调用技能时，应读取 `model:` 字段并传递给底层模型路由。
