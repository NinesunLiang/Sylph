The user is asking for my own concrete proposal for the governance scheme in AGENTS.md, tailored to their specific tech stack—Vite 8, React 19, TypeScript 6 with strict mode, Sass with CSS Modules, React Router v7, Zustand v5, and Axios v1, using design tokens from src/styles/tokens.

Rather than another exploratory analysis, they want a decisive, opinionated version grounded in real project constraints: the C7 red lines, Playwright with Chrome DevTools for visual testing, the .omc/ path conventions, and the three-source verification pattern from DECISIONS.md. I should make firm choices where the previous version hedged, structure it as an actual governance document ready to hand to other models, and integrate the real facts from the knowledge base into concrete defaults and file structure decisions. 我需要在 CSS Modules + Sass 的实际技术栈基础上制定这份治理规范，而不是假设 ant-design v6，把它作为可选项来处理。现在我要写出一个真正有决策力的版本，用具体的数字和硬性规则来区别于之前的方案。# CarrorOS 前端自主开发方案（我的定稿版）

> 定位：这是我最终推荐落地的版本，不再罗列选项。所有此前标 `[推断,待确认]` 的地方，我在这里直接拍板给出默认值，并用注释说明可调整点。评审时你们只需要判断「我拍的板对不对」，而不是「还有哪些可能」。
> 权威链沿用现有项目宪法：**用户指令 > 项目宪法 > CarrorOS 内核 > AI 默认行为**。[已验证:AGENTS.md:项目宪法头部]

---

## 0. 我做的三个关键取舍（先说结论）

这套方案和常规「AI 辅助前端」的区别，全在这三个决定上：

**取舍一：不追求「95% 代码由 AI 写」，只追求「95% 验收项自动通过」。**
代码谁写不重要，能不能被工具证明正确才重要。所有指标分母都改成「AC 通过率」，从根上杜绝「AI 写了但没人能验证」的假繁荣。

**取舍二：把「视觉」和「视觉判断」拆开。**
DeepSeek 用 Playwright + chrome-devtools 做确定性测量和像素对比（继承现有工具链），这部分不花 Kimi 一分钱。Kimi K3 只在「机器测出来有偏差、但说不清为什么」时进场做**语义诊断**，且只输出结构化清单、绝不写代码。[已验证:AGENTS.md:UI 还原工具链]

**取舍三：夜间 Loop 的默认产物是 Draft PR，不是合并。**
无人值守阶段 AI 没有合并权。这一条不接受妥协——它是「AI 出错也不会污染主干」的最后一道物理保险。

---

## 1. 我锁定的模型路由表

不做「按模型名分工」，做「按任务类型 + 失败类型」路由。这是死表，Agent 无权自行偏离。

| 触发场景 | 模型 | 硬约束 |
|---|---|---|
| 检索、typo、改 props、类型/Lint 修复、跑命令、整理证据 | **Flash** | 单次改动 <50 行，L0/L1 |
| 页面实现、组件抽象、Zustand 状态、Axios 接入、表单表格、交互 | **Pro** | L2/L3 主力 |
| Flash 连续 2 次同类失败 | **升级 Pro** | 不是「再试一次」，是换执行者 |
| V2/V3 页面，机器视觉测出偏差但 DeepSeek 修 1 轮仍不收敛 | **Kimi K3** | 单页 V2≤1 次 / V3≤2 次，只诊断不写码 |
| 规则冲突、架构裁决、PRD 与 API 打架、失败复盘 | **GPT-5.6-sol / Opus 4.8 / Grok 4.5** | 人工触发，不自动升级 |

Kimi 的进场条件我锁死为**同时满足 5 条**，缺一不进：

1. 任务标 V2 或 V3；
2. `pnpm typecheck` / `build` / 交互门禁已全绿；
3. 偏差不是「页面打不开 / 接口报错 / CSS 编译错」这类非视觉问题；
4. DeepSeek 已做过至少一轮基于 chrome-devtools 对比的自主还原；
5. Kimi 该页配额未耗尽。

> 可调整点：V3 配额从 2 调到 3，成本会明显上升，先按 2 跑。

---

## 2. 我给「完成」下的机器可判定定义

这套项目已经有 C6/C7 检查点和三源验证，我在其上把「完成」拆成 8 道门，从便宜到贵排列，前门不过绝不进后门：

