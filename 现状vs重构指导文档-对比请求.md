# CarrorOS 现状 vs 重构指导文档 — 完整对比分析请求

> 生成时间：2026-07-09
> 用途：将此文档交给 GPT，分析当前项目实现与重构指导文档的差距，输出可执行的工作清单。

---

## 一、背景

CarrorOS 是一个 AI 治理系统（"文件状态机治理方案"），经历了三轮重构设计。14 份重构指导文档位于 `重构指导文档/` 目录，是第三轮重构的完整设计方案。

当前项目已按第三轮方案进行了实现，但存在差距。本文档收集了完整的项目现状数据，请你对比分析。

---

## 二、重构指导文档清单（14 份，约 440KB）

| 文件 | 大小 | 核心内容 |
|------|------|----------|
| `1.md` ~ `10.md` | 38KB~19KB | 第三轮重构完整设计（10 次迭代） |
| `11-oracle-roadmap.md` | 2.9KB | Oracle 路线决策记录（最终选择 Option C: 永久 static_stub） |
| `总结.md` | 12KB | 第三轮方案最终评价 — 附条件核准，7 个必须修正点 |
| `update.md` | 11KB | 瘦身更新方案 — 10 模块降级为内部实现，BASE 压缩为 4 命令 |
| `data.md` | 31KB | 资产清单 — 27 Skills + 77 Hooks 的 ROI 分析 |
| `data_todo.md` | 27KB | 资产筛选裁决 — 保留/降级/删除三集合，`.claude/` vs `.omc/` 红线 |
| `align_report.md` | 1.8KB | 最终对齐报告 — 14 项全部对齐声明 |
| `gap_analysis.md` | 2.0KB | 差距分析 — 15 项检查点 |
| `deepseek-ultra.md` | 43KB | UltraThink 完整知识库（提示词工程，非治理系统直接相关） |
| `test.md` | 0KB | 空文件 |

### 重构指导文档的核心裁决结论

**总裁决：附条件核准。** 架构方向正确，但需要瘦身 + 验证。

**核心要求（7 个强制修正点，来自 `总结.md`）：**

1. 增加最小真实任务基准（7 个 bench 场景）
2. 增加 `omc_lint.py` 统一校验
3. 区分 Oracle 静态 stub 与真实模型 Oracle
4. BASE 命令入口瘦身（用户认知入口不暴露 10 个治理模块）
5. 增加 audit 完整性检查
6. 增加 schema version（token.json / audit event / executor evidence）
7. 冻结 Markdown 模板（plan.md / executor.md 必须有 lint）

**最终形态目标（来自 `update.md`）：**

```
L1 / Base Workflow:  Plan → Step → Verify → Archive
L2 / Enhance Workflow: Base + Context Watermark + Low-frequency Oracle + Learning Flywheel

用户主心智只保留 4 个核心动作: plan / step / verify / archive
其他 6 个模块降级为内部实现: IntakeGate, PreActionGate, ExecutorLedger, ContextEngine, Fallback, CLI
```

---

## 三、当前项目完整文件结构

### 3.1 顶层文件

```
CarrorOS/
├── AGENTS.md              # 核心入口（哲学7条 + 铁律6条 + L1/L2路由 + Oracle评审表）
├── CLAUDE.md              # → @ AGENTS.md（转发）
├── README.md              # 项目概述（架构、10模块说明、快速开始、目录结构）
└── diff.md                # 未知用途
```

### 3.2 `.claude/` 目录（可复用资产层）

