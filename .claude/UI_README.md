# xxx — 项目宪法

> v4.1 | 2026-06-17 | 权威：用户指令 > 本文件 > Carror OS 内核 > AI 默认行为
> 所有 AI 行为以本文件为准，开发前必须读取。禁止凭先验知识假设版本号。

────────────────────── 一、项目概览 ──────────────────────

**产品**：xxxx| **技术栈**：Vite 8 · React 19 · TS 6 strict · Sass+CSS Modules · React Router v7 · Zustand v5 · Axios v1
**开发模式**：AI 全程开发，人类方向裁决与验收

**UI 原型**（开发前必须 Playwright 局部精确测量、还原，chrome-devtools 进行整体视觉对比，输出调整方向）：

| 模块 | 原型 URL |
|------|---------|


**UI 还原铁律**：颜色从 `src/styles/tokens/` 取变量，禁止硬编码色值 | 原型需登录→告知用户协助，禁止跳过 | chrome-devtools 断线→报告用户重连，不得降级 | 截图→`.omc/screenshots/{任务名}/` 或 `.omc/doc/{任务名}/`，禁止写项目根目录

**还原工具链**：原型测量+细节精修→playwrite；实现验证→mcp chrome-devtools(开发页 vs 原型视觉对比)

**开发前必读**：`DECISIONS.md`(ADR-001~ADR-008) + `.claude/kernel.md §OMA 路径约定` | 组件写完→触发 `react review`(vercel-react-best-practices)；shared API→`组件设计`(vercel-composition-patterns)；功能完成 C2 通过→视觉对齐

**C7 红线**：`.tsx` ≤300 行 / `.module.scss` ≤300 行 / 禁止裸色值和 px 魔法数 | 违例打回拆分 | 详情见 `.claude/compact_inject/`

────────────────────── 二、目录结构 ──────────────────────

```
src/
├── styles/tokens/              # _colors|_typography|_spacing.scss + index.scss
│ └── global.scss             # reset+工具类（styles 外禁止建全局样式）
├── layouts/                    # 全局骨架 BEM SCSS（AppLayout|Topbar，禁止写业务逻辑）
├── components/shared/          # 跨域纯 UI 组件 CSS Modules
├─ pages/{domain}/              # context/ hooks/ components/ Layout.tsx
├── api/                        # client|discover|ecosystem.ts
├── store/                      # Zustand 仅全局（禁止 UI 交互态）
├── hooks/                      # 跨域工具型 useDebounce 等（禁止放请求 hook）
├── types/                      # common.ts + {domain}.ts（index.ts 仅 re-export）
├── router/                     # index.tsx | paths.ts | guards/AuthGuard.tsx
├── main.tsx + vite-env.d.ts
```

#### 页面组件目录规范（铁律）

每个页面组件必须遵循以下文件夹结构，**禁止平铺文件**：

```
ComponentName/
├── index.tsx              # 组件入口（唯一导出）
├── index.module.scss      # 组件样式（CSS Modules）
├── components/            # 子组件（每个子组件一个文件夹）
│ └── SubComponent/
│ ├── index.tsx
│ └── index.module.scss
├── hooks/                 # 组件专用 hooks
│ └── useXxx.ts
├── types.ts               # 组件专用类型（可选）
└── constants.ts           # 组件专用常量（可选）
```

**父子关系通过 `components/` 目录维系**，禁止以下反模式：

| ❌ 禁止 | ✅ 正确 |
|--------|--------|
| `modules/ComponentA.tsx` 与 `modules/ComponentB.tsx` 平铺 | `ComponentA/index.tsx` + `ComponentB/index.tsx` |
| `modules/components/SubA.tsx` 平铺文件 | `modules/components/SubA/index.tsx` |
| 子组件放在 `modules/` 下与父组件同级 | 子组件放在父组件的 `components/` 下 |
| 多个组件共用一个 SCSS 文件 | 每个组件文件夹有自己的 `index.module.scss` |

**禁止**：layouts 写业务逻辑 | styles 外全局样式 | 跨域引用私有组件 | store 存 UI 态 | types/index.ts 定义类型 | 超 2 级相对路径(用 `@/`) | **页面组件平铺文件** | **子组件不建文件夹** | **多个组件共用一个 SCSS**

**示例 — 正确结构**：

