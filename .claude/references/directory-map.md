# 生产项目目录结构（2026-07-24）

> AGENTS 哲学#1(少即是多) 驱动。每层标注功能定位和归属模块。

```
Carror_Base_OS/
├── AGENTS.md                     # [入口] Agent 指令根（铁律/工作流/完成标准）
├── CLAUDE.md                     # [入口] CC 项目入口 → 指向 AGENTS.md
├── README.md                     # [说明] 项目说明
├── .gitignore                    # [配置] Git 忽略规则
│
├── .claude/                      # [模块] 核心治理系统（只读域，AGENTS#7 保护）
│   ├── AGENTS.md                  # ← 见根目录 AGENTS.md
│   ├── index.md                   # [导航] 模块路由表（房间地图）
│   ├── kernel.md                  # [核心] 治理内核
│   ├── settings.json              # [配置] Hook 注册表（gitignored，磁盘生效）
│   ├── settings.local.json        # [配置] 本地覆盖（参考用）
│   ├── settings_ds.json           # [配置] 备用配置 DS
│   ├── settings_k3.json           # [配置] 备用配置 K3
│   ├── harness.yaml               # [配置] CI 模式门禁路由
│   ├── mcp.json                   # [配置] MCP 服务器注册
│   ├── VERSION                    # [版本] 版本号
│   ├── claude-next.md             # [学习] 学习笔记（飞轮自动补充）
│   │
│   ├── hooks/                     # [子模块] CC 治理 Hook 脚本（34个，G1-G6 门禁）
│   │   ├── hook-launcher.py       # [调度] Hook 统一调度器
│   │   ├── pretool-gate.py        # [门禁] G1-G6 统一门禁（核心）
│   │   ├── posttool-claim-audit.py# [审计] PostToolUse 审计校验
│   │   ├── posttool-output-schema.py # [规范] C4 输出格式校验
│   │   ├── error-dna.py           # [学习] 自动采集失败模式
│   │   ├── ... (34 个 .py 文件)   # [门禁+审计] 完整覆盖
│   │   └── lib/                   # [库] Harness 共享库
│   │
│   ├── scripts/                   # [子模块] 治理工具脚本（40+）
│   │   ├── carros_base.py         # [入口] 主入口（init/status/tick/verify/archive）
│   │   ├── context_engine.py      # [核心] 上下文引擎（compact 恢复）
│   │   ├── verify_gate.py         # [门禁] VerifyGate 证据等级校验
│   │   ├── oracle_agent.py        # [门禁] Oracle 双模型对抗审核
│   │   ├── meta_oracle.py         # [审计] G1-G4 独立审计框架
│   │   ├── fallback_engine.py     # [容错] 15 种失败/4 种决策
│   │   ├── lib/                   # [库] 工具库
│   │   └── ...                    # [工具] 其余 30+ 治理脚本
│   │
│   ├── references/                # [子模块] 公共资源文档
│   │   ├── index.md               # [导航] 资源目录
│   │   ├── evaluation-framework.md# [评测] C1-C9/E1-E8 评分框架
│   │   ├── agent-capability-analysis.md# [分析] Agent 能力来源分析
│   │   ├── coverage-gate-reuse-plan.md# [计划] Coverage Gate 复利方案
│   │   ├── anti-patterns.md       # [学习] 已知反模式库
│   │   ├── philosophy.md          # [哲学] 决策链哲学
│   │   ├── feature-registry.yaml  # [注册表] 功能注册表
│   │   ├── feature_test/          # [测试] ← 错位（见下文 §2.2）
│   │   ├── round7/                # [存档] ← 略重（建议与 design-docs 合并）
│   │   ├── adr/                   # [ADR] 架构决策记录
│   │   ├── design-docs/           # [设计] 编号设计文档（大编号优先，13 为活文档，历史已归档 ADR0017）
│   │   ├── task-architecture/     # [架构] 任务架构参考
│   │   ├── templates/             # [模板] Handoff/Stepwise 模板
│   │   └── ...                    # 其余 15+ 独立文件
│   │
│   ├── nodes/                     # [子模块] 最小公共节点（12个）
│   ├── schemas/                   # [子模块] 公共接口定义
│   ├── rules/                     # [子模块] 语言/工具行为规则
│   ├── profiles/                  # [子模块] 项目语言 Profile
│   ├── skills/                    # [子模块] AI Agent Skills
│   └── workflows/                 # [子模块] 工作流定义
│
├── .omc/                          # [模块] 运行时状态域（AI 写入域）
│   ├── index.md                   # [导航] 运行时目录
│   ├── session-handoff.md         # [状态] 会话导航
│   ├── tokens/                    # [状态] 运行时令牌
│   ├── tasks/                     # [任务] 任务文档系统
│   ├── state/                     # [状态] 运行时状态
│   ├── archive/                   # [存档] 归档任务
│   ├── audit/                     # [审计] 审计日志
│   ├── knowledge/                 # [学习] 升华管道数据
│   └── metrics/                   # [指标] 基准测试报告
│
├── scripts/                       # [模块] 顶层可执行脚本
│   ├── run-regression.sh          # [测试] 54/54 回归一体化入口
│   └── carroros-gates/            # (空目录，错位/待删除)
│
├── benchmark/                     # [模块] 性能基准测试
│   ├── README.md
│   ├── runner.py                  # [核心] 基准测试运行器
│   ├── tasks/                     # [数据] 80 个基准测试用例
│   ├── runs/                      # [结果] 历史运行结果
│   ├── verify/                    # [验证] 验证脚本
│   ├── reports/                   # [报告] 分析报告
│   └── repos/                     # [资产] 测试项目样本
│
├── packages/                      # [模块] 分发包
│   ├── carroros-base/             # [发行版] CarrorOS Base 包
│   │   ├── AGENTS.md
│   │   ├── CLAUDE.md
│   │   └── benchmark/             # [冗余] ← 与根 benchmark/ 内容重复
│   └── enhanced-lite-v7.1.0.tar.gz# [发布] 历史发布包
│
├── improve_plan/                  # [模块] 改进计划（eval-framework 引用）
│   ├── CarrorOS_second_time/      # [规划] 第二版改进计划
│   │   ├── scorecard.md           # [核心] 评分对账卡（evaluation-framework 引用）
│   │   ├── round3/                # [残留] .DS_Store 仅
│   │   └── round7/                # [冗余] ← 内容已迁至 .claude/references/round7/
│   └── CarrorOS_lying/            # [残留] ← 未跟踪，磁盘残留
│
├── main.go                        # [残骸] ← 空壳 Go 文件，无关项目
└── plans/                         # [残骸] ← 空目录（已删除？）
```