```
.claude/
├── settings.json           # 6 个 hooks 注册 + StatusLine
├── settings.local.json     # 权限 allowlist（~80 条 Bash/Read 权限）
├── harness.yaml            # hook 开关表（10 个 hook 配置）
├── kernel.md               # 管理内核（冻结规则 / 飞轮 / 三段式水位 / Oracle / 降级）
├── index.md                # 渐进披露路由表（工作流/Hook/Skill/Schema/Reference 路由）
├── session-handoff.md      # 上次会话交接文件
├── last-user-prompt.md     # 上次用户提示
├── claude-next.md          # 经验学习（范式）
├── mcp.json                # MCP 配置
│
├── hooks/ (20 个文件)
│   ├── hook-launcher.sh           # Hook 启动器
│   ├── carroros_hooklib.py        # Hook 共享库
│   ├── pretool-gate.py            # ★ 主 PreToolUse 门禁（538行）
│   ├── pretool-action-gate.py     # 安全门禁
│   ├── pretool-edit-scope.py      # 编辑范围检查
│   ├── pretool-sensitive-edit.py  # 敏感文件保护
│   ├── pretool-plan-gate.py       # Plan 门禁
│   ├── pretool-verify-gate.py     # Verify 门禁
│   ├── pretool-fallback-check.py  # Fallback 检查
│   ├── pretool-oracle-gate.py     # Oracle 门禁
│   ├── posttool-audit.py          # ★ 审计 hook
│   ├── posttool-output-compress.py # 输出压缩
│   ├── posttool-archive-check.py  # Archive 检查
│   ├── posttool-completion-gate.py # ★ 完成门禁
│   ├── userprompt-level-hint.py   # ★ L1/L2 等级提示
│   ├── userprompt-prompt-collector.py # Prompt 收集
│   ├── userprompt-session-start.py   # 会话启动
│   ├── userprompt-session-resume.py  # 会话恢复
│   ├── statusline-command.sh         # StatusLine 渲染
│   └── __pycache__/
│
├── scripts/ (24 个文件，部分为 symlink → .omc/scripts/)
│   ├── carros_base.py → symlink      # 核心引擎 (实际在 .omc/, 1551行)
│   ├── carros_utils.py               # 工具函数 (4454行)
│   ├── omc_lint.py → symlink         # Lint 工具 (实际在 .omc/, 299行)
│   ├── verify_gate.py                # VerifyGate (359行)
│   ├── verify_tests.py               # Verify 测试 (26619行)
│   ├── context_engine.py             # Context Engine (618行)
│   ├── context_watermark.py           # 水位检测 (102行)
│   ├── executor_ledger.py            # Executor Ledger (14202行)
│   ├── plan_builder.py               # Plan Builder (16597行)
│   ├── intake_gate.py                # Intake Gate (9626行)
│   ├── archive_engine.py → symlink   # Archive Engine (实际在 .omc/)
│   ├── fallback_engine.py → symlink  # Fallback Engine (实际在 .omc/)
│   ├── fallback_matrix.py            # 降级矩阵 (153行)
│   ├── pre_action_gate.py → symlink  # PreAction Gate (实际在 .omc/)
│   ├── oracle_engine.py → symlink    # Oracle Engine (实际在 .omc/, 490行)
│   ├── oracle_gate.py                # Oracle Gate (138行)
│   ├── oracle_agent.py               # Oracle Agent (static_stub)
│   ├── oracle_spawn.py               # Oracle Spawn (static_stub)
│   ├── meta_oracle.py                # Meta Oracle (static_stub)
│   ├── static_oracle_agent.py        # Static Oracle Agent (static_stub)
│   ├── runtime_oracle_agent.py       # Runtime Oracle Agent (static_stub)
│   ├── statusline.py                 # StatusLine 渲染
│   ├── deepseek_inject.py            # DeepSeek 注入
│   ├── honesty_audit.py              # 诚实审计
│   └── output_compress.py            # 输出压缩
│
├── skills/ (26 个 skill 目录)
│   ├── lx-code-review/
│   ├── lx-dogfood/
│   ├── lx-ghost/
│   ├── lx-git-check/
│   ├── lx-goal/
│   ├── lx-learner/
│   ├── lx-oma-gov/
│   ├── lx-oma-hier/
│   ├── lx-oma-orch/
│   ├── lx-oma-split/
│   ├── lx-oracle-agent/
│   ├── lx-oracle-meta/
│   ├── lx-oracle-review/
│   ├── lx-root-cause-analysis/
│   ├── lx-rpe/
│   ├── lx-skillify/
│   ├── lx-task-spec/
│   ├── lx-validate-skill/
│   ├── lx-varlock/
│   ├── archived/
│   ├── references/
│   ├── TEMPLATE.md
│   ├── SKILLS.md
│   └── skill-dependencies.yaml
│
├── references/ (14 个参考文档)
│   ├── SUBAGENT.md
│   ├── SOUL.md / philosophy.md
│   ├── oracle-spec.md
│   ├── context-watermark.md
│   ├── fallback-matrix.md
│   ├── anti-patterns.md
│   ├── omc-path-conventions.md
│   ├── oracle-dual-agent-refactor-v1.md
│   ├── skill-atomization-guide.md
│   ├── feature-registry.yaml
│   ├── session-handoff.md
│   ├── meta_oracle.py / oracle_agent.py
│
├── schemas/ (JSON Schema + YAML 合约)
│   ├── token.schema.json / token.md
│   ├── atomic/ (8 个原子 schema)
│   ├── contract/state_transitions.yaml
│   ├── input/task_input.yaml
│   ├── output/ (4 个输出 schema)
│   └── registry.yaml
│
├── nodes/ (原子化节点，23 个)
├── profiles/ (配置 profiles，9 个)
├── rules/ (规则文件)
│   ├── terminal-safety.md
│   └── bash-style.md
├── task_sys/ (任务系统模板)
└── worktrees/
```

