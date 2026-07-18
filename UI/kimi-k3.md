# CarrorOS 前端无人值守还原方案（K3 整合定稿版）

> v1.0 | 2026-07-17 | 作者：Kimi K3（在 CarrorOS 治理会话内产出）
> 定位：整合 GPT-5.6 Sol / Opus 4.8 / Grok 4.5 三份提案后的**可执行版**。
> 与三份提案的本质区别：它们写"治理体系应该怎样"，本文写"今晚睡前按哪个按钮、夜里每一步发生什么、早上收什么"。
> 硬约束（用户拍板，不可评审推翻）：**执行时没有高阶模型。高阶模型只存在于规则制定与方案评审阶段。**

---

## 0. 对三份提案的采纳表

| 来源 | 采纳 | 拒绝/修改 | 理由 |
|---|---|---|---|
| GPT-5.6 Sol | C0–C8 门禁体系、manifest/failure schema、证据绑定 SHA、防截图作弊红线 | 8 周 4 阶段组织路线、30 任务 Benchmark（留到第二阶段）、执行时高阶裁决路由 | 组织设计对单任务过重；执行时无高阶模型是硬约束 |
| Opus 4.8 | 三个取舍（AC 通过率 / 视觉与视觉判断分离 / 夜间只出 Draft PR）、K3 输入输出契约、预算熔断表、D0/D1/D2 分级 | "高阶模型人工触发裁决"改为"结构化阻塞转早晨" | 同上 |
| Grok 4.5 | 失败分类路由（替代"2 次失败才升级"）、B 级保守主义、输入治理优先、C7 必须机器门 | 无——全部采纳 | 它的保守恰好匹配无人值守 |
| 三家共识 | 实现/验收分离、D2 阻塞不编造、功能门先于视觉门、K3 只诊断不写码 | — | 直接继承 |

**本文独有（三家都没有的）**：
1. 所有流程映射到 CarrorOS 真实文件与命令（`carros_base.py`、`.omc/tasks/`、lx-goal 脚本），不是抽象角色；
2. **判断真空规则 J0**（见 §2）——执行侧没有裁决者时的完整行为定义；
3. **Phase 0 路由表预生成**——消灭夜间并行时的共享文件冲突（见 §6）；
4. **mock 层风险坍缩**——交互还原全程走宪法已有的 `api-routing.ts` mock 层，B2 写操作无真实副作用，风险等级坍缩为 B0/B1（见 §3）。

---

## 1. 执行时模型舰队（锁死）

| 角色 | 模型 | 形态 | 单页预算 |
|---|---|---|---|
| Implementer 实现者 | DeepSeek V4 Pro | Claude Code 主会话（代理路由 `claude-opus` → v4-pro） | ≤16 次调用 |
| Fixer 修复者 | DeepSeek V4 Flash | Subagent（`CLAUDE_CODE_SUBAGENT_MODEL=haiku` → v4-flash） | ≤4 次调用 |
| Visual 视觉诊断 | Kimi K3 | **工具脚本** `scripts/kimi-visual-diag.sh` 直连 Moonshot API，非会话模型 | 默认 0，V2≤1 / V3≤2 |
| 裁决者 | **不存在** | 任何需要裁决的情形 → J0 规则（§2） | — |

代理路由现状已满足此分工（`anthropic-deepseek-proxy.py` 的 MODEL_ROUTES：opus→pro、haiku→flash），**无需改代理配置**。夜间启动用 `settings_ds.json` 系配置，主会话 model=opus，子代理 model=haiku。

K3 是**测量工具，不是裁判**：它只输出结构化 issue 清单，pass/fail 永远由确定性门禁判定。配额耗尽或 API 故障时系统降级为纯确定性门禁 + 记录，不阻塞流水线。

---

## 2. 判断真空规则 J0（本文核心）

执行侧没有任何高阶模型，意味着三份提案里所有"升级裁决"的出口必须重定义为以下五种之一，**没有第六种**：