---

## 二、错位分析（不符合目录功能的文件）

### 2.1 root-level 残骸

| 路径 | 问题 | 解决方案 |
|------|------|----------|
| `main.go` | Go 空壳文件，项目是 Python/py 体系 | ❌ 删除 |
| `scripts/__pycache__/` | Python 缓存应被 gitignore，实际未忽略 | ❌ 删除 + gitignore |
| `scripts/carroros-gates/` | 空目录，完全没有内容 | ❌ 删除 |
| `.claude/references/.claude/` | 虚目录，迁移产物 | ❌ 删除 |
| `.claude/references/.omc/` | 虚目录，迁移产物 | ❌ 删除 |

### 2.2 功能错位（文件放错位置）

| 路径 | 问题 | 正确位置 | 原因 |
|------|------|----------|------|
| `.claude/references/feature_test/` | 54 个测试文件放在 `references/` 下，但**测试不是参考文档** | `scripts/test/` 或 `tests/` | references/ 的定义是"设计文档/ADR/模板等可复用资源"。测试是验收工具，应该独立 |
| `improve_plan/CarrorOS_second_time/round7/` | round7 内容已完整迁至 `.claude/references/round7/`，但磁盘未清理 | 无（已存档） | 归档完成后原始位置应删除 |
| `packages/carroros-base/benchmark/` | 与根 `benchmark/` 内容高度重复 | 保留 packages/carroros-base/ 为发布快照，不保留其 benchmark 数据 | 分发包不应包含基准测试结果和运行 |
| `improve_plan/CarrorOS_lying/` | 磁盘残留（从未在 git 中） | 无 | 删除 |

### 2.3 路径引用隐患

| 来源文件 | 引用错位路径 | 影响 |
|----------|-------------|------|
| `.claude/references/round7/gpt_full.md` | 引用 `improve_plan/round7/...` | 已归档的原始引用路径不存在，属引用漂移 |

---

## 三、推荐结构

```
Carror_Base_OS/
├── AGENTS.md          ← Agent 入口
├── CLAUDE.md          ← CC 入口  
├── README.md
├── .claude/           ← 治理系统
├── .omc/              ← 运行时状态
│
├── scripts/           ← 顶层可执行
│   └── run-regression.sh
│
├── tests/             ← 验收测试（从 references/feature_test/ 迁出）
│   └── test-*.py / test-*.sh
│
├── benchmark/         ← 基准测试
├── packages/          ← 分发包
└── improve_plan/      ← 活体规划（仅 scorecard.md）
    └── scorecard.md
```