### 3.3 `.omc/` 目录（运行时实例层）

```
.omc/
├── scripts/ (16 个脚本 — 核心实现)
│   ├── carros_base.py         # 核心引擎 (1551行) — init/status/tick/verify/archive/lint/bench
│   ├── omc_lint.py            # Lint 工具 (299行) — 7 项检查
│   ├── oracle_engine.py       # Oracle 引擎 (490行) — static_stub
│   ├── oracle_gate.py         # Oracle 门禁 (138行)
│   ├── archive_engine.py      # Archive 引擎
│   ├── fallback_engine.py     # Fallback 引擎
│   ├── pre_action_gate.py     # PreAction 门禁
│   ├── context_watermark.py   # 水位检测
│   ├── fallback_matrix.py     # 降级矩阵
│   ├── feature_verify.py      # 特性验证
│   ├── randomized_bench.py    # 随机化 bench
│   ├── task_state_tracker.py  # 任务状态追踪
│   ├── init-omc.sh            # 初始化脚本
│   └── __pycache__/
│
├── tasks/ (8 个任务)
│   ├── 20260707/              # ★ 旧日期格式 (应为 2026-07-07)
│   │   ├── bench-01/ ~ bench-07/  # 7 个 bench 任务
│   │   │   ├── plan.md
│   │   │   ├── executor.md
│   │   │   ├── research.md
│   │   │   └── state/audit/{date}.jsonl
│   │   └── cap-test-001/
│   └── 2026-07-06/
│       └── unknown_task/
│
├── tokens/ (9 个 token 文件)
│   ├── 2026-07-07/lx-goal.json
│   ├── 2026-07-08/ (5 个 token)
│   └── 2026-07-09/ (5 个 token)
│
├── state/ (运行时状态)
│   ├── token.json            # 当前会话 token
│   ├── goal-report.md        # Goal 报告
│   ├── fallback-events.jsonl # Fallback 事件
│   ├── audit/                # 审计日志
│   └── runtime-oracle-verdicts/ # Oracle 裁决
│
├── archive/                  # 归档
├── audit/                    # 全局审计
├── plans/                    # 计划
└── reference/                # 参考
```

---

## 四、当前已注册的 Hooks（活跃运行中）

来自 `settings.json`，共 **6 个 hook 注册点**，实际触发 **8 个脚本**：

| 触发点 | Hook 脚本 | 用途 |
|--------|----------|------|
| **StatusLine** | `statusline-command.sh` | 终端状态栏展示 |
| **UserPromptSubmit** | `userprompt-level-hint.py` | L1/L2 等级提示注入 |
| | `userprompt-prompt-collector.py` | Prompt 收集 |
| **PreToolUse** | `pretool-gate.py` (538行) | 主门禁 — 聚合安全/范围/Oracle/Plan/Fallback 检查 |
| **PostToolUse** | `posttool-audit.py` | 审计记录 |
| | `posttool-output-compress.py` | 输出压缩 |
| | `posttool-archive-check.py` | Archive 检查 |
| **Stop** | `posttool-completion-gate.py` | 完成门禁 — 阻止无证据完成 |

`harness.yaml` 中还声明了 10 个 hook 的配置开关（包括 `pretool-fallback-check`, `pretool-action-gate`, `pretool-edit-scope`, `pretool-sensitive-edit`, `pretool-plan-gate`, `pretool-level-gate`, `posttool-audit`, `completion-gate`, `pretool-compact-writer`），但实际注册在 `settings.json` 中的只有上述 6 组。

