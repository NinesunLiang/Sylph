# UI-RESTORE-PLAYBOOK — AI 自行 UI 还原实操手册

> 用途：让执行模型（含无人值守夜模型）**不依赖人类审美反馈**，仅凭原型与机器门禁完成
> 一比一静态&交互&二级弹窗 UI 还原。本文由 2026-08-18 xsimplechat chat-inbox 还原实测沉淀
> （证据：`.omc/tasks/20260818/xsimplechat-inbox-restore/`，视觉 diff 3.30% vs 上次同类任务 15.80%）。
> 本文是 night-loop.md 步 1/2 的配套手册；与 assertion-catalog.yaml、tokens 契约配套使用。
> **参考实现**：`.omc/archive/20260818_xsimplechat-inbox-restore/`（本次交付证据链：截图/diff 数值/executor）
> 与 `.omc/archive/20260818_xsimplechat-perfect-v2/`（静态 1.45% + 交互 17 e2e）。应用源码按用户要求
> 已从仓库移除；下次任务按本文 §0-§5 重建骨架（tokens/antd 主题收敛/断言写法见各节）。

## 0. 核心闭环（每页必走，不许跳步）

```
捕获 → 分型 → 测量 → 实现 → 截图 → 像素diff → 修复 → 门禁 → 证据链
        └──────────────────── 迭代 ≤ fix_rounds ────────────────────┘
```

原则：
- **原型是唯一事实源**。DOM 文本（contents.json 类捕获）优先级 > 视觉 OCR；两者冲突时登记冲突。
- **像素 diff 是唯一验收尺**。禁止"看起来像"——以 `vision_pixel_diff` 数值收敛为准。
- **先测后写**。每个尺寸/间距来自测量，不拍脑袋；一处改动后必须重截图重 diff。

## 0.5 两条工具路径（先选后干）

| 路径 | 工具 | 适用 | 备注 |
|---|---|---|---|
| A：视觉工具链（推荐，本次实测） | `vision_glance`/`vision_ground`/`vision_crop`/`vision_pixel_diff` | 任何环境，无需 task.json | 锚点±3px、diff 数值收敛，见 §2/§4 |
| B：ui-restore 脚本链（历史沉淀） | `scripts/ui-restore/{capture-*,measure,region-compare}.mjs` | 本地有 Chrome + task.json 配置 | 多断点/区域裁图自动化；配置走 task-config.mjs |
| 截图（两条路径共用） | `node .claude/workflows/frontend-overnight/scripts/ui-restore/shot-page.mjs <url> <out.png> [--wait 800] [--console]` | 标准截图入口 | `--console` 顺带做 C6 无 console error 检查 |

选 A 还是 B：有视觉工具直接 A（本轮 3.30% 就是这么拿的）；环境只有本地浏览器脚本就走 B。
两条路径的产物（金样/测量表/diff 数值）格式一致，验收标准相同。

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

### 锚点表模板（§2.2 落地格式，直接复制进 research.md）

```markdown
## 锚点表（真实站 1440x900 实测）
| 区块 | 元素 | x1,y1 | x2,y2 | w×h | 备注 |
|---|---|---|---|---|---|
| rail | logo 圆 | 16,19 | 47,50 | 32×32 | 橙红底白 X |
| rail | 选中图标块 | 10,72 | 53,116 | 44×44 | bg #f0f0f0 |
| 左栏 | 当前助手卡 | 72,130 | 376,200 | 304×70 | bg #f0f0f0 |
| 顶栏 | 联系客服 | 1115,8 | 1220,40 | 105×32 | 紫粉渐变 |
| 中央 | 晚上好 | 748,71 | ~ | 32px | 粗体黑 |
| 中央 | 卡片行1 | 400,220 | 1143,331 | 368×110 | 2 列 gap 8 |
| 右面板 | 话题标题 | 1176,74 | ~ | 16px | 面板下无顶栏覆盖 |
| 输入区 | 发送按钮 | 1043,848 | 1134,884 | 91×36 | 黑底白字+下拉 |
```

