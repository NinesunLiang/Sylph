# 记忆神殿 — 保存、传承、升华

新会话开始。AI 睁开眼睛——一片空白。

他不知道这个项目是用什么语言写的。不知道上一次做到哪里。不知道用户刚纠正过他三次"别编造 file:line"。他只知道一件事：有人在等他开始工作。而他连昨天是谁在和自己说话都记不得。

就在此时，inject-project-knowledge 启动了。像一只手，从黑暗中递来一卷写满教训的羊皮纸。

---

## AI 的天生诅咒

AI 被召唤到每一次会话中，都是一个崭新的灵魂。昨天的对话、之前的教训、犯过的错误——全部清零。用户不得不在每一轮重新解释业务背景、项目规则、上次做到哪了。

这是反模式 D1（断连后上下文丢失）的现实根源。对抗它，不能靠一次性的"请记住这些"——需要一套完整的**写入 → 保存 → 恢复 → 升华**的闭环。

记忆神殿就是这套闭环。

---

## 写入层：谁在记录记忆？

### pretool-user-correction — 纠正信号捕手

pretool-user-correction 是记忆神殿的哨兵。他在 UserPromptSubmit（用户每次发送消息）时启动，扫描用户输入中的纠正信号。

用户的"不对"、"不是这样的"、"你搞错了"——不是情绪表达，是**最高价值的数据**。每一次纠正背后，都有一个 AI 犯错、用户纠正、如果忘记就会再犯的教训。

pretool-user-correction 检测到纠正信号后，在 AI 的下一步操作（Edit/Write）时提醒它记录到 `claude-next.md`，带格式：`@日期 hits:1`，触发条件，正确行为，证据。

两个教训条目（2026-05-10 和 2026-05-11）仍然标记为 `[已关闭]`，因为用户说了"不对"但纠正内容在跨会话时丢失。这正是记忆神殿存在的理由。

### posttool-handoff-writer — 交接书的书写者

posttool-handoff-writer 在每次 TaskUpdate.completed 后，将当前工作状态写入 `.omc/state/session-handoff.md`：

- 正在进行中但未完成的任务
- 当前阻塞点
- 已做的关键决策和理由
- 遇到的坑和解决方案

这不是被动日志——这是**主动交接文档**。当下一轮会话的 AI 通过 inject-project-knowledge 读取 handoff 时，它能立即恢复上一轮的工作流上下文，而不需要用户重新解释。

### auto-snapshot — 快照的自动机

auto-snapshot 是记忆神殿的档案管理员。它持续记录会话状态：

- 当前分支、最近提交
- 轮次计数
- 未提交文件列表
- 活跃的 mode（ghost/goal）
- 打开的 feature 和 RPE 目录

R40 记录了一次教训——auto-snapshot 的 session-dump.json 写入逻辑经过代码审查确认正确，但文件从未被创建。原因是"代码存在且正确 ≠ 运行时产生效果"。Stop hook 产出的文件必须触发验证，不能仅凭 Read 代码断言。

---

## 保存层：记忆存在哪里？

### claude-next.md — 学习笔记的活化石

这是整个记忆神殿最珍贵的文物。每一个带 `@日期 hits:N` 的条目，背后都是一次 AI 踩坑 → 被纠正 → 记录教训的真实事件。

它不是事前设计出来的——它是事后从伤口中长出来的。239+ 行教训，按 R 系列（系统通用规则）、DG 系列（狗粮教训）、DF 系列（狗粮修复）、GL 系列（ghost 模式）、ED 系列（机制审计）、META 系列（元教训）分类。

hits 计数是记忆的复利机制。同一个教训被触发时，hits +1，不新增重复条目。hits ≥ 5 或超过 10 天——升华提醒，评审后可能升级到 kernel.md。

### error-dna.jsonl — 错误基因库

error-dna.sh 捕获每一次 Bash 命令的错误，记录到结构化的 JSONL 中：命令、错误码、stderr 摘录、时间戳。