| 夜间遇到的情形 | J0 行为 |
|---|---|
| PRD 与 API 契约冲突 | `BLOCKED_INPUT`：写入 `open-questions.md`（冲突点 + 两个候选解释），跳过该任务继续下一个 |
| 架构歧义（两种合理实现，工作量差 2 倍+） | 选**最小风险路径**（复用现有模式、改动小、可回滚），登记 `assumptions.yaml`，早晨复核；若不可逆 → `blocked_human` |
| 宪法未覆盖的新情况 | 最小风险路径（不删不改不发布）+ `lx-goal blocked-human` 记录，继续 |
| 失败复盘/根因裁决 | 不做。`error-dna.jsonl` 自动记录指纹，早晨人看 |
| 公共组件/Token/路由需要变更 | **夜间禁止**。页面内局部绕开 + 记录，或 `BLOCKED_SCOPE` |

J0 的哲学依据来自宪法自身："人类不在线（30 分钟无回应）：走最小风险路径，暂停等"。无人值守版把"暂停等"改为"记录并继续下一任务"——**单任务可以死，流水线不能停**。

---

## 3. 风险坍缩：为什么这个任务天然适合无人值守

宪法 `api-routing.ts` 三层架构的开发流程第一步就是"全部 mock 静态资源 → 前端独立开发"。夜间所有交互还原（表单提交、筛选、分页、Modal）**全部打在 mock 层**：

- 无真实后端 → 无数据破坏可能 → B2 写操作坍缩为 B1
- 无真实权限 → 无越权可能
- Grok 的 B 级保守主义自动满足：夜间任务集 = B0/B1 only

真实后端联调是白天的事，不在本方案范围。

---

## 4. 流水线总览

```
【有人】Phase 0 睡前 30 分钟（/lx-goal Phase 0，一次性澄清）
   │  输入：PRD 路径 + API 文档路径 + 原型目录 + 目标 repo + antd 裁决
   │  产出：night-manifest.yaml + 路由表预生成 + 每页 plan 骨架 + 预授权清单
   ▼
【无人】Phase 1–N 夜间（每页一个循环，页间隔离）
   │  init → research → plan 冻结 → 实现 → 门禁 C1→C8 → 修复循环 → verify → archive
   │  卡点 → J0 五种行为之一 → 继续下一页
   ▼
【有人】早晨（lx-goal report）
   退出报告 + 每页 acceptance_report + Draft PR 列表 + 结构化阻塞清单 + 成本统计
```

---

## 5. Phase 0：睡前清单（人类窗口期，逐项打勾）

### 5.1 输入收集（缺一则不启动）

- [ ] PRD 路径（每页：目标/角色/区域/字段/动作/状态/AC）
- [ ] API 文档路径（method/path/字段/枚举/错误码/示例）
- [ ] 原型图目录或可访问 URL（含弹窗/抽屉等关键状态截图）
- [ ] 目标 repo 路径 + 基线 SHA（`git rev-parse HEAD` 记入 manifest）
- [ ] **antd 裁决**（二选一，见 §5.2）
- [ ] 页面清单与分级：每页标 L（复杂度）/ V（视觉级）/ 优先级

### 5.2 antd 裁决（P0 前置，二选一）

- **Patch A（默认，自定义组件）**：宪法原样执行，C7 红线全适用。
- **Patch B（antd v6）**：启用以下补丁——
  1. `ConfigProvider` theme 从 `src/styles/tokens/` 生成，禁止组件内 style 覆盖色值；
  2. C3 架构门加一条"优先 antd 组件，禁止重复造 Form/Table/Modal 轮子"；
  3. antd 主题覆盖集中在 `src/styles/antd-theme.ts`，此文件豁免 `.scss ≤300 行` 红线；
  4. 依赖安装（`pnpm add antd`）在 Phase 0 由人类执行或预授权。

### 5.3 路由表预生成（消灭夜间共享文件冲突）

睡前由主会话生成全部页面的**空骨架 + 路由 + 菜单项**，人类确认后提交为一个 commit：

