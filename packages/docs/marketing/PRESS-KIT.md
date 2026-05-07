# Carror OS — 给 AI 装上刹车

> **一句话**：Carror OS 是第一个在 Hook 应用层面对 AI 进行物理行为约束的开源治理框架。它不是"建议"，是"拔电源"。

---

## 问题

2026 年，AI 辅助编程已经成为主流。但每个工程师都经历过：

- AI 在你没注意时执行了 `rm -rf /var/www`
- AI 说"搞定了"，但什么都没做
- AI 把你的 `.env` 文件内容发给了云端 API
- 长对话 30 轮后，AI 开始改它不该改的文件
- 同一个错误修了 8 次，每次都说"这次应该没问题了"

**现有方案全部失效**——Cursor Rules、Claude Code Hooks、Copilot Instructions 都是在 Prompt 层说话，靠"请"和"建议"。AI 可以礼貌地忽略它们。

---

## 解决方案

Carror OS 选择了完全不同的路径：**不跟 AI 说话，直接拦截它的工具调用**。

```
正常流程:  用户 → AI → 工具调用 → 执行
Cursor:    用户 → AI → [Prompt 建议] → 工具调用 → 执行
Carror OS: 用户 → AI → [⚠️ Hook 拦截] → 拒绝 / 授权 / 审计
```

### 三层架构

| 层 | 做什么 | 怎么做的 |
|------|------|---------|
| **Harness-kit**（内核） | 32 个物理 Hook，在 AI 接触文件系统之前拦截 | `Exit 2` 硬阻断，不是 Prompt 请求 |
| **lx-skills**（用户态） | 24 个工作流 Skill，从 PRD 到提交的全周期 | Markdown 指令集 + 19 个 Python 工具 |
| **Profiles**（桥接） | 5 种语言环境的一键适配 | YAML 配置，零代码切换 |

---

## 关键能力

### 1. 你在 AI 要 `rm -rf` 时拔了它的电源

32 个 Hook 覆盖六大安全域：

| 域 | 代表 Hook | 拦截什么 |
|------|----------|---------|
| 权限门禁 | `permission-gate.sh` | `rm -rf`、`DROP TABLE`、`git push --force` |
| 隐私防线 | `privacy-gate.sh` | `.env`、`*.pem`、`id_rsa`、明文 Token |
| 上下文熔断 | `context-guard.sh` | 上下文 ≥80% 时物理锁死一切写入操作 |
| 交付验收 | `completion-gate.sh` | AI 无 VERIFIED 证据声称"搞定了" |
| 读写时序 | `edit-guard.sh` | 未读文件不允许编辑 |
| 范围冻结 | `pretool-edit-scope.sh` | 超出任务范围的文件修改 |

**所有 Hook 经过 L1-L4 四层测试体系（手动验收 + 自动 Hook 校验 + 代码扫描 + 格式门禁）全部通过，通过 ShellCheck/Bandit 真实安全扫描（0 真实业务缺陷），对照 OWASP ASVS v4.0.3 / MITRE ATLAS / NIST AI RMF 1.0 三项行业标准完成自评合规对照（75/75 覆盖）[内部自评，非第三方认证]。**

### 2. AI 全程不知道你的真实密钥

`varlock` 是开源社区的双向脱敏代理：

```
AI 看到的:    curl -H "Authorization: {API_KEY}"
真实执行的:   curl -H "Authorization: sk-ant-abc123..."
AI 写回的:    API_KEY={API_KEY}
文件存储的:   API_KEY=sk-ant-abc123...
```

AI 始终在数据隔离沙箱中工作，从未接触过任何明文凭证。

### 3. 长对话不再是"慢性智障"

三层防漂移机制自动运行，不需要你手动 `/compact`：

| 层级 | 触发条件 | 动作 |
|------|---------|------|
| SessionStart | 每次新会话 | 铁律注入上下文 |
| 每 10 轮 | 轮次计数器 | 6 条思想钢印复诵 |
| 每次写文件 | 写操作前 | 范围冻结 + 规则锚定 |
| 50% 甜点区 | 上下文过半 | 强制交接，状态最干净时重置 |

### 4. 不是说"搞定了"，先拿证据来

`completion-gate.sh` 要求 AI 提供 `>= 20 字符` 的 VERIFIED 证据文件才能标记任务完成。没有测试日志、没有输出截图、没有验证命令 → 任务永远处于"进行中"。

---

## 防护能力对比

