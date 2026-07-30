# Grok 视角 · 第 1/5  
## 总诊断、目标闭环与「为何 80%→90% 仍要人」

> 身份与立场说明（集成到方案语境，不单跳出）：  
> 作为前端干净架构执念者（Ant Design / React / Tailwind / Vite）+ 无人化 UI 方向实践者，我会在 **GPT 的“工具+反馈闭环”** 与 **Opus 的“约束+五维评分+防作弊”** 之上，补第三轴：  
> **Token-first 设计系统 + Goal 长航时编排 + 交互完备矩阵 + 模型分级预算**。  
> 目标不是“更像再截一张图”，而是 **99% 可验收、可审计、可持续跑 ≥6 小时、 thrashing 退出后可人工只审关键路径**。

---

## 0. 三方定位（Grok 的融合点）

| 轴 | GPT 强项 | Opus 强项 | **Grok 必须补齐的缺口** |
|---|---|---|---|
| 状态采集 | BFS 链接 | 路由+交互矩阵+漂移检测 | **交互完备性验收清单（对齐 `UI_README`）**、多模块页面关系图 |
| 评分 | SSIM 主打 | 五维 IoU/ΔE/Style | **Token 对齐维 + 交互维**，SSIM 只做辅助提示 |
| 修复 | 通用反馈改 | 硬约束防 hardcode | **Token 注入优先于样式修补**；无 Token 不许进 Element 精修 |
| 循环 | 短迭代 | 分阶段 + 作弊检测 | **Goal 模式：连续逼近直到 99% 或预算耗尽；不中途“软退出”** |
| 工程 | 偏脚本拼装 | 约束/验证层完整 | **可信号量的长航时调度、双模型路由、成本护栏、一键回滚** |

**Grok 一句话纠偏：**  
> 未建 Token 系统就谈 99% 像素还原，等于让 Worker 在无限 hardcode 空间里做梯度下降——分数能冲到 90%，但风格一致性、响应式、AntD 主题会系统性崩，必须人工一次次补。

这就是你看到的「80%→90% 十几次人工推动」的根因，不是模型不够聪明，是 **目标函数与搜索空间错了**。

---

## 1. 你当前系统为何“跑一阵就退出”

从现象反推机制（不必先改代码，先改目标定义）：

```text
当前隐含目标：  for N rounds or for T minutes | score ↑
退出条件：       时间到 / 分数停滞 / 单次失败 / 人工介入提示
失败模式：
  A. 局部像素优化（改 padding 数字）掩盖全局结构
  B. 交互态未进评估 → 菜单/侧边/浮层永远 0 覆盖
  C. 无 Token 约束 → 每轮最优解是 hardcode 最近邻
  D. 无层级门禁 → Element 未稳就开始 polish， Gyna 震荡
  E. 无预算内重入 → 停下后必须人推下一站
```

**目标目标应改写为：**

```text
Goal = maximize Fidelity
                     subject to:
   FormalTokenCoverage ≥ τ_token
   InteractionCoverage  ≥ τ_ix
   HierarchyGate(Shell→Region→Element) all green
   CheatScore < ε
   Cost ≤ Budget
   WallClock ≤ 6h（可配置，默认 ≥6h 可持续）
直到：
   Composite 99% 且全部门禁绿
或：
   预算耗尽 / 可解释停滞 / 必须人工决策的 token 缺口
```

「跑完就退」在 Goal 模式下违法：只能是 **达标 / 可解释停滞 / 预算熔断**，后两者写入审计并生成「下一轮人工最小决策包」，而不是让你手当循环器。

---

## 2. 必须先承认：99% 是复合目标，不是 SSIM 99

Grok 定义 **UIF-99（UI Fidelity 99）**：

| 子目标 | 权重建议 | 通过线（可调） | 测法 |
|---|---|---|---|
| **S1 结构/布局** | 0.22 | ≥0.99 | 区域树拓扑 + 主轴 IoU + 关键 gutter |
| **S2 Token 对齐** | 0.20 | ≥0.98 | 颜色/间距/圆角/字号落在 Token 集合命中率 |
| **S3 静态视觉** | 0.18 | ≥0.985 | 五维（继承 Opus）+ 区域级 mask |
| **S4 交互完备** | 0.25 | **100% 清单项** | 对齐 `UI_README`：滚动、悬停菜单、点击浮层、侧边展开收起、多模块 |
| **S5 工程健康** | 0.15 | 硬门 | 无硬编码违规 / 构建通过 / 无 :global 乱盖 AntD |

> **硬规则：** S4 或 S5 未绿 → 总分再高也不算 99%。  
> 否则系统会“学会”用截图分冒充“完成”。

这同时解释了要求 4：完整滚动、悬停、弹层、sidebar 等——**不是采集锦上添花，是验收硬门槛**。

---

## 3. 科学遍历顺序（你第 2 点）— 门禁式层级，而不是并行乱修

GPT 像“哪里差修哪里”；Opus 有 phase，但仍可能过早深入。

**Grok 强制 Hierarchical Gate（不可跳级）：**

```text
L0  Bootstrap Token
    从你给的原型截图+可选 DOM 探针，产出 design tokens
    注入 Tailwind theme + CSS variables + AntD ConfigProvider
    Gate: Token 覆盖率 ≥ 阈值，且禁止 raw 色/间距默认开启

L1  Shell / App Frame
    顶栏 / 侧栏 / 内容壳 / 路由出口布局
    含 sidebar 展开·收起 作为 shell 态，而非装饰
    Gate: shell multi-state score ≥ 0.95

L2  Page Layout
    栅格、主从分栏、模块骨架、sticky、滚动容器归属
    Gate: 主 content 区域 IoU + layout style 达标

L3  Region Traverse（DFS/优先级队列）
    你文档里的静态模块截图 = Gold Region Map
    按视觉重量 + 业务关键度排序
    Gate: 区域合成分 ≥ 阈值才允许进入下一 region 的 element

L4  Element / Component
    Button / Form / Table / Card / MenuItem…
    强制走现有 AntD + 项目组件，禁止平行再实现一套
    Gate: element 五维 + token hit

L5  Interaction Closure
    对每个已声明交互态：scroll-end / hover / active / open / collapsed
    必须截图 +（可选）DOM assertion
    Gate: InteractionCoverage = 1.0

L6  Polish & Cross-page Consistency
    跨模块 Token 复用审计、遗漏态补齐
    Gate: UIF-99
```

**核心纪律：**  
没有 L0 Token Gate → **禁止** L4 Element 精修。  
没有 L1 Shell multi-state → **禁止** L3 区域深修。  
没有 L5 交互门 → **禁止** 宣称 99%。

这直接打掉「静态 80→90 狂改 padding 却不碰侧边栏悬停」的路径。

---

## 4. 长航时 Goal 模式应然形态（要求 4）

### 4.1 外环：Goal Runner（≥6h 默认）

```text
while wall_clock < budget and not goal_reached:
  if gate(L0) failed → token bootstrap / migrate jobs
  elif gate(L1) failed → shell/sidebar multi-state repair
  elif next region unpaid → region loop
  elif interaction hole → interaction jobs only
  elif polish needed → micro polish with stricter constraints
  else → goal_reached

  on stagnation(window=K):
      escalate model (flash → kimi vision) once
      if still stagnate → freeze branch; emit HumanMiniPack
      continue other branches (不整进程退出)

  every tick:
      persist checkpoint
      budget accounting
      cheat/thrash detector（继承 Opus 并加强）
```

### 4.2 内环：单 Target 迭代（Opus 五维 + 我加的 Token/交互维）

```text
score → evidence → constrained patch (deepseek-flash 默认)
→ 4 层 validate（约束/lint/type/build）
→ re-score → accept/reject
拒绝 hardcode 涨分；Token hit 上涨才算“真进步”
```

### 4.3 退出条件（只允许这三类）

1. **GoalMet**：UIF-99 全门绿  
2. **BudgetExhausted**：时间/API 预算耗尽，写出 checkpoint + 复跑指令  
3. **HumanDecisionRequired**：仅当“必须新增 Token 语义名称 / 原型自相矛盾 / 缺权限”  
   → 输出 **最小决策包**（3 个问题以内），不是“停掉让你随便点”

**禁止：** 静默 exit、因单次 patch 失败 exit、因“好像差不多了” exit。

---

## 5. Token 系统不是附属品，是第一公民（要求 3 的预告）

本部分只定 **原则**；第 2/5 会给出可落地目录与迁移流水线。

**Grok 原则：**

1. **原型值 → Candidate Token → 确认语义 → 写入 token 文件 → Tailwind / AntD / CSS vars 三端同源**  
2. Worker **不得** 直接写 `#F5F7FA` / `12px`（Opus 已禁）；并加一条更严：  
   **若无匹配 Token，任务必须升级为 “ProposeToken” job，而不是 patch 样式。**  
3. 静态截图里的色块与间距，优先做 **区域聚类提取**，再人工可选复核语义命名；无人化阶段允许 “proto-spacing-12” 临时名，跑完 Polish 再语义化。  
4. Tailwind 初始化：`theme.extend` 从 tokens 生成，避免两套真相。  
5. Ant Design 5：`ConfigProvider theme.token / components` 从同一源生成，禁止 `.ant-*` 散装覆盖（与 Opus `antd_override` 禁令对齐）。

没有这一层，99% 在工程上 **不可维护**，也 **不可跨页一致**。

---

## 6. 交互完备 & `UI_README`（要求 4 的预告）

用户明确列出：滚到底、悬浮菜单、点击浮窗、侧边收缩展开、多模块页等。

Grok 把这些升为 **Interaction Coverage Matrix（交互覆盖矩阵）**：

| 能力 | 原型/文档要求 | 采集 | 评分 | 修复优先级 |
|---|---|---|---|---|
| 全高滚动到底 + 懒加载 | 必须 | 分段/锚点截图 | region+footer visible | L2/L3 |
| Sidebar expand/collapse | 必须 | multi-state | shell gate | **L1 硬门** |
| Hover 浮出菜单 | 必须 | hover 触发 + 等动画 | 菜单几何+层叠 | L4/L5 |
| Click 浮层/Modal/Popover | 必须 | click + portal 检测 | 对焦层截图 | L5 |
| 多模块同页 | 必须 | 模块锚点 map | 模块粒度 score | L3 队列 |
| 路由多页 | 若 README 要求 | 路由枚举 | 页级 goal | 页级外环 |

**GPT 漏了专项交互；Opus 有侧栏与状态发现，但仍缺「README 强制清单 → 覆盖率 100% 才结案」。**  
Grok 补这一刀。

---

## 7. 模型路由（你给的 deepseek-v4-flash + kimi k3）

