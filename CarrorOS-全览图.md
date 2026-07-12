# 🏛️ CarrorOS 桌面版（Base）全览图

> 生成日期：2026-07-12（v7.1.0 — 结构重构）
> 版本：Base (DeepSeek V4 Flash / 中低阶模型治理套件)
>
> 本次重构变更：资产边界清理 → 运行时文件移入 .omc/ → 重构文档归档 → kernel/index 更新 → Nodes 热冷分离 → 技能合并（OMA 4→1, Oracle 3→1）

---

## 一、物理资源总览

| 区域 | 规模 | 说明 |
|------|------|------|
| **总文件数** | ~200+ 文件 | 纯 Python / Bash / Markdown，无 node_modules |
| **`.claude/hooks/`** | **4 个文件** | 2 个启动器 + pretool-gate.py(571行核心) + carroros_hooklib.py |
| **`.claude/scripts/`** | **~40 个** Python 脚本 | 主入口、Oracle 引擎、上下文引擎等 |
| **`.claude/skills/`** | **20 个** lx-\* 技能 + 3 个已归档 |
| **`.claude/nodes/`** | **24 个** 节点定义 + 3 个决策节点 + 3 个判断节点 |
| **`.claude/references/`** | **20+** 参考文件 | SOUL.md, oracle-spec, token.schema 等 |
| **`.claude/profiles/`** | **7 个** 配置 | base / enhanced / go / node / python / rust / merge |
| **`.omc/tasks/`** | **9 个** 活跃任务 | 全部归 20260710 |
| **`.omc/archive/`** | **15 个** 已归档任务 | bench-01~07, oracle-fix 等 |
| **根目录** | AGENTS.md(58行) + CLAUDE.md + README.md + 3 个重构报告 |

---

## 二、目录结构

```
CarrorOS/
├── AGENTS.md                    # 核心治理入口——铁律/哲学/工作流（58行）
├── CLAUDE.md                    # Claude 项目配置
├── README.md                    # 项目说明
│
├── .claude/                     # ===== Claude Code 核心治理配置（可复用资产）=====
│   ├── hooks/                   #     4 个 hook 文件
│   ├── scripts/                 #     ~40 个 Python 脚本
│   ├── skills/                  #     20 个 lx-* 技能
│   ├── nodes/                   #     24 个节点定义
│   ├── references/              #     20+ 参考文档
│   ├── profiles/                #     7 个 profile 配置
│   ├── schemas/                 #     14 个 schema 定义
│   ├── rules/                   #     2 个规则文档
│   ├── task_sys/                #     7+ 任务系统文档
│   ├── harness.yaml             #     治理总开关
│   ├── settings.json            #     Hook 配置
│   ├── kernel.md                #     管理内核（31行）
│   ├── index.md                 #     渐进式披露路由表（67行）
│   └── mcp.json                 #     MCP 配置
│
├── .omc/                       # ===== AI 任务运行时资产 =====
│   ├── tasks/                  #     活跃任务
│   ├── archive/                #     已归档任务（15个）
│   ├── tokens/                 #     令牌存储
│   ├── state/                  #     运行时状态
│   ├── scripts/                #     运行时脚本（25个）
│   ├── plans/                  #     计划历史
│   ├── reference/              #     运行时引用
│   ├── audit/                  #     审计日志
│   └── review/                 #     评审记录
│
├── opencode/                   # OpenCode 集成
├── rpe/                        # RPE 研究项目
├── scripts/                    # 顶层测试脚本
├── 重构指导文档/               # 中文重构文档（17个 .md）
├── 现状vs重构指导文档-对比请求.md
├── 重构对比报告.md
└── 重构差距清单.md
```

---

## 三、三门户治理架构

```
AGENTS.md (58行) —— 铁律/哲学/工作流           "什么该做"
    ↓
kernel.md (31行)  —— 冻结/飞轮/水位/Oracle/降级  "怎么保障"
    ↓
index.md (67行)   —— 17个路由入口                "去找哪里"
```

