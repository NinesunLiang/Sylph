# Agent Harness 行业全景与 Carror OS 定位分析

> **版本**：v6.1.8 | **分析日期**：2026-05-02
> **分析方法**：公开资料交叉验证 + 源码级深度审计 + 行业模式对比
> **关键词**：Agent Harness、AI 行为治理、Hook-based Safety、LLM Guardrails

---

## 1. Agent Harness：2026 行业热词

2026 年，"Agent Harness" 已从工程实践升级为正式的架构模式。核心公式：

```
Agent = Model + Harness
```

行业共识定义（综合 tianpan.co、aimagicx.com、bridger.to 等多源）：

> "The harness is everything around the LLM call: the execution environment, the tool integrations, the memory system, the retry logic, the guardrails, the context assembly pipeline, the output validation."

行业已经形成一个关键判断：**可靠性的最大提升不来自换模型，而来自更好的 Harness。**

### 关键信号

- 学术界：Agent Harness 架构综述论文已发表（[preprints.org/manuscript/202604.0428](https://preprints.org/manuscript/202604.0428)）
- 工程界：Claude Code 的 Hook 机制被视为 Harness 模式的标志性实现（[aitoolfinder.org](https://aitoolfinder.org)）
- 政府级：联邦平台 EupraxiaLabs 发布 Agent Harness Pattern ADR-005 架构决策记录
- 共识：["The biggest gains in agent reliability are not coming from model swaps. They are coming from better harnesses."](https://bridger.to)

---

## 2. 行业 Harness 标准五层模型

| 层 | 职责 | 典型实现 |
|:---|:-----|:---------|
| L1 工具编排 | 工具注册、调用路由、参数校验 | Claude Code Tool Use、LangChain Tools |
| L2 上下文管理 | Prompt 组装、记忆系统、会话状态 | Claude Code CLAUDE.md、Cursor .cursorrules |
| L3 安全执行 | 权限控制、沙箱、危险操作拦截 | Claude Code Hooks (Exit 2)、Gemini CLI hooks |
| L4 错误恢复 | 重试逻辑、降级策略、超时处理 | 框架内置 retry、circuit breaker |
| L5 状态持久化 | 会话交接、进度保存、跨会话连续性 | 手动 /compact、文件级 checkpoint |

---

## 3. 主要玩家 Harness 实现对比

### Claude Code 原生

- L1-L2 强：原生 Tool Use + CLAUDE.md 上下文注入
- L3 有框架：PreToolUse/PostToolUse Hook 机制，Exit 2 物理阻断
- L4-L5 弱：无内置重试策略，/compact 是手动操作，无自动会话交接
- 本质：**提供了 Harness 的骨架（Hook 机制），但没有填充治理逻辑**

### Gemini CLI

- 2025 年底跟进了类似的 hooks 系统
- 同样是框架级能力，具体治理规则需用户自建

### Cursor

- `.cursorrules` 是纯 Prompt 级软约束，[AI 经常无视](https://www.knostic.ai/blog/cursor-does-not-follow-rules)
- 无 Hook 机制，无物理阻断能力
- 严格来说不算 Harness，只是 L2 上下文注入

### Devin

- 内置硬编码限制（不能 push 到 default branch 等）
- 不可配置、不可审计、不可扩展
- 是 Harness 但是封闭的黑盒 Harness

### 框架级方案（LangChain / CrewAI / AutoGen）

- 提供 L1 工具编排 + L4 错误恢复
- 安全层通常是 API 级的 guardrails（输入输出过滤），不是工具调用级
- 不涉及文件系统防护、DLP、上下文衰减

### 专业 Guardrails 框架（Guardrails AI / NeMo / Bedrock）

- 专注 LLM 输出验证：PII 检测、毒性过滤、schema 校验
- 工作在 L1 层（模型输出后、工具调用前）
- 不涉及工具执行层的物理防护

### 联邦级实践（EupraxiaLabs ADR-005）

- 政府级 Agent Harness 架构决策记录
- 定义了标准化的 Harness 接口规范
- 侧重合规审计和可追溯性，但仍在设计阶段

---

## 4. Carror OS Harness 能力逐层对标

| 层 | 行业标准做法 | Carror OS 做法 | 差异 |
|:---|:-----------|:-------------|:-----|
| **L1 工具编排** | 框架内置 Tool Use | 依赖 Claude Code 原生能力 | 持平 |
| **L2 上下文管理** | CLAUDE.md / .cursorrules 静态注入 | 渐进式加载 + SessionStart 动态注入 + 铁律速查表 + 学习笔记自动升华 | **显著领先** |
| **L3 安全执行** | Hook 框架存在但规则为空 | 32 个注册 Hook 填充完整治理逻辑：permission-gate、privacy-gate、context-guard、completion-gate、edit-guard、write-lock... | **当前完整实现** |
| **L4 错误恢复** | 简单 retry | 3 轮修复上限 + 根因假设记录 + BLOCKED 升级 + build-validator 分类诊断 + 方案复用自检 | **显著领先** |
| **L5 状态持久化** | 手动 /compact | auto-snapshot 自动保存 + session-handoff 交接备忘 + 甜点区主动交接 + OOM 熔断 + error-DNA 跨会话记忆 | **系统性方案** |

---

## 5. 超越五层模型：Carror OS 独有能力

Carror OS 还覆盖了行业五层模型之外的能力：

| 额外能力 | 实现 | 行业对标 |
|:---------|:-----|:---------|
| **DLP 数据防泄漏** | `varlock.py` 双向脱敏代理（正向 mask + 反向 restore） | 企业级 DLP 方案 $50K+ |
| **抗上下文衰减** | 五层防漂移（注入 → 复诵 → 锚定 → 漂移词检测 → 甜点区交接 → OOM 熔断） | 无对标 |
| **证据门禁** | `completion-gate.sh` 要求 VERIFIED + 20 字符证据 | 无对标 |
| **A→B→A 对抗验证** | `subagent_reviewer.py` Zero-shot Persona Prompt 唤起独立 Sub-agent | 无对标 |
| **文件级并发锁** | `oma_lock_manager.py` 使用 `O_CREAT|O_EXCL` 原子操作 | 需 Redis/RPC |
| **反模式实时检测** | `anti-patterns.md` 14 个模式 + 检测信号 + 正确策略 | 无对标 |

---

## 6. 竞争全景图

```
                    Harness 完整度
                        ^
                        |
           Carror OS *  |  (32 hooks + DLP + 抗衰减 + 证据门禁)
                        |
                        |
                        |
      NeMo *            |         * Devin (黑盒)
                        |
    Guardrails AI *     |    * Copilot Enterprise
                        |
              * Aider   |  * Cursor (.cursorrules)
      ------------------+-------------------> 智能/自动化
                        |
         Claude Code *  |  (Hook 框架存在，规则为空)
                        |
```

---

## 7. 核心洞察

### 行业现状：框架有了，内容是空的

Claude Code 在 2025 年推出 Hook 机制，Gemini CLI 跟进。这意味着 **Harness 的基础设施层已经就绪**。但绝大多数用户的 Hook 配置是空的——他们有了"操作系统的系统调用接口"，但没有"安全内核"。

### Carror OS 的定位：第一个完整填充的 Agent Harness

Carror OS 不是在做框架，而是在做 **框架之上的完整治理层**。32 个注册 Hook 不是空壳，每一个都有具体的拦截逻辑、配置开关、证据要求。加上 DLP、抗衰减、证据门禁、A→B→A 交叉验证这些行业无对标的能力，Carror OS 定义了 Harness 的上限。

### 类比

> 如果 Claude Code 的 Hook 机制是"操作系统提供了系统调用接口"，
> 那 Carror OS 就是"在这个接口上构建了完整的安全内核"。
> 这也解释了为什么它叫 **AI Native Developer Operating System**——它确实在做 OS 层的事。

---

## 8. 一句话定位

> **行业在 2026 年刚刚认识到 Harness 的重要性。**
> **Carror OS 已经交付了行业第一个完整的 Agent Harness 实现。**
> **当别人还在讨论"要不要给 AI 加护栏"时，Carror OS 已经把 32 道注册护栏焊死了。**

---

**Carror OS -- AI Native Developer Operating System**
**先守护，后武装。Guard First, Arm Later.**