- `src/router/paths.ts`、`src/router/index.tsx` —— 全部页面路由一次到位
- `src/pages/{domain}/index.tsx` —— 空壳（返回 `<div/>`）
- 夜间每个任务的 `files_allowed` 严格限定为 `src/pages/{domain}/**`

效果：夜间任务**零共享文件**，并行不再需要文件租约（§11）。

### 5.4 环境自检（任一失败则不启动）

```bash
lsof -i :9001 | grep LISTEN          # dev server 必须在跑（宪法：AI 不得启动）
curl -s http://127.0.0.1:9998/health # 代理健康（路由到 v4-pro/flash）
# MCP playwright / chrome-devtools 各执行一次截图 smoke test
# 原型需登录的：确认登录态有效（宪法：需登录→告知用户协助）
git status --short                   # 工作区干净
```

### 5.5 预授权清单（写入 manifest，夜间越此清单即熔断）

```yaml
night-manifest.yaml:
  base_sha: <commit>
  pages: [{id, domain, L, V, files_allowed, ac_count}]
  pre_authorized:
    - "pnpm dev --port 9001 重启（仅当 9001 无监听且日志显示崩溃）"
    - "pnpm add <具体包名>（仅 Patch B 的 antd 及图标库）"
  deny:
    - "src/styles/tokens/**"
    - "src/components/shared/**"
    - "src/router/**"          # Phase 0 已预生成
    - "package.json（除预授权行）"
    - "src/auth/**"
  budgets: { per_page_calls: 20, fix_rounds: 4, visual_rounds: 3,
             page_wall_clock_min: 90, night_wall_clock_min: 600,
             kimi_calls_total: 5 }
  visual_diagnosis: enabled    # 或 disabled：全局关闭 K3 工具
```

### 5.6 激活

```bash
python3 .claude/skills/lx-goal/scripts/lx-goal.py on "前端还原夜跑 {date}"
ls -la .omc/state/tokens/lx-goal.json .omc/state/tokens/autonomous.active  # 验证激活
```

---

## 6. 夜间单页循环（12 步，全部映射真实命令）

每页一个独立任务目录，由 `carros_base.py` 管理状态（铁律 #7：先 init 后动手）：

```bash
python3 .claude/scripts/carros_base.py init --task-id FE-{domain} --step S1 --step S2 ...
```

| 步 | 动作 | 产物/命令 |
|---|---|---|
| 1 | **research**：Playwright 对原型局部精确测量（栅格/字号/间距/色值）；扫描仓库同类页面与可复用组件 | `research.md` + 测量数据落 `artifacts/` |
| 2 | **plan 冻结**：files_allowed（仅 `src/pages/{domain}/**`）、AC 逐条、verification 命令、rollback | `plan.md`（冻结后不可改） |
| 3 | **骨架**：页面目录四件套（index.tsx / index.module.scss / components/ / hooks/），类名按 `{domain}_{component}` 规范 | 原子 commit |
| 4 | **结构实现**：布局 + 组件拆分 + Token 取色（禁止硬编码） | 原子 commit |
| 5 | **交互实现**：表单/筛选/分页/Modal，全部接 mock（api-routing 全 mock） | 原子 commit |
| 6 | **C1 范围门**：`git diff --name-only {base_sha}` ⊆ files_allowed | 越界 → 回退越界文件 + 熔断 |
| 7 | **C2 代码门**：`pnpm typecheck && pnpm lint && pnpm build` | 失败 → §9 失败分类路由 |
| 8 | **C3 架构门**：C7 机器检查（行数/裸色值/魔法 px/功能块数） | `scripts/c7-check.sh`（§7.3） |
| 9 | **C4/C5 功能交互门**：Playwright 交互 spec（正常/空/加载/失败/防重/关闭行为） | `playwright {domain}.spec.ts` |
| 10 | **C6 视觉门**：chrome-devtools 三视口截图对比（xl 1440 主验收 / lg / md） | 截图落 `.omc/screenshots/{task}/` |
| 11 | **修复循环**：不过 → §9 路由修复 → 重跑门禁；视觉不收敛且 V2/V3 → §8 K3 工具（配额内） | 每轮更新 `executor.md` |
| 12 | **verify + archive**：`carros_base.py verify` → VERIFIED → `archive`；页面进独立分支 | `acceptance_report.md` |