```text
C0 输入门 → PRD/API/设计稿齐全，D2 级缺口已澄清
C1 范围门 → Diff 只碰 plan.md 声明的文件，无越界、无误提交锁文件
C2 代码门 → TS6 strict 过 / ESLint 过 / build 过 / 无 any 逃逸
C3 架构门 → C7 红线（.tsx≤300 / .scss≤300 / 文件内≤3 功能块 / 无裸色值px）
C4 功能门 → 正常+空+加载+接口失败+无权限+重复提交，逐态验
C5 交互门 → 提交防重、Modal/Drawer 关闭、表单焦点、成功后状态刷新
C6 视觉门 → Playwright 局部测量 + chrome-devtools 整体对比，Token 达标
C7 证据门 → 每条 AC 绑当前 Commit SHA 的截图/Trace/命令输出
C8 回归门 → 动了公共组件/Token/路由，跑受影响页面回归
```

C3 的红线直接引用现有宪法，不重新发明：`.tsx ≤300 行 / .module.scss ≤300 行 / 文件内 ≤3 功能块 / 禁止裸色值和 px 魔法数`，违例打回拆分。[已验证:AGENTS.md:C6/C7 检查点]

颜色一律从 `src/styles/tokens/` 取，硬编码色值直接判 C3 不过。[已验证:AGENTS.md:UI 还原铁律]

---

## 3. 我确定的视觉还原三层策略

不是所有页面都追像素。我按现有断点规则和 Token 体系，定死三层：

| 层 | 做什么 | 谁做 | 用 Kimi 吗 |
|---|---|---|:--:|
| L1 设计系统对齐 | Token 颜色/字号/间距/圆角/阴影统一 | DeepSeek | 否 |
| L2 结构对齐 | 栅格、三栏关系、卡片宽高、表格筛选区位置 | DeepSeek + chrome-devtools 对比 | 否 |
| L3 像素微调 | 局部间距、文本基线、图标尺寸、边框阴影 | DeepSeek 实现 / Kimi 仅诊断 | 仅 V2/V3 |

视口按现有宪法锁死，不自创：

- **xl ≥1440**：三栏全展示（主验收视口）
- **lg 1280–1439**：默认布局
- **md 1024–1279**：侧边栏折叠
- **<1024**：不支持，给最小宽度提示

[已验证:AGENTS.md:自适应+Design Tokens]

截图落 `.omc/screenshots/{任务名}/`，禁止写项目根目录，这条也直接继承。[已验证:AGENTS.md:UI 还原铁律]

**防作弊红线**（判 C6/C7 直接失败）：隐藏未实现区域、用静态图替真实组件、只适配单视口的绝对定位、偷偷更新基线截图。

---

## 4. Kimi K3 的输入/输出契约（锁死格式）

进 Kimi 只准带这 5 样，禁止塞整个仓库或历史对话：

```text
1. 目标设计截图（1 张）
2. 同视口实现截图（1 张）
3. 页面区域 + 视口标注
4. 当前 Token 摘要
5. 已知限制
```

Kimi 只准回这个 Schema，回完交给 Pro 改，改完由工具验，**不自动二次调用 Kimi**：

```json
{
  "verdict": "pass | fail | uncertain",
  "issues": [
    {
      "priority": "P0 | P1 | P2",
      "region": "header | main | table | form | modal",
      "category": "layout | spacing | typography | color | component",
      "observation": "可观察差异",
      "suggestion": "不绑实现细节的方向",
      "confidence": 0.0
    }
  ],
  "stop_recommended": false
}
```

P0 结构差异只要存在，整页视觉门就不过，跟总分无关。

---

## 5. 夜间 Loop：我锁定的预算和熔断

状态机沿用现有 L0–L3 工作流和三源验证，我只补前端字段和硬边界。[已验证:AGENTS.md:工作流速查/铁律]

```yaml
budget:
  task_max_model_calls: 20
  task_max_auto_fix_rounds: 4
  same_failure_max_retries: 1     # 同失败指纹只准再试 1 次，且代码必须已变
  visual_fix_rounds: 3
  kimi_calls_v2: 1
  kimi_calls_v3: 2
  wall_clock_timeout_min: 120
```

**熔断（命中任一立即停，转早晨人工）：**

- 同一 `failure.fingerprint` 复现 2 次且代码/输入/环境无有效变化；
- 超调用预算或墙钟；
- Diff 越出 `plan.md` 声明范围；
- PRD 与 API 契约冲突；
- 要动 B3（资金/删除/权限/不可逆）或 `package.json`/`src/auth/**`；
- Kimi 配额耗尽仍有 P0 视觉问题。

**夜间绝对禁止**：合并主干、发布生产、改权限模型、升依赖大版本、自动接受视觉基线更新。夜间成果一律进隔离分支或 Draft PR。

---

## 6. 我扩展后的任务目录（贴着现有 `.omc` 长）

不另起体系，在现有 `research.md / plan.md / executor.md` 铁律上加前端字段。[已验证:AGENTS.md:铁律]

