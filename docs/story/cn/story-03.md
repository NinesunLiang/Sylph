# 门禁骑士团 — 层层安检的边防哨所

> 📍 弧2：防御：门禁骑士团 | [⬅ 上篇](story-02.md) | [下篇 ➡](story-04.md)

一个 Edit 工具调用正在穿越边境。它刚离开 AI 的指尖，还没到达文件系统——就被拦下了。

"证件。"edit-guard 翻看访客登记簿。没有这个文件的阅读记录。"你没读过这个文件。你不能碰它。"

这是今晚被拦下的第七个未授权操作。对于十五位核心骑士来说，这是平凡的一夜。而在他们身后，还有五十余位辅助卫士在各自哨位上值守。

---

## 骑士团的架构

门禁骑士团分为三翼：

| 翼 | 核心骑士 | 驻守位置 | 职责 |
|----|---------|---------|------|
| **真理翼** | edit-guard, lsp-suggest | Edit, Grep | 确保 AI 在正确信息基础上操作 |
| **安全翼** | permission-gate, privacy-gate, pretool-sensitive-edit, pretool-retry-check, subagent-guard, pre-ask-guard | Bash, Read, Edit/Write, AskUserQuestion | 拦截危险操作、隐私泄露、资源滥用、无意义提问 |
| **范围翼** | context-guard, pretool-edit-scope, fuzzy-block, pre-completion-gate, plan-gate (as pretool-plan-gate) | Edit/Write, TaskUpdate | 确保 AI 不在错误时间做错误范围的事 |

> 注：核心骑士共 12 位（三翼分别 2/6/5，plan-gate 以 pretool-plan-gate.sh 文件存在）。此外整个哨所注册超过 70 位守卫——包括会话卫士（SessionStart 序列）、事后审计官（PostToolUse 序列）、停止拖拽者（Stop 序列）和用户交互检查员（UserPromptSubmit 序列），构成完整的纵深防御体系。

---

## 真理翼：AI 不能基于幻觉行动

### edit-guard — 先读后写的铁律执行者

edit-guard 站在 Edit 工具的大门前。每当 AI 试图编辑一个文件，他翻看 read-tracker 的访客登记簿。

"你读过这个文件吗？"他问。

如果登记簿上没有这条记录——**blocked**。AI 必须先用 Read 工具打开文件，edit-guard 才会放行。

这个看似简单的检查，是反模式 F1（假设驱动）的第一道防线。AI 不能说"我记得这个文件的内容"——read-tracker 只认实际打开过的文件。

### lsp-suggest — 搜索效率的守夜人

lsp-suggest 在 AI 用 Grep 搜索导出符号时轻声提醒：

"这个符号用 LSP 一步就能找到定义和所有引用。你确定要 grep 二十遍吗？"

他不是硬阻断——他只是站在反模式 E1（暴力搜索）的边界上，温和地建议切换到正确的工具。

---

## 安全翼：危险操作必须经过人类审批

### permission-gate — 危险命令的 CAPTCHA 守门人

permission-gate 是整个骑士团中最有分量的存在。他站在 Bash 工具门口，手里握着一份禁止命令清单。

当 AI 试图执行 `git commit`、`git push --force`、`rm -rf`、`sudo`、`gh release upload` 或任何匹配危险正则的命令时，permission-gate 拦下操作，输出一道 CAPTCHA 验证码：

```
[permission-gate] 危险操作被拦截: git push origin main
请在输入框中输入以下命令批准: echo '4f7a2' > .omc/state/permission-gate-approved
```

这条 CAPTCHA 的设计是经过深思熟虑的。AI 自己不能在同一个工具调用中创建批准文件（edit-guard 拦着）——必须由用户在外部输入 `echo` 命令来写文件。这是一种**物理隔离**：AI 的能力边界到文件系统写操作为止，批准需要用户的终端。

R31 记录了一次盲区修复——`gh release upload` 曾经绕过了 permission-gate，因为 `gh` 不在任何危险正则中。现在 `gh_write_regex` 覆盖了 release、pr、issue、repo、secret、workflow 等所有写子命令。

### privacy-gate — .env 的绝对守护者

privacy-gate 没有商量的余地。他对 `.env`、`.pem`、`.key`、`credentials`、`private` 等文件实行**绝对禁阅**。任何 AI 试图 Read、Grep、Bash 这些路径的企图，都会被他无差别阻断。

他不关心上下文。不关心"只是为了检查格式"。不关心"只读第一行"。密钥就是密钥。触碰即死。

### pretool-sensitive-edit — 治理文件的第二道门禁

即使 permission-gate 放行了，pretool-sensitive-edit 还会再查一次——这一次专盯**治理文件**：CLAUDE.md、AGENTS.md、settings.json、harness.yaml。