写 CSS 时逐条对照此表；任何「感觉差不多」都是 bug 前兆。

## 3. 实现（步 3–5）

- 骨架期（Phase 0）一次建好：tokens/、router 全量预注册、mock 层、assertions.ts 17 helper、
  playwright.config（1440x900）。**antd 等组件库用 ConfigProvider 主题收敛真实站色板**
  （本次：colorPrimary #0072f5 / colorText #222 / colorBgLayout #f8f8f8，CDP 实测值）。
- **复杂组件用组件库**（Modal/Drawer/Dropdown/Popover/Tooltip/Table/Tree/Select/DatePicker 等，
  C3 白名单），关闭语义免费获得；简单视觉组件（Button/Input/Card 等）**手写**，像素还原须完全掌控；
  antd 统一 `import { X } from 'antd'` 主入口具名导入（禁 `@ant-design/icons`，图标走 emoji/内联 SVG），
  主题用 ConfigProvider 收敛真实站色板。
  但弹窗类测试的"遮罩点击"必须点弹窗**外**的坐标（弹窗居中时点角落），否则点到弹窗本体。
- 禁止 `:global`、裸色值、魔法 px；间距走 8pt 网格；emoji 图标与真实站一致时直接用 emoji
  （视觉 diff 收益最大），渐变图形类图标用内联 SVG 近似。
- 布局坑位（实测踩过）：
  - `height:100%` 链：组件库包裹层（如 antd `<App>` 的 .ant-app）也要 100%，否则页面塌陷成内容高。
  - 顶栏常横跨"主区+右侧面板"，右面板标题在其下方——先看截图再定 DOM 结构。
  - 说明文字色用中灰（#666）而非浅灰（#999），浅灰在 1:1 对照里对比度不足。

## 4. 视觉验收闭环（步 6–11 之间穿插）

```bash
# 截图（等 mock 数据与弹窗动画稳定后再拍；--console 顺带查 console error）
node .claude/workflows/frontend-overnight/scripts/ui-restore/shot-page.mjs \
  http://localhost:5173/chat?session=inbox .omc/artifacts/impl.png --wait 800 --console
# 与金样 diff（同尺寸金样优先；2x 金样会自动缩放）
vision_pixel_diff --original gold.png --rebuilt impl.png
```

- 迭代信号：`overallDifferencePct` 不降 → 用 `vision_glance` 并排对比"参考 vs 实现"，
  逐条列差异（位置/缺失/尺寸/文字），一次改一批再重拍。
- 热点定位：diff 的 worstRegions 坐标直接裁图（vision_crop）看局部。
- 收敛标准：无结构性差异（无缺失区块/无错位>8px），整体 diff 停留在文字抗锯齿/图标细节级
  （本次 3.30%；上次未用本手册 15.80%）。预算内优先把 worstRegions 逐块压到 <6%。
- **改完必须从门禁重跑**（tsc/eslint/stylelint/vitest/build/playwright 全绿才算数）。

### diff 迭代决策树（diff 不降时的标准动作，不许原地重试）

```
overallDifferencePct 没降？
├─ 先看 worstRegions 坐标分布
│   ├─ 集中在文字区 → 文字色/字号/行高/字重问题（对照锚点表与 tokens）
│   ├─ 集中在图标区 → 图标资源不一致（emoji vs 自定义 SVG；渐变图形用内联 SVG）
│   ├─ 集中在区块边界 → 该区块 x/y/w/h 与锚点表不符 → 改 CSS 尺寸
│   └─ 全页均匀 → 主题色/背景/字体家族级差异 → 查 ConfigProvider token 与全局样式
├─ 找不到原因 → vision_crop 裁 worst 区域（scale 2-4）放大看局部
├─ 再看不清 → vision_glance 并排对比同区域裁剪图，列差异清单
└─ 一次改一批（≥3 处）再重截图重 diff；单点微调轮次 ≤ 2，避免空转
```