```text
.omc/task/{date}/{task}/
├── manifest.yaml          # 分级/范围/模型/预算/AC 计数
├── research.md            # 现有铁律
├── plan.md                # 现有铁律，每步带 files_allowed + AC + verification
├── executor.md            # 现有铁律，每步即时更新
├── requirement-contract.md
├── assumptions.yaml       # D1 级假设登记
├── state/
│   ├── token.json         # 唯一状态源
│   ├── acceptance_report.md
│   ├── failure.json       # 失败指纹 + 变化检测
│   └── handoff.md         # 恢复导航
└── artifacts/
    ├── commands/  logs/  screenshots/  traces/  visual-diffs/
```

`plan.md` 每步的固定结构：

```yaml
- id: FE-03
  goal: 订单筛选区
  files_allowed: [src/pages/order/**]
  acceptance:
    - 订单号+状态可筛选
    - 重置后恢复默认参数并重新查询
  verification:
    - pnpm typecheck
    - playwright order-filter.spec.ts
  rollback: 回退该步 Commit
```

---

## 7. 缺输入时的处理（我定的红线）

AI 最大的风险是「PRD 没写清就自己编业务」。我按可逆性分三级硬处理：

- **D0 可安全默认**：项目已有统一 Loading/空态 → 引用惯例，记一笔即可。
- **D1 可回滚假设**：筛选是否即时查询 → 按惯例做，但必须写进 `assumptions.yaml` 和验收报告。
- **D2 必须阻塞**：删除是否不可恢复、金额规则、权限边界、状态能否逆转 → **禁止自主假设，直接挂起转人工**。

这条配合置信度标记体系：没有 `[已验证]`/`[已测试]` 标记的技术结论一律视为不可信。[已验证:AGENTS.md:置信度标记]

---

## 8. 一处我必须提醒的事实冲突

你的角色设定提到 **ant-design v6**，但现有项目宪法里技术栈写的是 `React 19 · Sass + CSS Modules · 自定义组件`，**没有 antd**。[已验证:AGENTS.md:项目概览]

这两者不能含糊带过。我的处理：

- 若项目实际是**自定义组件 + CSS Modules**：视觉还原走 Token + `.module.scss`，C7 红线全适用，方案照上面跑。
- 若确实要引入 **antd v6**：那 Token 体系要改成「antd Theme ConfigProvider 优先，页面级覆盖为辅」，C3 架构门要加一条「优先用 antd 组件而非重复造轮子」，`.scss ≤300 行`红线对 antd 定制样式的适用范围也要重定义。

**这是评审前必须由你确认的第一个问题**，因为它直接决定视觉还原和架构门怎么写。我倾向于：以现有宪法为准（自定义组件 + CSS Modules），除非你明确要迁移到 antd v6。

---

## 9. 落地节奏（我建议的四步）

1. **规范统一（1–2 周）**：合并版本歧义，产出唯一 AGENTS.md + task schema + 模型路由表。先把冲突治理掉，再谈自治。
2. **白天监督（2–3 周）**：只跑 V0/V1、B0/B1、不并行、不用 Kimi，人工盯每次状态迁移，验的是控制面和证据链，不是吞吐。
3. **受限夜间（2–4 周）**：放开 L1/L2，隔离分支，单夜 3–5 任务，Kimi 只在 1 个 V2/V3 试点用。验收线：状态恢复率 ≥98%、越界改动 =0、假完成声明 <2%。
4. **规模化（4–8 周）**：Worktree 隔离、race 并行、文件租约、自动 Draft PR、成本仪表盘、固定 Benchmark 回归。

---

## 10. 给 Opus 4.8 / Grok 4.5 的评审靶子

请两位不要评「完不完整」，直接攻我拍的板：

1. **L2/B2 进夜间无人值守**——够不够安全？还是该压到 L1/B1？
2. **Flash 连续 2 次失败才升 Pro**——是否该改成「按失败类型立即升」？
3. **Kimi 单页 V2≤1/V3≤2 次**——够不够省，会不会因太抠导致视觉永远不收敛、反而拖更多轮 DeepSeek？
4. **95%/90%/80% 分母用 AC 通过率**——「人工只补需求、不改代码」算不算 AI 失败？我的立场是不算，请挑战。
5. **antd v6 与现有 CSS Modules 栈的冲突**——按哪个走？
6. **夜间只出 Draft PR、绝不自动合并**——是不是太保守、拖慢规模化？我认为初期值得，请反驳。

一句话收尾：

> **CarrorOS 管边界和状态，DeepSeek 干 95% 的活，Playwright + chrome-devtools 负责证明，Kimi K3 只在说不清视觉问题时进场诊断，高阶模型只裁决——先做到「AI 不编造、不越界、可恢复、失败会停」，再谈把自治比例顶到 95%。**