# Carror OS — 世界观故事系列

> 每一个机制，都是一段传奇。每一道门禁，背后都有一个世界。

---

## 故事索引

| # | 篇章 | 文件 | 覆盖机制数 | 故事隐喻 |
|---|------|------|-----------|---------|
| 1 | 七柱圣殿 | [cn/story-01.md](cn/story-01.md) | 7 哲学 + 冲突裁决 | 宇宙创世法则 |
| 2 | 八道铁律 | [cn/story-02.md](cn/story-02.md) | 8 铁律 + 惩罚 | 不可违逆的天条 |
| 3 | 门禁骑士团 | [cn/story-03.md](cn/story-03.md) | 11 hooks | 边防哨所，层层安检 |
| 4 | 证据裁判庭 | [cn/story-04.md](cn/story-04.md) | 6 hooks | 四层证据链的交响曲 |
| 5 | 记忆神殿 | [cn/story-05.md](cn/story-05.md) | 6 hooks + 知识文件 | 记忆的保存、传承与升华 |
| 6 | 上下文守望者 | [cn/story-06.md](cn/story-06.md) | 5 hooks | 资源哨兵，防止记忆洪灾 |
| 7 | OMA 铸造厂 | [cn/story-07.md](cn/story-07.md) | 4 skills + 3 hooks + 2 scripts | 一人成军的工业流水线 |
| 8 | 双生之子 | [cn/story-08.md](cn/story-08.md) | 2 skills + 全局模式感知 | 幽灵的探索与目标的执行 |
| 9 | 反面镜宫 | [cn/story-09.md](cn/story-09.md) | 16 反模式 | 照出 AI 弱点的镜子迷宫 |
| 10 | 审计军团 | [cn/story-10.md](cn/story-10.md) | 7 scripts | 三大审计师与自检仪 |
| 11 | 三重门神谕 | [cn/story-11.md](cn/story-11.md) | 协议 + nodes | 三端交叉验证的终极审判 |
| 12 | 飞轮回响 | [cn/story-12.md](cn/story-12.md) | 3 hooks + scripts + 协议 | 狗粮永动机的闭环哲学 |
| 13 | 错误炼金术士 | [cn/story-13.md](cn/story-13.md) | 5 hooks + scripts | 从失败中提炼黄金 |
| 14 | 圣器锻造所 | [cn/story-14.md](cn/story-14.md) | 14 skills | 工匠的工具箱 |
| 15 | 元环：蛇吞己尾 | [cn/story-15.md](cn/story-15.md) | 协议 + scripts | 自己治理自己的悖论之美 |

---

## 机制 → 故事 映射表

查到任意机制名，即可找到它出现的故事。

### 哲学 (Philosophies)

| 机制 | 故事 # |
|------|--------|
| 哲学 #1 The Less, The More | 1 |
| 哲学 #2 少量正确大增益 | 1 |
| 哲学 #3 先守护，后激发 | 1 |
| 哲学 #4 没通过验证等于没做 | 1, 4 |
| 哲学 #5 以人为本 | 1 |
| 哲学 #6 先天对 AI 0 信任 | 1, 11 |
| 哲学 #7 文档优先，调研先行 | 1, 12 |
| 哲学冲突裁决（优先级链） | 1 |

### 铁律 (Iron Laws)

| 机制 | 故事 # |
|------|--------|
| 铁律 #1 禁止编造 | 2, 9 |
| 铁律 #2 用户裁定 | 2 |
| 铁律 #3 证据门禁 | 2, 4 |
| 铁律 #4 Git 门禁 | 2, 3 |
| 铁律 #5 范围冻结 | 2, 3 |
| 铁律 #6 隐私防线 | 2, 3 |
| 铁律 #7 断言真实 | 2, 9 |
| 铁律 #8 反自我矛盾 | 2 |

### PreToolUse Hooks

| 机制 | 故事 # |
|------|--------|
| edit-guard | 3 |
| permission-gate | 3 |
| privacy-gate | 3 |
| context-guard | 3, 6 |
| pretool-edit-scope | 3 |
| pretool-sensitive-edit | 3 |
| lsp-suggest | 3 |
| plan-gate | 3 |
| pretool-write-lock | 3, 7 |
| pretool-rule-anchor | 6 |
| pretool-user-correction | 5, 9 |
| pretool-retry-check | 13 |
| fuzzy-block | 3, 9 |
| subagent-guard | 3 |
| pre-completion-gate | 4 |