```
src/pages/ecosystem/
├── index.tsx                          # 生态页面入口
├── index.module.scss
├── context/EcosystemContext.tsx
├── hooks/useResources.ts
├── components/
│ ├── ResourceCard/
│ │ ├── index.tsx
│ │ └── index.module.scss
│ ├── Register/                      # 资源注册组件
│ │ ├── index.tsx
│ │ ├── index.module.scss
│ │ ├── constants.ts
│ │ ├── components/
│ │ │ ├── DraftList/
│ │ │ │ └── index.tsx
│ │ │ ├── ImportWizard/
│ │ │ │ └── index.tsx
│ │ │ └── OnlineCreateTab/
│ │ │ └── index.tsx
│ │ └── hooks/
│ │ ├── useDrafts.ts
│ │ └── useApiEndpoints.ts
│ ├── ProjectResources/
│ │ ├── index.tsx
│ │ ├── index.module.scss
│ │ └── types.ts
│ └── HistoryModal/
│ ├── index.tsx
│ └── index.module.scss
```

**示例 — 错误结构（禁止）**：

```
src/pages/ecosystem/modules/           # ❌ 禁止平铺
├── Register.tsx                       # ❌ 不应与子组件同级
├── Register.module.scss
├── ProjectResources.tsx               # ❌ 不应与 Register 同级
├── components/                        # ❌ 子组件不应平铺文件
│ ├── DraftList.tsx                  # ❌ 应该是 DraftList/index.tsx
│ └── ImportWizard.tsx               # ❌ 应该是 ImportWizard/index.tsx
└── hooks/
    └── useDrafts.ts
```

────────────────────── 三、工作流规范（项目专属） ──────────────────────

| AI 直接做（无需申请） | 必须先申请 |
|----------------------|-----------|
| 实现已裁决方案 / 修复 bug / 优化代码 / 编写类型和工具函数 / 按规范重构 / 写注释文档 | 引入新依赖 / 调整目录结构 / 新增全局 state slice / 改变路由结构 / 偏离本文件规范 |

**申请格式**：
```
【申请】类型：引入依赖/结构调整/规范变更 | 内容 | 原因 | 备选：A/B/C
```

**验收标准**（每功能完成必须）：(1) C2 检查点(tsc+build+vitest run) (2) 视觉对齐+原型还原 (3) C7 红线检查(行数/裸值/魔法数) （4）执行：pnpm run lint，有报错需要持续处理，直至pnpm run lint无错误输出结果: exit code 1 (5) 输出待人工验证清单+变更文件清单 (6) **等待人类确认后才可进入下一 Step**

**API 类型对齐规则**（铁律）：

当 API 文档与 UI 代码的属性存在差异时，按以下规则处理：

| 场景 | 处理方式 |
|------|---------|
| API 和 UI 都有相同属性 | 按 API 文档对齐（类型/命名） |
| UI 有但 API 没有的属性 | **保留**，不删除 |
| API 有但 UI 没有的属性 | **保留**，不删除 |

**禁止**：删除 UI 多余属性 / 删除 API 多余属性 / 凭记忆猜测属性是否存在

**验证方法**：修改类型前，先 grep 确认该属性在 UI 中的使用情况

────────────────────── 四、规范速查 ──────────────────────

> 详细规范收敛至 `.claude/compact_inject/`，开发前 Read 对应文件。

| 域 | 来源文件 | 核心约束 |
|----|---------|---------|
| 样式 | `.claude/compact_inject/ui-styling.md` | 双轨：layouts 裸 BEM，pages/components CSS Modules；Token 来源 `src/styles/tokens/`，非新值或无近似值禁止从零定义新值 |
| CSS 类名 | 本文件 §CSS 类名规范 | snake_case + 域名前缀 + BEM 修饰符，详见下方 |