### 3.1 AGENTS.md 核心

**7 条哲学优先级（降序）：**
1. 🥇 **验证优先** — 每个断言必须有 `[已验证:file:line]`
2. 🥈 **零信任执行** — 每次工具调用独立验证
3. 🥉 **守护模式** — 发现风险立即阻断
4. 📄 **文档驱动** — 先写方案文档再执行
5. 👤 **人本决策** — 关键节点保留人工判断
6. 📈 **增益原则** — 改动价值 > 成本才做
7. ➖ **少即是多** — 极简上下文，按需披露

**8 条铁律：**
1. 不编造——断言带 `[已验证:file:line]`
2. 证据门禁——每步贴命令输出 / diff
3. 范围冻结——只改 plan.md 声明文件
4. 隐私防线——敏感路径 / 密钥 / 环境变量阻断
5. 不假完成——必须跑 VerifyGate 才能声称完成
6. 不自改治理文件——AGENTS.md / kernel.md / index.md 不同步
7. **先 init 后动手**——任何任务必须先 `carros_base.py init`
8. _(第8条隐含在1-7中)_

**工作流分级：**
- **L1（日常）**：Plan → Step → Verify → Archive
- **L2（高风险）**：跨模块 / 架构 / 不可逆 / 安全 / 发布等场景

**Oracle 三级评审：**
- Oracle-D（静态分析，广度优先）
- Oracle-V（运行时验证，深度优先）
- 双审（D+V，完整审核，必须双方 ACCEPT）

### 3.2 kernel.md 核心

| 机制 | 状态 | 说明 |
|------|------|------|
| 冻结规则 | ✅ 激活 | AGENTS.md/kernel.md/index.md 不可自改 |
| 学习飞轮 | ⚪ 骨架 | claude-next.md(经验层) + error-dna.json(失败模式层)，未接入 |
| 三段式水位 | ⚪ 骨架 | 🟢安全(0-40%) → 🟡警戒(40-70%) → 🔴临界(70%+)，未接入 |
| Oracle 门 | ✅ 激活 | 5 点触发：跨系统/不可逆/安全权限/发布/长时间无人 |
| 降级规则 | ✅ 定义 | 能力缺失可降级，证据/安全/状态冲突不可降级 |

### 3.3 index.md 核心

**四大路由块：**

| 路由块 | 入口 | 路由目标 |
|--------|------|---------|
| **工作流路由** | L1 日常 | state → kernel.md → carros_base.py |
| | L1 快速 | intake_gate.py + verify_gate.py |
| | L2 复杂 | carros_base.py + Oracle 评审 |
| **Hook 路由** | 7 个 hook | pretool-fallback-check / action-gate / edit-scope / sensitive-edit / compact-writer / posttool-audit / completion-gate |
| **Skill 路由** | 8 个 skill | lx-goal / lx-oracle / lx-race / lx-stepwise / lx-todo / lx-validate-skill / lx-varlock / update-carror-os |
| **Schema/Reference 路由** | 多路径 | token.schema / 合约 / 注册表 / SubAgent / 路径规范 / Oracle / 水位 / 降级 / 反范式 |

---

## 四、Hook 系统

### 架构
```
settings.json
    └── hook-launcher.sh（统一启动器）
            ├── pretool-gate.py（571行，统一门禁）
            │       ├── ① sensitive-edit    — 拦截 .env/.ssh/密钥
            │       ├── ② fallback-check    — 拦截 blocked/waiting_user 状态
            │       ├── ③ action-gate       — 阻断危险命令
            │       ├── ④ plan-gate         — 拦截缺失任务文件
            │       ├── ⑤ edit-scope        — 拦截越界写入
            │       ├── ⑥ privacy-gate      — 隐私防线
            │       └── ⑦ completion-gate   — 谎完成检测
            └── statusline-command.sh        — 状态横幅回调
```