每步执行前更新 progress.md + 写 evidence（lx-goal 文档强约束：跳过文档直接执行 = 违反哲学 #7）。

**页级熔断**（命中任一 → 本页 BLOCKED，记录原因，立即开始下一页）：
- 同一失败指纹复现 2 次且代码/输入/环境无有效变化（`failure.json` 指纹比对）
- 超 per_page_calls / fix_rounds / page_wall_clock
- Diff 越出 files_allowed 两次
- D2 级需求缺口（PRD/API 冲突）

**夜级熔断**（命中任一 → 全线停止，等早晨）：
- dev server 崩溃且预授权重启后仍失败
- 连续 3 页因同一环境问题 BLOCKED
- git 状态损坏（无法 checkout 干净分支）

---

## 7. 门禁细则（C0–C8 → 具体命令）

### 7.1 门禁总表

| 门 | 内容 | 执行者 |
|---|---|---|
| C0 输入门 | Phase 0 已完成，D2 已澄清 | 人类（睡前） |
| C1 范围门 | diff ⊆ files_allowed；无锁文件/生成物混入 | git 命令 |
| C2 代码门 | typecheck / eslint --max-warnings 0 / stylelint / build | pnpm 脚本 |
| C3 架构门 | C7 红线 + 目录铁律 + 复用检查 | c7-check.sh + 自查 |
| C4 功能门 | 正常/空/加载/接口失败/重复提交 | Playwright |
| C5 交互门 | 防重/关闭行为/焦点/成功后刷新 | Playwright |
| C6 视觉门 | 确定性对比（bbox/溢出/控制台错误/像素 diff 带 mask） | chrome-devtools |
| C7 证据门 | 每条 AC 绑当前 SHA 的截图/trace/命令输出 | Verifier 上下文 |
| C8 回归门 | 动了公共依赖时跑受影响页面（夜间 deny 清单使此门通常空转） | Playwright |

### 7.2 验收独立上下文

Verifier 不使用实现者的成功结论：新起上下文，只读 AC + 门禁原始输出 + artifacts 证据，输出 PASS/FAIL/BLOCKED/NA 逐条判定。可调用 `/lx-oracle review` 做静态分析复核。同模型不同上下文——执行侧没有第二种模型可用，这是 J0 下的最大独立性。

### 7.3 C7 机器检查（`scripts/c7-check.sh` 规格）

```bash
# 对 git diff 涉及的 .tsx/.module.scss：
# 1. wc -l ≤300（超出 → fail）
# 2. grep -E '#[0-9a-fA-F]{3,8}' （裸色值 → fail，tokens 文件除外）
# 3. grep -E '[0-9]+px'（魔法 px → fail，断点变量文件除外）
# 4. 单文件功能块 >3（export 数粗判 → warn 转人工）
```

### 7.4 防作弊红线（命中即 C6/C7 fail 并熔断本页）

隐藏未实现区域 / 静态图替真实组件 / 单视口绝对定位硬凑 / 更新基线截图 / 删测试或放宽断言 / 关真实交互。

---

## 8. K3 视觉诊断工具契约（默认关闭，按页开启）

**触发条件（同时满足，缺一不调）**：本页 V2/V3 且 `visual_diagnosis: enabled`；C2/C4/C5 已全绿；偏差非"页面打不开/接口报错/CSS 编译错"；Pro 已做过 ≥1 轮 chrome-devtools 对比修复；本页配额未耗尽。

**调用**：

```bash
scripts/kimi-visual-diag.sh \
  --design  .omc/screenshots/{task}/design-xl.png \
  --impl    .omc/screenshots/{task}/impl-xl.png \
  --region  "header+table" --viewport "1440x900" \
  --tokens  .omc/task/{task}/token-summary.md \
  --out     .omc/task/{task}/visual-diag.json
```

直连 Moonshot API（`MOONSHOT_API_KEY` 从环境变量读，**禁止写入任何入库文件**），不经代理，配额独立计数。

