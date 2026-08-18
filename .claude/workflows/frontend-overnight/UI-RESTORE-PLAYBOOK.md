# UI-RESTORE-PLAYBOOK — AI 自行 UI 还原实操手册

> 用途：让执行模型（含无人值守夜模型）**不依赖人类审美反馈**，仅凭原型与机器门禁完成
> 一比一静态&交互&二级弹窗 UI 还原。本文由 2026-08-18 xsimplechat chat-inbox 还原实测沉淀
> （证据：`.omc/tasks/20260818/xsimplechat-inbox-restore/`，视觉 diff 3.30% vs 上次同类任务 15.80%）。
> 本文是 night-loop.md 步 1/2 的配套手册；与 assertion-catalog.yaml、tokens 契约配套使用。

## 0. 核心闭环（每页必走，不许跳步）

```
捕获 → 分型 → 测量 → 实现 → 截图 → 像素diff → 修复 → 门禁 → 证据链
        └──────────────────── 迭代 ≤ fix_rounds ────────────────────┘
```

原则：
- **原型是唯一事实源**。DOM 文本（contents.json 类捕获）优先级 > 视觉 OCR；两者冲突时登记冲突。
- **像素 diff 是唯一验收尺**。禁止"看起来像"——以 `vision_pixel_diff` 数值收敛为准。
- **先测后写**。每个尺寸/间距来自测量，不拍脑袋；一处改动后必须重截图重 diff。

## 1. 捕获（S1，复用或新捕获）

| 资产 | 内容 | 获取方式 |
|---|---|---|
| contents.json | 页面全部 DOM 文本节点（x/y/字号/标签） | CDP `document.elementsFromPoint` 遍历 / DOM 序列化 |
| interactions/inventory.json | 可点击元素清单 + OVERLAY 发现（弹窗/下拉） | 逐元素 click + 监听 DOM 新增节点 |
| cdp-*-states.json | 元素四态矩阵（base/hover/active 色值） | CDP 强制状态采样 |
| gold/*.png | 目标页金样截图（1440x900 或 2x） | 视口截图 |

交互原型（interactive）必须：逐触发器扫描出全部 OVERLAY（inventory 里 kind=OVERLAY）；
静态原型（static）禁止伪装点击，浮层只认 PRD/标注/intake 登记。

## 2. 分型与测量（对应 night-loop 步 1）

1. **布局分型**：先问"几栏"（rail/侧栏/主区/面板），用 `vision_glance` 一次性拿到
   各区块 x/y 坐标与尺寸；再对关键锚点用 `vision_ground` 取精确像素框（误差 ±3px）。
2. **锚点表落地**：把锚点（顶栏按钮、标题、卡片行、输入区）的 x/y/w/h 写进 plan 或
   research.md——这是实现期的尺寸真值，禁止凭感觉写 CSS。
3. **交互态登记**：cdp-states 里的 base/hover/active 色值直接进 tokens/_colors.scss，
   组件样式只引用 token。
4. **overlay 清单**：触发器 → 浮层 → 关闭语义（modal=Esc+遮罩+×；click popover=外点+Esc+再点；
   tooltip=hover 显/leave 隐），写进 manifest overlay_contract（status 必须 declared）。

## 3. 实现（步 3–5）

- 骨架期（Phase 0）一次建好：tokens/、router 全量预注册、mock 层、assertions.ts 17 helper、
  playwright.config（1440x900）。**antd 等组件库用 ConfigProvider 主题收敛真实站色板**
  （本次：colorPrimary #0072f5 / colorText #222 / colorBgLayout #f8f8f8，CDP 实测值）。
- **复杂组件用组件库**（Modal/Dropdown/Tooltip 等），关闭语义免费获得；
  但弹窗类测试的"遮罩点击"必须点弹窗**外**的坐标（弹窗居中时点角落），否则点到弹窗本体。
- 禁止 `:global`、裸色值、魔法 px；间距走 8pt 网格；emoji 图标与真实站一致时直接用 emoji
  （视觉 diff 收益最大），渐变图形类图标用内联 SVG 近似。
- 布局坑位（实测踩过）：
  - `height:100%` 链：组件库包裹层（如 antd `<App>` 的 .ant-app）也要 100%，否则页面塌陷成内容高。
  - 顶栏常横跨"主区+右侧面板"，右面板标题在其下方——先看截图再定 DOM 结构。
  - 说明文字色用中灰（#666）而非浅灰（#999），浅灰在 1:1 对照里对比度不足。

## 4. 视觉验收闭环（步 6–11 之间穿插）

```bash
# 截图（等 mock 数据与弹窗动画稳定后再拍）
node .omc/scripts/shot-chat.mjs impl.png
# 与金样 diff（同尺寸金样优先；2x 金样会自动缩放）
vision_pixel_diff --original gold.png --rebuilt impl.png
```

- 迭代信号：`overallDifferencePct` 不降 → 用 `vision_glance` 并排对比"参考 vs 实现"，
  逐条列差异（位置/缺失/尺寸/文字），一次改一批再重拍。
- 热点定位：diff 的 worstRegions 坐标直接裁图（vision_crop）看局部。
- 收敛标准：无结构性差异（无缺失区块/无错位>8px），整体 diff 停留在文字抗锯齿/图标细节级
  （本次 3.30%；上次未用本手册 15.80%）。预算内优先把 worstRegions 逐块压到 <6%。
- **改完必须从门禁重跑**（tsc/eslint/stylelint/vitest/build/playwright 全绿才算数）。

## 5. 门禁链（步 6–12）

| 门禁 | 命令 | 通过标准 |
|---|---|---|
| C2 | `pnpm exec tsc --noEmit` + `eslint . --max-warnings 0` + `pnpm build` | 0 错误 |
| 样式 | `stylelint "src/**/*.scss"` | 0 错误（modern color notation，禁 darken 用 color.adjust） |
| 单测 | `pnpm exec vitest run` | 全绿（含 assertions 17/17 对齐 catalog 专项测试） |
| C4/C5 | `pnpm exec playwright test` | 全绿（交互矩阵 + 浮层关闭语义 + 焦点陷阱/归还） |
| C6 | vision_pixel_diff | worstRegions 收敛 + 无 console error |
| 证据链 | 截图 + evidence.json（diff 数值/门禁结果/覆盖清单） | 文件真实存在、非空 |

## 6. 预算参考（本次 dry-cost 实测，首夜 1 页）

| 项 | 实测 |
|---|---|
| 视觉调用（glance/ground/crop/diff） | ~30 次/页（含 7 轮迭代） |
| 修复轮次 | 7 轮（布局 3 轮 + 局部细节 4 轮） |
| e2e 全量 | 12 spec ≈ 24s |
| 全门禁一遍 | ≈ 1min（含 build） |
| 建议预算 | per_page_calls 80 / fix_rounds 8 / online_vision_calls 30 |

## 7. 禁止事项（违反 = 当夜作废）

- 不许用"看起来像"代替像素 diff；不许跳过门禁直接宣布 DONE。
- 不许手写 gate-results / 结论文件（finalize_page 重算）。
- 不许碰 tokens/shared/router 之外的公共面；夜间不许改 router。
- 视觉工具失败 ≠ DONE 的借口——记 BLOCKED_ENV，等环境恢复重跑。