### PostToolUse Hooks

| 机制 | 故事 # |
|------|--------|
| completion-gate | 4 |
| posttool-format-gate | 4 |
| posttool-anti-pattern-detect | 4, 9 |
| posttool-bash-audit | 13 |
| posttool-edit-quality | 4 |
| posttool-write-cite | 4 |
| posttool-write-lock | 7 |
| posttool-claim-audit | 4 |
| posttool-subagent-audit | 3 |
| posttool-completion-audit | 4 |
| posttool-handoff-writer | 5 |
| posttool-read-cite | 4 |
| intent-tracker | 4 |
| proactive-handoff | 5 |
| auto-snapshot | 5 |
| error-dna | 13 |
| token_writer | 6 |
| read-tracker | 4 |

### SessionStart / Stop / UserPromptSubmit Hooks

| 机制 | 故事 # |
|------|--------|
| inject-project-knowledge | 5 |
| flywheel-report | 12 |
| ecosystem-probe | 3 |
| turn-counter | 6, 9 |
| compact-detect | 6 |
| stop-drain | 13 |
| skill-flywheel | 12 |
| knowledge-condenser | 5 |

### Skills

| 机制 | 故事 # |
|------|--------|
| lx-oma-hier | 7 |
| lx-oma-split | 7 |
| lx-oma-gov | 7 |
| lx-oma-orch | 7 |
| lx-ghost | 8 |
| lx-goal | 8 |
| lx-race | 7 |
| lx-code-review | 14 |
| lx-security-review | 14 |
| lx-react-review | 14 |
| lx-web-perf | 14 |
| lx-browser-verify | 14 |
| lx-test-gen | 14 |
| lx-todo | 14 |
| lx-task-spec | 14 |
| lx-rpe | 14 |
| lx-prd | 14 |
| lx-tdd-spec | 14 |
| lx-debug-spec | 14 |
| lx-status | 14 |
| lx-varlock | 14 |
| lx-pre-commit | 10, 14 |
| lx-pre-push | 10, 14 |

### Scripts & Shared Libraries

| 机制 | 故事 # |
|------|--------|
| harness_config.sh (hc_enabled 门禁) | 3 |
| audit-hooks.sh | 10 |
| harness-smoke-test.sh | 10 |
| hook-production-verify.sh | 10 |
| pre-commit-self-review.sh | 10 |
| doc-sync-check.sh | 10 |
| score-self-check.sh | 10 |
| oma_lock_manager.py | 7 |
| race_manager.sh | 7 |
| error_classifier.py | 13 |
| retry-budget.sh | 13 |
| flywheel_analytics.py | 12 |
| context_monitor.py | 6 |

### 协议 (Protocols)

| 机制 | 故事 # |
|------|--------|
| 三重门交叉验证 | 11 |
| 证据门禁协议 | 4 |
| Oracle 终审 | 11 |
| 狗粮反馈循环 | 12, 15 |
| 机制采纳门禁 | 12 |
| 软完成语禁令 | 4 |
| Ghost/Goal 模式协议 | 8 |
| RPE 文档体系 | 7 |
| Source Mirror 同步 | 15 |

---

## 阅读建议

- **新玩家**：从 #1 七柱圣殿开始，了解世界观基石，然后按兴趣跳跃
- **机制查询**：通过上方映射表找到感兴趣的具体机制，跳到对应故事
- **深度游览**：按 #1 → #3 → #4 → #6 → #11 → #15 的顺序，跟随"门禁 → 验证 → 记忆 → 审计 → 自噬"的主线

---

## 叙事约定

- 所有故事中出现的机制行为均来自真实源码（`file:line` 可追溯）
- 人物化命名：hooks = 骑士/守卫，skills = 工匠/术士，哲学 = 宇宙法则，scripts = 审计师/炼金术士
- 复合机制用"团队协作场景"呈现，体现真实的事件链与数据流
