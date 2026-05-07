# Carror OS — 全特性参考手册 (v6.1.8 Cross-Platform Edition)

> **版本**：v6.1.8 | **更新日期**：2026-05-03
> **设计哲学**：先守护，后武装 (Guard First, Arm Later)。
> Carror OS 分为【基础版】与【增强版】，根据你的需要按需加载。

---

## 🛡️ 基础版 (Base Edition: 零学习成本的静默守护者)

**适用人群**：只需 AI 变规矩、不犯错，不想学习新指令的开发者。
**安装方式**：`bash install.sh base`
**包含内容**：Harness-kit (30 个注册 Hooks) + 10 款门禁审查 Skill。
| 能力 | 作用 | 触发方式 |
| :--- | :--- | :--- |
| **底层拦截网 (Hooks)** | 物理阻断 AI 的幻觉、破坏性命令 (如 `rm -rf`)、隐私泄露和长会话智力衰减。 | **静默拦截** (任何时刻) |
| `lx-pre-commit` | 提交前质量门禁总控，包含类型检测、增量编译、测试与代码审查。 | 终端输入 `/lx-pre-commit` 或集成至 Git Hook |
| `lx-pre-push` | 推送前安全与合规门禁，包含 `ANK-1.5.6.16` Commit 格式校验。 | 终端输入 `/lx-pre-push` |
| `lx-code-review` | 语言无关的通用代码审查（附带 Auto-fix）。 | 门禁自动唤醒 / 主动调用 |
| `lx-react-review` | 前端/React 专属审查。 | 门禁自动唤醒 / 主动调用 |
| `lx-security-review`| 安全扫描，结合底层工具检测硬编码和漏洞。 | 门禁自动唤醒 / 主动调用 |
| `lx-style-guide` | 样式规范审查。 | 门禁自动唤醒 / 主动调用 |
| `lx-web-perf` | Web 性能审查。 | 门禁自动唤醒 / 主动调用 |
| `lx-validate-skill` | Skill 验收审查。frontmatter/原子化声明/节点引用 11 项规则检查。 | 主动调用 |

---

## ⚔️ 增强版 (Enhanced Edition: 高阶武器库)

**适用人群**：接手复杂重构、大型特性开发、深水区 Debug，希望”一人成军”的资深工程师。
**安装方式**：`bash install.sh enhanced` (或 `full`)
**包含内容**：基础版的全部能力 + 以下 14 款主动工作流 Skill。

### 1. 三大任务驱动引擎 (Task Drivers)

* **/lx-rpe**：大型特性流水线。包含 Research -> Plan

> Execute 三阶段，带有 **50% 上下文甜点区主动交接** 及 A→B→A 交叉验证对抗。
* **/lx-task-spec**：中型复杂任务。精确 AC 驱动，无需冗长 PRD。
* **/lx-todo**：零散小任务。≤3个文件的 5 步快速闭环，超过自动升级。

* **/lx-oma**：一人成军司令部。需求拆解为正交功能分支，支持目录/单文件输入。
* **/lx-race**：蜂群协调层。注册子任务 → 派发 → 收集 → 报告，复用 OMA Lock 并发引擎。

### 2. 高阶诊断与生成 (Diagnostics & Generation)

* **/lx-root-cause-analysis**：5-Why 根因追溯。
* **/lx-debug-spec**：深水区并发调试。
* **/lx-prd**：自动化产品需求文档生成。
* **/lx-tdd-spec**：TDD 测试驱动场景生成。
* **/lx-browser-verify**：Playwright E2E 浏览器验收。
* **/lx-golang-test** & **/lx-frontend-test**：语言专属的自动化测试框架。
* **/lx-perf-analysis**：Go 性能分析。CPU/内存 profiling、goroutine 泄漏检测、benchmark 分析。

### 3. 专业运维与监控 (Specialized Tools)

* **/lx-status**：健康监控大屏。三屏数据展示”Token 节省”、”错误自愈力”、”任务执行链路图”。
* **/lx-varlock**：企业级 DLP 隐私脱敏代理管理器。允许 AI 在脱敏占位符的环境下进行密码交互与命令执行，双向透明混淆，彻底隔绝泄密。 **(用法：`varlock.py set KEY val` -> `varlock.py read .env`)**

---

## 切换指南

无论是从基础版升至增强版，还是回退：

```bash
# 升级到全特性增强版
bash install.sh enhanced

# 回退为只做静默拦截的基础版
bash install.sh base
```

---

## ✅ 安装后验收

安装完成后，可通过内置的自动化验收流程确认所有特性正常运作：

### 第一部分：半自动验收（推荐新成员、日常回归）

| 文件 | 说明 |
| :--- | :--- |
| **`auto-feature-test.md`** | 验收执行手册。对 AI 说"请帮我执行战区一的测试"即可启动，无需手动敲命令。涵盖 Agentic UI 门禁体验、图表化可观测性、OMA 并发引擎等核心特性。 |
| **`auto-feature-test-log.md`** | 验收战报模板。边测试边记录实际表现，最终签字存档。 |

> 💡 **新成员首次上手**：直接打开 `auto-feature-test.md`，按头部三步引导操作，整个过程以 AI 全自动代跑为主，你只需要在弹出的交互表单里做选择。

---

### 第二部分：全人工验收（正式交付、安全审计、Zero Trust）

| 文件 | 说明 |
| :--- | :--- |
| **`manual-acceptance-test.md`** | 全人工验收清单，共 **49 项**，覆盖 harness-kit 全部 30 个注册 Hook 及所有核心 Skill。每一条命令你亲自执行，每一个结果你亲眼确认。Agentic UI 的拦截弹窗由 Hook 真实触发，而非 AI 模拟。 |
| **`manual-acceptance-test-log.md`** | 对应战报模板，49 行空白记录表，Fail 项必须填写根因与修复方案，验收官签字后存档。 |

> ⚠️ **正式交付场景**：使用全人工验收流程。AI 的总结不算证据，你的亲手执行和签字才算数。这是 Carror OS 零信任理念的最高表达。