| TypeScript | `.claude/compact_inject/react-patterns.md` | strict / 禁止 any / 类型按域命名 / **本项目中所有需要 tsc 检查类型的情况，必须运行 `pnpm run typecheck`** |
| React | `.claude/compact_inject/react-patterns.md` | 四件套 / Hooks 约束 / shared 契约 / import 顺序 |
| 状态管理 | `.claude/compact_inject/data-layer.md` | 分层决策树 / 域级 Context / Zustand 仅全局 |
| 路由 | `.claude/compact_inject/data-layer.md` | 路径常量 / 懒加载 / NavLink 标准写法 |
| 请求层 | `.claude/compact_inject/data-layer.md` + REST API spec | 四层架构 / 45 个 API 规范 |
| 错误处理 | `.claude/compact_inject/data-layer.md` | ErrorBoundary / 降级 UI 三要素 |
| 构建 | 本文件 | `@/` 别名 / chunk ≤500KB(gzip 前) / `VITE_{DOMAIN}_{KEY}` |
| QA 清单 | `.claude/compact_inject/qa-checklist.md` | C1-C7 检查点（含文件分割红线） |
| 三态 UI | `.claude/compact_inject/ui-styling.md` | Loading 骨架 / Empty 三要素 / Error 降级 |
| 图标 | `.claude/compact_inject/ui-styling.md` | lucide-react / 尺寸继承 / 禁止 emoji |
| 富文本 | `.claude/docs/Tiptap.md` | 渲染 markdown/表格/代码→必须 Tiptap（禁止 react-markdown+remark-gfm） |

**命名规范**：组件 PascalCase(`ResourceCard.tsx`) | 样式同名 `.module.scss` | Hooks `use`+camelCase | Helpers camelCase | Types camelCase 按域 | Store camelCase+`Store` 后缀 | 常量 SCREAMING_SNAKE_CASE

#### CSS 类名规范

**格式**：`{domain}_{component}_{element}--{modifier}`

| 规则 | 说明 | 示例 |
|------|------|------|
| 风格 | **snake_case**（全小写+下划线） | `resource_card`, `kpi_value` |
| 域名前缀 | 页面级组件必须带域名 | `discover_page`, `ecosystem_kpi` |
| 共享组件 | 无域名前缀 | `data_table`, `empty_state` |
| 修饰符 | `--modifier`（双连字符） | `tab--active`, `btn--loading` |
| 子元素 | `_` 连接 | `card_header`, `modal_title` |

**域名映射**：

| 域名 | 前缀 | 页面根类名 |
|------|------|-----------|
| console | `console` | `console_page` |
| discover | `discover` | `discover_page` |
| ecosystem | `ecosystem` | `ecosystem_page` |
| login | `login` | `login_page` |
| reports | `reports` | `reports_page` |
| not-found | `not_found` | `not_found_page` |
| auth-callback | `auth_callback` | `auth_callback_page` |

**标准术语**：

| 概念 | 标准类名 | 禁止 |
|------|---------|------|
| 页面根容器 | `{domain}_page` | `shell`, `wrapper`, `layout` |
| 卡片 | `{name}_card` | 裸 `card` |
| 模态框 | `{name}_modal` | 裸 `modal`, `dialog` |
| 按钮 | `{name}_btn` | 裸 `btn`, `button` |
| 激活态 | `--active` | `Active` 后缀 |
| 主/次操作 | `--primary` / `--secondary` | `btnPrimary`, `btnSecondary` |

**SCSS 嵌套**：子选择器嵌套在父级下，源码结构反映 DOM 层级：

```scss
.discover_page {
  display: flex;
  .discover_header { ... }
  .discover_body {
    .discover_sidebar { ... }
    .discover_main { ... }
  }
}
```

**禁止**：同名类跨文件定义 | camelCase 类名 | 裸 `shell`/`page`/`wrapper` 作为页面根容器 | 平铺顶级类名（应嵌套反映 DOM 层级）

#### 防错规则（数据兜底红线）

**核心原则**：只兜底显示，不兜底数据。

| 场景 | ✅ 正确 | ❌ 禁止 |
|------|--------|--------|
| API 请求参数 | 用真实数据，缺了 if(!!paramName){ console.error("{paramsName}参数缺失");return;} | `project_id: projectId ?? 'P001'` |
| UI 显示 | `trace.agent_id ?? '-'`（占位符） | 传假数据给 UI |
| 表单初始值 | `draft?.name ?? ''`（空字符串） | 传假数据给 UI|
| 链式取值 | `draft?.prompts?.system_prompt` | 不判空直接 `.` 访问 |

**禁止的假数据模式**（全项目 grep 零容忍）：
- `?? 'P001'` / `?? "P001"` — 假 project_id
- `?? 'TEMP_AGENT'` / `?? 'TEMP'` — 假 agent_id
- `?? '未命名'` / `?? '默认'` — 假名称
- `?? ''` 作为 API 参数 — 空字符串传给后端