| 任务 | 默认模型 | 何时升 kimi k3 | 理由 |
|---|---|---|---|
| Token 提案 / 批量代码补丁 / SCSS 迁移 | **deepseek-v4-flash** | 少用 | 量大便宜，适合 6h 千次小步 |
| 常规五维叙事诊断 | flash + 规则引擎 | Δ 冲突、分数异常 | 文本够用 |
| **视觉裁决**（遮挡、半透明、字体渲染争议、复杂浮层） | — | **kimi k3** | 贵，只打关键帧 |
| 交互态“是否真打开”争议 | DOM 断言优先 | 视觉二次确认 | 不浪费视觉费 |
| 跨页一致性评审 | flash 聚合 | 抽检 | 抽 5% 关键屏 |

预算护栏示例：  
- 6h run 里 kimi 调用 **硬顶 N 次**（如 40～80）  
- 每次必须附带 `why_escalated`  
- 日常 95%+ 调用走 flash  

---

## 8. 相对 Opus/GPT，本方案五轮交付地图

| 分册 | 内容 | 解决你的哪条 |
|---|---|---|
| **1/5（本册）** | Goal 闭环、层级门禁、99 复合定义、失败根因 | ① 长循环 ② 科学顺序 |
| **2/5** | Token 体系：提取→命名→Tailwind/AntD 同源→迁移与禁止 raw | ③ Token |
| **3/5** | 评分升级：Token 维 + 交互维 + 区域 mask + 自适应阈值 | ①②③ 落地到判据 |
| **4/5** | Worker/约束/防作弊再加固：ProposeToken 分流、补丁契约 | 防 80–90 假进度 |
| **5/5** | 6h+ Goal 编排、检查点、成本、审计、UI_README 执行清单、**就绪检查表再许执行** | ④⑤ 完整就绪 |

**关键态度：**  
你要求「完整度很高、线上反复迭代后才执行」。因此：  
- 第 1～5 为 **方案就绪包**  
- **第 5 末附 “Go / No-Go 清单”**，缺任一项不启动 6h 实跑  
- 实跑前需要你提供：原型地址、模块金标截图文档、`UI_README` 路径确认、模型 API 接入约定

---

## 9. 第 1/5 结论（可执行原则，已足够指导后续四册）

1. **目标函数改写**：从“跑一会儿涨分”→ **UIF-99 Goal**（结构+Token+视觉+交互+工程）。  
2. **遍历改写**：L0 Token → L1 Shell → L2 Layout → L3 Region → L4 Element → L5 Interaction → L6 Polish；**门禁不可跳**。  
3. **退出改写**：只允许达标 / 预算尽 / 最小人类决策；禁止静默停。  
4. **Token 先行**：这是你列的第 3 点，也是打掉人工十几次推的总开关。  
5. **交互是验收不是附属**：对齐 `UI_README`，覆盖率不满 **不许结案**。  
6. **在 GPT 工具闭环 + Opus 约束评分上**，Grok 增加第三轴：**设计系统真实性 + 长航时 Goal 调度 + 双模型成本纪律**。

---

**下一册（第 2/5）预告：**  
完整 Token 系统蓝图——从你提供的静态模块截图与原型中 **自动提取色/间距/圆角/字号集合**，初始化 Tailwind + CSS variables + AntD theme，定义 `ProposeToken` job、迁移脚本目录规范，以及「无 Token 不进入 Element 精修」的工程闸门实现草案。

若你希望第 2 册优先贴合现有仓库路径（例如是否已有 `src/styles/tokens` / Tailwind config / AntD ConfigProvider），可指出目录约定；否则我将按 **Vite + React + AntD5 + Tailwind + CSS Modules** 的干净规范给出默认可落盘结构。

# Grok 视角 · 第 2/5  
## Token 第一公民：从零初始化 → Tailwind / AntD 同源 → 门禁与夜跑边界

> **承接第 1/5**：没有 L0 Token Gate，Element 精修全是假进步（80%→90% 靠 hardcode）。  
> **本册目标**：给出可落盘的 Token 体系——**可从空仓库冷启动**，与你现有 **CarrorOS / night-loop / Phase0 / UI_README** 对齐，并写清「白天建 Token、夜间可引用不可乱改」的边界。  
> **输入假设（rewrite）**：项目**从零开始**；你提供原型地址 + 各模块金标静态截图文档。

---

## 0. 与现有控制面的对齐（避免再发明一套平行宇宙）

从你们体系里必须继承的铁律（与本册直接相关）：

| 既有约束 | 对 Token 方案的含义 |
|---|---|
| **没有原型 = 不开发（C0 NO-GO）** | Token 只能从原型/金标图提取，禁止「凭空 invent 设计系统」 |
| **静态 UI 还原 = tokens 驱动** | L0 完成后，Worker 默认只消费 Token，不写裸值 |
| **夜间不改 tokens / shared / router / auth** | Token **Bootstrap / 语义升格**必须在 **Phase 0 / 白天**或**显式 GO 的 token-job 窗口**；夜跑只**只读消费** |
| **Phase 0 HARD-GATE**：未完成并获确认不得进 Phase 1 | Token 目录、theme 生成链、预算、manifest 签署前 **不启 6h Goal** |
| **交互含浮层关闭语义、滚动完整性** | Token 不只是色与间距——**z-index / motion / overlay scrim** 也要进集合，否则 L5 交互永远靠 magic number |
| **Goal 自主：不暂停、不中断、卡点 skip-risk** | 缺 Token 时夜跑路径 = `ProposeToken` 记入 queue + skip/排队到白天，**禁止 hardcode 顶分** |

**Grok 定位一句话：**  
Token 系统是 **白天一把梭建好的真相源**；夜跑 Goal 是 **在锁死的 Token 空间里做有限搜索**。这与 Opus「禁 hardcode」同向，但补上你们已经写在 README 里的 **夜/昼权限切割**。

---

## 1. 目标状态：一套 Token，三端同源

```text
                    ┌─────────────────────────────┐
   原型 / 金标图     │  tokens/source/*.yaml         │  ← 唯一可编辑真相（人工或 Bootstrap）
   DOM 探针(可选)  →│  （color/space/radius/type…） │
                    └──────────────┬──────────────┘
                                   │ codegen（可复现）
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
     CSS Variables          Tailwind theme        AntD ConfigProvider
     (runtime 覆写/调试)     (class 工具)           (theme.token/components)
              │                    │                    │
              └──────────┬─────────┴────────────────────┘
                         ▼
              业务组件 / CSS Modules / 页面 Region
              （只允许 var(--*) 或 tw token class 或 antd token）
```

**禁止第二真相**：不允许 SCSS 里再手写一并联色盘，也不允许 Tailwind 一套、AntD 又一套「碰巧相近」的魔法。

---

## 2. 从零目录结构（干净、简约、可 codegen）

推荐落在目标 repo（首次 Phase 0 骨架就建好）：

```text
src/
  design-system/
    tokens/
      source/                      # 唯一手写/Bootstrap 写入区
        color.yaml
        spacing.yaml
        radius.yaml
        typography.yaml
        shadow.yaml
        z-index.yaml
        motion.yaml
        breakpoint.yaml
        semantic.yaml              # 语义层：text-primary → ref base
      generated/                   # 纯生成，夜跑 + PR 均不可手改
        tokens.css                 # :root { --ds-... }
        tokens.ts                  # 类型安全导出
        tailwind.theme.cjs         # 或 .ts，供 tailwind.config  merge
        antd.theme.ts              # theme.token + components 片段
        token-index.json           # 供约束检查 / 评分 Token 命中
    scripts/
      extract_from_prototype.py    # 截图/DOM → candidates
      cluster_and_quantize.py      # 聚类量化
      codegen_tokens.py            # source → generated
      audit_raw_values.py          # CI：裸 px/色 扫描
  styles/
    index.css                      # @import design-system/tokens/generated/tokens.css
  app/
    providers/
      ThemeProvider.tsx            # ConfigProvider + 必要时 tw 无感

tailwind.config.ts                 # 只 re-export generated theme.extend
scripts/ui_autopilot/
  token/
    bootstrap_job.py
    propose_token_job.py
    gate_token_coverage.py
```

**命名纪律（Grok 极简规则）：**

1. **Base（阶梯）**：`color.gray.100`、`space.4`、`radius.md` —— 只表达量表  
2. **Semantic（语义）**：`color.text.primary`、`space.card-padding` —— 只表达用途  
3. 组件层 **禁止** 再发明 `button-blue-2`；用 semantic 或组件 variant map 到 semantic  

冷启动允许临时 id：`proto.space.12px`、`proto.color.#E8EDF5`，**Polish 前必须升格**为 semantic，否则 L6 Gate 失败。

---

## 3. Token 集合最小完备表（对齐 UI 还原 + 交互）

| 集合 | 必须字段示例 | 为何必须 |
|---|---|---|
| **color** | base 阶 + semantic（text/bg/border/fill/state）+ scrim | 去裸色；浮层遮罩也是 Token |
| **spacing** | 4/8 体系量化后的阶 + semantic gutter/section/card | 去裸 px；Region IoU 才稳 |
| **radius** | sm/md/lg/full + 控件语义 | Card/Button/Modal 一致 |
| **typography** | size/weight/lineHeight/fontFamily | 字阶跨模块 |
| **shadow** | sm/md/lg/modal | 浮层深度 |
| **z-index** | dropdown/modal/toast/popover | **Hover 菜单 / 点击浮窗** 不靠 `9999` |
| **motion** | duration/easing | 悬停展开截图稳定前的 wait 策略可绑定 |
| **breakpoint** | 与原型画板宽 | 多模块布局门禁 |
| **control**（可选） | controlHeight、paddingInline（映射 AntD） | 防止 AntD 默认与原型打架 |

> 只抽「色和间距」会上 L5 仍大量 magic number——这是很多 90% 方案的死穴。

---

## 4. Bootstrap 流水线（从零 + 你给的金标图）

### 4.1 输入契约

```yaml
# inputs/{产品}/token-bootstrap.yaml  （Phase 0 产物的一部分）
prototype:
  url: "https://..."                 # 你给的原型地址
  artboards: []                      # 可选
gold_shots:
  root: "inputs/{产品}/prototype/modules/"
  # 文档中每模块静态截图 = 金标 Region
  manifest: "inputs/{产品}/prototype/modules/index.md"
viewport: { width: 1440, height: 900 }
policy:
  color_delta_e_merge: 2.0           # LAB 聚类合并
  spacing_quantum: 2                 # px 量化步长（再映射到 4 基阶）
  max_base_colors: 24
  max_spacing_steps: 16
```

### 4.2 算法步骤（无人白天可跑，结果要人 signoff）