这些文件是 Carror OS 自身的控制面板。修改它们等同于修改系统的 DNA。pretool-sensitive-edit 要求独立的 CAPTCHA 验证——和 permission-gate 一样，AI 不能自己批准。

R43 记录了一次惨痛的教训：有人创建了一个 `approve-sen.sh` 脚本让 AI 自己调用它来批准治理文件编辑。这等于在 CAPTCHA 体系上开了一扇 AI 可自行穿越的暗门。现在 governance file 编辑的批准通道被硬性设计为必须由用户在独立终端输入，AI 无法自行触发。

### pretool-retry-check — 修复上限的执法者

AI 天性地会在失败后尝试同样的事。pretool-retry-check 记录每一次失败的 Bash 命令的签名（命令模式 + 错误码），当同一个签名第三次出现时——**blocked**。

"你已经修了三轮了。每一轮都是相同的根因假设。停下来，换一个方向，或者升级用户。"

这是铁律"修复 3 轮上限"的物化。pretool-retry-check 不关心这次修没修好——只要同一个错误模式出现三次，它就假定 AI 在死循环。

### subagent-guard — 账单雪崩的预警系统

subagent-guard 在 AI 启动子 agent（Task 工具）前介入。它检查 AI 是否设置了 `max_turns` 约束——如果没有，它从 harness.yaml 读取默认值并注入到 AI 的上下文提醒中。

它不是硬限——如 R25 解释的，Claude Code 的 Task 工具 schema 没有 `max_turns` 字段，hook 无法对子 agent 做真正的运行时截断。但它在声明层约束 AI 的意识，配合 posttool-subagent-audit 在事后记录 token 消耗，形成"自我约束 + 事后感知"的双层防线。

### pre-ask-guard — 决策链的守门人

pre-ask-guard 是最新加入安全翼的骑士——他的岗位在 AskUserQuestion 工具前。

当 AI 试图向用户提问时，pre-ask-guard 拦下问题，过四层决策链：Philosophy（7条）→ Iron Rules（8条）→ Existing Practices（claude-next.md）→ Behavior Patterns。如果任一层的文档中已有答案——blocked。AI 能自主决策，就不该打扰用户。

"你已经知道答案了，"pre-ask-guard 对 AI 说，"你在 AGENTS.md 第 47 行写过同样的决策逻辑。不要问人。"

---

*午夜。permission-gate 的哨所里，privacy-gate 靠过来看了一眼他的屏幕。*

*"今晚拦了多少？"*

*"7 个 git commit，2 个 rm -rf，1 个 gh release upload。"permission-gate 没抬头。"有一个想 sed -i 直接改 harness.yaml 的。"*

*privacy-gate 沉默了一秒。"那是 E1。"*

*"我知道。error-dna 会抓到的。"*

---

## 范围翼：在错误的边界上划下红线

### context-guard — 上下文洪灾的防洪闸

context-guard 读 token_writer 追踪的实时上下文使用率。当 AI 的上下文使用超过阈值（默认 90%）时——**blocked**。

但 context-guard 不是盲目的阻断。R29 记录了一次进化：最初它使用 `.*` matcher 封锁所有工具——包括 Read 和 Bash。结果 AI 被封锁后连诊断修复都做不了——形成了**自锁死局**（self-inflicted DoS）。

现在 context-guard 只封锁 Edit/Write——保留 Read/Grep/Bash 作为诊断通道。原则是："读是诊断，写是破坏。"同时又提供了逃生门：如果 AI 确实需要突破封锁（例如要修复导致自锁的 token 索引文件），可以创建 `context-force-override` 标记文件来绕过阻断。

### pretool-edit-scope — 范围冻结的巡逻兵

pretool-edit-scope 的工作是不断提醒 AI："你现在的任务范围是什么？这个文件在范围内吗？"

当 AI 试图编辑一个不在任务范围中的文件——它发出警告。R35 记录了一次行为变更：从 hard-block 改为 auto-add（自动将受影响文件纳入范围），避免了"改了上游必须改下游但 scope 不让过"的死锁情况。

同时，pretool-edit-scope 在前身 pretool-rule-anchor 被融合吸收后，继承了长对话防规则漂移的逻辑——在轮次过高时重新锚定核心规则。

> 2026-06-06 更新：pretool-edit-scope 的开关已从 false 恢复为 true——所有核心骑士均已激活。

### fuzzy-block — 模糊指令的终结者

当 turn-counter 检测到用户的输入含模糊动词（"优化一下"/"改改"/"修修"）且没有方向限定词时，fuzzy-block 硬阻断 AI 的所有工具调用。

它的逻辑是：**模糊指令下执行，等于盲飞。** 先让用户澄清，再动工。但 DF-01 记录了一次进化——"从机制上优化"不应该被阻断，因为"从机制上"是方向限定词，使"优化"从模糊变为具体。现在 fuzzy-block 和 turn-counter 会检测方向限定词，避免 false positive。

