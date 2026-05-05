## 里程碑节点（若干任务项完成后）

**触发条件**：累计完成 ≥3 个 RPE 任务项 或 用户主动要求。
**Claude Code 端**：

```
1. 清理 tech-debt list： readFile rpe/{feature_name}/state/progress.md Tech-Debt List ├─ 每项评估： │ · 简单小修 → 记入 tech-debt list（待特性完成后处理） │ · 中等复杂（>3文件或需 AC 驱动）→ /lx-task-spec 创建独立任务 │ （buglist 中的问题是修复/改进性质，不升级到 RPE） └─ 清理完成 → 更新 state/progress.md
2. 代码全局健康检查： /lx-pre-commit（全量文件，非增量）
```
**OpenCode 端**：

```
1. 全量 Auto-test-and-fix
2. RPE 整体状态审视与演化
3. → 产出 buglist 传递给 Claude Code
1. 全量 Auto-test-and-fix
2. RPE 整体状态审视与演化
3. → 产出 buglist 传递给 Claude Code

```
**Buglist 处理**：

```
接收 buglist → 逐项分拣：├─ 小修（≤3文件，简单） → 记入 tech-debt list└─ 中等复杂（>3文件 或需 AC 驱动）→ /lx-task-spec
buglist 中的问题本质是修复/改进。RPE 是从业务 PRD 出发的新特性，不是任务大小的升级目标。
```