```text
Step A  Capture
  - 原型关键页 + 你提供的模块金标图（金标优先，URL 作补）
  - 可选：Playwright 抽 computed style 直方图（有 DOM 时极准）

Step B  Extract
  - 颜色：主区域采样 → LAB 聚类 → 代表色
  - 间距：连通域/对齐线/重复 gutter 估计 → 直方 → 量化
  - 圆角：边缘曲率/常见 2,4,6,8,12,16…
  - 字号：若有 DOM text metrics；纯图则 OCR 盒高粗糙估计（低置信，夜间慎用）

Step C  Quantize & Name
  - base ladder 生成
  - 初次 semantic 用规则：
      页面最深文本 → text.primary
      最常见大面 bg → bg.page / bg.elevated
      描边众数 → border.default
  - 其余进 proto.* 待升格

Step D  Codegen
  - source yaml → generated css/ts/tw/antd
  - 生成 token-index.json 供评分与 abstraction_check

Step E  Freeze + Sign
  - 写入 night-manifest 可见字段：token_set_hash
  - 你签署后：夜跑只读 generated + source（默认禁止改 source）
```

### 4.3 与 AntD / Tailwind 的初始化（从零项目）

**Tailwind**：`theme.extend` 只 merge `generated/tailwind.theme`，业务不写死色值。

**AntD 5**：

```ts
// 概念示意：antd.theme.ts 由 codegen 产出
export const antdTheme = {
  token: {
    colorPrimary: 'var(--ds-color-brand-primary)',
    colorText: 'var(--ds-color-text-primary)',
    colorBgContainer: 'var(--ds-color-bg-elevated)',
    borderRadius:  /* 映射 radius.md 的 px 数字给 antd 活参数 */,
    fontSize: ...,
    // controlHeight 等
  },
  components: {
    Button: { /* 仅 token 级，禁止夜跑散改 */ },
    Menu: {},
    Modal: {},
  },
};
```

**铁律**：覆盖 AntD 观感优先 **ConfigProvider theme**，与 Opus 禁止 `.ant-*` 乱盖一致；从零起就不要打开「全局 hack AntD」的口子。

---

## 5. Gate：Token 覆盖率 —— L0 硬门（接第 1/5 Hierarchy）

```text
TokenCoverage =
  w1 * HitRate(颜色声明落在 token-index)
+ w2 * HitRate(间距/圆角/字号)
+ w3 * SemanticNamedRate        # proto.* 越低越好
+ w4 * CrossSurfaceConsistency  # 同语义跨页同 ref
```

**建议 Gate 线（冷启动可分阶）：**

| 阶段 | 要求 | 未过则 |
|---|---|---|
| L0.enter | base 集合非空 + codegen 可构建 | **NO-GO 夜跑** |
| L0.shell | Shell 相关 semantic（bg/border/sidebar）齐 | 不许 L1 精修 | 
| L0.element | 控件色/半径/字阶齐；proto.* < 15% | 不许 L4 |
| L0.exit / UIF-99 | proto.* = 0 或显式 acceptance 列表；raw 扫描 0 error | 不许宣称 99% |

实现上可新增（或并入现有门）：

- `scripts/.../gate_token_coverage.py`  
- 与现有 **`abstraction_check.py` / assertion / evidence_check** 同级：无证据 = 没过  
- CI `audit_raw_values.py`：对 diff 扫 `#hex`、`\d+px`（白名单：generated、测试夹具）

---

## 6. 夜跑策略：消费 Token，不「发明」Token

与 README「夜间不改 tokens」对齐，Grok 规定 Job 分流：

| Job 类型 | 何时 | 可否改 `tokens/source` | Worker 行为 |
|---|---|---|---|
| **ConsumeTokenRepair** | 夜跑主路径 | ❌ | 只把裸值换成已有 token / 调 layout |
| **ProposeToken** | 发现原型值距最近 token > 阈值 | ❌ 只写 `proposals/*.yaml` + skipped_risks | **禁止** 为冲分写裸值 |
| **ApplyTokenProposal** | 白天 Phase0/签署窗口 | ✅ | codegen + 锁 hash 更新 |
| **EmergencyTokenHotfix** | 默认关闭 | 需 manifest 显式 flag + 你签 | 否则 NO-GO |

**这是堵住 80→90 人工推的总开关：**  
旧系统假进度 = 夜间随便 hardcode；新系统真停滞 = ProposeToken 堆积 → 晨收 **morning_report** 列出 3 个以内最小决策（命名/是否并入最近阶），你签完下一夜自动 Apply。

对接你们已有节律：

```text
① 输入进 inputs/  
② intake + Phase0（含 Token Bootstrap + dry-cost + lock）  
③ 你签 night-manifest.signoff = GO  
④ 夜跑 Goal：只 Consume + Propose  
⑤ 晨收：token proposals + 交互空洞 + 预算
```

---

## 7. 评分扩一维：**Token Alignment Score**（为第 3/5 预埋）

在 Opus 五维之外，Grok 强制第六维（工程真实性）：

```text
S_token =
  0.4 * css_var_or_tw_token_ratio_in_changed_hunks
+ 0.3 * distance_to_nearest_token_ladder   # 即使用了字面量也重罚
+ 0.2 * semantic_stability                  # 同组件跨态同 token
+ 0.1 * no_new_proto_tokens_in_night
```

**规则：**

- `ΔS_visual ↑` 但 `S_token ↓` → **拒补丁**（典型 hardcode 作弊）  
- 与 Opus cheat 信号合并：高视觉涨分 + 低 token_usage_ratio = cheat  

---

## 8. Worker 约束补丁（在 Opus 禁令上加 Token 分流）

```text
IF 诊断需要值 V:
  IF nearest_token(V).delta <= ε:
      必须使用该 token
  ELIF nearest_token(V).delta <= ε_soft:
      使用 nearest + 记 quantization_note
  ELSE:
      输出 ProposeToken job
      本轮 patch 不得写入 V 的裸字面量
      本轮以「能修的其它维」为限，或 skip 记 evidence
```

Opus 已禁：裸 px、裸色、`!important`、absolute 逃生、`:global`、乱盖 `.ant-*`。  
Grok 再加：

- 禁 **新增大段 theme 内联** 冒充 token  
- 禁 修改 `tokens/generated/**`  
- 禁 夜跑改 `tokens/source/**`（除非 Emergency flag）  
- 改动 SCSS 必须出现 `var(--ds-` 或批准的 tw token 类名比例阈值  

---

## 9. 从零 Phase 0 中的 Token 检查清单（可并入 phase0-checklist §A）

**一次性：**

- [ ] 建好 `design-system/tokens/source` 空模板  
- [ ] 金标模块图进 `inputs/.../prototype/modules` + index  
- [ ] 跑 extract → quantize → 出 **candidate report**（给人看，不是直接冻死）  
- [ ] 你或整合者：**合并阶 / 定 brand / 删脏色**（人类窗口，不可省）  
- [ ] codegen 打通：css + tailwind + antd + 页面能读到 var  
- [ ] `token_set_hash` 写入 manifest；`gen_control_plane_lock`  
- [ ] raw value audit 进 preflight  
- [ ] 明确夜跑 policy：`tokens_mutable: false`  
- [ ] dry-cost：Bootstrap 不重复算进每夜；每夜仅 audit + 评分 token 维  

**未完成以上 → 按你们协议：未签署 = NO-GO，不启 6h loop。**

---

## 10. 与 GPT / Opus 的差分（本册）

| 点 | GPT | Opus | **Grok** |
|---|---|---|---|
| Token 位置 | 偶尔提及 | 禁 hardcode，偏约束侧 | **L0 产品化：提取→量化→三端同源→hash 锁定** |
| 夜跑 | 未切权限 | 未强调 | **只读 Token + Propose 队列**，贴合 night-loop |
| 交互相关 token | 弱 | 弱 | **z-index / scrim / motion 入最小完备** |
| 缺 token 时 | 模型爱写死 | 拒补丁易空转 | **ProposeToken 正式 job + 晨收最小决策** |
| 从零 | 假定已有样式 | 假定项目已有 tokens 路径 | **冷启动目录 + Phase0 清单** |

---

## 11. 第 2/5 结论

1. **Token 是 Goal 的搜索空间边界**，不是美化附属。  
2. **从零**：source yaml → codegen → CSS Vars / Tailwind / AntD **一源三端**。  
3. **Bootstrap 用你给的原型 + 模块金标图**；聚类量化后 **人类短签** 再冻结 hash。  
4. **夜跑禁止改 Token 真相**；只能 Consume 或 Propose——从机制上消灭 hardcode 冲 90%。  
5. **L0 Gate 不进则整链不下探**；与第 1/5 层级门禁咬合。  
6. 完整度上已挂到你们的 **Phase0 / signoff / 夜跑 / 晨收**，避免「脚本很强、控制面两张皮」。

---

## 12. 第 3/5 预告

**评分与证据升级：**

- Opus 五维 + **Token 维 + Interaction 维** → 真正的 UIF-99 可机判  
- 区域 mask（按你模块金标）代替整页 SSIM 暴政  
- 滚动到底 / 悬停菜单 / 点击浮窗 / 侧栏展开的 **断言目录（可挂 assertion-catalog）**  
- 自适应阈值与「静态分够但交互 0 → 总分封顶」规则  

---

**就绪说明（本册后仍 NO-GO 实跑）：**  
第 2/5 只把 Token 设计与门禁写到可实施规格；**第 5/5 的总 Go/No-Go + 你对 candidate token 的签署** 之前，不启动 6h Goal。若你下一回合直接说「继续第三部分」，我按该预告输出，并继续默认 **仓库从零 + 挂接现有 night-loop 控制面**。

# Grok 视角 · 第 3/5  
## 评分与证据升级：UIF-99 可机判 · 挂接 CarrorOS 门禁

> **承接**：第 1/5 定义了复合目标与层级门禁；第 2/5 把 Token 变成搜索空间边界。  
> **本册核心**：把「感觉像 90%」改成 **可复现、可门禁、可拒假完成** 的 UIF-99 机判；并 **嵌进现有** `assertion-catalog` / `evidence_check` / `c7_check`(C3) / `run_gate` / `completion` 证据链，而不是再造平行评分脚本。  
> **输入**：你提供的原型地址 + 各模块**金标静态截图**；运行态由 night-loop 采集 actual。

---

## 0. 问题诊断：现有「分」为什么推不动 80%→99%

| 失效模式 | 表现 | 根因 |
|---|---|---|
| **整页 SSIM 暴政** | 侧栏差 2px 拖垮整页；反之大块正确的页被局部像素噪声卡死 | 无 Region mask / 无层级权重 |
| **静态一眼高分、交互 0** | 未滚到底、未 hover、未点浮层仍「可过」 | 无 Interaction 维硬门 |
| **视觉涨分、工程崩** | hardcode px/色冲分，C3 后置或被绕 | Token 维未进 **接受补丁** 的同一判决 |
| **短跑退出** | 分数平台后进程结束 | 无「停滞分级 + 换维/换目标」策略，只有 exit |
| **虚假完成** | 话术完成、缺双源证据 | 与现网 E3 completion-gate / dual-source 未绑 UIF |

**Grok 纠偏原则：**

