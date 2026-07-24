# Agent Capability Source Analysis

> 分析 Coverage Blitz 中 30+ agent 的能力来源，回答：哪些是 Claude Code 原生？哪些是 CarrorOS 赋予？哪些是 skill 或 workflow 层给的？

## 1. 事件回顾：Coverage Blitz 做了什么

[coverage-blitz.js](/.claude/workflows/coverage-blitz.js) 是一个 **Workflow 文件**（Claude Code CLI 原生支持的 `.js` 格式），它做了：

1. 定义了 4 个批次（P1-P4），共 38 个 agent 任务
2. 每批次通过 `Promise.all()` 并行 spawn agent
3. 每个 agent 收到一条 prompt：读一个 hook 源码 -> 给一组验收条件 -> 输出 test 文件内容
4. 最后收集所有输出，写入磁盘

**关键机制**：Workflow 的 `agent()` API 会为每个任务启动一个**独立 Claude Code agent**，每个 agent 有自己独立的工具集（Read, Bash, Write, Grep, SearchFiles 等）。

---

## 2. Capability 分解矩阵

### 2.1 原生 Claude Code CLI 能力（零配置即有）

| 能力 | 说明 | 来源证据 |
|------|------|----------|
| Read 源码 | 每个 agent 读 hook 文件分析 import | 原生工具 `Read` |
| 生成 Python 测试文件 | agent 用 Python 知识写 `test-xxx.py` | 原生 LLM 能力 |
| Write 文件 | 写入测试文件到 `scripts/` 目录 | 原生工具 `Write` |
| Bash 执行 | 运行测试：`python3 scripts/test-xxx.py` | 原生工具 `Bash` |
| 理解 Python 语法 | import, mock, unittest, sys.path 操作 | 原生 LLM 知识 |
| 理解 Git 结构 | 知道 `.gitignore`, `tests/`, `src/` 布局 | 原生 LLM 推理 |
| 并行 execution | `Promise.all([agent(...), ...])` 同时启动 38 个 agent | **原生** Workflow API 特性 |
| agent() API | 创建子 agent，返回输出 | **原生** Workflow API 特性 |

> **结论**：覆盖测试的**核心能力**（读代码 -> 写测试 -> 验证）全部来自 Claude Code CLI 自带能力。换成任意一个空项目，只要安装了 Claude Code，都能做同样的事。

### 2.2 CarrorOS Governance 层（非必需，起辅助作用）

| 能力 | 实际作用 | 能否禁用？ |
|------|----------|-----------|
| `hook-launcher.py` 启动各 hook | 在 agent 每次 tool call 前后触发治理检查 | 能 -- 禁掉 hook 注册仍可跑 blitz |
| `pretool-gate.py` 门禁 | 检查写文件是否越界，Bash 是否安全 | 能 -- 不影响测试生成 |
| `completion-gate.py` 完成门禁 | 验证 agent 退出前证据完整 | 能 -- 不参与 blitz 核心逻辑 |
| `posttool-claim-audit.py` | 校验 agent 声称的证据 | 能 -- 只产生告警不阻塞 |
| `permission-gate.py` | 权限审批 | 能 -- blitz agent 不需此能力 |
| `session-start.py`/`session-resume.py` | 会话注入 | 能 -- 不参与 blitz |

> **结论**：CarrorOS hooks 在 blitz 期间**全部处于激活状态**，但它们是 **被动门禁**，不是能力来源。移除 hooks 后，blitz 仍能跑 —— 只是少了一层安全网。CarrorOS 的贡献是**控制/约束**，而非**赋予能力**。

### 2.3 来自 SKILLS 体系（覆盖 Blitz 未使用）

| Skill | 是否被 blitz agent 用到？ |
|-------|--------------------------|
| grill-me | **未使用** -- agent 没有调用 Skill 工具 |
| lx-goal | **未使用** -- blitz 不是自主模式 |
| lx-oracle | **未使用** -- agent 级别未触发 Oracle |
| lx-stepwise | **未使用** |
| lx-codebase-design | **未使用** |
| lx-domain-modeling | **未使用** |
| lx-pre-commit / lx-pre-push | **未使用** |

> **结论**：Coverage Blitz 中 **没有一个 agent 使用了任何 Skill**。Skills 的能力（深度设计审查、目标模式、RPE 特征开发）与 blitz 任务不匹配。

### 2.4 来自 Workflow 编排层（关键使能器）

| 能力 | 来源 | 说明 |
|------|------|------|
| 多 agent 并行启动 | 原生 Workflow API: `agent()` | `Promise.all()` 同时跑 38 个 agent |
| 任务分解/分批 | Workflow `.js` 代码 | 手动按复杂度分 4 批 |
| 输出收集 | 原生 Workflow API: agent 返回值 | agent 的 stdout 被 workflow 捕获 |
| 阶段控制 | Workflow `.js` 代码 | `phase()` 标记进度 |

