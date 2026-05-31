# 飞轮回响 — 狗粮永动机的闭环哲学

> 📍 弧6：元环：飞轮回响 | [⬅ 上篇](story-16.md) | [下篇 ➡](story-15.md)


AI 在修 completion-gate 的 stderr 路由 bug 时发现了一个更深的问题：completion-gate 本身在 goal mode 下每次扫描都报"证据缺失"——但证据文件本就该在最后才创建。这是 6 次无效扫描。

在其他项目里，这个发现会被修复，然后被遗忘。但在 Carror OS 里——AI 自己就是 Carror OS 的使用者，而 AI 正在修的是 Carror OS 自己的门禁系统。他修完 bug 后，打开 claude-next.md，写了一条 DF-03：goal mode 缺乏阶段性证据桩。

一周后，这个教训被 knowledge-condenser 检测到 hits ≥ 3 的模式，推荐升华为正式规范。又一周后，它被 `package-release.sh` 同步到 source/ 和 packages/——所有下游用户的下一个版本将包含这个修复。

这就是飞轮。不是"持续改进"的口号——是 AI 吃自己的狗粮，消化，排出更好的自己。

---

## 狗粮：悖论如何成立

Carror OS 是一个"AI 辅助开发治理框架"。它的用户是 AI + 人类开发者。当人类开发者使用 Carror OS 来开发 Carror OS 自身时——框架在被框架自己治理。

这产生了一个哲学悖论：
- 如果 Carror OS 好用 → 开发 Carror OS 的过程会发现问题 → Carror OS 被改进 → 更好用 → ...
- 如果 Carror OS 有问题 → 开发 Carror OS 的过程会暴露问题 → 问题被记录 → Carror OS 被修复 → 问题减少 → ...

**不管好还是坏，狗粮模式都让系统向好的方向演化。**

---

## 飞轮的三个齿轮

### 第一齿轮：发现与修复

每一次 AI 在狗粮模式下犯错——被 gate 拦截、被用户纠正、产生无证据的完成声明——都是一次"狗粮发现"。

发现的筛选不是盲目的。META-03 定义了发现的应用性三问：

1. 揭示 hook/skill 设计缺陷？ → **系统通用**，记录为教训
2. 显示验证盲区？ → **系统通用**，记录为教训
3. 暴露流程缺失？ → **系统通用**，记录为教训

跳过：项目特有业务逻辑、客户偏好、一次性配置问题。

筛选后的发现按 AGENTS.md 的 triage 决策树分类：
- 仅元项目特有 → 直接修复
- 仅框架通用 → 先在 source/ 修复，再同步到 root
- 两者兼有 → 修复框架 → 同步 root
- 揭示框架差距 → 先在 AGENTS.md 添加规则

### 第二齿轮：机制化

修复不是终点。每一次修复后，必须在框架层添加**可重复的 gate/hook/验证**来防止复发。

这就是机制采纳门禁（AGENTS.md §机制采纳门禁）的概念——不是所有发现都需要一个新 hook。添加一个机制之前，必须先回答三问：

1. **收益可证伪吗？** 该机制成功时会产生什么明确的可观测信号？失败时呢？
2. **噪声上限明确吗？** 该机制的可能 false positive 率上限是多少？超过后谁负责关闭它？
3. **如果 0 收益，多久能发现？** 定义观察期和终止条件。

ED-01 是这个门禁的典型案例——Error-DNA Auto-Fix 和 Build-Validator 通过了"存在且运行"的形式检查，但没有通过"实际产生价值"的收益检查。83.5% 噪声率、0 次 repair_success、40 条无人消费的 build 记录——按机制采纳门禁的三问判定为：搁置归档。

但故事没完。

文件没有删除——它们躺在 `.claude/hooks/` 的角落里，像被封印的石像。hook 代码完整，harness.yaml 里的开关设为 `false`，settings.json 里的注册被撤下。它们不是被处决，是被冷冻。