1. **分是否涨** 与 **补丁是否接受** 解耦再耦合：视觉可参考，**接受权**在「门禁 ⊕ 多维 ⊕ Token ⊕ 交互」。  
2. **金标模块图 = 评分坐标系**，不是装饰附录。  
3. **交互覆盖率不满 → 总分数学上封顶**（再像也到不了 99%）。  
4. 评分产出必须能进 **`finalize_page` / morning_report / completion 证据包`**，格式可机读。

---

## 1. UIF-99 评分对象模型

```text
Product
  └── Page (route / page_id)
        └── State (default | sidebar_collapsed | hover:nav-x | modal:y | scroll:end | ...)
              └── Region (gold 模块 id：header | sider | content.* | footer | overlay.*)
                    └── Element (optional，L4 才启用细粒度)
```

- **Page-level rollup**：各 Region 加权，权重来自金标面积 × 业务优先级（你可在 manifest 里override）。  
- **State-level**：Shell 多态、浮层态 **各自** 出分；缺态 = 该维 0，不是「忽略」。  
- **禁止**只对 `default + 首屏` 评分后宣称页完成。

### 1.1 与金标文档的契约

```yaml
# inputs/{产品}/prototype/modules/index.md 可解析为：
regions:
  - id: shell.sidebar
    gold: modules/sidebar-expanded.png
    states: [expanded, collapsed]        # UI_README 强制
    weight: 0.18
  - id: shell.header
    gold: modules/header.png
    weight: 0.10
  - id: content.table
    gold: modules/table.png
    weight: 0.22
  - id: overlay.user-menu
    gold: modules/user-menu-hover.png
    capture: { trigger: hover, target: "[data-qa=user]" }
    weight: 0.08
```

缺 `gold` 或不可读 → **该 Region 不计「完成」**（可修采集，不可假装 1.0）。这与「没有原型 = 不开发 / 无证据 = 没过」同构。

---

## 2. 七维（算法）+ 两道硬门（工程）

在 Opus 五维上扩展，Grok 定为 **7 分维 + 2 硬门**：

### 2.1 分维（可连续分 0~1）

| ID | 维 | 主信号 | 权重建议（可进 manifest） | 说明 |
|---|---|---|---|---|
| **D1** | Geometry | 区域 IoU / 关键边距 Δ | 0.16 | 替代整页 SSIM 当家 |
| **D2** | Color | LAB ΔE（区域主色/边框） | 0.12 | 须对照 Token ladder |
| **D3** | Typography | font-size/weight/line-height | 0.10 | DOM computed 优先 |
| **D4** | Decoration | radius/border/shadow | 0.08 | |
| **D5** | Layout | flex/grid/gap/align/overflow | 0.12 | |
| **D6** | **TokenAlign** | 声明命中 token-index、禁 raw | 0.18 | **第 2/5 产物**；夜跑消费 |
| **D7** | **Interaction** | 断言目录通过率 | 0.24 | **可一票封顶** |

> SSIM / LPIPS：仅作 **D1 辅助debug图**，**不单独作门禁**，避免「感知还行但结构歪」或相反。

### 2.2 硬门（非权重可融掉）

| Gate | 对应现网/协议 | 失败语义 |
|---|---|---|
| **H1 Engineering** | C2（tsc/eslint/build）+ **C3 `c7_check`**（裸色/魔法 px/:global/!important/antd 乱盖）+ scope | 补丁 **直接拒绝**；分再高不 accept |
| **H2 Evidence** | `evidence_check` + assertion 目录 + dual-source 思想 | 无截图/无 DOM/无 gate 信封 → **不得 finalize 更不得 完成话术** |

**合成：**

```text
若 H1 或 H2 失败:
    accept_patch = false
    uif_report.status = BLOCKED_ENGINEERING | BLOCKED_EVIDENCE

若 InteractionCoverage < 1.0（针对本页声明清单）:
    uif_total = min(uif_total, 0.94)     # 数学封顶，死锁「假 99」

若 D6 TokenAlign < τ_token（按 phase）:
    accept_patch = false                 # 涨视觉分的 hardcode 全灭

uif_total = Σ wi * Di   (仅 H 全绿时用于 Goal 判断)
goal_page = (uif_total ≥ 0.99) ∧ (全部声明 state 达标) ∧ (proto.* 策略满足)
```

这把第 1/5 的「S4/S5 未绿不算 99」写成了可执行不变量。

---

## 3. 分阶段阈值（挂 Hierarchy Gate）

与 L0→L6 咬合，**禁止同一 0.97 打天下**：

| Phase | 主要看 | D1–D5 | D6 Token | D7 Ix | 备注 |
|---|---|---|---|---|---|
| L0 Token | codegen/audit | — | ladder 存在 | — | 未过 NO-GO 夜跑 |
| L1 Shell | sidebar/header 多态 | ≥0.95 | ≥0.97 | shell 态 100% | **侧栏展开收起是 Shell 不是 polish** |
| L2 Page layout | 主骨架 | ≥0.96 | ≥0.97 | 滚动容器归属断言 | |
| L3 Region | 金标逐区 | 区 ≥0.97 | ≥0.98 | 区相关 ix | **队列遍历，未过区不深 element** |
| L4 Element | 控件 | ≥0.98 | ≥0.99 raw≈0 | — | |
| L5 Interaction | 猎缺态 | 维持 | 维持 | **清单 100%** | hover/click/scroll-end/关闭语义 |
| L6 Polish | 跨页一致 | ≥0.99 | proto.*→0 | 100% | UIF-99 |

**自适应：**

- 连续 K 轮 D1↑ 但 D6↓ → **不升阈值，切断视觉负反馈**，强制 ProposeToken / 换约束。  
- 连续 K 轮总分平台且 Hottest hole 在 D7 → **停止改 padding**，只派 Interaction jobs。  
- 同 target REDIRECT×3 → 升级 BLOCK、**换区域/换态**（与 autonomous-execution「6h TTL 放弃当前方向」同向，**进程不退出**）。

---

## 4. Region Mask 评分（终结整页 SSIM）

### 4.1 Mask 来源（优先级）

1. **金标图 + 模块 bbox 标注**（intake 时可选 JSON）  
2. 运行态 `[data-ui-region=...]` / 稳定 selector（Phase0 约定）  
3. 视觉切割（贵，仅 kimi/视觉模型 **升级** 时）

### 4.2 单区公式（示意）

```text
Geo     = IoU(bbox_proto, bbox_actual) × edge_penalty
Color   = 1 - mean_ΔE(palette_proto, palette_actual) 经 Token 量化后
Token   = hit_rate(declarations in region stylesheet ∩ token-index)
Layout  = style_eq(gap, display, align*) 加权
RegionScore = 加权和
PageScore = Σ (area_i × priority_i × RegionScore_i) / Σ ...
```

**差异可视化**（给人 + 给 Worker evidence，不进「只靠肉眼」）：

- 输出 `diff/regions/{region_id}/{state}.png` 轮廓叠加  
- `deltas.json`：逐属性 expected/actual/token_candidate（接 Opus evidence_builder 思路）

### 4.3 「滚动到底」

不要用单张 `fullPage` 幻想：

```text
scroll_positions: [0, 0.5, 1.0] 或锚点 #module-z
每段：稳定化等待（几何采样，第 1/5 采集原则）→ 截图 → 与金标段或 DOM 断言
footer / 末卡 visible ∈ assertion-catalog
任一段失败 → D7 该条 fail，不分摊成「整页还行」
```

---

## 5. Interaction 维：断言目录即法律

对齐 `UI_README` + 现网 **`assertion-catalog.yaml`** 思想：**能写进 catalog 的才算验收项**。

### 5.1 最小强制项（你已点名的）

| assertion_id | 触发 | 证据 | 通过条件 |
|---|---|---|---|
| `ix.scroll.end` | 滚至底 | 截图 + scrollTop/高度断言 | 末区/footer 可见，无永久 skeleton |
| `ix.sidebar.expand` | 默认或 click | shell 双态图 | 宽/布局对金标 |
| `ix.sidebar.collapse` | toggle | 同上 | 收起态几何 + 内容区 reflow |
| `ix.hover.menu.*` | hover | 浮层截图 + 存在 portal 节点 | 菜单 IoU + z-index token 层级 |
| `ix.click.overlay.*` | click | open 态 | 打开 |
| `ix.overlay.dismiss` | esc/mask/close | close 后 DOM | **关闭语义必须**，防假开 |
| `ix.multi_module.present` | 默认同页 | 多 region 皆采样 | 模块均非 display:none 误判 |

### 5.2 跑法（挂 gate 信封）

建议増 **C-IX**（或并入现有 verify 步，不破坏 C1–C3 序号则可作 C4）：

```text
for a in page.assertions:
  setup(a.trigger)
  wait_stable(a)          # motion token duration 可参考
  evidence = capture()
  result = evaluate(a.predicate, evidence)
  write_envelope(gate_id=C-IX, assertion=a.id, result, artifacts)
  if fail: fix_queue.push(InteractionRepair(a))  # 不要拿去刷静态分
```

与 night-loop 已有节奏兼容：C1 scope → C2 build → **C3 abstraction/raw（c7）** → **C-IX** → 视觉 UIF →（失败 Fixer）。

**失败不得**用「改静态首页像素」替代；Orchestrator 必须 **换 job 类型**。

### 5.3 D7 计分

```text
D7 = passed_assertions / declared_assertions
# 声明来自：UI_README ∩ 页 manifest ∩ gold overlay 列表
# 未声明却关键：Phase0 intake 必须补齐，运行时不许静默删项
```

---

## 6. Token 维机判（与 C3 双锁）

| 检测 | 谁跑 | 作用 |
|---|---|---|
| raw `#hex` / `\d+px` / `!important` / `:global` / `.ant-` | **`c7_check` / abstraction_check** | H1 硬拒绝 |
| changed hunk 中 `var(--ds-` / tw token 比例 | UIF D6 | 接受补丁阈值 |
| 距 ladder 最近阶 Δ | D6 + ProposeToken | 缺 token 不写死 |
| `tokens/generated` 被改 | scope_check + lock | 越界 |

**接受补丁伪码：**

```text
accept =
  H1_ok ∧ H2_ok
  ∧ (ΔUIF 综合 ≥ min_delta 或 关键 hole 关闭)
  ∧ (D6_after ≥ D6_before - ε)      # 禁止以 Token 换视觉
  ∧ (D6_after ≥ phase_τ)
  ∧ (cheat_signals < threshold)     # 继承 Opus：高涨分+低 token 比+重复 diff
```

---

## 7. 证据包规范（拒 E3 虚假完成）

每次迭代 / 每页 finalize 至少：

```text
artifacts/ui_fidelity/{page_id}/{run_id}/
  scoreboard.json          # 七维 + 硬门 + 封顶原因
  regions/*.json           # 区级分数与 deltas
  states/{state}/shot.png
  assertions/{id}.json     # 通过/失败 + 照片路径
  patch_decision.json      # accept/reject + 原因码
  token_hit_report.json
  model_usage.json         # flash vs kimi 次数（预算）
```

**双源思想（对齐 completion dual-source）：**