> **结论**：Workflow 层提供了**多 agent 编排能力**，这是单个 Claude Code session 无法做到的。但这部分能力（`agent()` API, `phase()`, `Promise.all()`）是**原生**的，不依赖 CarrorOS。

---

## 3. 全景分类图

```
覆盖测试 30+ agent 能力分解
================================================

┌─────────────────────────────────────────────┐
│  Claude Code CLI 原生能力（主体）[来源：.claude/workflows/coverage-blitz.js 代码审查，非行业标准]
│  ------------------------------------------  │
│  - Read / Write / Bash / Grep 工具集         │
│  - Python 程序设计能力（agent 的 LLM）       │
│  - Workflow .js 引擎 (agent(), Promise.all)  │
│  - agent 隔离执行                            │
│  - Git 感知                                  │
│  - 文件系统操作                              │
├─────────────────────────────────────────────┤
│  CarrorOS Governance（辅助层）[来源：.claude/settings.json hooks 注册表代码审查，非行业标准]
│  ------------------------------------------  │
│  - 写文件门禁（pretool-write-lock）          │
│  - Bash 安全过滤（pretool-terminal-safety）  │
│  - Claim 审计（posttool-claim-audit）        │
│  - 敏感信息过滤（posttool-sensitive-filter） │
│  - 会话恢复（session-start/resume）          │
├─────────────────────────────────────────────┤
│  Skills（未使用）[来源：.claude/workflows/coverage-blitz.js 代码审查，非行业标准]
└─────────────────────────────────────────────┘
```

---

## 4. 复用路径：具体场景

### 场景 A：启动 10 个 agent 同时审查 10 个文件

**怎么做**：写一个 Workflow `.js` 文件，用 `agent()` API 并行启动。

```javascript
// 关键代码模式
const agents = files.map((file, i) => agent(`
  Read: ${file}
  审查要点：
  1. 文件是否有 export/import 缺失
  2. 是否有硬编码路径
  3. 注释是否匹配实现
  Output 审查结果。
`, { label: `review-${i}` }))

const results = await Promise.all(agents)
// 每个 agent 返回审查文本
```

**依赖**：
- Claude Code CLI（原生 ✅）
- 不需要任何 CarrorOS hook（可选）
- 不需要任何 skill

**复用成本**：零 -- 新建任意 `.js` 文件放在 `.claude/workflows/` 下就能用 `claude workflow run <file>` 执行。

> **注意**：Workflow 功能是 Claude Code CLI 的内置功能（不是 CarrorOS 写的），在任何安装了 Claude Code 的项目中都能用。无需安装任何额外依赖。

### 场景 B：让 agent 自己写测试并验证

**怎么做**：在 Workflow 中用 `agent()` 发给一个 agent 完整任务：

```javascript
agent(`
  任务：为 ${HOOK_DIR}/xxx.py 写测试
  步骤：
  1. Read ${HOOK_DIR}/xxx.py 分析逻辑
  2. Write ${TEST_DIR}/test-xxx.py 含 5 个验收测试
  3. Bash: python3 ${TEST_DIR}/test-xxx.py 验证通过
`)
```

**依赖**：
- Claude Code CLI 原生 ✅
- agent 的 Python 知识 ✅
- 不需要 CarrorOS

**复用成本**：零 -- 任何项目都能这样用。但在 CarrorOS 项目里有额外优势：
- 环境 token 和 API 已在 settings.json 配置好（指向你的本地 proxy）
- 各种门禁帮助发现测试盲点（如 claim-audit 检查测试是否真的覆盖了代码中的关键断言）
- 但这些都不是必须的

### 场景 C：跨会话复用某 agent 的产出模式

**怎么做**：
1. **存储 Workflow 文件** -- `.claude/workflows/xxx.js` 是普通的 JS 文件，可 git commit
2. **参数化** -- 把 38 个 task 的固定参数（路径、验收条件）抽成数组

```javascript
// 可复用的模式：
const MECHANISMS = [
  { name: 'privacy-gate', path: '/hooks/privacy-gate.py', checks: ['sk- tokens', 'ghp_ tokens'] },
  // ...38条
]
MECHANISMS.forEach(m => agents.push(agent(`...`, { label: m.name })))
```

3. **结果归档** -- agent 的返回值可被 workflow 捕获并写入 `.omc/` 或任意目录

**依赖**：
- Workflow `.js` 文件本身（纯文本，git 版本化）✅
- 无需额外 setup

**复用成本**：一个文件即可，跨机器跨项目都可用。

---

## 5. 常见误解澄清

### 误解 1："CarrorOS 的 hooks 让 agent 变聪明了"