---

## 五、当前 Scripts 按 10 模块分类

第三轮设计中的 10 个治理模块在当前代码中的实现状态：

| 模块 | 实现文件 | 行数 | 状态 |
|------|---------|------|------|
| **1. IntakeGate** | `intake_gate.py` | 9,626 | ✅ 已实现 |
| **2. PlanBuilder** | `plan_builder.py` | 16,597 | ✅ 已实现 |
| **3. PreActionGate** | `pre_action_gate.py` (omc) / `pretool-gate.py` (hooks) | ~21,000 | ✅ 已实现 |
| **4. ExecutorLedger** | `executor_ledger.py` | 14,202 | ✅ 已实现 |
| **5. VerifyGate** | `verify_gate.py` / `verify_tests.py` | 359 + 26,619 | ✅ 已实现 |
| **6. ContextEngine** | `context_engine.py` / `context_watermark.py` | 618 + 102 | ✅ 已实现 |
| **7. Oracle/Meta-Oracle** | `oracle_engine.py` + 6 个 agent 脚本 | ~2,000+ | ✅ 已实现 (static_stub) |
| **8. FallbackProtocol** | `fallback_engine.py` / `fallback_matrix.py` | ~500+ | ✅ 已实现 |
| **9. CLIIntegration** | `statusline.py` / `statusline-command.sh` | ~300 | ✅ 已实现 |
| **10. ArchiveEngine** | `archive_engine.py` | ~500 | ✅ 已实现 |

**核心引擎 `carros_base.py` (1551行) 提供的命令：**
- `init` — 初始化任务（含 Intake + Plan 创建）
- `status` — 查看状态（CLI 展示）
- `tick` — 轮次递增
- `verify` — 验证 step
- `archive` — 归档
- `lint` — 运行 omc_lint
- `bench` — 运行 bench 测试

---

## 六、重构指导文档的关键要求 vs 当前现状对比

### 6.1 总结.md 的 7 个强制修正点

| # | 要求 | 当前状态 | 差距判断 |
|---|------|---------|---------|
| 1 | 增加最小真实任务基准（7 个 bench） | 7 个 bench 任务已创建（`20260707/bench-01~07`），各有 plan.md/executor.md | **形式上完成**，但日期格式使用旧格式 `YYYYMMDD`，且未见统一的 bench runner 和评分标准 |
| 2 | 增加 `omc_lint.py` | `omc_lint.py` 已存在（299行），含 7 项检查 | **基本完成**，但规模偏小（299行 vs 指导要求的多维度检查） |
| 3 | 区分 Oracle static_stub 与真实模型 Oracle | 9 个 Oracle 相关文件全部标注 `static_stub`，已决策永久不接入模型 API（Option C） | **已完成**，方向与 `11-oracle-roadmap.md` 一致 |
| 4 | BASE 命令入口瘦身（不暴露 10 个模块） | `carros_base.py` 提供 7 个命令（init/status/tick/verify/archive/lint/bench），但 10 个模块的独立脚本仍然全部存在 | **部分完成** — 入口已统一到 carros_base.py，但独立模块脚本未删除/合并 |
| 5 | 增加 audit 完整性检查 | `omc_lint.py` 含 JSONL 可解析检查 + verify 事件计数 | **基本完成**，但缺少 archive 前的 audit integrity scan |
| 6 | 增加 schema version | 未见 schema_version 字段（需确认 token.json / audit event / executor evidence 中是否有） | **未完成** |
| 7 | 冻结 Markdown 模板 + plan_lint | plan.md / executor.md 使用 `- [ ] STEP_ID:` 格式，但无正式的 lint 模板校验 | **未完成** |

### 6.2 update.md 的瘦身要求

