# CarrorOS 桌面版（Base）优化建议

> 审阅者：波比（DeepSeek V4 Flash）
> 日期：2026-07-12
> 基线：CarrorOS-全览图.md（基于实际目录扫描）

---

## 一、架构完整性

### 🔴 P0 | 类型：架构 | Hook 系统过高耦合

`pretool-gate.py`（571行）把 7 个独立门禁合并到一个文件中。对 Base 模型来说，每次工具调用都要加载+解析 571 行的 Python 逻辑——认知负担和 token 消耗都有代价。

**建议**：保持合并架构，但按门禁分模块引用：
```python
# pretool-gate.py 只做路由
from pretool_gates.sensitive_edit import check_sensitive_edit
from pretool_gates.fallback_check import check_fallback
# ...
```
这样单次调用只加载实际需要的门禁模块，减少每次 hook 调用的认知 footprint。

---

### 🔴 P0 | 类型：架构 | Oracle 引擎有框架无灵魂

oracle_engine.py(487行) + static_oracle(230行) + runtime_oracle(249行) + meta_oracle(208行) = ~1200 行框架代码。但当前 review 逻辑全是本地静态规则，不是真正的 LLM 审核。这意味着：
- 对于 Base 模型，Oracle 本质上只是一个 glorified grep
- 1200 行框架代码的维护成本 > 它的实际价值

**建议**：二选一——
- **路径A（推荐）**：砍掉 80% 的 Oracle 框架，只保留 `verify_gate.py` 做简单质量门禁。等后续接高阶模型后再恢复完整 Oracle 架构
- **路径B**：保持框架但标记为"L2 Enhance"，明确告诉当前模型不用管它

---

### 🟡 P1 | 类型：架构 | L2 Enhance 三件套全是骨架

kernel.md 中声明的三个核心机制：
| 机制 | 状态 | 代价 |
|------|------|------|
| Context Watermark | ⚪ 骨架 | 6 个相关文件存在但无实际水位检测逻辑 |
| Learning Flywheel | ⚪ 骨架 | claude-next.md + error-dna.json 存在但未接入 |
| 三段式水位 | ⚪ 骨架 | 🟢🟡🔴 概念定义但无运行时切断逻辑 |

**建议**：如果这三个机制短期内不上线，**从 kernel.md 和 index.md 中移除对它们的路由引用**。骨架代码保留但不暴露给 Base 模型，避免它在 context 中以为自己有这些能力。

---

## 二、上下文工程

### 🔴 P0 | 类型：上下文 | 24 个 Nodes 对 Base 模型是认知过载

`.claude/nodes/` 下 24 个节点定义 + 3 个决策节点 + 3 个判断节点 = 30 个文件。对于 DeepSeek V4 Flash（13B 活跃参数），这个规模是过量的。

**问题**：index.md 的路由表指向了 skills/，但 skills 本身又通过 SKILL.md 和其他引用文件展开更多的上下文。没有做"按需加载"的分级。

**建议**：
- 将 nodes/ 按使用频率分两级：
  - **热节点（≤8 个）**：orchestrator, verifier, explore, gate_checker — 放在 .claude/ 顶层或 indexed
  - **冷节点（其余）**：移到 .claude/references/nodes/，只在明确需要时加载
- index.md 中只用软链接（`@` 引用），不展开具体内容

---

### 🔴 P0 | 类型：上下文 | 20 个 Skills 中至少 6 个重叠

技能系统分析：

| 重叠组 | 技能 | 问题 |
|--------|------|------|
| **OMA 四件套** | lx-oma-gov / hier / orch / split | 4 个技能本质是同一套治理体系不同视图，可合并为 1 个 |
| **Oracle 三件套** | lx-oracle-review / agent / meta | 3 个技能对应 3 种审级但实际只用了双审路径 |
| **lx-ghost + lx-oracle-meta** | 两个技能功能高度重叠 | 都是 Oracle 评审相关 |

**建议**：合并→
- OMA 四件套 → `lx-oma`（1 个技能，用 SKILL.md 内 section 区分视图）
- Oracle 三件套 → `lx-oracle`（1 个技能，双审模式 / 单审模式参数化）
- 移除 lx-ghost（与 lx-oracle-meta 重复）
- 移除 lx-race（已归档且是实验性功能）
- 保留 vs 精简后：**20 → 12 个技能**

---

### 🟡 P1 | 类型：上下文 | 40 个 scripts/ 缺乏入口索引