**输出 Schema**（校验失败视为本次调用无效，计配额但不重调）：

```json
{
  "verdict": "pass | fail | uncertain",
  "issues": [{
    "priority": "P0 | P1 | P2",
    "region": "header | main | table | form | modal",
    "category": "layout | spacing | typography | color | component",
    "observation": "可观察差异",
    "suggestion": "不绑实现细节的方向",
    "confidence": 0.0
  }],
  "stop_recommended": false
}
```

输出交 Pro 修改 → 工具重验。**不自动二次调用**。P0 结构差异存在即整页视觉门不过。配额耗尽仍有 P0 → 本页标 `VISUAL_BLOCKED`，照常交付门禁内部分，早晨人工定夺。

---

## 9. 失败分类路由（Grok 表，替代"2 次失败升级"）

| 失败类型 | 立即路由 | 禁止 |
|---|---|---|
| CompileError / LintError / 简单 TypeError | Flash | 不要 Pro 浪费钱 |
| 跨文件类型传导 / 状态流错误 / 复杂泛型 | Pro（立即） | 不让 Flash 撞两轮 |
| 交互失败且根因不清 | Pro + Playwright trace 分析 | 不盲改 |
| ApiContractError（PRD 与 API 打架） | **J0：BLOCKED_INPUT**，不升级模型 | 禁止"聪明地编" |
| EnvironmentError（dev server/MCP/网络） | 恢复流程（§10），不改业务代码 | 不把环境抖动当 bug 修 |
| VisualError | Pro 修 1 轮 → 不收敛且 V2/V3 → K3 工具 | 不超配额 |
| RequirementGap | J0：阻塞 | — |

每次修复必须产生变化摘要；`failure.json` 指纹相同且代码/环境/输入无有效变化 → 禁止再试，页级熔断。

---

## 10. 健壮性设计（无人值守专项）

| 故障 | 行为 |
|---|---|
| 上下文压缩 / 会话崩溃 | 磁盘态恢复：token.json(CAS) → handoff.md → plan.md 最后一步继续（CarrorOS 抗 Compact 设计 + lx-goal 跨会话续跑，均已有） |
| 机器重启 / 新会话 | 检测 `.omc/state/tokens/lx-goal.json` 存在 → 读 goal + 过期时间 → 从断点续跑，不重新 Phase 0 |
| chrome-devtools MCP 断线 | 退避重连 3 次（30s/2min/5min）→ 仍断：本页标 `BLOCKED_ENV` 继续下一页；**遵守宪法"不得降级"**，不跳过视觉门假装通过 |
| playwright MCP 断线 | 同上 |
| DeepSeek API 限流/超时 | 指数退避（1m/5m/15m），3 次失败 → 本页 BLOCKED_ENV；连续 3 页同因 → 夜级熔断 |
| K3 API 故障 | 计配额、降级为纯确定性门禁、记录，不阻塞 |
| dev server 死亡 | 仅当命中预授权条款时重启一次；再死 → 夜级熔断 |
| 模型越界改文件 | PreToolUse hook（G1-G6）拦截 + C1 门兜底 + 越界文件 checkout 回退 |
| 早晨前完成全部页面 | `lx-goal report` → `lx-goal off`，正常退出 |

---

## 11. 并行策略（首夜保守）

- **首夜：串行**。目标是校准（单页耗时、门禁通过率、K3 收益），不是吞吐。
- **第二夜起：≤2 路并行**。前提：lx-race 从 `.claude/skills/archived/` 恢复并验证；两路任务的 domain 目录无交集（§5.3 已保证零共享文件）；共享资源（dev server 9001、K3 配额、API 限流）串行化。
- 不并行超过 2 路：DeepSeek 限流未知，且视觉门共用同一个浏览器实例。

---

## 12. 早晨报告（lx-goal report 扩展格式）