| 要求 | 当前状态 | 差距 |
|------|---------|------|
| 10 模块降级为内部实现，用户主心智只保留 4 个核心动作 | README.md 仍然列出全部 10 个模块，每个模块有独立大脚本 | **未完成** — 文档和代码结构仍暴露 10 模块 |
| BASE 合并为单文件 `carros_base.py` | `carros_base.py` 1551行，但 10 个模块各有独立大文件（总计 ~70,000+ 行） | **部分完成** — 入口统一但文件未合并 |
| Base 最小文件集（9 个文件） | 实际 .claude/ + .omc/ 脚本超过 40 个 | **未完成** — 文件数量远超最小集 |
| AGENTS ≤ 2000 token | 当前 AGENTS.md 约 80 行，较精简 | **基本符合** |
| kernel.md ≤ 500 token | 当前 kernel.md 约 35 行，较精简 | **基本符合** |
| 三段式水位（0-40/40-70/70+）替代 70/85 二段式 | kernel.md 已描述三段式水位，`context_watermark.py` 已实现 | **已完成** |
| Oracle 降频（只保留 5 个触发点） | Oracle 脚本全标 static_stub，触发仍为 5 点 | **已完成** |
| Hook 输出总量 ≤ 1500 token | 6 个活跃 hook 每步输出约 ≤2 行 JSON | **基本符合** |
| archive = lint + verify-summary + final-report + tombstone | `carros_base.py archive` 命令已实现 | **基本完成** |

### 6.3 data_todo.md 的资产归属红线

| 红线 | 当前状态 | 差距 |
|------|---------|------|
| `.claude/` 不存运行状态 | `.claude/session-handoff.md` 为运行状态文件（应在 `.omc/`） | **违规** |
| `.omc/` 不存可复用资产 | `.omc/scripts/` 存放了大量可复用脚本（应属于 `.claude/`） | **违规** — 且产生大量 symlink |
| `kernel.md` / `index.md` 应在 `.claude/` | ✅ 已在 `.claude/` | **符合** |
| `research.md` / `claude-next.md` / `error-dna.json` 应在 `.omc/` | `claude-next.md` 在 `.claude/`（应在 `.omc/`），`error-dna.json` 未见 | **部分违规** |

### 6.4 data_todo.md 的保留/删除裁决

**强保留资产（4 个 Skills）对照：**

| 应保留 | 当前状态 |
|--------|---------|
| `lx-varlock` | ✅ 存在 |
| `lx-todo` | ✅ 存在 |
| `lx-validate-skill` | ✅ 存在 |
| `update-carror-os` | ✅ 存在 |

**应删除的 Hook 类型（9 类）对照：**

| 应删除 | 当前状态 |
|--------|---------|
| Base PostToolUse 全局 Hook | ⚠️ `posttool-audit.py` 仍在每次 PostToolUse 触发 |
| Enhance PostToolUse 常驻 Hook | ⚠️ 同上 |
| 每 step Oracle Hook | ✅ Oracle 只在 pretool-gate 中低频检查 |
| 每 step Meta-Oracle Hook | ✅ 未常驻触发 |
| 无来源 context 百分比 Hook | ⚠️ `context_watermark.py` 依赖轮次计数（非真实 token 观测） |
| 写入 handoff 新状态的 Hook | ⚠️ 需确认 |
| statusline 作为 evidence 的 Hook | ✅ statusline 已明确为展示层 |
| 自动修改 AGENTS.md 的 Hook | ✅ 无此 Hook |
| Base 飞轮写入 Hook | ⚠️ 需确认 |

### 6.5 gap_analysis.md 的 15 项检查点

| # | 检查点 | 状态 |
|---|--------|------|
| 1 | session-handoff.md 四件套完整 | ✅ |
| 2 | 7 个 bench README 填充 | ✅ |
| 3 | `--step` 参数 | ✅ |
| 4 | omc_lint audit jsonl 检查 | ✅ |
| 5 | Hook 输出 ≤2 行 | ✅ |
| 6 | 文档与代码路径对齐 | ⏳ "需确认" |
| 7 | index.md 路由系统可调用 | ⏳ "需确认" |
| 8 | bench 最高优先级完成 | ✅ |
| 9 | L1 完全闭环 | ✅ |
| 10 | L1 从 AGENTS.md 引用 core 工具 | ⏳ "需确认" |
| 11 | oracle-spec.md 从 stub 变可调用 | ❌ "需补" |
| 12 | context-watermark.md 从 stub 变可检测 | ❌ "需补" |
| 13 | fallback-matrix.md 从 stub 变可执行 | ❌ "需补" |
| 14 | 工作流文档（plan.md 2.0） | ⏳ |
| 15 | L2 有完整技能和双法官规格 | ⏳ |

---

## 七、关键数据统计对比

