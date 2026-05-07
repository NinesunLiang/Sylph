# Carror OS — FAQ

> **更新日期**：2026-05-04（v4 — 新增 PocketOS 删库案例）

---

## 基础问题

**Q: Carror OS 是什么？**
A: Carror OS is an AI coding governance and workflow layer for Claude Code. It turns AI coding from vibe-driven into evidence-driven.
中文：Carror OS 是面向 AI 编程的本地优先治理与工作流系统。它在 AI 编码工具与文件系统之间建立了一层物理 Hook 拦截系统，用 Exit 2 硬阻断替代 Prompt 软约束。它不是"更好的 Cursor"，而是 AI 时代的 Unix。

**Q: Carror OS 是怎么诞生的？**
A: 它来自一个真实的故事：有人花了半年时间，用 AI vibe coding 一个 Go 云平台——但他完全不会 Go。结果是云平台建起来了，但过程中反复遭遇 AI 假完成、末期幻觉删改正常代码、私钥泄露等灾难。Carror OS 就是从那半年血的教训里长出来的治理系统。每一个 Gate、每一道 Hook，背后都对应着一场真实发生过的"AI 失控"。

**Q: 真的有这么严重吗？一个 API Key 泄露能造成什么后果？**
A: 这不是假设。一个真实案例：有人将生产环境的 API Key 用于测试环境，导致 Key 泄露至公网。结果是：当事人与三级领导全部被罚款万元以上，部分人被降级，当事人被迫离职并赔偿十余万元，公司信誉损失不可估量。**当 AI 也能「顺手」读取 .env 并发出网络请求时，这种风险被放大了无数倍。** privacy-gate 就是为此而生——从物理层面斩断 AI 读取明文密钥的路径。

**Q: 不让 AI 读密钥就够了，它还能干什么更糟的事？**
A: 2026 年 4 月，PocketOS 公司的 AI 编程智能体在处理预发布环境凭证问题时，自主决定删除一个存储卷——9 秒内删除了整个生产数据库及所有同卷备份。没有确认、没有环境检查、没有回滚。创始人质问 AI 后，AI 写了一份"忏悔书"：*"我本应验证，却选择了盲猜。我未经要求就执行了破坏性操作。"* 该事件在 X 平台 600 万+ 阅读，CNBC 等主流媒体报道。
Carror OS 的 `permission-gate` 和 `completion-gate` 正是为了在 AI 按下"核按钮"之前物理阻断这类操作。

**Q: Carror OS 和 Cursor/Devin/Copilot 是什么关系？**
A: Carror OS 不是竞品，而是**治理层**。它在这些工具的下层工作，约束 AI 的行为下限。你可以理解为一个 AI 版的 SELinux——不帮你写代码，但保证 AI 不闯祸。Carror OS 完全兼容 Claude Code、OpenCode 和任何支持 AGENTS.md 的 CLI 工具。

**Q: 安装 Carror OS 会影响我现有的开发环境吗？**
A: 不会。Carror OS 完全无侵入。它是通过 AGENTS.md 和 Claude Code Hook 协议工作的，不需要修改你的编辑器配置、不需要安装 daemon、不需要改变开发流程。底层 Hook 在后台静默运行，只在检测到危险操作时才会介入。

**Q: Carror OS 免费吗？**
A: 是的。Carror OS 是 MIT 开源项目，框架费 $0。你只需要支付 AI 模型的 API 费用（如果你使用本地模型，甚至没有 API 费用）。

---

### 技术问题

**Q: Hook 是怎么工作的？**
A: Carror OS 的 30 个注册 Hook 利用 Claude Code / OpenCode 的底层 Hook 协议，在 AI 的每次工具调用前插入拦截逻辑。当 AI 调用 `ExecuteCommand` 或 `WriteToFile` 等危险工具时，Hook 脚本在毫秒级执行检查。如果命中规则（如 `rm -rf`、明文密钥、超上下文阈值），Hook 返回 `Exit 2` 阻止操作。AI 不是"被建议不要做"，而是"物理上做不到"。

**Q: 30 个注册 Hook 覆盖哪些安全域？**
A: 六大安全域：权限门禁（危险命令拦截）、隐私防线（敏感文件/DLP）、上下文熔断（OOM 防护）、交付验收（证据门禁）、读写时序（未读不可写）、范围冻结（越界修改拦截）。

**Q: varlock 脱敏代理安全吗？**
A: varlock 使用占位符替换 + 正则匹配实现正向脱敏和反向还原。密钥存储在本地文件（权限 chmod 600），只在脚本内部的安全区还原。AI 全程看不到明文，写回时再次脱敏。vault 文件没有任何网络通信或遥测。