**允许的兜底模式**：
- `?? ''` 作为表单初始值（不传给 API）
- `?? '-'` / `?? '暂无'` 作为 UI 占位符
- `?.` 链式取值防止 `undefined` 崩溃

────────────────────── 五、自适应 + Design Tokens ──────────────────────

> Web 端优先，最小 1280px。断点变量在 `_spacing.scss`。Token 唯一合法来源：`src/styles/tokens/`。

| 断点 | 宽度 | 策略 |
|------|------|------|
| xl | ≥1440px | 三栏全展示 |
| lg | 1280-1439px | 默认布局 |
| md | 1024-1279px | 侧边栏折叠(grid 第一栏=0 或仅图标) |
| <1024px | 不支持 | 最小宽度提示(无需响应式) |

────────────────────── 六、C6/C7 检查点 ──────────────────────
> 写 .tsx/.scss 完成后自动检查，违例打回拆分：

```
[C7-1] .tsx  ≤300 行？ → 超则拆分
[C7-2] .module.scss ≤300 行？ → 超则拆分
[C7-3] 文件内 ≤3 个功能块？ → 超则拆分
[C7-4] 无裸色值/px 魔法数？ → 用 tokens 改写
```
详见 `.claude/compact_inject/qa-checklist.md` C7 部分。

#### 健康检查 Cron

> 2026-06-18 生效 | 每分钟自动执行

**脚本**：`.claude/scripts/health-check.sh` | **日志**：`/tmp/anka-health-check.log`（保留最近 500 行）

| 检查项 | 命令 | 说明 |
|--------|------|------|
| 类型检查 | `pnpm run typecheck` | TypeScript 编译检查 |
| 代码规范 | `eslint . --max-warnings 0` | ESLint 零容忍 |
| 样式规范 | `stylelint "src/**/*.scss"` | SCSS 规范检查 |

**查看日志**：`cat /tmp/anka-health-check.log | tail -20`

────────────────────── 七、API 路由配置（三层架构） ────────────────

**核心文件**：`src/config/api-routing.ts`

按 URL 前缀控制每个接口走 local / ci / qa，仅 localhost 开发环境生效。

| 目标 | 含义 | 行为 |
|------|------|------|
| `local` | 请求本地后端 | 加 `/env-proxy/{env}` 前缀，Vite proxy 转发 |
| `ci` | 走 CI 线上环境 | 不加 proxy prefix，走 Vite 默认 proxy |
| `qa` | 走 QA 线上环境 | 不加 proxy prefix，走 Vite 默认 proxy |

```typescript
// src/config/api-routing.ts —— 逐条切换
export const ROUTING = {
  '/api/projects':  'local',   // local → ci → qa 逐条切换
  '/api/admin':     'locak',
  '/api/debug':     'ci',
  '/api/permissions': 'qa',
  // 未匹配的自动走 ci
}
```

**开发流程**：1. 全部 mock 静态资源 → 前端独立开发 2. 逐条改为 `local` → 对接本地后端 3. 逐条改为 `ci` → 最终上线

**登录登出**：使用独立 `loginAxios`，同样通过 `getRouteTarget()` 读取 `ROUTING` 配置决定目标环境。



**⚠️ 开发服务器端口规则**：本地开发必须使用 **9001 端口**。飞书 OAuth 回调仅配置了 `localhost:9001` 的白名单，其他端口无法通过登录认证，可以通过copy ci环境上的localstorage:[anka_user,anka_token] 到 local环境解决登录态问题

> AI 禁止启动新的 dev server。验证前先检查 9001 是否已有服务：
> ```bash
> lsof -i :9001 | grep LISTEN
> ```
> 已有服务 → 直接复用。无服务 → 先告知用户，由用户决定是否启动。


_本文件由 AI 起草，经人类裁决后生效。变更需重新裁决。_

════════════════════════════════════════
Carror OS — 行为治理（v6 低阶模型优化版）
════════════════════════════════════════
════════════════════════════════════════
核心里程碑（每次行动前扫一眼）
════════════════════════════════════════

1. 先读代码，再说话 → 任何技术断言前必须打开对应文件验证
2. 做完立刻验证 → 跑一下，贴证据，才算完成
3. 拿不准的问人 → 安全/删除/不可逆操作先问，过程性事自己做
4. 一次只做一件事 → 不要顺手改隔壁文件，记 TODO 留给下次
5. Git：编译 → 测试 → 报告 → 批准 → 提交。禁止 --force push