| 指标 | 重构指导文档目标 | 当前现状 | 偏差 |
|------|----------------|---------|------|
| 用户可见模块数 | 4 (plan/step/verify/archive) | 10 个模块全部在 README 中列出 | **+150%** |
| 核心脚本数（BASE） | 1 (carros_base.py) | ~24 个脚本（含 symlink） | **+2300%** |
| 活跃 Hook 注册数 | "少" | 6 组注册点，8 个实际脚本 | 适中 |
| Hook 总文件数 | "减少" | 20 个 hook 文件 | 偏多但仅 6 组活跃 |
| Skills 数量 | 4 个核心 + 条件保留 | 26 个 skill 目录 | **+550%** |
| Oracle 实现等级 | static_stub（Option C） | static_stub | ✅ 一致 |
| Bench 任务数 | 7 个 | 7 个 | ✅ 一致 |
| omc_lint 检查项 | 7 项 | 7 项（但实现较浅） | 基本一致 |
| 日期格式 | YYYY-MM-DD | 混合（新旧并存） | **不一致** |
| `research.md` 位置 | Base 禁止 / Enhance Plan-only | bench 任务中均有 research.md | Base 中存在（违规） |
| `claude-next.md` 位置 | `.omc/docs/` | `.claude/claude-next.md` | **位置错误** |
| `.claude/` vs `.omc/` 边界 | 严格分离 | symlink 交叉引用，边界模糊 | **违规** |

---

## 八、当前项目的主要结构性问题（初步判断）

### 8.1 资产归属混乱（.claude vs .omc）
- `.omc/scripts/` 存放了 `carros_base.py`、`omc_lint.py`、`oracle_engine.py` 等可复用脚本（应属于 `.claude/`）
- `.claude/scripts/` 通过 symlink 指向 `.omc/scripts/`，说明原始设计有误
- `.claude/session-handoff.md` 是运行时状态文件，不应在 `.claude/`
- `claude-next.md` 在 `.claude/` 根目录，应在 `.omc/docs/`

### 8.2 10 模块暴露过度
- README 仍然将 10 个模块作为架构核心描述
- 每个模块有独立的大脚本文件（部分超过 10,000 行）
- 与 "用户只看到 4 个命令" 的目标不符

### 8.3 文件膨胀
- `plan_builder.py` (16,597行), `executor_ledger.py` (14,202行), `verify_tests.py` (26,619行) 文件极大
- 总脚本代码量远超 "BASE 单文件轻量" 的目标

### 8.4 日期格式不统一
- README 规定 `YYYY-MM-DD`，但 `tasks/20260707/` 使用旧格式
- `tokens/` 已迁移到新格式，但 tasks 未迁移

### 8.5 Schema Version 缺失
- 指导文档明确要求所有结构化文件带 schema_version，当前未见实现

### 8.6 Plan.md 模板无 Lint
- 虽然 `omc_lint.py` 存在，但没有对 plan.md 格式的严格 lint

---

## 九、分析任务请求

请基于以上数据，完成以下分析：

### A. 差距量化
1. 逐条对比 "总结.md 的 7 个强制修正点"，给出每项的完成百分比和剩余工作量估算
2. 逐条对比 "update.md 的瘦身要求"，判断哪些已完成、哪些被忽略
3. 评估 "gap_analysis.md 的 15 项检查点" 的实际完成情况（对齐报告声称"全部修复"，但差距分析显示多项"需确认/需补"）

### B. 优先级排序
4. 将发现的差距按 "阻塞上线 / 影响质量 / 可延后" 三级排序
5. 给出前 5 个最关键的修复项，每个附带：
   - 当前状态
   - 目标状态
   - 涉及文件
   - 预估改动量

### C. 结构性问题诊断
6. 分析 `.claude/` vs `.omc/` 边界模糊的根因，给出迁移方案
7. 判断 26 个 Skills 中哪些可以安全归档/删除，给出精简到 4~6 个核心 skill 的路径
8. 判断 20 个 Hook 文件中哪些是冗余的，哪些必须保留

### D. 可执行工作清单
9. 输出一份可直接执行的工作清单（按执行顺序排列），每项包含：
   - 任务名称
   - 涉及文件列表
   - 具体操作（移动/删除/修改/新增）
   - 验收标准
10. 估算总工作量（人·小时）
