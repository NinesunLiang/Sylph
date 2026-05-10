# 统一交付 Schema

> >
> 所有节点必须遵循的输出格式
> 版本：v1.0.0

---

## 结论 / 当前状态
- state: `ready` | `need_clarification` | `planning` | `spec_review` | `executing` | `fallback_exploring` | `blocked` | `done`- task: `{task_name}` - priority: `p0` | `p1` | `p2`- mode: `stepwise` | `race`

## 我需要你确认的问题（仅在 need_clarification）
1. xxxx2. xxxx

## 本轮产出

### 方案 / 变更
1. xxxx

### 证据
- `[已验证: path:line]` ...- `[已测试: cmd + output 摘要]` ...- `[用户确认]` ...

### 风险与回退
- 风险：...- 回退：...

## 需要用户裁定

> 给选项，不替你决定。规则：有推荐项、每项附说明+适用场景、末尾留自定义输入。

- A: {选项A} — 推荐 ✓
  - 说明：{做什么}
  - 适用场景：{什么时候选这个}
- B: {选项B}
  - 说明：{做什么}
  - 适用场景：{什么时候选这个}
- C: 自定义操作
  - → {输入你想要的操作}

## 下一步（可执行、可验收）
- [ ] ...

---

## State 转换规则
| 当前状态 | 允许转到 | 触发条件|
|---------|---------|---------|
|`need_clarification` | `ready` | 用户确认所有澄清问题|
|`ready` | `planning` | 任务非琐碎，进入规划|
|`ready` | `executing` | 任务琐碎（<3步，无架构决策）|
|`planning` | `spec_review` | Plan Gate 通过|
|`planning` | `need_clarification` | 发现缺失信息|
|`spec_review` | `executing` | Spec Gate 通过（技术方案 + 验收标准已锁定）|
|`spec_review` | `planning` | 方案需修改|
|`executing` | `done` | 所有 AC 通过，验收报告已生成|
|`executing` | `fallback_exploring` | 执行失败 ≥2 轮或用户要求探索|
|`executing` | `blocked` | 3 轮修复失败 + Fallback 耗尽 / 依赖缺失|
|`executing` | `need_clarification` | 发现方案偏差|
|`fallback_exploring` | `executing` | 用户确认新方案（轮次重置）|
|`blocked` | `executing` | 用户提供新约束（Half-Open 试探） |

## 证据层级
| 层级 | 类型 | 可信度|
|------|------|--------|
|L1 | **端到端功能验证**（实际使用场景中生效） | ✅ 强|
|L2 | 测试通过 + 输出匹配预期 | 中|
|L3 | 脚本执行成功 / 编译通过 | 弱|
|L4 | 格式/语法合法 | ❌ 不可单独作为证据 |
**只有 L1/L2 可支撑 "done" 结论。**

## 置信度标注
| 标注 | 含义 | 使用场景|
|------|------|---------|
|`[已验证: file:line]` | 从源码直接确认 | 代码引用、字段存在性|
|`[已测试: 命令+输出]` | 运行验证通过 | 接口行为、编译结果|
|`[推断, 待确认]` | 基于上下文推理但未直接验证 | 架构推断、行为假设|
|`[文档来源: URL/doc:line]` | 从文档确认 | 官方文档、项目文档 |
