# Carror OS 产品指南：三阶段产品结构与全特性参考

> **版本**：v6.1.8 | **更新日期**：2026-05-02
> **设计哲学**：先守护，后武装 (Guard First, Arm Later)

---

## 设计哲学

真正的操作系统从来不会强迫用户一开机就去学习复杂的系统调用。它应该默默地在后台管理内存和进程。

Carror OS 提出了 **"先守护，后武装 (Guard First, Arm Later)"** 的渐进式交付哲学，将系统切分为三层递进的火箭架构：

- **Level 1 - Harness Only**：最底层的 Kernel 防火墙。只有物理拦截器，零认知负担。
- **Level 2 - Base Edition**：静默守护者。增加 10 款自动化审查门禁，被动触发，全自动运行。
- **Level 3 - Enhanced Edition**：高阶武器库。24 款流水线 Skill，主动式调度，需要指挥权。

---

## Level 1 — Harness Only（纯内核版）

**构成**：32 个底层物理拦截 Hooks（27 个注册激活 + 5 个独立探针）
**设计**：绝对的零认知负担。完全没有主动工作流，AI 仅仅是被戴上了安全镣铐。

| 能力模块 | 具体包含 | 说明 |
|:---------|:---------|:-----|
| 底层防线 (Hooks) | `privacy-gate`, `context-guard`, `permission-gate` 等 32 个 Hook | 拦截隐私泄露、危险命令、80% Context 熔断、记录错误 DNA |

**适合**：只想给 AI 加一层物理防呆锁，完全不想看到任何复杂配置的极简主义者。

---

## Level 2 — Base Edition（基础守护版，默认推荐）

**构成**：Level 1 全部防线 + 10 款自动化审查门禁 Skills
**设计**：静默式质量总控。被动式触发，全自动运行。
**安装**：`bash install.sh base`

| 能力 | 作用 | 触发方式 |
|:-----|:-----|:---------|
| 底层拦截网 (Hooks) | 物理阻断 AI 的幻觉、破坏性命令、隐私泄露和长会话智力衰减 | 静默拦截（任何时刻） |
| `lx-pre-commit` | 提交前质量门禁总控，包含类型检测、增量编译、测试与代码审查 | `/lx-pre-commit` 或集成至 Git Hook |
| `lx-pre-push` | 推送前安全与合规门禁，包含 Commit 格式校验 | `/lx-pre-push` |
| `lx-code-review` | 语言无关的通用代码审查（附带 Auto-fix） | 门禁自动唤醒 / 主动调用 |
| `lx-react-review` | 前端/React 专属审查 | 门禁自动唤醒 / 主动调用 |
| `lx-security-review` | 安全扫描，检测硬编码和漏洞 | 门禁自动唤醒 / 主动调用 |
| `lx-style-guide` | 样式规范审查 | 门禁自动唤醒 / 主动调用 |
| `lx-web-perf` | Web 性能审查 | 门禁自动唤醒 / 主动调用 |
| `lx-oma` | OMA 并发锁管理 | 后台静默运行 / 主动调用 |
| `lx-perf-analysis` | 性能分析诊断 | 后台静默运行 / 主动调用 |
| `lx-race` | 竞态条件检测 | 后台静默运行 / 主动调用 |

**适合**：
- 刚接触 AI 辅助开发的新手，不想改变现有开发习惯
- 只需要一个"懂代码的 AI"陪聊，并在提交代码前自动帮你查漏补缺

---

## Level 3 — Enhanced Edition（全栈增强版）

**构成**：Level 2 全部能力 + 14 款主动式工作流 Skills
**设计**：高学习成本，高回报率。主动式调度，需要指挥权。
**安装**：`bash install.sh enhanced`

### 三大任务驱动引擎

| Skill | 定位 | 说明 |
|:------|:-----|:-----|
| `/lx-rpe` | 大型特性流水线 | Research → Plan → Execute 三阶段，带 50% 甜点区交接与 A→B→A 交叉验证对抗 |
| `/lx-task-spec` | 中型复杂任务 | 精确 AC 驱动，无需冗长 PRD |
| `/lx-todo` | 零散小任务 | ≤3 文件的 5 步快速闭环，超过自动升级 |

### 高阶诊断与生成

| Skill | 说明 |
|:------|:-----|
| `/lx-root-cause-analysis` | 5-Why 根因追溯 |
| `/lx-debug-spec` | 深水区并发调试 |
| `/lx-prd` | 自动化产品需求文档生成 |
| `/lx-tdd-spec` | TDD 测试驱动场景生成 |
| `/lx-browser-verify` | Playwright E2E 浏览器验收 |
| `/lx-golang-test` | Go 语言专属自动化测试框架 |
| `/lx-frontend-test` | 前端专属自动化测试框架 |

### 专业运维与监控

| Skill | 说明 |
|:------|:-----|
| `/lx-status` | 健康监控大屏：Token 节省、错误自愈力、任务执行链路图 |
| `/lx-varlock` | 企业级 DLP 隐私脱敏代理，双向透明混淆 |
| `/lx-validate-skill` | Skill 完整性验证，自动检测元数据/脚本漂移 |

**适合**：
- Tech Lead、架构师、资深全栈工程师
- 正在接手极其复杂的重构项目，必须严格遵循工程纪律的极客
- 需要让 AI 执行复杂的多步骤调试、并需要实时监控 Token 效率和自愈率的"一人成军"型黑客

---

## 无缝切换

Carror OS 的架构完全解耦，你可以随时、安全地在三个层级之间平滑切换，底层 Hooks 永不掉线，且完全无损：

```bash

# 极简主义：只要底层防线
bash install.sh harness

# 默认守护：提交前的自动化门禁与审查
bash install.sh base

# 火力全开：调动大模型工作流流水线
bash install.sh enhanced
```

---

## 安装后验收

### 半自动验收（推荐新成员、日常回归）

| 文件 | 说明 |
|:-----|:-----|
| `tests/auto-feature-test.md` | 验收执行手册。对 AI 说"请帮我执行战区一的测试"即可启动 |
| `tests/auto-feature-test-log.md` | 验收战报模板，边测试边记录 |

### 全人工验收（正式交付、安全审计、Zero Trust）

| 文件 | 说明 |
|:-----|:-----|
| `tests/manual-acceptance-test.md` | 49 项全人工验收清单，覆盖全部 32 个 Hook 及核心 Skill |
| `tests/manual-acceptance-test-log.md` | 对应战报模板，Fail 项必须填写根因与修复方案 |

### 终极审判（Dogfooding 前置）

| 文件 | 说明 |
|:-----|:-----|
| `tests/final-exam.md` | 终极人工审判清单，零信任原则，每一项亲自执行才算数 |

---

**Carror OS — AI Native Developer Operating System**
**先守护，后武装。Guard First, Arm Later.**