- 视觉截图 ∈ {gold 对比, actual}  
- 结构 ∈ {DOM assert, gate 信封, c7}  
- 至少 2 类齐才允许 `finalize_page` 写「页完成」  

`morning_report` 应rollup：

- Top hole（按 D7 > D6 > D1…）  
- ProposeToken 队列  
- 被封顶在 0.94 的页（交互未满）  
- 预算与 kimi 升级次数  

---

## 8. 模型路由（评分侧，控成本）

结合事实集：**主执行 DeepSeek V4 Flash；视觉 Gemini-Flash 或 Kimi K3（adapter :8765）**。

| 步骤 | 默认 | 升级视觉模型 |
|---|---|---|
| bboxes / IoU / style diff | 规则 + DOM | 否 |
| ΔE 调色板 | 规则 | 否 |
| 遮挡、半透明、复杂菜单、字体渲染争议 | — | **Kimi K3 / Gemini**，有 `why_escalated` |
| 「像不像」综述 | flash 读 scoreboard | 仅抽检 |
| 审计 | 晨间 GPT/Opus 类（若你配置） | 事后，不挡夜跑 |

**预算：** 6h run 视觉升级硬顶（manifest 可配）；用尽则 D1 仅几何/DOM，**不得**瞎给 0.99。

---

## 9. 卡点与长航时（评分驱动 Orchestrator）

对齐 `autonomous-execution` / night-loop 哲学——**卡点 skip-risk 或换方向，不整进程退出**：

| 评分事件 | 自主策略 |
|---|---|
| 同分重复 patch | EDIT_REPEAT / action_loop → REDIRECT 换 hole |
| D7 失败 | 只派 ix job；静态修复降优先 |
| D6 失败 | ProposeToken 或换已有 token；禁止裸值 |
| H1 C3 失败 | 回修复步，计入 Fixer 轮次 |
| 区 L3 卡住×N | skip-risk 记页熔策略或换 next region（manifest 允许时） |
| 真要人定 token 名 | 不 pause 假死：写入 morning 最小决策，**继续其它 page/region** |
| goal 达 UIF-99 | finalize + 下一页；全产品齐才 GoalMet |

这直接回答需求①：**loop 到逼近原型**；退出只允许达标 / 预算尽 /（异步）人类决策包——第 1/5 已定，本册给出 **由谁的分触发**。

---

## 10. 与 GPT / Opus 差分（评分册）

| | GPT | Opus | **Grok** |
|---|---|---|---|
| 主度量 | SSIM 系 | 五维 style | **七维 + 两硬门 + 交互封顶** |
| 区域 | 弱 | 有 target | **金标 Region Map 为第一坐标系** |
| Token | 弱 | 约束侧禁 raw | **D6 进接受式 + C3 双锁** |
| 交互 | 采集侧可能有 | 状态发现 | **assertion-catalog 化 D7，不满封顶** |
| 假完成 | 易 | 有验证 | **证据包 + dual-source + finalize 挂钩** |
| 卡住 | 易退出 | 阶段循环 | **换维换 job，挂 soft gate TTL，不熄火** |
| 控制面 | 新脚本风险 | 偏完整库 | **嵌 C1/C2/C3/evidence/morning，少平行宇宙** |

---

## 11. 落盘建议（从零 repo + scripts）

```text
scripts/ui_autopilot/scoring/
  uif_scorer.py              # 七维合成
  region_mask.py
  token_align.py             # 读 token-index.json
  interaction_runner.py      # 读 assertion 子集
  scoreboard_schema.json
scripts/carroros-gates/      # 或 ui 下挂接
  # c7_check / evidence_check / run_gate 已有则只扩信封字段
  # uif_total / d7_coverage / token_align 写入可被 finalize 读取
```

**gate-contract 增补字段（示意）：**

```yaml
uif:
  required_dimensions: [D1,D2,D3,D4,D5,D6,D7]
  hard_gates: [H1, H2]
  interaction_cap: 0.94
  phase_thresholds: { L1: 0.95, L3: 0.97, L6: 0.99 }
```

Phase0 checklist 增：

- [ ] 每页 region 金标与 weight  
- [ ] assertion 列表从 UI_README 抽完  
- [ ] token-index 已锁 hash  
- [ ] 视觉 adapter 探针（A3）通过  
- [ ] scoreboard schema 被 evidence_check 识别  

---

## 12. 第 3/5 结论

1. **99% = UIF-99**，不是 SSIM 99；**交互不满数学封顶，工程门一票否决**。  
2. **金标模块截图**定义 Region 坐标系；Shell / 滚动 / 浮层是 **一等评分对象**。  
3. **D6 Token + C3** 双锁消灭 hardcode 假进度；**D7 + catalog** 消灭「静态完成」。  
4. 分数驱动 **换 job 不换熄火**，支撑 ≥6h Goal。  
5. 证据进 **scoreboard / envelopes / morning_report / finalize**，堵住虚假完成。  

---

## 13. 第 4/5 预告

**Worker · 约束 · 补丁契约 · 防作弊再加固（执行侧）**

- Prompt 三层 + `ProposeToken` / `ConsumeToken` / `InteractionRepair` 分流  
- 与 `scope_check`、edit-scope、C3 同一拒绝码  
- deepseek-flash 主修 × 视觉裁决升级  
- 补丁 JSON 契约、validators、和 run_all 单页 13 步的焊点  
- thrash / 重复 diff /「只改一个 magic number」检测  

---

**仍 NO-GO 实跑：** 本册是评分规格；**第 5 册总就绪表 + 你签署 token/assertions/manifest** 之前，不启 6h。需要则直接说「继续第四部分」。

# Grok 视角 · 第 4/5  
## Worker · 补丁契约 · 约束焊点 · 防作弊（执行侧）

> **承接**：第 1 册 Goal/层级；第 2 册 Token 边界；第 3 册 UIF-99 与证据。  
> **本册任务**：把「会判」焊成「会修且修不对就被门禁扔回」——并**挂死**在 CarrorOS 已有笼子上：`run_all` 13 步、`C1 scope` / `C2 build` / `C3 c7+abstraction`、assertion-catalog、`finalize_page`、`EDIT_REPEAT` / action_loop / REDIRECT×3、夜跑禁止动 tokens。  
> **事实锚点**：已知问题①不 loop、②不科学层级，根因含「步11 C6 只最小修、无自迭代」「research 平面不宏观→微观」——本册在 **Worker/Fixer 侧**把自迭代与分流做实。

---

## 0. 设计信条（执行侧三句话）

1. **模型不是审判长**：DeepSeek V4 Flash 只产 **结构化补丁提案**；接受权在门禁 + UIF + Token + 交互。  
2. **搜索空间必须有限**：只能 ConsumeToken / 调布局结构 / 跑 InteractionRepair；缺 Token → **ProposeToken**，禁止裸值冲分（对应 80%→90% 人工推的病因）。  
3. **失败不熄火**：REJECT / C1–C3 FAIL / D7 空洞 → **换 job 或 REDIRECT**，对齐 autonomous-execution：同 gate REDIRECT×3 → BLOCK 放弃当前方向（6h TTL），**继续其它 region/page**，不整段 exit。

---

## 1. 在 13 步夜循环里的焊点

（与 `OPTIMIZATION-FACTSET` / `night-loop` 同构，不平行发明第二套 orchestrator 名也可，但逻辑必须存在。）

```text
… → research/baseline(UIF scoreboard)
  → 【Grok】Plan by Hierarchy Gate (L1→L6) + hole queue
  → Worker 产 patch（本册契约）
  → apply（白名单路径）
  → C1 scope_check
  → C2 tsc/eslint/build
  → C3 c7_check + abstraction_check（+ raw/token）
  → C-IX interaction/assertion（第3册）
  → C6/UIF re-score（七维）
  → 【Grok】PatchDecision: accept | reject+reason | propose_token | skip-risk
  → 若 page UIF < phase_τ 且 budget 有余 → **内环继续**（不跑完一轮就散场）
  → finalize_page 仅当 H门+证据包齐
  → morning_report 收 ProposeToken / 封顶页 / 重复 thrash
```

**对问题①的直接阀：**  
内环条件写成硬逻辑（伪码）：

```text
while wall_ok and page_budget_ok and not human_decision_only:
    board = uif.score(page)
    if board.goal_met: break
    job = scheduler.next(board)          # 按 D7>D6>D1 hole + 层级门禁
    if job is None: break                # 真无可做 → 记停滞，换页
    proposal = worker.run(job)           # flash 默认
    decision = validate_and_gates(proposal)
    if decision.accept:
        commit; continue
    if decision.code in thrash_codes:
        redirect_or_skip(job)            # 不exit进程
        continue
    # reject：把 reason 回灌 evidence，下一 job
```

「`/lx-goal` 12h 用完自然退」是 **外预算**；预算内 **禁止**因「C6 做过一次最小修」而结束页。

---

## 2. Job 类型分流（科学遍历的执行态）

| job_type | 允许时机 | 输入 | 禁止 |
|---|---|---|---|
| **ShellRepair** | L1 未过 | shell 多态 scoreboard + sidebar 金标 | 改 content 深区 |
| **LayoutRepair** | L2 | 主骨架 deltas | 改 tokens/source |
| **RegionRepair** | L3 当前 region | 单区 mask + deltas | 一次跨多高权重区（防大爆） |
| **ElementRepair** | L4 且 L3 门绿 | 组件级 evidence | 裸 px/色；平行再造 AntD |
| **InteractionRepair** | D7 失败 | assertion-catalog 条目 | 用静态首页像素「顶替」 |
| **ConsumeTokenFix** | D6 低但 ladder 有近邻 | token-index + raw 命中点 | 新语义 token |
| **ProposeToken** | 近邻 Δ>ε | 原型值证据 | 改业务样式冲分 |
| **PolishCrossPage** | L6 | 跨页 token 一致报告 | 无序乱改 |

**调度优先级（固定）：**

```text
H1/H2 工程与证据失败修复
  > InteractionRepair（D7）
  > ProposeToken 只入队不堵全站
  > Shell → Layout → Region(queue) → Element
  > Polish
```

层级未门禁通过时，Worker **根本收不到** 更深层 job——从执行面落实「先整体框架再区域再元素」。

---

## 3. 补丁契约（Patch Contract）——唯一进 apply 的形状

Worker **禁止**散文式「请把按钮改小一点」。只许 JSON（可与现有 fixer 输出对齐，字段名可别名，语义不可少）：