`.claude/scripts/` 下 ~40 个 Python 脚本，index.md 只引了其中几个关键入口（carros_base.py, verify_gate.py, intake_gate.py）。其他脚本当前只能靠 agent 自己搜索发现。

**建议**：在 index.md 中加一个 `## scripts 快速索引` 表，按功能分组列出所有脚本的用途（一行描述即可）。这样 agent 不用读 40 个文件也能知道哪些可用。

---

## 三、结构合理性

### 🔴 P0 | 类型：结构 | 资产边界违规——运行时文件混入 .claude/

`.claude/` 的设计定位是"可复用资产"（AGENTS.md, index.md, hooks, scripts, skills, references），但当前包含：

| 文件 | 问题 |
|------|------|
| `session-handoff.md` | 运行时状态，应属于 .omc/ |
| `last-user-prompt.md` | 运行时状态，应属于 .omc/ |
| `.claude/skills/` 下的 state/ 目录 | 运行时缓存 |

**建议**：
```
.claude/  ← 只放资产（hooks, scripts, skills, references, schemas, rules, profiles）
.omc/     ← 运行时（state, tasks, tokens, audit, session-handoff）
```

具体操作：
- 把 `session-handoff.md` → `.omc/session-handoff.md`
- 把 `last-user-prompt.md` → `.omc/state/last-user-prompt.md`
- 检查 settings.json 和 hooks 中对这些文件的引用，全部更新

---

### 🟡 P1 | 类型：结构 | 根目录的 重构指导文档/ 是孤儿目录

17 个中文重构 .md 文件 + 3 个根级对比报告。这些是**历史设计文档**，不是运行时资产也不是可复用参考。留在根目录会让 agent 在搜索时产生噪声。

**建议**：
- 如果还在使用 → 移到 `.claude/references/design-docs/`
- 如果已完成 → 删除或移到 `.omc/archive/design-docs/`
- 根目录只留：AGENTS.md, CLAUDE.md, README.md, kernel.md(?), index.md(?)

---

### 🟢 P2 | 类型：结构 | 日期格式不统一

`20260710` vs `2026-07-10` 两种格式混用，涉及：
- `.omc/tasks/` 下两种格式
- `.omc/tokens/` 下两种格式
- `carros_base.py` 中的 strftime 格式

**建议**：
- 统一为 `YYYYMMDD`（纯数字，路径友好，排序正确）
- 搜所有 `strftime` 调用和日期目录引用，一次改完

---

### 🟢 P2 | 类型：结构 | 嵌套 .omc/.omc/ 目录

`.omc/.omc/audit/20260706.jsonl` 存在，说明初始化脚本或 archive 逻辑中产生了嵌套路径。

**建议**：在 `carros_base.py init` 和 `archive` 中加路径存在性检查，检测并清理嵌套 `.omc/`。

---

## 四、已知问题优先级修正

全览图中列了 8 个问题，重新排序：

| 原# | 原严重度 | 调整后 | 理由 |
|-----|---------|--------|------|
| 7 | ⚪ | **🔴 P0** | `.claude/` 有运行时文件—架构边界违规，直接影响 agent 理解系统 |
| 2 | ⚠️ | **🔴 P0** | 嵌套 `.omc/.omc/` 残留 |
| 1 | ⚠️ | **🟡 P1** | 日期格式不统一—影响功能但不是阻塞 |
| 3 | ⚪ | **🟡 P1** | Oracle 未集成模型—框架已就绪，等高阶模型即可 |
| 4 | ⚪ | **🟡 P1** | L2 Enhance 未实现—骨架代码已存在 |
| 8 | ⚪ | **🟡 P1** | 重构文档在根目录—噪声问题 |
| 5 | ⚪ | **🟢 P2** | bench 从未执行—质量保障但不阻塞 |
| 6 | ⚪ | **🟢 P2** | OC plugin 不同步—只影响一半用户 |

---

## 五、遗漏盲区

### 🔴 P0 | 盲区：无错误恢复机制

全览图中完全没有覆盖：

| 缺失 | 影响 |
|------|------|
| `carros_base.py` 调用失败时的回退策略 | 任务执行到一半崩溃，状态丢失 |
| hook 异常时的行为（fail-open vs fail-closed） | pretool-gate.py 崩溃→所有工具调用被阻断？ |
| token.json 损坏的恢复路径 | 关键状态文件损坏则整个系统不可用 |
| compact 时的上下文保护 | 丢失关键决策记录 |

