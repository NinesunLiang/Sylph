# 交互式参数引导 — 所有 skill 通用

> 当用户调用 skill 但未提供完整参数时，自动进入引导式问答。
> 本文件被所有 lx-* skill 引用。

## 触发条件

用户调用 skill 时：有参数 → 直接执行（向后兼容）；无参数 → 进入引导式问答

## 标准交互模式

所有交互统一使用以下模式（已验证通过）：

```
AskUserQuestion:
  header: "{分类标签}"
  question: "{问题描述}\n\n或直接在对话中输入你的想法"
  options:
    - label: "{推荐选项} — 推荐 ✓"
      description: "{一句话说明}"
      preview: "**说明**：{有什么效果}\n**适用场景**：{什么时候选这个}"
    - label: "{备选方案}"
      description: "{一句话说明}"
      preview: "**说明**：{有什么效果}\n**适用场景**：{什么时候选这个}"
    - label: "{第三方案}"
      description: "{一句话说明}"
  # Other 按钮自动提供自由输入框
  # 用户也可直接在对话中打字回复
```

**规则**：
1. 至少 3 个选项，首项标记 `— 推荐 ✓`
2. 每项 `description` = 说明（选了这个会怎样）
3. 推荐项和重要选项加 `preview` = 适用场景
4. 问题末尾提示"或直接输入你的想法"
5. Other 按钮 = 自定义输入入口（可键入任意内容）
6. 用户也可直接打字回复到对话中

## 通用 3 选项映射

| 角色 | scope gate 版 | skill 深度版 | 确认版 |
|------|---------------|-------------|--------|
| 选项1 推荐 ✓ | 加入 scope 并写入 | 全量+验证 | 确认执行 |
| 选项2 | 跳过此文件 | 深度分析 | 拒绝 |
| 选项3 | 取消整个操作 | 快速扫描 | 稍后再说 |
| Other | 任意输入 | 自定义参数 | 其他想法 |

## 场景：scope gate 阻断

当文件被 scope gate 拦截时，AI 不再让用户执行 echo >>，而是弹 AskUserQuestion：

```
Write 被拦 → AI 弹 AskUserQuestion
  → 允许     → AI 自动更新 scope → 继续写入
  → 跳过     → 放弃此文件
  → Other    → AI 按输入内容处理
```

## 场景：permission gate 阻断

当危险命令被 permission gate 拦截时，AI 不再让用户复制 token：

```
Bash 被拦 → AI 弹 AskUserQuestion
  → 批准    → AI 自动走 token 审批 → 重试命令
  → 拒绝    → 放弃命令
  → Other   → AI 按输入内容处理
```

## 场景：skill 参数收集

```
第 1 问：目标（AskUserQuestion）
  header: "{skill_name}"
  question: "问题 1/3：{目标提示}"
  options: [{示例}]  # Other 或对话输入

第 2 问：深度（AskUserQuestion）
  header: "执行深度"
  question: "问题 2/3：{深度提示}"
  options:
    - "全量+验证 — 推荐 ✓": "检测 + 自动修复 P0/P1 + re-scan"
    - "深度分析": "检测 + 自动修复 P0/P1"
    - "快速扫描": "仅检测，列出问题"
  # Other → 自定义参数

第 3 问：重点关注（AskUserQuestion，可选）
  header: "重点关注"
  question: "问题 3/3：有重点关注吗？"
  options: ["跳过"]  # Other → 输入关注类别
```

## 文本回退（AskUserQuestion 不可用时）

```
📋 {skill_name} 已启动。
问题 1/3：{目标提示}  示例：{示例1} {示例2}

问题 2/3：
1. 全量+验证 — 推荐 ✓
   说明：检测 + 自动修复 P0/P1 + re-scan
   适用：需要完整质量保证
2. 深度分析   说明：检测 + 自动修复 P0/P1
3. 快速扫描   说明：仅检测列出问题
4. 自定义参数 → 自行指定

问题 3/3：有重点关注？（直接回车跳过）
```

## 各 skill 引导配置

| Skill | Q1 目标提示 | Q2 选项 | Q3 示例 |
|-------|-----------|--------|--------|
| lx-code-review | 审查什么？ | 全量+验证 / 深度分析 / 快速扫描 | 并发安全 |
| lx-frontend-test | 测试什么？ | 单元 / E2E / 全量 | 表单交互 |
| lx-perf-analysis | 分析什么？ | CPU / 内存 / Goroutine / 全域 | 内存分配 |
| lx-rpe | 什么功能？ | 完整 RPE 流程 | — |
| lx-root-cause-analysis | 什么 bug？ | 5-Why / 完整免疫 | — |
| lx-oma-gov | 治理什么？ | reconcil / propagate / audit | 冲突 ID |
| lx-oma-hier | 拆解什么？ | 文件 / 目录路径 | 输出目录 |
| lx-oma-orch | 管线操作？ | status / advance / gate | — |
| lx-oma-split | 拆解什么？ | 路径 / —pipeline 模式 | sub_prd_id |
| lx-varlock | 操作什么？ | set / list / rm / run / read / write | 环境变量名 |
| lx-validate-skill | 校验哪个？ | 单 skill / 全部 | skill 名称 |