```markdown
# Night Run {date}

## 总览
页面：完成 x/y | 门禁全绿 x | VISUAL_BLOCKED x | BLOCKED_INPUT x | BLOCKED_ENV x
成本：Pro 调用 n 次 / Flash n 次 / K3 n 次（$估算）
墙钟：xh ym

## ✅ 可验收（每页一行）
FE-order: 14/14 AC PASS, 视觉 xl 视口通过, 分支 fe/order-20260718, Draft PR #n

## ⚠️ 需你裁决（J0 结构化阻塞）
1. [BLOCKED_INPUT] FE-report: PRD §3.2 说导出含已删除行，API 文档说不含 → 两个候选解释在 open-questions.md
2. [blocked_human] FE-ecosystem: 注册向导需要新增 token `color_warning`，已局部绕开（assumptions.yaml #3）

## 🔧 需工程处理
1. [BLOCKED_ENV] chrome-devtools 03:12 掉线未恢复，影响 2 页视觉门

## 📋 假设登记（可回滚，复核用）
assumptions.yaml 共 4 条，逐条列出

## 🧬 失败 DNA
error-dna.jsonl 新增 3 指纹，Top1: playwright:modal-close-esc（出现 2 页）
```

---

## 13. 回答 Grok 的三个杀手问题

**Q1：没有专职前端，谁拥有 Design System 和 shared 组件合同？**
人类（早晨复核者）。夜间 deny 清单物理禁止 AI 触碰 `src/styles/tokens/**` 和 `src/components/shared/**`——AI 只能**使用**设计系统，不能**修改**。需要新 token/新 shared 组件 → blocked_human + 页面内局部绕开 + 记录。Design System 的每一次演化都经过人。

**Q2：PRD/API/设计冲突时，系统会停还是会"聪明地编"？**
停。J0 表第 1 行 + D2 阻塞 + 宪法防错规则"只兜底显示，不兜底数据"三重保证。冲突进 open-questions.md（带候选解释），页面跳过，流水线继续。**系统没有任何一条路径允许模型在契约冲突时自行选择一种解释实现。**

**Q3：公共组件有历史病，局部绕开还是允许碰公共面？**
夜间：只允许页面内局部绕开 + assumptions.yaml 登记 + 早晨报告单列。`shared/**` 在 deny 清单里，hook 物理拦截。白天：人类决定修公共面还是接受绕开。**AI 永不夜间碰公共面，没有例外条款。**

---

## 14. 给三位评审的靶子（请直接攻击，别评完整性）

1. **J0 完备性**：是否存在一种夜间情形，"阻塞并继续"在工程上不成立，必须即时裁决？请举反例。
2. **路由表预生成**（§5.3）：睡前生成全部空骨架+路由，换夜间零共享文件——这个交易有没有隐藏代价（如空壳页面误入主干）？
3. **K3 工具默认关闭**：在"执行时无高阶模型"约束下，视觉语义判断缺失会不会导致 V3 页面系统性低分？默认关闭 vs 默认 V3 配额 1，哪个更优？
4. **预算表**：per_page 20 次调用 / 90 分钟墙钟，对"静态+交互还原"是紧是松？请给出你们的数字。
5. **验收独立性**：同模型不同上下文的 Verifier，是否足以防自证？还是必须引入第二个确定性检查层（如独立 Playwright 断言集）？
6. **首夜串行**：是否过于保守？如果 Phase 0 路由预生成可靠，首夜 2 路并行的实际风险是什么？

---

## 15. 落地检查清单（评审通过后，今晚即可执行）

```
□ 用户裁决：antd Patch A / B
□ 用户提供：PRD 路径 / API 文档路径 / 原型目录 / 目标 repo
□ 用户裁决：lx-race 恢复 or 首夜串行（建议串行）
□ 主会话执行：Phase 0 全部（§5），生成 night-manifest.yaml
□ 用户确认 manifest → lx-goal on
□ 睡觉
□ 早晨：lx-goal report → 逐页验收 → 微调
```

---

一句话总结：

> **宪法管边界，carros_base 管状态，lx-goal 管无人值守，DeepSeek 干活，Playwright + chrome-devtools 证明，K3 是可选的测量工具，裁决全部留给早晨的人类——执行侧没有任何高阶模型，也不需要。**
