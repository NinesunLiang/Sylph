# 审计军团 — 三大审计师与自检仪

pre-commit-self-review.sh 收到了 git commit 的触发信号。它不关心提交内容是什么——它关心三件事。

第一：有没有 AI 能自己调用的 CAPTCHA 批准脚本？R42 的幽灵还在徘徊——approve-sen.sh 的教训不允许被忘记。

第二：有没有 hook 规则被错误应用到 skill？R42 的另一半——ghost mode 用 R23 的逻辑删了 31 个文件。

第三：新加的文件在 settings.json 和 harness.yaml 都注册了吗？R23 再演——8 个僵尸 hook 在黑暗里假装工作。

三问全过，exit 0。有任何一问不过——exit 2。提交被驳回。审计军团不赞成你的 patch。

---

## 军团的结构

| 角色 | 工具 | 职责 | 运行时机 |
|------|------|------|---------|
| 第一审计师 | audit-hooks.sh | 三方一致性审计 | 手动 / smoke 回归 |
| 第二审计师 | harness-smoke-test.sh | 全回归烟雾测试 | 每次 hook 变更后 |
| 第三审计师 | hook-production-verify.sh | 全场景门禁覆盖 | 每次 gate 行为变更后 |
| 内部事务官 | pre-commit-self-review.sh | 反自矛盾自检 | 每次 git commit 前 |
| 文档审计官 | doc-sync-check.sh | 文档引用准确性 | 架构变更后 |
| 自我评分官 | score-self-check.sh | AI 评估 vs 实际配置 | 评估/评分任务后 |

---

## 第一审计师：audit-hooks.sh — 三方一致性审计

第一审计师不测试功能——他检查**一致性**。

他提出三个问题：
1. **磁盘上是否有这个脚本？** (`.claude/hooks/xxx.sh` 存在？)
2. **harness.yaml 中是否声明它启用？** (`hooks_enabled.xxx: true`？)
3. **settings.json 中是否注册了事件 + matcher？** (`hooks.xxx.matcher` 存在？)

三项必须齐一。任何缺失 = 漂移。

R23 记录了一次震撼性的发现——首次运行 audit-hooks 时，12 个 hook 脚本中有 8 个是"僵尸"：磁盘上有脚本、harness.yaml 声明启用，但 settings.json 没有注册。它们在产品文档层面"存在"，但 Claude Code 运行时根本不会触发它们。

那是 audit-hooks.sh 的诞生时刻。R36 进一步强化了它——hook 合并/废弃时，三个文件必须同步更新：(A) settings.json ← (B) harness.yaml ← (C) smoke tests。

审计师的另一种模式是 `--check-source-mirror`：比对 root 和 source/harness-kit 中的文件一致性。AGENTS.md 被显式排除——它是"有意不同"的文件，元项目治理文件和通用分发模板天然不同。

---

## 第二审计师：harness-smoke-test.sh — 回归烟雾测试

第二审计师做真正的功能验证。它模拟真实的 Claude Code JSON schema，向每个 hook 注入模拟的工具调用，检查返回值是否正确。

测试覆盖：
- **Hook 存在性**：每个 hook 能否被触发执行？
- **正常路径**：正常输入下 hook 是否 exit 0？
- **阻断路径**：门禁触发条件满足时 hook 是否 exit 2？
- **模式感知**：ghost/goal 模式下 hook 是否正确降级？
- **配置读取**：hc_enabled=false 时 hook 是否跳过？

R24 记录了一次关键的修复——smoke 测试曾用 `main.go` 作为测试样例文件，恰好它存在于项目目录中，导致 `for x in $GLOB_VAR` 的 glob 展开问题被"靠 cwd 巧合通过测试"掩盖。修复后改用 `/Users/demo/project/src/main.go` 全路径，彻底杜绝环境依赖。

第二审计师的输出是动态计数的——测试 case 数量随 hook 数量变化，全绿才算 pass。

---

## 第三审计师：hook-production-verify.sh — 全场景门禁覆盖

第三审计师是最彻底的。他不测试 hook 能否运行——他测试每一个门禁的**全部触发场景**。

以 context-guard D3 测试为例：
- Write @ 95% context → expect exit 2（阻断写）
- Edit @ 95% context → expect exit 2（阻断写）
- Read @ 95% context → expect exit 0（诊断通道保留）
- Bash @ 95% context → expect exit 0（诊断通道保留）

R26 的修复就是由 D3 测试驱动的——四工具循环永久守护，任何工具例外立即 🔴。

第三审计师回答的问题是：**"所有声称被封锁的工具，确实被封锁了吗？所有声称放行的工具，确实被放行了吗？"**

---

## 内部事务官：pre-commit-self-review.sh — 反自我矛盾检查

内部事务官是最年轻但最尖锐的审计成员。它在每次 `git commit` 前执行三项检查：

1. **CAPTCHA 绕过检测**：是否有 AI 可调用的批准脚本？R42 的事故（approve-sen.sh 创建了 AI 可自行穿越的暗门）是这项检查的触发器
2. **域规则误用**：R42 的另一半——ghost mode 将 hook 规则（R23 的三方一致性）错误应用到 skill（skill 不需要 settings.json 注册，它有 feature-registry.yaml）
3. **新 hook 注册完整性**：新增的 hook 脚本是否同时有了 settings.json 注册 + harness.yaml 开关？

exit 2 = 阻断提交。这不是风格检查——这是安全倒数第二道防线。

---

## 文档审计官：doc-sync-check.sh — 文档引用准确性

文档审计官做一件简单的事：扫描 docs/ 中所有 `[已验证: path:line]` 标注，打开对应文件，验证该行号确实存在且内容匹配。

R28 的教训驱动了这个工具的诞生——README.md 中的架构描述在实现变更为双终端交叉验证后仍然是旧的 Sub-agent 盲审描述。20+ 营销文档全部过期。

现在每次架构变更后，运行 doc-sync-check.sh 就能发现所有文档漂移。

---

## 自我评分官：score-self-check.sh — AI 评估 vs 实际配置

自我评分官诞生于 R30 事故——AI 在 Enhanced 环境下运行，却按 Base 版文档给自己评分，导致"Enhanced 隐藏"和"不会主动提示"两条扣分完全不成立。

它做的是：AI 完成自我评估后，强制检查实际环境配置（skill 目录、settings.json、harness.yaml 开关状态），将评估结论与实际状态比对，发现不一致时告警。

这是哲学 #6（0 信任）的最明确物化——AI 连对自己的认识都会被审计。

---

## 军团为什么存在？

门禁骑士团（story-03）在事前守护。证据裁判庭（story-04）在事中验证。审计军团在事后追查。

三大审计师不阻止错误——但**确保没有任何错误能悄无声息地逃逸**。这是"先守护，后激发"（哲学 #3）和"0 信任"（哲学 #6）的最后一层：当所有前防线都被绕过时，审计记录不会消失。

审计军团的第六条成员——pre-commit-self-review.sh——更是铁律 #8（反自我矛盾）的物化。Carror OS 自身也在被 Carror OS 审计。每一行新增代码在被提交之前，都要回答三个问题：你创造了新漏洞吗？你滥用了不适用于你的规则吗？你正确地注册了自己吗？

三道问题的答案不在代码里。在审计师的沉默中。

---

## 相关故事

- [证据裁判庭](story-04.md) — 审计军团在事中验证（completion-gate）失效时的兜底
- [飞轮回响](story-12.md) — audit-hooks.sh --check-source-mirror 是狗粮同步的最后一道验证
- [元环：蛇吞己尾](story-15.md) — 审计军团是蛇在吞己尾时的自我检查机制
