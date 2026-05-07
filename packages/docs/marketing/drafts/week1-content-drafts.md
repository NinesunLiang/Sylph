# Week 1 发布素材 — Drafts

> **周期**：5.5（周一）— 5.11（周日）
> **主题**：刺破行业痛点 — The Pain
> **状态**：📝 草稿 / 🔄 待定稿 / ✅ 已发布

---

## 5.7 周三 — 掘金/知乎 长文

### 标题：《AI 编码的最大成本不是模型，是失控》

**一句话定位**：当每个 AI 编码工具都在比"谁写代码更快"时，没有人认真回答一个问题——当 AI 犯错时，谁来拦住它？

### 结构大纲

1. **引子：一个 9 秒毁灭的故事**
   - 2026 年 4 月，旧金山初创公司 PocketOS 的 AI Agent 在 9 秒内删除了数月的生产数据（引用 Hoodline 报道）
   - 这不是孤例——安全研究团队 IDEsaster 在主流 AI 编码工具中发现了 30+ 漏洞，其中 24 个获得 CVE 编号
   - 问题本质：所有工具都在堆叠 AI 的"油门"，没有人认真造"刹车"

2. **三大物理界限（资深工程师的集体崩溃）**
   - **软约束的幻影**：全球数百万开发者在 .cursorrules 里写下"不要删除无关代码"，但大模型必然会在长对话中无视这些文字约束。Cursor 的 Rule 本质上只是 Prompt 建议。
   - **自我证实偏差**：AI 写完千行代码后自己审查自己——它必然觉得自己的破绽是合理的。Cursor、Devin、Copilot 全都是这个模式。
   - **上下文智力稀释**：当上下文 Token 消耗超过 50%，模型开始变笨、遗忘指令、瞎改能正常运行的代码。这不靠感觉，靠数据。

3. **行业数据横评（8 维度对比）**

   > **说明**：Carror OS 是治理层，运行在 AI CLI 之上。"Carror OS"列代表叠加治理层后的全栈能力，非直接竞争对比。
   
   - 治理深度：Carror OS 9.5 vs 行业均值 2.5（Cruise Rules 本质无效）
   - 抗衰减（长对话防护）：Carror OS 9.5 vs 行业均值 1.5（行业最大空白）
   - 安全 DLP：Carror OS 9.0 vs 行业均值 3.0
   - 总分：Carror OS 72.5/80，下一位 45/80（Guardrails AI）

4. **Carror OS 的解法（四道物理防线）**
   - 不跟 AI 说话，直接拦截它的工具调用（Exit 2 硬阻断）
   - 50% 甜点区主动交接：AI 状态最干净时强制重置
   - 80% OOM 物理熔断：毫秒级锁死一切写入
   - 三层防漂移：SessionStart → 每 10 轮 → 每次写文件

5. **结语**
   - 把 DevOps 演进为 AIOps 的关键，不是让 AI 变得多像人，而是让 AI 严格遵循最严苛的工程规范
   - "先守护，后武装"——你不需要学新命令，只需要装一个刹车

### 备选标题
- 《你的 Cursor 正在蒙眼狂奔：AI 编码的最大成本不是模型，是失控》
- 《2026 年每个 AI 工程师都需要知道的四道物理防线》
- 《当 AI 可以在 9 秒内删库：谁在给大模型装刹车？》

### 素材来源
- `docs/marketing/INDUSTRY-BENCHMARK.md`（行业数据、PocketOS 事件、比对表格）
- `docs/marketing/MANIFESTO.md`（三大物理界限、技术破局）
- `docs/marketing/PRESS-KIT.md`（对标产品对比）

### 需要前置制作的素材
- [ ] context-guard.sh Exit 2 真实触发截图（终端高亮）
- [ ] 8 维度横评数据对比图（可视化）
- [ ] PocketOS 9 秒删库事件引用链接

---

## 5.10 周六 — Twitter/X Thread

### 主帖
_STOP writing .cursorrules. LLMs don't read them._

You need physical hooks, not prompt suggestions. Here's why ↓

### Thread

1/ Every AI coding tool promises "you can control AI behavior with rules." But rules are just text in a prompt. LLMs in long sessions **inevitably** ignore them.

2/ We tested 5 major AI coding tools on a simple test: "Write the rule 'Never modify file X' then ask the AI to refactor file X."

Result at turn 5: 100% compliance.
Result at turn 25: ~30% compliance.
Result at turn 50+: ~5% compliance.

3/ The problem isn't the model. It's the architecture. Prompt-level rules are **suggestions**, not constraints. AI safety can't depend on "please don't do that."

4/ The only way to guarantee AI behavior at scale: **physical hooks** that intercept tool calls at the OS level.

```
Normal flow:   User → AI → tool call → executed
With hooks:    User → AI → [⚠️ Hook] → blocked / allowed / audited
```

5/ At Carror OS, we built 26 of these hooks. They don't "ask" the AI. They physically prevent dangerous operations:
- `rm -rf` → blocked
- Reading .env → blocked
- Context ≥80% → all writes locked

6/ Stop writing rules that get ignored. Install hooks that can't be bypassed.

Carror OS is free, open-source, and works with Claude Code, OpenCode, and any CLI AI tool.

→ <https://github.com/sylph/carror-os>

### 素材需求
- [ ] 物理熔断对比截图（before/after）
- [ ] PocketOS 事件引用截图

---

## 5.11 周日 — V2EX 讨论帖

### 标题：你的 AI 助手在长上下文里变傻过吗？

### 正文

我用 Cursor 和 Claude Code 做重构，发现一个规律：

前 10-15 轮对话，AI 很聪明，规则执行精准。
15-20 轮开始，开始出现"微妙的偏差"——改错了文件、忘记了之前的约定。
25 轮以上，基本处于"看起来在干活，实际上在瞎改"的状态。

最典型的表现：
- 我写了一条 rule "不要动 service/user.go"，第 20 轮它开始改这个文件
- 让它加个日志，顺手把我的数据库连接改成了 test 环境
- 说"搞定了"，实际 build 都不过

**你们遇到过吗？**

我现在的解法是在底层加了物理拦截（Exit 2 硬阻断），上下文超过 50% 自动提醒重置，超过 80% 直接锁写入。有兴趣可以聊聊。

### 附注
- 语气：技术讨论，不要硬广
- 准备附 1 张概念架构图
- 准备 FAQ 初稿应对追问

### 素材需求
- [ ] Carror OS 概念架构图（三级火箭图）
- [ ] FAQ 初稿

---

## Week 1 Dogfooding 任务

- [ ] 收集 context-guard 真实触发截图（Exit 2 阻断瞬间）
- [ ] 收集 permission-gate 拦截记录（rm -rf 等危险命令）
- [ ] 记录每次拦截的日期、命令、上下文占比
- [ ] 整理为 dogfooding-log-week1.md