几个月后，知识管道（kernel.md 的 Phase 4 升华引擎）逐渐成熟。claude-next.md 里的 DG 教训越积越厚，却缺少一个自动扫描器来挑出高频模式。context-compressor 的重生门修复让会话压缩后的知识恢复变得可靠。在这个新的生态位里，error-dna-auto-fix 的"跨会话错误回顾"和 build-validator 的"构建失败诊断"突然有了截然不同的意义——它们不再是冗余收集器，而是知识管道的输入传感器。

v6.3.27，三扇封印同时解开：`knowledge_condenser: true`、`build_validator: true`、`error_dna_auto_fix: true`。不是推翻 ED-01——是尊重它，然后在新的条件下重新评估。

### 第三齿轮：同步与传播

修复和机制化完成后，变更必须传播到所有下游：

```
root (修复) → scripts/package-release.sh
  → source/harness-kit/ (框架治理源)
  → source/lx-skills-v5/ (框架能力源)
  → packages/ (构建产物 .tar.gz)
```

`audit-hooks.sh --check-source-mirror` 验证同步后的一致性。META-04 记录了教训——狗粮优化后必须运行 package-release.sh 自动同步，手动 cp 容易漏。

---

## 飞轮数据流

### skill-flywheel — 技能使用缓冲

skill-flywheel 在每次 skill 被调用时记录到内存缓冲区。Stop hook 触发时，将缓冲区 flush 到 flywheel.log——持久化的使用记录。

### flywheel-report — 30 天频率摘要

SessionStart 时，flywheel-report 读取 flywheel.log，生成 30 天滚动摘要：
- 最常触发的 P0 事件
- skill 使用频率排名
- 高频错误签名
- 活跃的教训（hits 排行）

这些摘要被注入 AI 的 SessionStart 上下文——让新的 AI 实例能感知到最近 30 天的"系统健康状态"。

### flywheel_analytics.py — 分析引擎

在所有数据之上，flywheel_analytics.py 做深度分析：
- 哪些 hook 触发频率异常上升？（潜在的新盲区）
- 哪些 skill 长期未被使用？（可能的死代码）
- 错误类型的季节变化？（新版本引入了新的错误类别？）

---

## 狗粮记录的追踪性

狗粮发现被记录为结构化 YAML + 故事（docs/dogfooding/）。每个记录包含：
- 发现标题 + 分类（系统通用 vs 项目特定）
- 原始 source 引用（`file:line`）
- 修复行动
- 机制化结果（新增/修改了哪些 hook/skill/规则）
- 关联的 claude-next.md 条目

META-05 记录了一个重要的追踪性问题——YAML 记录结构良好但无法链接回原始 source 行。狗粮记录现在使用 `.md` 格式 + `[source: path:line]` 标签，确保每一条发现都可以追溯到原始会话的具体位置。

---

## 飞轮的哲学根基

飞轮不是"持续改进"的励志口号。它是**哲学 #4（没通过验证等于没做）和哲学 #7（文档优先，调研先行）的联合物化**：

- 哲学 #4 → 每次发现必须通过实际的修复和机制化来"验证"——不只是"意识到问题"
- 哲学 #7 → 每次发现都经过"发现 → 方案 → 审核 → 执行 → 验证 → 终审"的 L3 流水线

更重要的是——飞轮让哲学 #2（少量正确大增益）不被哲学 #3（先守护，多建安全层）吞噬。机制采纳门禁的三问，是飞轮的"刹车"——不是所有发现都值得一个永久机制。收益为 0 的机制，不论出发点多好，直接移除。

---

## 飞轮在转

Carror OS v6.1.9 的每一次版本号增加，都有对应的 claude-next.md R 条目或 DG 条目作为来源。这些条目不是某个人凭空想出来的优化方向——它们是狗粮模式下的真实踩坑、真实修复、真实机制化。

飞轮在转。永远在转。每一圈的产物是下一圈的燃料。每一圈的燃料是上一圈的教训。

---

## 相关故事

- [记忆神殿](story-05.md) — 飞轮的燃料来源：狗粮记录 → claude-next.md 教训提取
- [审计军团](story-10.md) — 飞轮的验证节点：audit-hooks --check-source-mirror
- [元环：蛇吞己尾](story-15.md) — 飞轮的终极隐喻：系统用自己产出的教训改进自己