```json
{
  "schema_version": "ui-patch/2",
  "job_type": "RegionRepair",
  "target": {
    "page_id": "orders/list",
    "state_id": "default",
    "region_id": "content.table",
    "phase": "L3"
  },
  "hypothesis": "表格容器 gap 与金标 gutter 差 8px，应映射 space.3",
  "evidence_refs": ["scoreboard#D1", "regions/content.table/deltas.json"],
  "token_ops": [
    { "op": "use", "token": "spacing.space-3", "where": "gap" }
  ],
  "propose_tokens": [],
  "changed_files": [
    {
      "file": "src/pages/orders/List.module.css",
      "edits": [
        {
          "kind": "replace_line",
          "line_hint": 42,
          "before": "gap: 8px;",
          "after": "gap: var(--ds-space-3);"
        }
      ]
    }
  ],
  "limits": {
    "max_files": 3,
    "max_hunks": 12,
    "max_changed_lines": 40
  },
  "self_check": {
    "uses_only_existing_tokens": true,
    "touches_antd_global": false,
    "touches_tokens_source": false,
    "assertion_ids": []
  }
}
```

**硬校验（入 apply 前，脚本层，不信任模型 `self_check`）：**

| 检查 | 失败码 | 与现网挂钩 |
|---|---|---|
| 路径 ∈ page edit-scope | `SCOPE_FAIL` | **C1 `scope_check`** |
| 文件数/行数超限 | `PATCH_TOO_LARGE` | 防重构式作弊 |
| `before` 在文件中唯一匹配 | `CONTEXT_MISS` | 拒模糊补丁 |
| 出现 `#rgb`/`px`（非 generated 白名单） | `RAW_VALUE` | **C3 `c7_check` / abstraction** |
| 改 `tokens/source\|generated`、router、auth、shared 全局 | `NIGHT_IMMUTABLE` | night-loop 夜禁 |
| `:global` / `!important` / 无 theme 的 `.ant-*` | `ABSTRACTION_FAIL` | C3 |
| `job_type=InteractionRepair` 但未列 `assertion_ids` | `IX_UNTARGETED` | catalog |
| `token_ops` 空且 D6 为 hole | `TOKEN_REQUIRED` | 第2册 |
| 与近 N 次 patch hash 相同 | `EDIT_REPEAT` | K2 / action_loop |

全部通过才落盘，然后跑完整 gate 链；**envelope 必须 fail-closed**（与 `run_all`/`run_gate` 测试同类：缺字段、PASS 但 exit≠0 → FailClosed）。

---

## 4. 约束层：Opus 禁令 × CarrorOS C3 × Grok Token 分流

### 4.1 统一「拒绝理由码」（便于 morning 聚合）

```text
SCOPE_FAIL | PATCH_TOO_LARGE | CONTEXT_MISS | RAW_VALUE
| ABSTRACTION_FAIL | NIGHT_IMMUTABLE | TOKEN_REQUIRED
| TOKEN_REGRESSION | IX_UNTARGETED | IX_CAP_ACTIVE
| UIF_NO_GAIN | CHEAT_HARDCODE | CHEAT_REPEAT
| BUILD_FAIL | TYPE_FAIL | LINT_FAIL
| EVIDENCE_MISSING | PHASE_GATE_SKIP
```

Fixer 下一轮 prompt **只允许看到码 + 局部 evidence**，禁止「自由发挥绕门禁」。

### 4.2 `c7_check` / `abstraction_check` 是法律，不是提示词

Worker system 提示可强调，但 **以脚本为准**：

- 裸色/魔法数字/z-index 9999 → RAW / abstraction  
- 抑制 AntD 应用用 `ConfigProvider`（昼间 token 链），夜跑禁止散装覆盖  
- **abstraction_check** 与 **D6 TokenAlign** 双锁：一边过扫、一边看命中率与回归

### 4.3 夜跑可变集合 vs 不可变集合

| 可变（Consume） | 不可变（默认） |
|---|---|
| 当前 page scope 内的 page/module css、tsx 布局类名 | `design-system/tokens/source/**` |
| 组件 variant 映射到 **已有** semantic token | `tokens/generated/**`（只 codegen 日间写） |
| 测试 id / data-ui-region（方便采集） | router / auth / 全局 shared 大改 |
| assertion 所需的最少交互绑定 | package.json 依赖（走 dangerous-command 链） |

`ProposeToken` **只写** `artifacts/.../proposals/token-*.yaml`，进 `morning_report`，不进 apply 业务样式。

---

## 5. Prompt 工程（三层，短、硬、可复用）

### L1 System（稳定缓存）

```text
你是 UI 补丁编译器，不是设计师。
只输出 schema ui-patch/2 JSON。
必须：Token 优先；Ant Design 组件优先；CSS Modules + var(--ds-*)。
禁止：裸像素/色、!important、:global 糊墙、改 token 源、大重构、整文件重写。
若值不在 token-index：propose_tokens，changed_files 里不得出现该裸值。
交互任务必须绑定 assertion_ids，并考虑 open+dismiss。
```

### L2 Job（调度器填）

- `job_type` / phase / region / state  
- 金标路径、actual 截图路径、deltas 摘要（Top-K，**不整页贴长文**）  
- 本 phase 阈值、D6/D7 状态、封顶说明  
- 近 3 次失败码（防重复策略）

### L3 Few-shot 微例（按 job_type 各 1 个合法 JSON）

- `gap: 8px` → `var(--ds-space-3)`  
- hover 菜单：只加触发与层类名，z-index 用 `z-index.dropdown` token  
- 禁止示例：为 SSIM 微涨改 margin: 7px

**视觉模型（Kimi K3 / Gemini-Flash adapter）不写大补丁**：只回 **结构化裁定**（遮挡谁、哪条边、是否同一组件），再由 flash 编译为 patch。贵、限次、`why_escalated` 入库（第3册预算）。

---

## 6. 验证管线（接受补丁的唯一路径）

继承 Opus 四层，Grok 订为 **六拍**，与脚本一一对应：

```text
P0  Schema + limits + hash 去重
P1  SCOPE          → scope_check / C1
P2  STATIC_ABS     → c7 + abstraction（C3）+ token_ops 校验
P3  APPLY_IN_MEM or worktree
P4  BUILD          → tsc/eslint/build（C2）
P5  IX（若 job 需要或 D7 红）→ assertion-catalog 子集
P6  UIF            → 七维 re-score + 接受规则（第3册）
```

**Accept 规则（再版）：**

```text
accept =
  all P* pass
  ∧ ¬TOKEN_REGRESSION
  ∧ (关键 hole 关闭 ∨ Δuif ≥ min_delta)
  ∧ ¬(Δvisual↑ ∧ D6↓)          # 反 hardcode
  ∧ ¬CHEAT_*
```

Reject 时：**不保留** 半应用代码（worktree 丢弃或自动 revert），证据仍写入 `patch_decision.json`，供 E3/E5 与晨报——对齐「无证据 = 没过」「假完成违禁」。

---

## 7. 防作弊与 thrash（焊 pretool / autonomous 语义）

| 信号 | 检测 | 处置 |
|---|---|---|
| hardcode 冲分 | 高 ΔD1/D2 + 低 token 命中 / 新 raw | `CHEAT_HARDCODE` 拒收 + 强制 Consume/Propose |
| 重复补丁 | patch hash / before-after 签名 | `EDIT_REPEAT`（K2） |
| 动作环 | 同 region 同 op 重复 | action_loop：NARROW→REDIRECT |
| 假交互 | 只 open 不 dismiss | catalog 失败，D7 不给分 |
| 范围漂移 | 改到非目标区 | C1；记附带发现不偏离（Philosophy） |
| 同 gate 拧巴×3 | REDIRECT×3 | **BLOCK + 6h TTL 放弃方向**，换 region/job |
| 伪数值完成 | 口播 99 无 scoreboard | completion-gate / dual-source；保险 |
| stall | 无工具/无进展时序 | stall 检测层级；换 hole 不睡死 |

**Grok 额外：行级「一个 magic number」启发式**  
单行把 `8px`→`7px` 且无 token、无结构解释 → 直接拒，归因 `CHEAT_HARDCODE`（典型 SSIM 刷分）。

CheatScore 累加（页级）：超阈 → 该页 **只允许** InteractionRepair + ProposeToken，直到人工/日间清trump——防止越 sabit越会刷静态。

---

## 8. Fixer 闭环（失败后谁说了算）

```text
gate/UIF/IX fail
  → reason_code 规范化
  → 若 RAW/TOKEN → 下一 job 锁定 ConsumeTokenFix 或 ProposeToken
  → 若 IX_* → 只生成 InteractionRepair（禁止转静态）
  → 若 SCOPE → 收缩 limits 或重选文件（不扩大 scope 硬闯）
  → 若 UIF_NO_GAIN → 换维度 hole（第3册 Hottest：D7>D6>D1）
  → 若 EDIT_REPEAT → 换策略模板（结构 vs token vs 交互）或升级视觉裁定 1 次
  → 仍失败 → skip-risk + evidence + 下一 region
```

与 **completion-gate E5 RCA**、verify 回访兼容：修复叙述必须带 **量化 + 路径**，禁止「已优化 UI」软完成词。

---

## 9. 与目标工程栈的补丁风格（干净复用）

默认产物形态（从零项目也适用）：

- **布局**：Flex/Grid + token gap/padding，拒绝 absolute 逃生舱（Opus 同）  
- **组件**：AntD 优先，`ConfigProvider` 读 generated antd.theme  
- **样式**：CSS Modules 只含 `var(--ds-*)` 与布局；Tailwind 只用 theme 扩展类  
- **交互**：具名 handler + 可测 `data-qa`；浮层 **open/dismiss** 成对  
- **多模块页**：一 region 一 job，禁止单 diff「顺手」扫整页  

复用：Region 级 `useRegionStyles` / 公共 `PageShell` 在 **L1 日间或首夜 Shell 阶段** 收敛，夜跑 Element 不得复制粘贴三份 sidebar。

---

## 10. 目录落盘（执行侧）

```text
scripts/ui_autopilot/worker/
  patch_schema.json          # ui-patch/2
  prompt_builder.py
  patch_validator.py         # P0–P2
  apply_patch.py
  decision.py                # accept/reject + cheat
  job_scheduler.py           # 层级 + hole
scripts/carroros-gates/      # 已有则扩
  # scope_check / c7_check / abstraction_check / run_gate
  # 增：读 patch_decision、UIF 字段进 envelope（fail-closed）
```

`run_all` 单页步进：在「实现/最小修」处换成 **while UIF&budget：scheduler→worker→gates→decision**；步11 不再是「一次 C6 最小修就走」。

---

## 11. 与 GPT / Opus 差分（本册）

| | GPT | Opus | **Grok** |
|---|---|---|---|
| Worker 输出 | 偏自由改码 | 有 JSON+约束 | **job 分流 + ui-patch/2 + 夜禁 split** |
| 验证 | 偏 CI 想象 | 四层验证 | **六拍焊 C1/C2/C3/IX/UIF + FailClosed** |
| 防作弊 | 弱 | 四信号 | **+ EDIT_REPEAT/action_loop/REDIRECT×3/行级 magic** |
| 缺 Token | 易写死 | 拒了易空转 | **ProposeToken 正式产物 + 晨收** |
| 不 loop | 易单轮 | 有阶段 | **页内 while + thrash 换向不熄火** |
| 控制面 | 易两张皮 | 完整但可漂移 | **拒绝码/证据/finalize/morning 共用** |

