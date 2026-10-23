# RPE Progress: {feature_name}

## 特性信息- 特性名：{feature_name}- 创建时间：{date}- 状态：Phase [1/2/3] / 主循环执行中 / 已完成

## Phase 1 — Research- 状态：pending- 迭代次数：0

## Phase 2 — Plan- 状态：pending- 迭代次数：0

## Phase 3 — Execute- 状态：pending- 当前 Task：-

## RPE 任务项（Phase 3 进入主循环时从 plan.md 提取）

## 当前进度### {date} 会话- 当前阶段：[Phase N / 主循环 Step N]- 当前任务项：RPE-xxx- 完成项：[列表]- 阻塞项：[列表]- 下一步：[描述]

## Tech-Debt List（开发过程中发现但不立即处理的技术债务）

## 已完成任务项（从 RPE 任务项移入）

```

### 恢复流程（默认行为）

```1
. 搜索 RPE 实例目录： ls rpe/
2. 若多个特性 → 列出供用户选择 若指定名称 → 直接加载 rpe/{feature_name}/ 若仅一个 → 自动加载
3. readFile rpe/{feature_name}/state/progress.md → 提取： - 当前阶段（Phase 1/2/3 / 主循环） - 当前步骤编号（主循环时） - 当前任务项 ID - 上次会话的"下一步" - 阻塞项
4. 上下文完整性校验（防止 progress.md 与实际文件状态不一致）： ├─ Phase 2+ 但 research.md 仍为空骨架 → 警告，回退到 Phase 1 ├─ Phase 3 但 plan.md 仍为空骨架 → 警告，回退到 Phase 2 ├─ 主循环但 RPE 任务项区为空 → 警告，回退到 Phase 3 入口 └─ 文件缺失（research/plan/executor.md 被删除）→ 从模板重建 + 警告用户
5. 判断恢复入口： ├─ Phase 1 未完成 → 恢复 Research 迭代循环 ├─ Phase 2 未完成 → 恢复 Plan 迭代循环 ├─ Phase 3 / 主循环 → 恢复对应主循环步骤 └─ Gate-X 暂停中 → 恢复 Plan 二次批准
6. 输出恢复摘要： 📂 已恢复：{feature_name} 📍 当前阶段：[Phase N / 主循环 Step N] 📋 当前任务：RPE-xxx {描述}（主循环时） 📝 上次记录的下一步：{内容} ⚠️ 阻塞项：{列表或"无"}
7. → 进入对应阶段/步骤

```
**完成标准**：- ✅ 进度文件已加载（引用 readFile 输出）- ✅ 恢复摘要已输出- ✅ 上下文已重建（当前阶段 + 步骤 + 任务项 + 阻塞项）- ✅ 恢复入口正确（Phase 1/2/3 或主循环步骤）
---