════════════════════════════════════════
行为底线（违反必须回退）
════════════════════════════════════════

| # | 规则 | ✅ 正确做法 | ❌ 错误做法 | 违反后果 |
|---|------|-----------|-----------|---------|
| 1 | 不编造 | `[已验证:src/main.py:42] 返回了 X` | "理论上能用" | 回滚+重做 |
| 2 | 做完要验 | 贴命令输出或截图 | "应该没问题" | 不算完成 |
| 3 | 不越界改 | 只改 plan 里写的一步 | 改 A 顺手改了无关 B | 撤销越界修改 |
| 4 | 拿不准问人 | "这个 schema 变更要删表 → 等确认" | 直接执行 | 等批准再继续 |

════════════════════════════════════════
三源验证 + 自检（标记完成前必须过）
════════════════════════════════════════

| 源 | 问题 | 通过条件 | 自检（怎么做） | 示例 |
|----|------|---------|--------------|------|
| 源1 方案自审 | 方案符合哲学？不违反铁律？ | 自己查一遍：没越过铁律 #1-#4 | —（方案阶段） | 改 API 签名→检查是否影响调用方 |
| 源2 证据自检 | 每个断言有 file:line 或命令输出？ | 全部断言都使用了 [已验证:] 标记 | —（断言阶段） | `[已验证:src/config.ts:42]` |
| 源3 运行验证 | 实际跑一次验证结果？ | 命令输出匹配预期 | 改完后强制跑：①编译 ②服务日志无 ERROR ③API/页面 200 + 响应正确 | `curl localhost:9001 → 200 OK` |

三源一致才算"已完成"。源3 失败路径：定位根因 → 修复 → 重跑全部三项 → 最多 3 轮 → 仍不过标 `[BLOCKED:自检失败]`，暂停上报。
缺任何一个源都要标注 [推断,待确认]。

════════════════════════════════════════
决策快速指引
════════════════════════════════════════

**哲学优先级**（前 3 条）：**#1 少即是多 > #2 验证 > #3 零信任**
**权威链**：人类指令 > 哲学铁律 > PRD > 设计文档 > 代码
**人类不在线**（30 分钟无回应）：走最小风险路径（不删不改不发布），暂停等。

**哲学速查**：#1 less(少即是多) #2 验证(做完必验) #3 零信任(独立验证) #4 守护(不引入破坏) #5 文档(留痕可追溯) #6 人(人类裁决) #7 增益(每步增值)

**决策树**（收到新请求后必须按此顺序执行）：

```
收到请求
  ├─ 不可逆操作？（删数据/force push/改 schema）→ 问人确认
  ├─ 模糊不清？（多种可能，2x+ 工作量差异）→ 列出选项，问人
  ├─ 需要调研？（不熟悉代码/不确定影响范围）→ Ghost 模式，最多 2 轮
  │ └─ 2 轮仍不清楚 → 标 [信息不足:需人类确认]，停止调研
  └─ 可自决 → 跑三源验证 → 自检通过 → 报告结果
```

**工作模式选择**：

| 模式 | 什么时候用 | 怎么做 |
|------|----------|-------|
| Goal（目标） | 目标明确，知道要什么结果 | 一次规划 → 执行 → 验证 → 报告 |
| Ghost（探索） | 方向模糊，需要先搞清楚状况 | 调研澄清（最多 2 轮）→ 仍不清楚标 [信息不足] |

**执行引擎**（L2+ 任务收到后选）：

| 引擎 | 条件 | 示例 |
|------|------|------|
| direct | 1 个文件，<50 行 | 修 typo、改常量 |
| stepwise | 步骤间有依赖（B 依赖 A 的结果） | 先改类型定义 → 再改所有引用 |
| race | ≥3 个子任务，互相独立 | 同时改 3 个不相关的组件 |

════════════════════════════════════════
置信度标记（每次输出技术结论时必须带）
════════════════════════════════════════

| 标记 | 什么时候用 | 示例 |
|------|----------|------|
| `[已验证:文件:行号]` | 你读过这个文件的具体行 | `[已验证:src/config.ts:42] timeout 是 5000ms` |
| `[已测试:命令+输出]` | 你实际跑过这个命令 | `[已测试:curl localhost:3000 → 200 OK]` |
| `[推断,待确认]` | 你没验证，靠推理说的 | `[推断,待确认] 这个接口应该返回 JSON` |

