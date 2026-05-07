# Carror OS：三阶段产品结构与版本说明书

> **The Three-Stage Rocket**
> **这不是功能的阉割，而是认知负荷的完美释放。**

---

## 1. 哲学思维产物 (The Philosophy)

在过去的迭代中，我们发现如果一次性将 24 款强大的 AI 开发流水线（Skill）全部推给一个新用户，他会面临巨大的**认知过载 (Cognitive Overload)**。他不知道该从哪里学起，他会害怕敲下错误的命令。
真正的操作系统从来不会强迫用户一开机就去学习复杂的系统调用。它应该默默地在后台管理内存和进程。
因此，Carror OS 提出了 **“先守护，后武装 (Guard First, Arm Later)”** 的渐进式交付哲学，将系统硬性切分为三层递进的火箭架构：
* **Level 1 - 纯内核版 (Harness Only)**：它是最底层的 **Kernel 防火墙**。完全没有应用态 Skill，只有物理拦截器。它只在你犯下致命错误时站出来**硬阻断**你。
* **Level 2 - 基础守护版 (Base Edition)**：它是 **静默守护者**。在纯内核之上，增加了 10 款代码审查与安全门禁 Skill。你不需要学习新命令，只需要像往常一样让 AI 帮你 `pre-commit`，它就会在后台全自动完成质量检测。
* **Level 3 - 全栈增强版 (Enhanced Edition)**：它是 **Userland（用户空间）的高阶武器库**。包含所有的 24 款流水线 Skill，这是需要你主动学习、阅读文档才能驾驭的超级兵器库，为你提供”一人成军”的自动化战力。

---

## 2. 版本清单 (What's Included)

### 🧱 Level 1

- Harness Only (纯内核版)
  **构成**：32 个底层 Hook 脚本（30 个注册激活 + 2 个独立工具）。
  **设计**：绝对的 0 认知负担。完全没有主动工作流，AI 仅仅是被戴上了安全镣铐。

| 能力模块 | 具体包含 | 说明 |
| :--- | :--- | :--- |
| **底层防线** (Hooks) | `privacy-gate`, `context-guard`, `permission-gate` 等 30 个注册 Hook | 负责拦截隐私泄露、危险终端命令、80% Context 内存熔断、记录错误 DNA。 |

### 🛡️ Level 2 - Base Edition (基础守护版

- 默认推荐)
  **构成**：Level 1 的全部防线 + 10 款自动化审查门禁 Skills。
  **设计**：静默式质量总控。被动式触发，全自动运行。

| 能力模块 | 具体包含 | 说明 |
| :--- | :--- | :--- |
| **提交门禁** (Skills) | `lx-pre-commit`, `lx-pre-push` | 用户只需要在代码完成时说一句”帮我做个 pre-commit”，门禁总控就会自动拉起后续检查。 |
| **自动审查** (Skills) | `lx-code-review`, `lx-react-review`, `lx-security-review`, `lx-style-guide`, `lx-web-perf` | 这 5 款 Skill 在基础版中是**不需人工调用**的，它们作为 `pre-commit` 流水线的一环，在后台被自动唤醒执行代码和安全审查。 |
| **深度分析** (Skills) | `lx-oma`, `lx-perf-analysis`, `lx-race` | 并发锁管理、性能分析与竞态条件检测。在后台静默运行，不增加用户认知负担。 |

### ⚔️ Level 3

- Enhanced Edition (全栈增强版)
  **构成**：Level 2 的全部能力 + 14 款主动式工作流 Skills。
  **设计**：高学习成本，高回报率。主动式调度，需要指挥权。

| 能力模块 | 额外包含 | 说明 |
| :--- | :--- | :--- |
| **大型特性流水线** | `lx-rpe` | 处理复杂业务的 Research -> Plan -
> Execute 三阶段工作流，带有 50% 甜点区交接与 A→B→A 交叉验证对抗。 |
| **中/小型任务驱动** | `lx-task-spec`, `lx-todo` | 精确 AC 驱动的中型任务，与 ≤3 文件的快速 Bug 修复闭环。 |
| **高阶诊断生成** | `lx-root-cause-analysis`, `lx-debug-spec`, `lx-prd`, `lx-tdd-spec`, `lx-browser-verify` | 5-Why 根因分析、深水区并发调试、PRD 文档和 TDD 测试代码的自动化生成。 |
| **专业测试与监控** | `lx-golang-test`, `lx-frontend-test`, `lx-varlock`, `lx-status`, `lx-validate-skill` | 语言专属测试框架、**DLP 透明脱敏代理 (varlock)**、一键健康监控大屏 (status)。 |

---

## 3. 适合谁 (Who is it for?)

**Harness Only 适合：**
* 只想给 AI 加一层物理防呆锁，完全不想看到任何复杂配置的极简主义者。

**Base 适合：**
* 刚接触 AI 辅助开发的新手，不想改变现有开发习惯。
* 只需要一个”懂代码的 AI”陪聊，并在提交代码前自动帮你查漏补缺。

**Enhanced 适合：**
* Tech Lead、架构师、资深全栈工程师。
* 正在接手极其复杂的重构项目，必须严格遵循工程纪律的极客。
* 需要让 AI 执行复杂的多步骤调试、并需要实时监控 Token 效率和自愈率的”一人成军”型黑客。

---

## 4. 无缝切换指南 (How to Switch)

Carror OS 的架构完全解耦，你可以随时、安全地在三个层级之间平滑切换，底层 Hooks 永不掉线，且完全无损（Safe In-Place Upgrade）。
```bash
# 0. 极简主义：我只要底层防线，剥离所有应用态技能 (Harness)
bash install.sh harness

# 1. 默认守护：我需要提交前的自动化门禁与审查 (Base)
bash install.sh base

# 2. 火力全开：我遇到了硬骨头，需要调动大模型工作流流水线 (Enhanced)
bash install.sh enhanced
```
