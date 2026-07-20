# CarrorOS — 使用指南

> 如何理解、安装和驾驭行为治理内核

---

## 快速开始

### 前提

- macOS / Linux / Windows WSL
- Claude Code（推荐）或 OpenCode
- Python 3.9+

### 安装

```bash
# 克隆
git clone <repo-url> CarrorOS
cd CarrorOS

# 执行安装脚本
bash install.sh
```

安装后自动注册：
- 6 个 CC PreToolUse hooks → 工具调用安全门禁
- 治理核心参照系统（CLAUDE.md → AGENTS.md → kernel.md → index.md）
- 任务文档模板（`.omc/tasks/`）和 Token 系统（`.omc/tokens/`）

### 第一轮交互

```bash
# 查看治理状态
python3 .claude/scripts/carros_base.py status

# 运行 lint 一致性检查
python3 .claude/scripts/carros_base.py lint

# 跑 benchmark 测试
python3 .claude/scripts/carros_base.py bench
```

### 创建第一个任务

```bash
python3 .claude/scripts/carros_base.py init --task-id hello-world
```

---

## 核心概念

### CarrorOS 是什么

CarrorOS 不是操作系统，而是 **AI 代理的行为治理内核**——一套支配代理如何规划、执行、验证、归档的规则框架。

核心灵魂（按优先级排序）：

> **验证 > 零信任 > 守护 > 文档 > 人本 > 增益 > 少**

### 8 铁律（违反必须回退）

| # | 规则 | 含义 |
|:-|:-----|:------|
| 1 | 不编造 | 断言必须带 `[已验证:file:line]` |
| 2 | 证据门禁 | 每改完一步贴命令输出或 diff |
| 3 | 范围冻结 | 只改 plan.md 声明的文件 |
| 4 | 隐私防线 | 禁止读 `.env` / 密钥 / `.ssh` |
| 5 | 不假完成 | 没跑 VerifyGate = 没完成 |
| 6 | 不自改治理 | 不改 AGENTS.md / kernel.md / index.md |
| 7 | 先 init 后动手 | 任何任务必须先 `carros_base.py init` |
| 8 | 哲学先行 | 问人之前先过哲学 7 条 |

### 任务等级

| 等级 | 场景 | 特点 |
|:----|:-----|:-----|
| **L1**（默认） | 日常开发、单文件修复、文档更新 | 轻量：Plan → Step → Verify → Archive |
| **L2**（增强） | 跨模块、架构、不可逆、安全/权限、发布、长期无人 | 含 Oracle + 水位 + 降级熔断 |

模型与代理一致性规则：**L1/L2 由任务风险决定，不按模型档位区分。** SubAgent 与 MainAgent 默认使用同一模型、同一治理规则、同一证据标准。

### 治理组件

| 组件 | 角色 |
|:-----|:------|
| **IntakeGate** | 任务入口分类 → 自动路由 L1/L2 |
| **PlanBuilder** | 计划冻结（plan.md 模板） |
| **PreActionGate** | 安全门禁（敏感路径/危险命令/范围检查） |
| **Executor Ledger** | 执行证据链（executor.md） |
| **VerifyGate** | 完成验证门——没通过 = 没做完 |
| **Context Engine** | 上下文管理——水位阈值 + 自动 compact |
| **Oracle** | 高阶复核——仅 L2 触发，同级/高级模型 |
| **Fallback** | 降级熔断——能力缺失可降级，证据缺失不可降级 |
| **Error DNA** | 错误自动记录 → 模式学习 → 规则进化 |
| **Archive** | 归档封存——任务完成后的收官仪式 |

---

## 常见任务流程

### Goal 模式（无人值守）

适用于明确验收条件的、无需实时交互的任务。

1. Agent 收到任务 → 识别为 L2+ 良好定义
2. 自动触发 `/lx-goal`：一次前置澄清 → 全自动执行
3. 执行期间不提问，自主完成
4. 退出时提交报告 + 完成证据

### Ghost 模式（方向驱动探索）

适用于需要大量先期调查、方向未知的任务。

1. Agent 收到任务 → 触发 `/lx-ghost`
2. Phase 0：穷尽澄清 → 问题列表冻结
3. Oracle 自动审核计划
4. 全自动探索执行
5. 退出报告：发现、结论、未解问题