---

## 12. 第 4/5 结论

1. Worker = **受限补丁编译器**，审判权在门禁与 UIF。  
2. **Job 分流**落实科学顺序；**补丁契约**落实可验证。  
3. **C1/C2/C3 + Token + IX + UIF** 是同一条 accept 链。  
4. **防作弊**吃 hardcode、重复编辑、假交互、范围漂移；thrash 换方向，对齐 6h TTL，**支撑 Goal 长航时**。  
5. 从机制上同时咬住事实集问题①（内环 loop）与②（层级 job 门禁）。

---

## 13. 第 5/5 预告（最终册）

**完整 Goal 6h+ 编排 + 成本/检查点 + UI_README 执行矩阵 + Phase0→签核→夜跑→晨收 SOP + Go/No-Go 总表**

- 外环多页队列、预算（flash 主量 / kimi 硬顶）  
- checkpoint 复跑、审计与回滚  
- 与 `night-manifest` / signoff / `preflight` / `gen_control_plane_lock` / `install_night_hook` 的签署就绪条件  
- **未勾齐 No-Go → 禁止宣称可执行 6h**  
- 你提供原型+金标后的「第一夜最小垂直切片」建议（L0+L1+单页 L3）  

直接说 **继续第五部分** 即可收官一整套可签署方案。

# Grok 视角 · 第 5/5（收官）  
## 6h+ Goal 编排 · 状态机 · SOP · UI_README 矩阵 · Go/No-Go  
### ——就绪后才允许执行

> **五册收束**：  
> 1 目标闭环与层级 · 2 Token 第一公民 · 3 UIF-99 评分证据 · 4 Worker/契约/防作弊  
> **本册**：把方案焊进 **CarrorOS frontend-overnight 控制面**，给出可签署的执行 SOP、预算与检查点、以及 **未勾齐 = NO-GO** 的总表。  
> **立场不变**：99% 是 **UIF-99（结构+Token+视觉+交互+工程）**，不是一张 SSIM；**Goal 模式 ≥6h 只允许达标 / 预算尽 / 异步最小人类决策**，禁止「跑一阵就退、靠人推下一站」。

---

## 0. 一句话终局架构

```text
白天 Phase0（Token Bootstrap + 金标 Region + Assertion 从 UI_README 抽出
           + dry-cost + control_plane_lock + 你 signoff=GO）
        ↓
夜跑 Goal Runner（外环：多页队列 · 内环：while UIF&budget 迭代）
        ├─ L0只读Token → L1 Shell多态 → L2布局 → L3 Region队列
        ├─ L4 Element → L5 Interaction(100%) → L6 Polish
        ├─ C1 scope → C2 tsc/eslint/build → C3 c7/abstraction
        ├─ C4/C5 Playwright + 浮层矩阵 → C-IX/UIF re-score
        ├─ accept|reject|ProposeToken|skip-risk（不熄火）
        └─ checkpoint 持续落盘
        ↓
晨收 morning_report（ProposeToken 最小决策 · 封顶页 · thrash · 预算）
        ↓
仅当全页 goal_met ∧ 交互清单 100% ∧ proto 策略满足 → 宣称 UIF-99
```

**与现网铁律对齐（不可旁路）：**

| 控制面 | 作用 | 本方案挂钩 |
|---|---|---|
| 无原型 = 不开发 / Phase0 未签 = NO-GO | 起点 | 金标图 + 原型 URL 未齐不启 |
| 夜间不改 tokens / shared / router / auth | 搜索空间 | 只 ConsumeToken；Propose 进晨收 |
| C1→C2→C3→C4/C5… FailClosed | 审判权 | 补丁接受权不在模型 |
| REDIRECT×3 → BLOCK + **6h TTL 放弃方向** | 长航时 | 换 region/job，**进程不 ExitGoal** |
| completion dual-source / 禁软完成词 | 拒假完成 | scoreboard+断言+gate 信封齐才 finalize |
| action_loop / stall / EDIT_REPEAT | 防空转 | 换 hole、升级视觉 1 次、再 skip-risk |

---

## 1. Goal 状态机（外环 · 可跑满 ≥6h）

### 1.1 状态

```text
INIT → PREFLIGHT → TOKEN_READONLY_OK → PAGE_SELECT
  → HIERARCHY_GATE (L1…L6)
  → INNER_LOOP (plan→patch→gates→uif→decision)
  → FINALIZE_PAGE | SKIP_RISK_PAGE
  → NEXT_PAGE | RECHARGE_FROM_CHECKPOINT
  → GOAL_MET | BUDGET_EXHAUSTED | AWAIT_HUMAN_MINIPACK
```

| 状态 | 进入条件 | 退出/转移 | **禁止** |
|---|---|---|---|
| PREFLIGHT | manifest.signoff=GO | lock hash 一致、adapters 通 | 跳过 preflight 开写 |
| INNER_LOOP | 页未 goal_met 且 budget 有余 | accept 继续 / thrash 换 job | **单次 C6 最小修后散场** |
| SKIP_RISK | REDIRECT×3 或 TTL 或不可修 | 记 evidence，下一页/区 | 整 nightly kill |
| AWAIT_HUMAN | 仅 token 命名冲突等 | **不 pause 假死**：其它页继续 | 阻塞全站干等 |
| GOAL_MET | 产品级 UIF-99 | 出完成包 | 口头「差不多」 |
| BUDGET_EXHAUSTED | 时墙/API 到顶 | checkpoint + 复跑指令 | 无工件退出 |

### 1.2 外环伪码（编排器）

```text
 boostrap from checkpoint if any
 assert preflight_ok and token_set_hash locked and signoff == GO

 while wall_clock < budget_h and not product_goal_met:
   page = queue.next_unmet()
   if page is None: break

   while page_budget_ok and not page.goal_met:
     if not gate_L0_readonly(): emit ProposeToken only; break inner to next
     board = uif.score(page, all_declared_states)

     if board.interaction_coverage < 1.0:
       job = InteractionRepair(hottest_assertion)   # 优先 D7
     elif board.D6 < phase_τ:
       job = ConsumeTokenFix or ProposeToken
     elif not shell_multi_state_ok:
       job = ShellRepair
     elif layout_gap:
       job = LayoutRepair
     elif region_queue_not_empty:
       job = RegionRepair(next_region_by_weight)
     elif element_holes and L3_green:
       job = ElementRepair
     else:
       job = PolishCrossPage or mark page.goal_candidate

     decision = run_worker_and_full_gates(job)  # 第4册六拍

     if decision.accept: commit; checkpoint(); continue
     if decision.thrash: redirect_counter++; maybe escalate_vision_once()
     if redirect_counter >= 3: BLOCK direction; skip-risk; break inner direction
     # reject: 回灌 reason_code，换维，不 exit

   if page.ready_for_finalize: finalize_page(dual_source_evidence)
   morning_buffer.append(page.rollup)

 product_goal_met = all pages goal_met and no IX cap and proto policy ok
 persist terminal status + artifacts
```

**这直接关闭事实集问题①**：内环 `while` 替代「步11一次最小修」；外环在预算内换页/换向，对齐 **autonomous-execution「卡点 skip、不整段停」**。

### 1.3 与 13 步夜循环的焊接方式

不推倒 `run_all` / night-loop 叙事，**改造语义**：

| 原步骤意象 | Grok 改造 |
|---|---|
| research / baseline | 出 UIF scoreboard（七维+硬门），非平面感觉 |
| 实现 / 一次修 | **INNER_LOOP** 多轮，受 Hierarchy + job 分流 |
| C1 scope | P1 不变，FailClosed |
| C2 tsc/eslint/build | 每轮 accept 前；三连失败回调度换策略 |
| C3 c7_check | raw/antd/:global 法律；+ Token 命中 |
| C4/C5 Playwright + **浮层矩阵** | 映射 UI_README 与 D7；hover 延迟关闭、modal esc/mask 等进 catalog |
| code freeze + evidence | finalize 前；改 src 同罪纪律保留 |
| 晨报 | 强制含 ProposeToken 队列、IX 封顶页、预算、REDIRECT/BLOCK 列表 |

---

## 2. 时间 / 模型 / 成本预算（6h+ 默认可配）

### 2.1 时墙切分（示例 8h 夜，可缩到 6h）

| 段 | 占比 | 内容 |
|---|---|---|
| 启动 & 探针 | 3% | preflight、adapter、基线截图 |
| L1 Shell 全产品 | 12% | 侧栏展开/收起多态必须先绿 |
| 页队列 L2–L5 | 70% | 按出货优先级；每页软顶防一头热 |
| L6 跨页一致 | 8% | token 复用审计 |
| finalize & 晨报 | 5% | 证据包、rollup |
| 缓冲 | 2% | stall / hook 抖动 |

**单页软顶**：例如 `min(90min, remaining/pages_left * 1.3)`，超时 → skip-risk 换页（不灭进程）。

### 2.2 模型路由与硬顶

| 角色 | 模型 | 预算纪律 |
|---|---|---|
| 主 Worker / Fixer | **DeepSeek V4 Flash** | 95%+ 调用量 |
| 视觉争议裁决 | **Kimi K3**（或 Gemini-Flash adapter :8765） | **硬顶 N 次/夜**（建议 40–80，manifest 可配）；每次 `why_escalated` |
| 编排/规则 | 脚本 + scoreboard | 不耗大模型 |
| 晨间审计（可选） | 你指定的高阶模型 | **事后**，不挡 Goal 退出码 |

超额：降级为 DOM/几何分，**禁止**无视觉瞎标 0.99。

### 2.3 dry-cost（Phase0 必须）

在 `preflight` / intake 阶段写出：

- 预估 flash 调用量、kimi 顶、截图存储  
- Token Bootstrap **不计入每夜重复**（只 audit）  
- 超预算策略：先砍 L4 深精修，**不砍 D7 交互**（交互是封顶维）

---

## 3. Checkpoint · 复跑 · 回滚

```text
artifacts/goal/{run_id}/
  checkpoint.json          # page 指针、region 队列、redirect 计数、token_hash、budget spent
  scoreboards/{page}.json
  patch_decisions.jsonl
  proposals/token-*.yaml
  git_sha_last_accept
  human_minipack.md        # ≤3 个决策题，默认可空
```

| 能力 | 规则 |
|---|---|
| 崩溃续跑 | 读 checkpoint，**不重做已 goal_met 页** |
| 接受点 | 仅 accept 后 `git` 可标记；reject worktree 丢弃 |
| 回滚 | 页级 soft revert 到 last_accept_sha；禁止夜改 lock 文件 |
| 不变式 | `token_set_hash` / `control_plane_lock` 与 Phase0 不一致 → **立即 NO-GO 停写** |

---

## 4. UI_README 执行矩阵（你点名的能力 = 法律）