### 设计模式
- `hook-launcher.sh` 用 `$0` 定位自身路径 → 切到项目根 → 调用对应 `.py` hook
- `carroros_hooklib.py` (257行) 提供共享工具：read_input / hc_read_config / output_continue 等
- 所有 hook 合并为 1 个 Python 文件 + 1 个共享库，而非分散的 7 个独立文件

---

## 五、技能系统

### 5.1 活跃技能（17 个）

| 分类 | 技能名称 | 用途 |
|------|---------|------|
| **研发** | lx-goal | Goal 模式流程管理 |
| | lx-rpe | 研究与规划引擎 |
| | lx-ghost | Ghost Oracle 评审 |
| | lx-task-spec | 任务规格定义 |
| | lx-root-cause-analysis | 根因分析 |
| **审查** | lx-oracle-review | Oracle 双审工作流 |
| | lx-oracle-agent | Oracle 静态代理 |
| | lx-oracle-meta | Oracle 元审 |
| **质量** | lx-code-review | 代码审查 |
| | lx-dogfood | 自测（狗粮） |
| | lx-git-check | Git 提交检查 |
| | lx-validate-skill | 技能验证 |
| **治理** | lx-oma (hier) | OMA L1 分层拆解 |
| | lx-oma (split) | OMA L2 特性拆解 |
| | lx-oma (gov) | OMA 治理 |
| | lx-oma (orch) | OMA 编排 |
| **辅助** | lx-learner | 模式学习 |
| | lx-skillify | 技能生成 |
| | lx-varlock | 变量锁 |

### 5.2 已归档技能（3 个）

| 技能 | 说明 |
|------|------|
| lx-race | Race 文档令牌 |
| lx-purify | 清理 |
| lx-sync | 同步检查 |

---

## 六、核心工作流引擎

```
carros_base.py    —— 主入口，6 个命令
    init          —— 创建 token.json + plan.md + executor.md
    status        —— 显示当前状态 / 进度
    tick          —— 推进步骤
    verify        —— 验证完成
    archive       —— 归档 + 生成报告
    lint          —— 7 项 lint 检查

辅引擎：
    omc_lint.py      —— 7 项代码规范检查
    verify_gate.py   —— 验证门禁
    plan_builder.py  —— 计划生成
    output_compress.py —— 输出压缩
    context_engine.py  —— 上下文引擎
    pre_action_gate.py —— 动作前门禁
    task_state_tracker.py —— 任务状态追踪
    executor_ledger.py   —— 执行台账
    intake_gate.py       —— 入口门禁
    honesty_audit.py     —— 诚实审计
```

---

## 七、Oracle 评审系统

```
oracle_engine.py (487行) —— 评审编排器
    │
    ├── static_oracle_agent.py (230行)
    │       └── Oracle-D: 广度优先，静态代码分析
    │
    ├── runtime_oracle_agent.py (249行)
    │       └── Oracle-V: 深度优先，运行时证据验证
    │
    └── meta_oracle.py (208行)
            └── 聚合裁决，双审汇聚评分

支持模块：
    oracle_spawn.py       —— 子代理派发
    oracle_gate.py        —— Oracle 门禁触发
    oracle_agent.py       —— 代理层封装
    carros_oracle_base.py —— Base 版 Oracle 适配
    model_oracle_*.py     —— 模型级 Oracle（5 个文件）
```

**⚠️ 当前状态**：框架完整（~1200行），但核心 review 逻辑是**本地静态规则**，未真正集成 LLM 驱动审核。

---

## 八、运行时状态（`.omc/`）