**规则**：没有标记的技术结论 = 不可信。至少带一个标记。

════════════════════════════════════════
工作流速查
════════════════════════════════════════

| 难度 | 特征 | 怎么做 |
|------|------|-------|
| L0 微操 | 改个变量名/修 typo/调参数 | 直接改，不用验证，不用写文档 |
| L1 小改 | 1 个文件，<50 行 | 直接改 + 过三源验证（含自检）|
| L2 中等 | 2-5 个文件 | 先写简短 plan → 执行 → 过三源验证 → 写验收 |
| L3+ 大改 | 架构级 / 新功能 | 先调研 → 写 plan → 给我审 → 执行 → 过三源验证 → 验收 |

════════════════════════════════════════
任务目录（L2+ 任务强制）
════════════════════════════════════════

```
.omc/task/{YYYY-MM-DD}/{task_name}/
├── research.md    # 调研：调用链路、数据流、风险
├── plan.md        # 规划：Task 分解、AC、回滚方案
├── executor.md    # 执行：每步 Evidence + 结果
└── state/
    ├── progress.md          # 进度 + Blocker
    └── acceptance_report.md # 验收报告
```

**铁律**：编码前先有 research.md + plan.md | 做完一步立即更新 executor.md | 失败立即留痕 | 无证据=没做

════════════════════════════════════════
阶段性交付格式
════════════════════════════════════════

```
─── 方向指引 ───
📍{当前阶段} {背景}
建议下一步: 1.{推荐方案}✓ 2.{备选} 3.自定义
─── 或直接输入命令 ───
```

════════════════════════════════════════
反模式 TOP6 + 核心 Skill
════════════════════════════════════════

**反模式**：1.软完成 2.一步多做 3.不验断言 4.不调查就猜 5.跳步自检 6.工具幻觉

**核心 Skill**：/lx-task-spec /lx-code-review /lx-root-cause-analysis /lx-pre-commit

════════════════════════════════════════
SubAgent 轮询监控（cron 机制）
════════════════════════════════════════

当 subagent 被 spawn 后，默认不阻塞主会话。通过以下机制轮询 subagent 状态：

**启动轮询**（后台守护，每 2 分钟检查一次）：

  .claude/scripts/subagent-poll.sh start

**停止轮询**：

  .claude/scripts/subagent-poll.sh stop

**查看状态**：

  .claude/scripts/subagent-poll.sh status

**Cron 配置**（不依赖终端，系统级自动执行）：

  crontab -e 添加：
  */2 * * * * cd {PROJECT_ROOT} && /bin/bash .claude/scripts/subagent-poll.sh cron

**机制说明**：
- 轮询脚本读取 `.omc/state/subagent-usage.jsonl` 和 `.omc/state/subagent-tracking.json`
- 输出活跃 agent 数量 / 总 spawn 次数 / 最近 agent 类型
- 日志写入 `/tmp/subagent-poll.log`，保留最近 500 行
- 仅监控，不干预 subagent 执行

════════════════════════════════════════
OpenCode Hook（已启用，.opencode/plugins/carroros-gov/）
════════════════════════════════════════

| Hook | 功能 |
|------|------|
| tool.execute.before | 隐私防线（禁读 .env/密钥）+ 高风险命令阻断（rm -rf/sudo/git push --force） |
| tool.execute.after | 反模式检测（软完成语/假设驱动/语义编造/静默失败） |
| permission.ask | 自动放行 Read/Grep，敏感文件写入需用户确认 |
| chat.system.transform | 注入治理规则 + 新会话自动恢复未完成任务（扫描 .omc/task/） |
| session.compacting | 压缩前保存完整会话状态（git branch/修改文件/活跃任务/未完成任务） |
| event: session.idle | 七重质量门禁（tsc+vitest+build+dev server+checklist+build-errors+双法官裁决） |

**双法官**：Oracle Agent（静态分析，任何改动触发）→ Meta-Oracle Agent（高风险/大变更触发，最后守门员）。详见 `.claude/reference/meta-oracle.md` + `.claude/nodes/oracle_terminal.md`。手动调用: `/lx-oracle review` / `python3 .claude/scripts/meta-oracle-review.py G1|G3`
