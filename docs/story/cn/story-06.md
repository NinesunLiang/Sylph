# 上下文守望者 — 防止记忆洪灾的资源哨兵

第 28 轮对话。token_writer 的计数器跳到了 91%。

AI 还在喋喋不休地输出——他不知道自己快要失去最早的记忆了。就像一条金鱼在鱼缸漏水时还在游。context-guard 看了一眼计数器，把手放在了 Edit 和 Write 的大门上。

"够了。从现在起，你只能读。不能写。"

---

## 黄金的稀缺性

AI 的上下文窗口有硬上限。每次 Read、每次工具输出、用户的每一句话——都在消耗这个窗口。当 context 接近上限时，AI 开始遗忘最早的对话内容。它不会告诉你它忘了——它会假装记得，然后开始犯错误。

反模式 F1（假设驱动）在高 context 压力下爆发率飙升。因为 AI 没办法再去 Read 文件来验证记忆——它只能凭"我记得是这样的"来行动。这就是为什么上下文管理不只是性能优化——它是安全机制。

---

## 五件套架构

上下文守望者由五个机制组成，按事件链连接：

```
token_writer (记录) → turn-counter (评估) → context-guard (阻断)
                      ↓                    ↓
              pretool-rule-anchor (锚定)  compact-detect (恢复)
```

---

### token_writer — 不眠的计量员

token_writer 是守望者军团的眼睛。在每个 PostToolUse 事件中（matcher: `.*`，即所有工具），它更新 token 使用计数器。

它不只是一个计数器——它是 context-guard 能否做出正确决策的基础。如果 token_writer 的数据滞后，context-guard 可能会在 context 已经 95% 时仍然放行——或者在 context 才 60% 时就误报。

SessionStart 时 token_writer --reset 将计数器归零，标记新会话的开始。

---

### turn-counter — 节奏的节拍器

turn-counter 在每次 UserPromptSubmit 时启动。它记录三个关键数据：

1. **轮次计数**：当前会话已经过了多少轮对话
2. **上下文使用率**：从 token_writer 读取的数据，评估 context 消耗百分比
3. **模糊指令检测**：用户输入是否含模糊动词（"优化/改进/修修"）但缺少方向限定词？

轮次不是唯一的危险信号。高轮次 + 高上下文使用率才是。R33 的复合触发机制就在这里实施：当 context > 50% **且** turns > 20 时，turn-counter 触发 L2 层复合注入——重新锚定核心规则，防止长对话中的规范漂移。

模糊指令检测触发后，turn-counter 写入 marker 文件，fuzzy-block 在 PreToolUse 时读取并硬阻断 AI 的工具调用。但 DF-01 的进化修复了 false positive：方向限定词（"从机制上优化"/"针对 hook 的优化"）现在会被正确识别为具体指令。

---

### context-guard — 防洪闸的物理阻断

context-guard 是守望者军团的拳头。当 context 超过阈值（默认 90%）时，它封锁 Edit/Write 工具——阻止 AI 继续产出"新内容"。

但 R29 记录了一次关键的设计进化。最初 context-guard 用 `.*` matcher，封锁了**所有**工具——包括 Read 和 Bash。结果形成了死锁：

```
AI: context 95%，被封锁，无法诊断
AI: 需要 Read 来理解 token 数据为什么这么高 → blocked
AI: 需要 Bash 来修复 token-tracking-index → blocked
AI: 需要 Write 来创建 context-force-override → blocked
死锁。
```

修复后 context-guard 改用 `Edit|Write` matcher——只封锁写操作，保留 Read/Grep/Bash 作为诊断通道。"读是诊断，写是破坏。"

同时保留了逃生门：如果 AI 确实需要突破封锁修复问题，`context-force-override` 标记文件的机制允许绕过阻断——但绕过本身被记录，形成了可审计的例外轨迹。

---

### pretool-rule-anchor — 长对话的锚定者

当会话达到高轮次（由 turn-counter 的 L2 触发），pretool-rule-anchor 在每次 Edit/Write 前重新注入核心规则摘要。

它的逻辑是：长对话中，AI 开始被最近的细节淹没，忘记了 SessionStart 时注入的基础规则。pretool-rule-anchor 就像一个偶尔拍你肩膀提醒你的人："嘿，还记得铁律 #1 吗？禁止编造。你现在引用的那个 file:line，你真的读过吗？"

---

### compact-detect — 压缩事件的急救员

compact 是最危险的时刻。AI 的上下文从 ~95% 骤降到 ~30%，但代价是丢失了项目知识注入的内容。

compact-detect 在检测到 `/compact` 命令后立即行动：

1. 保存 compact 前的关键状态
2. 重新注入项目知识摘要：index.md 铁律速查 + kernel.md 架构 + claude-next.md 高频教训 + 当前 step 状态

R33 记录了一次教训——compact 后 AI "失忆"，忘了技术栈、ADR 决策、活跃 feature 状态。修复后 compact-detect 现在充当了"二次 SessionStart"的注射器，确保 compact 后的 AI 仍然知道自己在做什么。

---

## 为什么是五件套而不是一个？

一个单体"上下文管理器"可以做所有这些事——但把它拆成五个独立的 hook，每个只做一件事，才是哲学 #1（less is more）的真谛。

每个 hook 可以独立开关（harness.yaml）、独立调试、独立测试（smoke test 有独立的 case）。其中一个出问题不会拖垮全系统。这是"原子化处理"——五个小机制的表面噪声可能比一个大机制更大，但**可维护性和可诊断性指数级提升**。

---

## 灾难瞬间：一次真实的上下文危机

```
Round 28, Context 88%
AI: 继续修 completion-gate.sh 的 auto_soft_block
→ turn-counter: L2 触发，注入核心规则锚定

Round 29, Context 93%
AI: (准备修改 completion-gate.sh:47)
→ context-guard: blocked — context 超过阈值
→ 但 Read/Bash 仍然可用 → AI 诊断 token 数据

Round 29, AI: (Read token index, 发现异常)
AI: (创建 context-force-override marker)
→ context-guard: 检测到 override → 放行 Edit

Round 30, AI: (修复完成)
→ Context 回落到 85%（部分工具输出被自然淘汰）
→ context-guard: 阈值恢复，正常放行

没有死锁。没有丢失进度。
```

这就是五件套协同运作的真实场景——不是完美的，但是可控的。

守望者们不需要赢。他们只需要确保 AI 在输掉之前，知道自己还剩下多少筹码。

---

## 相关故事

- [门禁骑士团](story-03.md) — context-guard 在骑士团的"范围翼"中的位置
- [记忆神殿](story-05.md) — compact-detect 在 compact 后重新注入记忆
- [双生之子](story-08.md) — ghost/goal 模式下 context-guard 降级为 warn-only