| 区域 | 内容 |
|------|------|
| `tasks/20260710/` | 9 个活跃任务：bench-02~07, oracle-engine-fix, e2e-smoke, refactor-doc-sync |
| `archive/` | 15 个归档：bench-01~07, cap-test-001, smoke-test-01, test-full-goal 等 |
| `tokens/` | 4 个 token JSON，分属 `20260710` 和 `2026-07-10` 两个日期目录 |
| `state/` | token.json, oracle-verdicts, oracle-cache, audit 等 |
| `scripts/` | 25 个运行时脚本，含 sub_agent_*（4 个）、carros_base.py、oracle_* 等 |

---

## 九、已知问题

| # | 问题 | 严重度 | 影响 |
|---|------|--------|------|
| 1 | **日期格式不统一** — `20260710` vs `2026-07-10` 混用 | ⚠️ | 路径查找混乱，归档断裂 |
| 2 | **嵌套 `.omc/.omc/`** — 初始化脚本产物残留 | ⚠️ | 无用文件，增加扫描噪声 |
| 3 | **Oracle 未真正集成模型** — review 逻辑是本地规则 | ⚪ | 评审质量有限，无 LLM 驱动 |
| 4 | **L2 Enhance 未实现** — Context Watermark / Learning Flywheel / 三段式水位 | ⚪ | 核心机制骨架化 |
| 5 | **bench 从未真正执行** — 只有 README 文档 | ⚪ | 无回归测试保障 |
| 6 | **OC plugin 不同步** — `.opencode/plugins/` 落后于 `packages/` | ⚪ | OpenCode 集成可能断裂 |
| 7 | **`.claude/` 有运行时文件** — session-handoff.md, last-user-prompt.md 混入可复用资产 | ⚪ | 架构污染 |
| 8 | **`重构指导文档/` 在根目录** — 17 个 .md 中文文档 | ⚪ | 根目录杂乱，非资产也不是运行时 |

---

## 十、与 Sylph 版的差异

| 维度 | 桌面版（Base） | Sylph 版（Enhance） |
|------|---------------|-------------------|
| **目标模型** | DeepSeek V4 Flash / 中低阶 | Opus / GPT / 高阶 |
| **治理密度** | 轻量化（4 hooks, 571 行核心） | 完整治理（29 hooks） |
| **技能数量** | 20 个 | 更多（含完整 CarrorOS 技能） |
| **定位** | `.claude/` = 可复用资产，`.omc/` = 运行时 | 同上结构但更完整 |
| **依赖** | 纯 Python stdlib，无外部依赖 | 同上 |

---

## 更新记录（2026-07-12 实际执行）

### 已修复的问题

| 原问题 | 状态 | 改动 |
|--------|------|------|
| 资产边界违规 — 运行时文件在 .claude/ | ✅ 已修复 | session-handoff → .omc/, last-user-prompt → .omc/state/ |
| 嵌套 .omc/.omc/ | ✅ 已修复 | 已删除 |
| 重构文档在根目录 | ✅ 已修复 | 移至 .claude/references/design-docs/ |
| root 级报告文件 | ✅ 已修复 | 移至 .omc/archive/design-docs/ |
| kernel.md L2 Enhance 未标记骨架 | ✅ 已修复 | 标注 ⚪ 骨架 + 运行时说明 |
| index.md Hook 路由指向不存在的单文件 | ✅ 已修复 | 合并为 pretool-gate.py 统一入口 |
| index.md 无脚本索引 | ✅ 已修复 | 添加 18 条快速索引表 |
| index.md 无 Nodes 路由 | ✅ 已修复 | 添加热/冷节点分离路由 |
| 无版本号/CHANGELOG | ✅ 已修复 | VERSION v7.1.0 + CHANGELOG.md |
| OMA 四件套（4 个技能） | 🔄 执行中 | 合并为 1 个 lx-oma |
| Oracle 三件套（3 个技能） | 🔄 执行中 | 合并为 1 个 lx-oracle |
| lx-ghost 评估 | 🔄 执行中 | 保留+精简，委托 lx-oracle |

> 本文件将在结构重构全部完成后统一刷新。