**建议**：在 kernel.md 中加一个 `## 故障恢复` 章节，定义：
- Hook 异常 → fail-open（只警告不阻断），除非是隐私/安全门禁
- carros_base.py 崩溃 → `verify` 可重入（幂等）
- token.json 损坏 → `init --recover` 模式自动重建

---

### 🟡 P1 | 盲区：无系统健康度度量

项目没有定义"什么算正常运作"：

| 缺失 | 影响 |
|------|------|
| 每次工具调用的平均 hook 执行时间 | 不知道 hook 是否是性能瓶颈 |
| 单次任务的平均 token 消耗 | 无法评估 Base 模型的上下文效率 |
| hook 调用成功率 / 阻断率 | 不知道门禁是否过于严格或无效 |
| Lint 通过率的趋势 | 无法追踪治理质量变化 |

**建议**：
- 在 `.omc/state/` 加一个 `health-metrics.json`，每次工具调用后记录：hook执行耗时、阻断/放行、token消耗
- 每周汇总一次趋势

---

### 🟡 P1 | 盲区：无版本号和变更日志

项目无版本号：
- AGENTS.md 无版本
- carros_base.py 无版本
- 整个项目无 CHANGELOG
- `.claude/harness.yaml` 有配置版本字段吗？

**建议**：
- 根目录加 `VERSION` 文件（当前 v7.1.0）
- `carros_base.py` 加 `--version` 参数
- AGENTS.md 头部加 `> 版本：v7.1.0`
- 简单的 CHANGELOG.md 记录每次重要变更

---

### 🟢 P2 | 盲区：无多项目管理指导

当前 CarrorOS 桌面版假设单项目部署。但实际中可能需要：
- 同一个模型管理多个 CarrorOS 项目
- 项目之间共享 skills 但不共享 token/state
- 不同项目有不同治理密度

**建议**：目前不需要实现，但在 AGENTS.md 或 kernel.md 中加一句话说明当前是单项目模式。

---

## 六、自适应优化切入建议

如果用高阶模型做 hooks + skills 自适应优化，推荐以下顺序：

### 第一轮（P0 清理 + 结构精简）
1. **清理资产边界** — 运行时文件移出 `.claude/`
2. **清理嵌套目录** — 删除 `.omc/.omc/`
3. **技能合并** — OMA 四件套→1 个，Oracle 三件套→1 个，lx-ghost 移除
4. **移除或归档重构指导文档**

### 第二轮（上下文瘦身）
5. **Nodes 冷热分离** — 24→8 热节点 indexed，其余移到 references/
6. **index.md 加 scripts 索引表** — 一行一个脚本功能描述
7. **pretool-gate.py 模块化** — 按门禁分模块文件，路由入口不变

### 第三轮（机制注入）
8. **Oracle 真正接入 LLM** — 用高阶模型（通过 xsimplechat）实现真正的 review pipeline
9. **L2 Enhance 实现** — Context Watermark（实际水位检测写入 token.json）+ Learning Flywheel（error-dna 自动接入）

### 第四轮（质量 + 度量）
10. **错误恢复机制** — kernel.md 加故障恢复章节，幂等 verify
11. **健康度量** — hook 性能埋点
12. **版本号 + CHANGELOG**

### 第五轮（验证）
13. **bench 真正运行** — 7 个基准场景全过
14. **双法官验收** — Oracle 审核架构变更
15. **OC plugin 同步** — `.opencode/plugins/` 从 `packages/` 同步

---

## 总结评分

| 维度 | 当前 | 问题密度 | 优化后预估 |
|------|------|---------|-----------|
| 架构完整性 | 6/10 | 3 个 P0 | 8/10 |
| 上下文工程 | 5/10 | 3 个 P0 | 8/10 |
| 结构合理性 | 5/10 | 2 个 P0 | 9/10 |
| 盲区覆盖 | 4/10 | 2 个 P0 | 7/10 |
| **综合** | **5.0/10** | **10 个 P0/P1 问题** | **8.0/10** |

> 核心矛盾：CarrorOS Base 版的设计复杂度（200+ 文件、40 脚本、20 技能、24 节点）与它服务的目标模型（DeepSeek V4 Flash 13B 活跃参数）之间存在显著落差。优化的核心方向是"降认知负担"——不是删功能，是把功能藏到按需加载的门后。