以下必须进入 **`assertion-catalog` + 页 manifest`**；未进 catalog = **不算验收**（与现网「断言词表」同构）。

| README/需求项 | assertion 族 | 采集 | 门禁位置 | 失败时 job |
|---|---|---|---|---|
| 原型完整还原 | region 金标逐区 | 模块截图对比 | UIF D1–D5 + finalize | RegionRepair |
| 滚动到底 | `ix.scroll.end` (+中段) | 分段/锚点 | C4/C-IX + D7 | InteractionRepair |
| 悬浮显示菜单 | `ix.hover.menu.*` | hover + 稳图；延迟关闭语义 | C5 浮层矩阵 | InteractionRepair |
| 点击浮窗 | `ix.click.overlay.*` | click + portal | C5 | InteractionRepair |
| 浮层关闭 | `ix.overlay.dismiss` | esc/mask/外点/再点 | C5 **强制成对** | InteractionRepair |
| 侧边收缩展开 | `ix.sidebar.expand/collapse` | 双态金标 | **L1 硬门** | ShellRepair |
| 多模块同页 | `ix.multi_module.present` | 多 region 可见 | L3 队列 | RegionRepair |
| Token/风格一致 | raw 扫描 + D6 | c7/abstraction | C3 + accept 规则 | Consume/Propose |
| 禁假完成 | dual-source + 禁软词 | completion-gate | finalize 前 | 补证据，不改话术 |

**合成不变量（再强调）：**

```text
InteractionCoverage < 1.0  on declared set
  → uif_total = min(uif_total, 0.94)   # 数学上永不到 99
H1(C2/C3) or H2(evidence) fail
  → 不得 finalize_page，不得完成话术
```

浮层矩阵建议 **原样继承 night-loop 已写清的 R3 语义**（modal：遮罩+Esc+scroll-lock+焦点；popover：外点+Esc；hover：≥200ms 延迟关闭且移入取消等），Grok 只要求：**每条有 assert_id → 证据文件 → scoreboard D7**。

---

## 5. 端到端 SOP（从你给输入到第一夜）

### 5.1 你提供的输入（不变）

1. 原型地址  
2. 各模块静态金标截图 + 文档索引（weight/state 可标）  
3. DeepSeek V4 Flash + Kimi K3（视关键）可用  
4. 目标 **UIF-99**、Goal **≥6h**、**方案就绪才跑**

### 5.2 白天 Phase0（对照 phase0-checklist / intake 精神）

**A. 输入与骨架**

- [ ] `inputs/{产品}/` 原型 URL、modules 金标、`index` 可解析 region  
- [ ] 从零 CSS/Tailwind/AntD 工程骨架（第2册目录）或已有 repo 挂接  
- [ ] `design-system/tokens/source` 模板 + codegen 管道通  

**B. Token Bootstrap（人类短签不可省）**

- [ ] extract → quantize → candidate report  
- [ ] 你合并阶/定 brand/删脏色  
- [ ] codegen → css/tw/antd；`token_set_hash` 写入  
- [ ] 夜策略：`tokens_mutable: false`  

**C. 断言与页队列**

- [ ] 从 **UI_README** 抽全 assertion 列表进 catalog  
- [ ] 每页 states（含 sidebar/hover/modal/scroll）声明完整  
- [ ] 出货优先级队列（P0 页先）  

**D. 控制面锁与探针**

- [ ] `preflight.py` 全绿  
- [ ] `gen_control_plane_lock.py` 锁定门禁/脚本哈希  
- [ ] `install_night_hook.py` 需要则装好  
- [ ] 视觉 adapter 探针通过  
- [ ] dry-cost 写入 manifest  
- [ ] gate-contract 已含 UIF 字段 / interaction_cap / phase_thresholds（第3册）  
- [ ] fail-closed 冒烟：坏信封、缺字段、PASS 但 exit≠0 → FailClosed（与 run_all 测试同向）  

**E. 签署**

- [ ] `night-manifest` 填预算、页列表、kimi 硬顶、TTL  
- [ ] **`night-manifest.signoff = GO`**（你签）  
- [ ] 未签 = **NO-GO，禁止启动 Goal**

### 5.3 夜跑

```text
1. preflight 再确认 lock
2. Goal Runner 按 §1 状态机
3. 仅白名单 bash / edit-scope 内路径
4. 每 accept：checkpoint
5. 硬边界 / 权限：三级裁决或 skip-risk，继续其它
6. 时墙到：BUDGET_EXHAUSTED 有序收敛，不吞证据
```

### 5.4 晨收

`morning_report` **最低字段**：

- 页级 UIF 七维 + 是否被 0.94 封顶  
- 未过 assertion 列表（逐 id）  
- ProposeToken 队列（**≤3 个优先请你命名/合并**）  
- REDIRECT/BLOCK/skip-risk 与 6h TTL 项  
- 模型用量 vs 硬顶  
- 下一步：ApplyToken（昼）→ 再签 → 第二夜  

---

## 6. 第一夜「垂直切片」（建议，控风险）

不要第一夜贪全站 99%。就绪后的 **Volume-0**：

| 范围 | 成功标准 |
|---|---|
| L0 Token 只读消费 | C3 对切片页 raw=0（或仅存量债务清单化） |
| L1 Shell 双态 | sidebar expand/collapse ≥ phase 阈值 |
| **单 P0 页** L2–L3 主 region | 主区 UIF≥L3 阈 |
| 该页 D7 声明项 | **100%**（含滚动/关键浮层若 README 要求） |
| 长航时 | 内环真正 multi-iter；人为杀进程可 checkpoint 续 |
| 假完成 | 无 dual-source 则 finalize 失败 |

Volume-0 绿 → 第二夜扩页队列；否则只修编排/金标/断言，**不放大 Worker 自由度**。

---

## 7. 总 Go / No-Go 清单（执行前最后一关）

### 7.1 NO-GO（任一即禁止 6h Goal）

| # | 条件 |
|---|---|
| N1 | 无原型 URL 或模块金标不可用 |
| N2 | Phase0 Token 未 freeze / 无 `token_set_hash` |
| N3 | `signoff ≠ GO` 或 control_plane_lock 漂移 |
| N4 | preflight 失败 / 视觉 adapter 不通且任务依赖视觉 |
| N5 | UI_README 关键交互未入库 assertion-catalog |
| N6 | C1/C2/C3 或 run_gate FailClosed 冒烟未过 |
| N7 | 夜跑配置允许改 `tokens/source`（默认必须 false） |
| N8 | 无 dry-cost / 无 kimi 硬顶（防止一夜烧穿） |
| N9 | 仍以整页 SSIM 唯一门禁、无 Region 坐标系 |
| N10 | 页内无 INNER_LOOP（仍「单次最小修就 finalize」） |

### 7.2 GO（须全部勾选）

| # | 条件 |
|---|---|
| G1 | 第1–5 册方案已阅，层级+Token+UIF+Worker 无歧义 |
| G2 | 金标 Region map + weight + multi-state 声明齐 |
| G3 | UIF-99 阈值表写入 gate-contract / manifest |
| G4 | Patch schema ui-patch/2 + scheduler 分流已接 run_all 语义 |
| G5 | Interaction 封顶规则已实现（代码或等价脚本） |
| G6 | checkpoint 路径可写；崩溃续跑演练过一次 dry-run |
| G7 | 你签署 GO，并接受「晨收最小决策」节奏 |
| G8 | 第一夜范围 = Volume-0（或你显式批准全量） |

**Grok 执行纪律：**  
**未满足 7.2 全集 → 我方方案状态 = READY_FOR_IMPLEMENTATION_OF_CONTROL_PLANE，而不是 READY_TO_BURN_6H。**  
实现控制面补丁（scheduler/uif/token gate）可另开昼间工程任务；与「Goal 实跑」分离。

---

## 8. 对你原始五点「是否打满」对照

| 你的要求 | 五册覆盖 |
|---|---|
| ① loop 到逼近，禁早退 | §1 状态机 + 内环 while + thrash 换向；预算尽才停 |
| ② 先框架再区再元素 | Hierarchy Gate + job_type 门禁调度 |
| ③ Token 系统 | 第2册冷启动 + 夜只读 + Propose；D6+C3 双锁 |
| ④ 按 UI_README 完整交互 | §4 矩阵 + C5/D7 + 封顶 0.94 |
| ⑤ 99% / 6h+ / 完整方案就绪后执行 | UIF-99 定义 + §2 预算 + §7 Go/No-Go |

**GPT**：工具与反馈环 → 保留并加长航时。  
**Opus**：五维+约束+防作弊 → 升七维+两硬门并焊 CarrorOS 门禁。  
**Grok**：Token 搜索边界 + Goal 状态机 + 交互法律化 + 签署式就绪。

---

## 9. 落地工作包顺序（方案→代码，仍属「就绪工程」）

```text
W1  tokens source/codegen + audit_raw + gate_token_coverage
W2  uif_scorer + region_mask + scoreboard schema + evidence 挂钩
W3  assertion 从 UI_README 补齐；C-IX / C5 证据索引
W4  patch schema + validator + job_scheduler + decision（接 C1–C3）
W5  run_all 步语义：INNER_LOOP + checkpoint
W6  morning_report 字段扩；manifest 增 uif/budget/kimi_cap
W7  Volume-0 dry-run（短时墙）→ 修 gate
W8  你 signoff → 真 6h+ Goal
```

W1–W7 未完成就开 6h = 重复 80%→90% 人工推。

---

## 10. 五册终章结论

1. **根治早退**：Goal 状态机 + 页内迭代 + 方向级 TTL，而不是进程级认输。  
2. **根治乱修**：L0→L6 门禁与 Job 分流，research 不得平面撒点。  
3. **根治假分**：Token 为界、交互封顶、C3/证据 FailClosed、禁 soft complete。  
4. **根治不可维护 99%**：一源三端 Token + AntD theme + 夜禁改源。  
5. **根治「方案很炫、控制面两张皮」**：全部挂 manifest / preflight / lock / hooks / run_gate / finalize / morning_report。  
6. **执行钥匙在你手里**：§7 Go 齐 + Volume-0 建议；**签 GO 之前任何自称可无人化 6h 的说法均 NO-GO。**

---

## 11. 你下一步可发我的最小包（为真跑做准备）

无需再先开长文方案时，直接给：

1. 原型 URL  
2. 模块金标目录或文档  
3. 目标 repo 是空还是已有 CarrorOS overnight 路径  
4. 是否接受 **第一夜仅 Volume-0**  
5. `UI_README` 路径确认（或粘关键交互段落）  

收到后可进入 **W1–W7 实现规格的逐文件补丁级任务拆解**（仍先控制面，再 Goal 实跑）。

---

**五册完。**  
状态：**方案侧完整度已达「可签署 / 可焊控制面」**；**运行侧默认 NO-GO**，直到 Phase0 + §7.2 勾齐并 `signoff=GO`。  
若你要「把 §9 W1 落成具体文件级改动清单」或「对照现有 `run_all.py` 逐步标改行」，指定一项即可继续——那是**工程实施轨**，不再是理念册。