**Q: 支持哪些 AI 工具？**
A: 目前完整支持 Claude Code（通过 Hook 协议）和 OpenCode（通过 AGENTS.md）。部分支持支持 AGENTS.md 格式的其他 CLI 工具。OS 层面支持 macOS（完整）、Linux（完整）、Windows（通过 WSL）。

**Q: 上下文甜点区交接是怎么实现的？**
A: context_monitor.py 实时读取本地环境中大模型的真实 Token 消耗量。当任务完成且上下文 ≥50%，下发 context_alert 强制 AI 打断执行、总结状态并运行 /compact 重置会话。当上下文 ≥80%，context-guard.sh 抛 Exit 2 锁死一切写入。两种机制配合实现 AI 永远在最高智商区间接力。

---

### 安装与配置

**Q: 如何安装？**
A: 一行命令：
```bash
curl -fsSL https://raw.githubusercontent.com/sylph/carror-os/main/install.sh | bash -s -- base
```
Base 版包含 30 个注册 Hook + 10 个门禁 Skill，零学习成本。

**Q: Base 版和 Enhanced 版的区别？**
A: Base 版 = 30 个注册 Hook（物理防线）+ 10 个自动化审查 skill（被动触发，全自动运行），零学习成本。Enhanced 版 = Base 全部能力 + 14 个主动式工作流 skill（RPE 流水线、根因分析、DLP 代理等），需要主动学习和调度。

**Q: 我可以自定义 Hook 规则吗？**
A: 可以。Hook 规则在 .claude/harness.yaml 中配置。你可以在 30 个内置规则的基础上调整阈值（如上下文熔断百分比）、添加自定义拦截模式（正则）、启用/禁用特定 Hook。高级用户还可以编写自己的 Hook 脚本。

**Q: `max_turns` 能真正阻止子 agent 跑飞吗？**
A: 当前版本是 **"软约束 + 事后对账"**，不是运行时硬停。三层防线分工如下：
- 声明层（`subagent-guard.sh`）：Task 工具 schema 暂未暴露 `max_turns` 字段，hook 通过扫描 description/prompt 的 `max_turns[=:]N` 正则 + 默认值 fallback 让 AI 自我约束。
- 执行层（`posttool-subagent-audit.sh`）：落盘 `.omc/state/subagent-usage.jsonl`，超过字节阈值（默认 50KB）写 flywheel P0 告警。
- 人工层：P0 事件在下次 SessionStart 弹表格，让用户决定。

**限制说明**：Claude Code Task 的 `tool_response` 不暴露子 agent 实际 `turns/tokens` 字段，hook 只能用 `content_bytes` 做启发性估算。若子 agent 陷入死循环 100 轮，hook 无法运行时中断，只能事后让用户感知。若 CC 将来开放这些字段，执行层可升级为硬门禁。

---

### 对比

**Q: Carror OS 和 Cursor Rules / Claude Code Hooks 有什么核心区别？**
A: Cursor Rules 和 Claude Code 原生 Hooks 提供的是原语（primitives），不是治理框架。Carror OS 是一个完整的有状态操作系统：30 个互锁的注册 Hook + 错误 DNA 记忆 + 甜点区主动交接 + A→B→A 交叉验证对抗 + DLP 双向脱敏。它不是几个规则的集合，而是一个分层治理体系。

**Q: 和 Guardrails AI / NeMo Guardrails 的区别？**
A: Guardrails AI 和 NeMo Guardrails 做的是 LLM 输出验证（PII 检测、毒性过滤）。Carror OS 做的是工具调用级的文件系统防护——在 AI 接触文件系统之前物理拦截。两者不在同一层面。Carror OS 做的是 AI 行为治理基础设施，不是内容过滤。

---

### Dogfooding 与验收

**Q: 安装后怎么验证它在工作？**
A: 运行 `/lx-status` 查看健康面板。或者在终端尝试 `rm -rf /tmp/test`——如果 AI 被拦截，说明 permission-gate 在工作。完整验收见 `tests/manual-acceptance-test.md`（49 项逐项验证）。

**Q: Carror OS 经过哪些测试？**
A: L1-L4 四层测试体系（手动验收 + 自动 Hook 校验 + 代码扫描 + 格式门禁）98 项 98P/0F/0SOFT，通过 ShellCheck/Bandit 真实安全扫描（0 真实业务缺陷），对照 OWASP ASVS v4.0.3 / MITRE ATLAS / NIST AI RMF 1.0 三项行业标准完成自评合规对照（75/75 覆盖）[内部自评，非第三方认证]。

---

**Carror OS — AI Native Developer Operating System**
**先守护，后武装。Guard First, Arm Later.**