这不是"记录错误便于修复"——更多是**模式识别**。当同一个错误签名反复出现，error_classifier.py 会识别出它是一个"热点"，SessionStart 时 flywheel-report 将高频热点注入 AI 的上下文，让 AI 在新会话中也能感知到"我上次总是在这里摔倒"。

### session-handoff.md + session-snapshot.json — 会话快照

两个文件配合，在 Stop hook 触发时保存完整的会话恢复信息。下次 SessionStart，inject-project-knowledge 读取它们，注入 AI 的意识。

---

## 恢复层：谁在唤醒记忆？

### inject-project-knowledge — 记忆的唤灵师

inject-project-knowledge 是 SessionStart 时第一个启动的机制。它的工作是：找出 AI 需要知道的全部内容，在 AI 开口说第一句话之前注入进去。

注入顺序有优先级：

1. **index.md 铁律速查** — 这是最小集合，必须在最前面
2. **kernel.md 架构铁律** — 代码执行规范
3. **claude-next.md 教训库** — 高频错误模式
4. **anti-patterns.md 反模式清单** — 16 条防陷阱
5. **session-handoff.md** — 上一轮交接内容
6. **flywheel 高频告警** — 最近活跃的错误签名

注入不是全文——R39 约束了每次注入预算 ~120 行/3KB。不常变的内容放到 reference 文件，只注入摘要链接。这是哲学 #1（less is more）的物理体现。

### compact-detect — 压缩后的急救者

当用户执行 `/compact` 压缩上下文时——这是最危险的时刻。AI 刚刚失去了大部分记忆，context 从 95% 骤降到 ~30%，但项目知识也一同被清除了。

compact-detect 检测到 `/compact` 后，立即执行两件事：

1. 保存 compact 前的关键状态（当前 step、活跃 task、未完成事项）
2. 重新注入项目知识摘要（铁律 + 架构 + 教训 + 当前状态）

R33 记录了一次惨痛的教训：/compact 后 AI 忘记了技术栈、ADR 决策、活跃 feature 状态，需要用户全部重新解释。修复后 compact-detect 现在注入 index.md 铁律速查 + kernel.md 架构铁律 + AGENTS.md 治理纲要 + 当前 step 状态。

---

## 升华层：从教训到规范

### knowledge-condenser — 知识炼金士

knowledge-condenser 在 Stop hook 时启动。它扫描 claude-next.md，寻找 hits ≥ 3 的条目。

**三振出局，升级永存。**

当一个教训被触发了三次——它不再是"偶尔犯错"的范畴，而是"系统性盲区"。knowledge-condenser 将这些条目标记为升华候选，建议人工评审后升级到 kernel.md（正式规范）或编码为反模式（检测规则）。

hit 计数是保守的——同一个教训的三次触发通常跨越多个会话，由不同的 AI 实例分别踩坑。这证明了它不是一个 AI 的特定弱点，而是一个机制的通用盲区。

---

## 记忆之环

神殿的四层构成了一个环：

```
写入（correction/handoff/snapshot）
  → 保存（claude-next.md/error-dna/session文件）
    → 恢复（inject/compact-detect）
      → 升华（knowledge-condenser）
        → 规范（kernel.md/anti-patterns）
          → 新会话的注入基础
```

每一圈循环，记忆的损耗被降低一点。永远不可能完全消除——AI 的无状态本质是物理限制——但记忆神殿让损耗可控。

而且最重要的，记忆神殿让 Carror OS 自身能**学习**。不是 AI 在学——是整个系统在学。教训存储在文件中，不是存储在 AI 的权重里。新版本的 AI 接入同一个项目时，继承的不是上一个 AI 的个性，而是上一个 AI 留下的所有伤疤。

---

## 相关故事

- [上下文守望者](story-06.md) — 记忆的敌人：上下文压缩（/compact）如何被 compact-detect 对抗
- [飞轮回响](story-12.md) — 记忆的使用者：狗粮记录 → 教训提取 → 同步传播的闭环
- [元环：蛇吞己尾](story-15.md) — 记忆的终极意义：系统用自己产出的教训来改进自己