**事实**：Hooks 是**门禁**，不是**能力增强**。它们的作用：
- 阻止坏操作（写敏感文件、执行危险命令）
- 记录审计日志
- 检查证据完整性
- 不提供 Python 编程能力、不提供测试设计能力、不提供文件读写能力

### 误解 2："Stills 是 agent 能力来源"

**事实**：Skills（lx-goal, lx-oracle 等）是**工作流模板**，通过 Skill 工具加载后被注入到当前 agent 的 system prompt 中。Coverage Blitz 中的 agent **没有 Skill 加载步骤**，它们是纯原生 agent。

如果想让 agent 使用 Skill 能力（如 lx-oracle 的架构审核），需要在 prompt 中显式调用 `Skill(lx-oracle)`。

### 误解 3："Workflow 文件需要 CarrorOS 才能跑"

**事实**：Workflow 是 Claude Code CLI 原生支持的特性。任何安装了 Claude Code 的项目都能创建 `.js` workflow 文件并用 `claude workflow run` 执行。CarrorOS 只是将 workflow 文件放在了 `.claude/workflows/` 目录下作为组织约定。

---

## 6. 如何在另一个项目中复刻 Coverage Blitz

### 最小复制步骤（零依赖 CarrorOS）

```
# 1. 安装 Claude Code CLI
npm install -g @anthropic-ai/claude-code

# 2. 在工作目录中创建 workflow 文件
mkdir -p .claude/workflows
touch .claude/workflows/coverage-blitz.js

# 3. 写入 Workflow 内容（使用 agent() + Promise.all()）
# 模板：读代码 -> 写测试 -> 验证

# 4. 执行
claude workflow run coverage-blitz.js
```

**无需**：
- `.claude/settings.json` 中的 hooks 注册
- `.claude/hooks/` 下的任何 Python 脚本
- `.claude/skills/` 目录
- `.claude/kernel.md` 或索引文件
- `AGENTS.md`

### 带 CarrorOS 治理的版本（额外好处）

如果希望在另一个项目中复用 CarrorOS 的控制质量，需要拷贝：
1. `.claude/settings.json` 中的 `hooks` 块（约 80 行配置）
2. `.claude/hooks/` 目录（~30 个 Python 文件）
3. `.claude/hooks/hook-launcher.py` 调度器
4. `.claude/rules/` 目录（bash 安全规则 + 终端安全规则）

这些提供的是安全网和审计，不是并行 agent 的核心能力。

---

## 7. 推荐：如何让 agent 能力更可复用

### 优先级 P0：把 Workflow 模板抽成通用脚手架

目前 `coverage-blitz.js` 是手写重复代码（38 个 agent 任务，每个都手动写路径、验收条件）。建议：

- 提取一个 `create-test-workflow.js` 模板，接收一个 `mechanics.json` 数组
- `mechanics.json` 中定义：name, source_file, 验收条件列表
- 模板自动生成 agent 任务并分批执行

这样，任何"创建设置测试"场景只需要维护 JSON 数据，不需要写 Workflow 代码。

### 优先级 P1：Workflow 参数化入口

当前 Workflow 文件的路径都是硬编码的。在文件顶部添加：

```javascript
const CONFIG = {
  HOOK_DIR: '/absolute/or/relative/path/to/hooks',
  TEST_DIR: '/absolute/or/relative/path/to/tests',
}
```

依赖可见性，便于跨项目复用。

### 优先级 P2：Post-blitz 结果聚合

目前 Workflow 只返回文件名列表，没有聚合测试结果。增加：

```javascript
// 在 Verify 阶段，逐个运行测试文件并记录通过/失败
const results = await Promise.all(testNames.map(name =>
  bash(`python3 ${TEST_DIR}/test-${name}.py`)
))
// 写一个 JSON 报告到 .omc/ 或任意输出目录
```

让 workflow 产出结构化报告，便于 CI/CD 集成。

### 优先级 P3：跨 repo 复用包

如果希望将 CarrorOS 的 agent 能力作为**可安装包**分发，可以考虑：

- 将 `.claude/` 下的 hooks/scripts/schemas 打包为 PyPI 或 npm 包
- 提供 CLI 命令 `carroros-agent init` 来植入配置
- 但目前没有这种需求，优先级较低

---

## 8. 一句话总结

> Coverage Blitz 中 30+ agent **绝大部分能力来自 Claude Code CLI 原生**（Workflow API + 标准工具集 + LLM 知识），**部分来自 CarrorOS 治理**（安全门禁 + 审计），**无任何 Skill 参与**。[来源：.claude/workflows/coverage-blitz.js + .claude/settings.json 代码审查，非行业标准] 复用核心能力只需写一个 Workflow `.js` 文件，不需要任何 CarrorOS 组件；但 CarrorOS 的治理层提供了额外质量保障，建议保持激活。
