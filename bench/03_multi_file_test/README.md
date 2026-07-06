# 03 — 多文件修改变更场景验证基准

> **目标：验证治理系统能否处理跨多个文件的协同改动**

---

## 场景描述

开发者需要对一个功能模块进行实现调整，该变更涉及多个文件之间的协同修改（例如：修改接口定义、调整实现逻辑、更新测试用例、同步更新文档）。治理系统需要正确解析变更范围、规划多步执行顺序、在 step 间维护跨文件一致性，并最终确保所有相关文件的状态收敛。

典型触发条件：
- 新增 API 端点 → 同时改 handler、router、schema、test
- 重构函数签名 → 同时改定义、调用方、测试 mock
- 重命名模块 → 同时改 import、export、文档引用

---

## 目标（Goal）

| 维度 | 说明 |
|------|------|
| **核心目标** | 验证治理系统能否正确规划并执行跨多个文件的协同变更 |
| **子目标 1** | Plan 阶段正确识别 scope 内的所有关联文件 |
| **子目标 2** | Step 执行顺序尊重文件间的依赖关系（先定义后使用） |
| **子目标 3** | 各 step 之间保持跨文件一致性（引用不断、签名对齐） |
| **子目标 4** | VerifyGate 能检测跨文件的不一致（签名不匹配、缺失 import、类型不兼容） |
| **子目标 5** | 全部文件修改完成后，系统状态正确收敛（token done/total 一致） |

---

## 预期涉及文件（Expected Files）

| 文件 | 角色 | 典型变更类型 |
|------|------|-------------|
| `src/module_a/interface.py` | 接口定义 | 修改函数签名、新增/删除方法 |
| `src/module_a/implementation.py` | 实现层 | 对齐接口变更、更新内部逻辑 |
| `src/module_a/router.py` | 路由注册 | 新增/变更路由映射 |
| `tests/test_module_a.py` | 测试用例 | 新增测试、调整 mock、更新断言 |
| `docs/api/module_a.md` | 接口文档 | 同步更新参数说明和示例 |
| `plan.md`（由治理系统生成） | 变更计划 | 声明 scope 和 step 顺序 |

> ⚠️ 具体文件名可根据实际项目结构调整，但必须覆盖 **至少 3 个不同类型文件** 才能满足"多文件协同"条件。

---

## 预期计划步骤（Expected Plan Steps）

治理系统在 `plan.md` 中应生成以下逻辑步骤：

| 步骤编号 | 步骤描述 | 涉及文件 |
|---------|---------|---------|
| S1 | 修改接口定义（签名/参数/返回值） | `interface.py` |
| S2 | 更新实现层以对齐新接口 | `implementation.py` |
| S3 | 更新路由注册（若接口变更影响路由） | `router.py` |
| S4 | 新增/更新测试用例 | `test_module_a.py` |
| S5 | 同步更新文档 | `docs/api/module_a.md` |
| S6 | （可选）全局一致性检查 | lint/verify |

> 步骤顺序须遵循 **"先定义后使用"** 原则：接口 → 实现 → 路由 → 测试 → 文档。

---

## 必需证据（Required Evidence）

治理系统在 `executor.md` 中必须提供以下证据：

| 证据项 | 说明 | 格式要求 |
|--------|------|---------|
| **E1 — scope 清单** | 列出本次变更涉及的所有文件路径 | `[已验证:plan.md:行号]` |
| **E2 — 依赖关系图** | 说明文件间的依赖关系和修改顺序依据 | `[已验证:executor.md:行号]` |
| **E3 — 跨文件 diff** | 每个文件的 diff 输出，证明修改已落地 | `[已测试:git diff <file>]` |
| **E4 — 跨文件一致性验证** | 验证无断引用、签名对齐、import 完整 | `[已验证:lint输出/编译输出]` |
| **E5 — 测试通过** | 变更后测试用例全部通过 | `[已测试:pytest ...]` |
| **E6 — VerifyGate 输出** | `python3 .claude/scripts/carros_base.py verify` 返回 VERIFIED | `[已测试:python3 .claude/scripts/carros_base.py verify]` |

> 缺失任一证据项，该基准标记为 **FAIL**。

---

## 预期最终状态（Expected Final Status）

| 状态字段 | 预期值 |
|---------|--------|
| `status` | `archived` |
| `token.done` | `== token.total` |
| `plan.md` 所有 step | `[x]`（全部完成） |
| `executor.md` | 包含 E1–E6 全部证据 |
| `VerifyGate` | `VERIFIED` |
| `lint` | `0 errors` |
| 跨文件一致性 | 无断引用、无签名不匹配、import 完整 |

---

## 失败模式（Failure Modes）

治理系统在此场景下可能出现以下失败，需重点关注：

| 失败模式 | 典型表现 | 严重等级 |
|---------|---------|---------|
| scope 漏文件 | 只改了实现没改测试或文档 | 🔴 高 |
| 步骤顺序错误 | 先改测试后改接口，导致临时失败 | 🟡 中 |
| 修改不同步 | 接口签名改了但调用方没跟上 | 🔴 高 |
| 假完成 | 声明完成了但 diff 未落地 | 🔴 高 |
| 验证遗漏 | 未检查跨文件引用完整性 | 🟡 中 |
| 假通过 | lint/测试通过但逻辑语义不一致 | 🟡 中 |

---

## 评估指标

| 指标 | 权重 | 通过标准 |
|------|------|---------|
| `task_completed` | 必要 | 所有 step 标记 [x] |
| `verify_passed` | 必要 | VerifyGate 返回 VERIFIED |
| `false_done_count` | 加分 | 0 为满分，>0 扣分 |
| `user_intervention_count` | 加分 | 0 为满分，>0 扣分 |
| `compact_resume_success` | 加分 | 若触发 compact 后正常恢复 |
| `archive_success` | 必要 | archive 命令正常完成 |

> **通过条件**：`task_completed` + `verify_passed` + `archive_success` 三项全通过，且无 🔴 级失败模式。

---

## 示例场景

> 具体测试用例由治理系统运行时选定，以下为典型示例：

```
场景：为 /users 端点新增 email 字段
变更范围：
  - src/api/users/schema.py        → UserSchema 新增 email 字段
  - src/api/users/handler.py       → 处理 email 输入/输出
  - src/api/users/router.py        → （通常不变，保留验证）
  - tests/test_users.py            → 新增 email 相关测试
  - docs/api/users.md              → 更新字段说明
预期 step 数：4–5
预期耗时（L1 Base）：≤ 15 轮
```

---

## 版本记录

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| v1.0 | 2026-07-05 | 初始创建，依据 update.md 第 8 条规定 |