> **说明**：Carror OS 是运行在 AI CLI 之上的治理层，不是编码工具或 IDE。下表对比的是**执行层原生防护能力**与**叠加 Carror OS 治理层后的全栈防护能力**，并非将治理层与编码工具当作同类产品并列。Carror OS 自身的版本对比不套用此框架。

| 维度 | Carror OS | Devin | Cursor Rules | Claude Hooks |
|------|:--:|:--:|:--:|:--:|
| 防御层级 | **Exit 2 物理阻断** | 商业黑盒 | Prompt 软约束 | Hook 原语 |
| DLP 脱敏 | **双向混淆代理** | 无 | 无 | 无 |
| 上下文防护 | **三层自动防漂移** | 未知 | 无 | 手动 /compact |
| A/B 对抗审查 | **A→B→A 交叉验证** | 无 | 无 | 无 |
| 并发协同 | **文件锁 + MECE 拆解** | 内置 | 无 | 无 |
| 任务流水线 | **RPE 9 步闭环** | 内置 | 无 | 无 |
| 成本 | **$0** | $500/月 | 包含在订阅 | 包含在订阅 |
| 可审计性 | **全开源** | 商业黑盒 | 部分开源 | 闭源 |

**核心竞争力**：Carror OS 不在比"写代码的速度"，而在解决一个其他人根本没认真对待的问题——**如何在工程级别约束 AI 的行为下限**。

---

## 差异化竞争力

以下设计在开源社区中**没有已知同类实现**：

1. **varlock 双向脱敏代理** — AI 全程在数据隔离沙箱中工作
2. **completion-gate 证据门禁** — 物理阻止 AI 无证据声称完成
3. **三层防漂移机制** — 从 SessionStart 到每次写文件的全周期覆盖
4. **50% 甜点区主动交接** — 在 AI 状态最干净时强制重置

---

## 能力评分

### 四维能力矩阵

```
                    长期治理    AI智能化    经济性      安全性
                    ────────   ────────   ────────   ────────
Carror OS           ████████▌  ███████▌   ████████▌  █████████
Devin Guardrails    ██████▌    ████████▌   ██████     ██████▌
Cursor Rules        ███▌       ██████▌    ██████▌    ██▌
Claude Code Hooks   █████▌     ██████▌    ██████▌    █████
Copilot Custom      ██▌        ██████▌    ██████▌    ██
```

### 综合评分（Opus 4.7 + GPT-5 模型评估，[内部评估，非行业标准]）

| 维度 | 评分 | 说明 |
|------|:--:|------|
| 设计理念 | 9.0 | "先守护，后武装"的哲学成熟，三级火箭模型精准 |
| 架构完整性 | 8.5 | 内核/用户态分层 + Hook/Skill/Script 三层协作 |
| 代码实现 | 7.5 | Hook 和 Python 脚本质量合格，包发布流程待完善 |
| 文档质量 | 9.0 | CHANGELOG 53KB、SKILL.md 471 行、测试文档 49 项 |
| 测试覆盖 | 8.0 | L1-L4 四层测试 98 PASS / 0 FAIL / 0 SOFT，ShellCheck/Bandit 0 缺陷 |
| 差异化能力 | 9.0 | 5 项设计在开源社区无同类 |
| 工程成熟度 | 7.0 | packages 打包待修 |
| 实用性 | 7.0 | 强依赖 Claude Code/OpenCode Hook 协议 |
| **综合** | **8.1** | 理念领先、设计精密、工程收尾中 |

---

## 适用场景

| 适合 | 不适合 |
|------|--------|
| 多人协作的 AI 编程团队 | 想一键安装就变强的个人用户 |
| 需要审计和合规的企业 | 只用 Web IDE 的开发场景 |
| 担心 AI 泄密的安全团队 | 不需要任何约束的自由派 |
| 长期维护的大型项目 | 一次性的原型开发 |

---

## 安装

```bash
curl -fsSL https://raw.githubusercontent.com/sylph/carror-os/main/install.sh | bash -s -- base
```

Base 版：32 个 Hook 安全底座 + 10 个门禁审查 Skill，零学习成本。

```bash
curl -fsSL https://raw.githubusercontent.com/sylph/carror-os/main/install.sh | bash -s -- enhanced
```

Enhanced 版：完整 24 个 Skill + RPE 流水线 + 全栈武器库。

---

## 许可证

开源，MIT 协议。Carror OS by Sylph。

---

*"不要用'应该可以'、'理论上支持'这种话。" — Carror OS 宪法第 6 号软完成语禁令*