### L1 标准工作流（日常任务）

```
Plan   →  carros_base.py init --task-id <ID>
Execute → 按 plan.md 执行，贴 executor.md 证据
Verify →  carros_base.py verify [--step S1]
Archive → carros_base.py archive
```

### L2 复杂工作流

```
Plan → L2 自动启动：
  - 水位防线 → Context 预算卡控
  - Oracle 触发 → 双审判官独立裁决
  - Error DNA → 失败模式自动归档
  - Fallback 就绪 → 降级熔断预案
Execute → 严格按计划 + 证据链
Verify → 通过 Oracle + VerifyGate 双重门
Archive → 完整归档
```

### Hook 路由一览

| 触发点 | 作用 | 注册位置 |
|:------|:-----|:---------|
| PretoolUse | 统一门禁 G1-G6：每工具调用前检查 | `.claude/settings.json` |
| UserPromptSubmit | compact 轻量触发（每 5 轮检查水位） | `.claude/settings.json` |
| PostToolUse | 证据收集 + 工具落盘 | 同上 |

---

## 最佳实践

### 1. 计划 > 行动

任何改动之前先 `carros_base.py init`。跳过 init 直接改代码是违规（铁律 #7）。

### 2. 贴证据，不是贴结论

每条断言附带命令输出或 diff。`[已验证:file:line]` 是最低标准。

### 3. 小心 Compact

CC `/compact` 压缩的是对话记忆，不碰以下文件：
- **Token**（任务状态唯一源）→ `.omc/tokens/*.json`
- **Handoff** 导航 → `.omc/session-handoff.md`
- **Plan** 冻结计划 → `plan.md`
- **Executor** 执行证据 → `executor.md`
- **Error DNA** → `error-dna.jsonl`

恢复路径：新会话读 token → handoff → Resume Preflight → 继续工作。

### 4. 水位管理

| 预算水位 | 动作 |
|:---------|:-----|
| 🟢 <40% | 正常执行 |
| 🟡 40-70% | checkpoint，禁止扩张 |
| 🔴 >70% | 暂停 + 写 handoff + 请求 compact |

| 上下文水位 | 动作 |
|:-----------|:-----|
| 🟢 <50% | 正常执行 |
| 🟡 50-70% | 提醒 compact |
| 🔴 70-80% | 只读模式（禁写） |
| ⛔ >=80% | 强制 compact |

### 5. 哲学先行

问人之前，先过 7 条哲学原则裁决链：
```
验证 → 零信任 → 守护 → 文档 → 人本 → 增益 → 少
```

技术决策在规则范围内，AI 自行裁决即可。不可逆/安全相关操作必须问人。

### 6. 「少」但「强」

每个机制必须赚取其重量。不做多余的抽象，不为未来过度设计。

选择改动最小的路径（#2 增益），但优先级链不允许因为"少做"而跳过验证（#4 验证 > #1 少）。

### 7. 抗 Compact 设计思想

全部治理状态在磁盘，不在对话。AI 可以死、会话可以 compact、进程可以掉——Token 永存。这就是 CarrorOS 的运行时真相。

---

## 参考命令速查

```bash
# 任务生命周期
python3 carros_base.py init --task-id <ID>
python3 carros_base.py status
python3 carros_base.py tick
python3 carros_base.py verify --step S1
python3 carros_base.py lint
python3 carros_base.py archive

# Oracle（L2 任务调试）
python3 carros_base.py oracle

# 评测
python3 carros_base.py bench
CARROROS_ROOT="$PWD" python3 feature_verify.py 1

# 预算/水位
# 自动：context_watermark.py 内置在 hooks 中
# 手动：python3 context_engine.py status
```

---

## 平台支持

| 平台 | 状态 |
|:-----|:-----|
| Claude Code | 全拟 hooks |
| OpenCode | plugin |
| 独立 CLI | carros_base.py |
| macOS | 已验证 |
| Linux | 支持 |
| Windows/WSL | pathlib 路径已验证 |

---

> **CarrorOS 铁律第一条：不编造。**  
> 本指南描述的每个机制都有对应文件为证。  
> 证据门禁是底线，不是天花板。