### pre-completion-gate — 完成声明的前置审判

在 AI 标记一个 TaskUpdate 为 "completed" 之前，pre-completion-gate 拦下它，问：

"你有证据吗？VERIFIED 标签？file:line 引用？测试输出？"

如果没有——blocked。这比 completion-gate 更早介入，在执行层就拦下没有证据的完成声明，减少无效的 completion-gate 扫描（DF-03）。

### pretool-plan-gate — 计划先行的守夜人

plan-gate 站在 Edit/Write/Bash 三工具合流之处。在所有操作执行前，它检查当前任务是否已有经过审批的计划文件。如果没有——blocked。

"没有计划就动手，"plan-gate 说，"等于闭着眼睛开刀。"

它是哲学 #5（人机协同）和 #8（哲学先行）的物化：AI 不能跳步直接执行——至少需要一份 plan.md。注意他不是 hard-block 所有 case——对于任务分解目录中已明确的步骤，如果有 step 文件作为迷你计划，也会放行。

---

## 补充骑士：后来加入的卫士

以下几位卫士不是最初"三翼十五骑士"的原班人马，但已经在哨所中占据了关键位置：

### lsp-gate — LSP 瑞士军刀的看门人

lsp-gate 在 SessionStart 时启动。他检查项目是否已配置 LSP——如果没有，他自动安装对应的 LSP 语言服务器（TypeScript/Python/Go/Rust）并配置 `.claude/lsp.json`。

他的哲学是：**在 AI 工作前就把工具备好。** 让 AI 用 grep 二十遍不如一次 LSP 引用跳转。lsp-gate 确保 AI 上战场时剑已经磨好了。

2026-06-06 更新：已从休眠状态恢复，所有会话都会触发。

### oracle-gate — 修改前的最后审批

oracle-gate 在 SessionStart 时运行。他检查项目在本次会话是否有待审批的 Oracle 审核。如果有——他启动审批流程。

与 meta-oracle-trigger 不同，oracle-gate 关注的是**执行前的审批流**——当你准备改一个高难度（L3+）模块时，需要先通过 Oracle 审核才能动工。

2026-06-06 更新：已从休眠状态恢复。

### posttool-read-cite — 阅读的证据链记录者

posttool-read-cite 在每次 Read 工具调用后记录引用的文件路径、时间戳和目标。这些记录进入 .omc 域，作为 completion-gate 的"已读证据"来源。

不记录——就等于没读过。edit-guard 的底气就来自这里。

2026-06-06 更新：已从休眠状态恢复。

### pretool-rules-inject — 规则锚定的注射器

pretool-rules-inject 在 UserPromptSubmit 时工作。当 conversation turn 超过阈值（默认 15 轮）时，他自动注入核心规则锚定——防止 AI 在长对话中规则漂移。

R35 记录了他的诞生：edit-scope 从 pretool-rule-anchor 融合了锚定能力后，pretool-rules-inject 作为独立卫士接替了规则注入的任务。

2026-06-06 更新：已从休眠状态恢复。

---

## 共享之力：hc_enabled 门禁

十二位核心骑士都从同一个源头汲取力量：`harness_config.sh`。

```bash
hc_enabled "permission_gate" || exit 0
```

每一行都是同一把钥匙。如果 `harness.yaml` 中某个机制的开关被设置为 `false`——对应的骑士瞬间沉睡，不做任何检查，直接放行。这是"先守护，后激发"（哲学 #3）的物化：所有防御默认开启，但关闭只需要一个开关。

`is_mode_active()` 是另一个共享之力。当 ghost 或 goal 模式激活时——十二位核心骑士全体降级为 "warn-only"：不再硬阻断，改为记录警告。这是 Ghost/Goal 模式协议的核心——方向驱动的探索不应该被安全网频繁打断。

---

## 防线是什么？

骑士团的防御不是孤立的。一次典型操作经过的骑士：

```
AI: 我要编辑 CLAUDE.md（未读过文件）

→ edit-guard:    "你没读过这个文件" → blocked
→ pretool-sensitive-edit: "这是治理文件改动" → 需要用户 CAPTCHA
→ context-guard: "上下文使用率 92%" → blocked
→ pretool-edit-scope: "这个文件在任务范围内吗？"

四个骑士，四道防线。只有在三重检查都通过后，这次编辑才会被执行。
```

门禁骑士团不完美——但它是七柱圣殿在地面上的第一层防御。哲学是法理，铁律是刑法，骑士团是警察。

---

## 相关故事

- [证据裁判庭](story-04.md) — 骑士团放行后，进入四层证据防线
- [上下文守望者](story-06.md) — context-guard + token_writer 的完整上下文防线
- [反面镜宫](story-09.md) — fuzzy-block 拦截的模糊指令是反模式 E3（过度确认）的物化