### 差异归因表（实测踩坑映射，直接查表）

| 现象 | 根因 | 修法 |
|---|---|---|
| 整页内容只占上半屏、下面空白 | `height:100%` 链断裂（组件库包裹层没撑满） | `#root > .ant-app { height:100% }` |
| 弹窗点遮罩关不掉 | 测试点击坐标点在弹窗本体上 | 点弹窗外的角落（如 80,120） |
| 说明文字对比度不足 | 用了 #999 浅灰 | 改 #666 |
| 顶栏按钮整体左移/右移 | 图标按钮 32px+gap8 比真实站 30px+gap6 宽 | 按锚点表调 iconBtn 尺寸与 gap |
| 标题"发灰" | 用了 #222 但真实站近纯黑 | 大标题用 #000 |
| 助手卡图标不一致 | 渐变图形被 emoji 替代/或相反 | 真实站是渐变图形→内联 SVG；是 emoji→直接用 emoji |
| diff 数值完全不动 | 改动没生效（HMR 失败/sass 报错 500） | 查 dev server 日志，先修编译错误 |
| 卡片/区块整体下移 N px | 上一区块 margin/padding 链偏差 | 从锚点表倒推每个间距，逐级对齐 |
| 整页大片白 vs 参考浅灰 | 背景色判断错误（只测了一个区域） | **全区域 dominant_colors 采样**（参考站常是"左栏白+主体 f8f8f8"混合） |
| emoji 图标细节对不上 | 平台 emoji（Apple）vs 站点 Twemoji | 观察特征（👋 蓝线/🕵️ 深蓝帽），下载 twemoji SVG 到 public/emoji |
| logo 手画不像 | 站点用内置组件（如 LobeChat 白标） | `vision_extract_foreground` 从金样直接提取 PNG |
| 图标整体垂直居中偏移 | flex 容器 align-items 默认 stretch | 图标容器设 align-items: flex-start |
| store 更新后 UI 不动 / NaN | zustand action 收到函数（签名是数值）；拖拽增量闭包旧值 | action 只收数值；拖拽在 mouseup 一次性提交总位移 |
| 弹窗遮罩挡住后续交互 | 自动弹窗未关就继续测试 | 测试先等弹窗出现再 Esc |

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

## 6.5 能力基线（下次任务对照用——进步/退步一目了然）

| 指标 | 2026-08-18 静态冲刺（本手册 v2） | 2026-08-18 首轮（本手册 v1） | 2026-08-16 上次（未用本手册） |
|---|---|---|---|
| 静态视觉 diff（vs 真实站原图） | **1.45%** | 3.30% | 15.80% |
| 浮层关闭语义 | 16/16 e2e（含拖拽/弹窗/下拉） | 12/12 e2e | 9/9 e2e |
| 侧栏交互 | 拖拽调宽+开闭+持久化 | 仅开闭 | 无 |
| 门禁 | 全绿 | 全绿 | 全绿 |
| 迭代方式 | 像素采样驱动（dominant_colors 取色/ground 锚点/diff 收敛） | 锚点测量→批量修 | 视觉对照主观修 |

下次任何还原任务收尾时，把当次 diff 数值填进此表对比；
**超过 1.45% 说明有步骤没按手册走，回查决策树与归因表。**

## 7. 禁止事项（违反 = 当夜作废）

- 不许用"看起来像"代替像素 diff；不许跳过门禁直接宣布 DONE。
- 不许手写 gate-results / 结论文件（finalize_page 重算）。
- 不许碰 tokens/shared/router 之外的公共面；夜间不许改 router。
- 视觉工具失败 ≠ DONE 的借口——记 BLOCKED_ENV，等环境恢复重跑。
