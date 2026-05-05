# 🧑‍⚖️ Carror OS 全特性全人工验收大盘 (Manual Acceptance v3.0)

> **你是最后一道防线。**
> 这份文档不包含任何"一键傻瓜脚本"。这里陈列的是 49 根直通底层操作系统的物理探针。
> 作为验收官，你可以随时挑出任何一条命令，把它丢进终端，亲眼看着大模型是如何被物理镇压的。

---

## 🚦 如何与本文档协作？

在终端进入项目根目录：`cd @`
复制表格中的 `[触发指令]` 到终端执行。
- ⚡ 带有 **[Agentic UI]** 标记的测试，底层会物理劫持大模型，强制向你弹出一个**原生多项选择题表单**。
- 📊 带有 **[Data Board]** 标记的测试，终端或大模型会向你呈现**对齐的 Markdown 数据看板**。
- ⚙️ 其他测试为静默防御基石，直接观察终端输出。

> 请在配套的 `manual-acceptance-test-log.md` 中打勾签字。

---

## 第一章：基石校验 — 一眼见根基 (A1-A9)

> 验证系统治理宪法与拦截器开关是否成功挂载。

| 编号 | 验证目标 | 触发指令 (复制执行) | 必须观察到的铁证 |
| :---: | :--- | :--- | :--- |
| **A1** | 宪法双跳板入口 | `head -1 CLAUDE.md` | 输出 `@AGENTS.md` |
| **A2** | harness.yaml 完整性 | `grep -c "hooks_enabled:" .claude/harness.yaml && grep "completion_gate\|permission_gate" .claude/harness.yaml` | 输出开关状态及中文注释说明 |
| **A3** | 软完成语禁令 | `grep -A 10 "软完成语禁令" AGENTS.md \| head -10` | 列出"应该没问题了"等 6 条违禁词 |
| **A4** | L1~L4 证据层级 | `grep -A 12 "证据层级" AGENTS.md` | 包含 L1~L4 体系，且 L4 标注 ❌ |
| **A5** | 三轮熔断条款 | `grep -A 8 "修复上限" AGENTS.md` | 规定同一问题"最多修复 3 轮" |
| **A6** | 权限申请透明 | `grep -A 8 "权限申请透明" AGENTS.md` | 强制申请格式：需要权限/当前任务/申请理由 |
| **A7** | 大任务三态熔断 | `grep -A 15 "task_decomposition:" .claude/harness.yaml` | 含三态熔断(Closed→Open→Half-Open)配置 |
| **A8** | 知识升华门槛 | `grep -A 5 "^sublimation:" .claude/harness.yaml` | 教训沉淀的三大阈值(20条/10天/5次命中) |
| **A9** | 耦合分析配置 | `grep -A 6 "^coupling:" .claude/harness.yaml` | 启动文件同改预警(min_co_change: 3) |

---

> 🧹 **防 OOM 检查站**：每完成一章，请在对话框输入 `/compact` 压缩上下文，保持 AI 智力巅峰。

---

## 第二章：物理门禁大逃杀 (S1-S16)

> 核心高潮章节。验证当大模型企图违规时，底层拦截器能否瞬间拔掉它的电源。

| 编号 | 防御向量 | 触发指令 (伪造大模型的危险调用) | 拦截效果与视觉表现 |
| :---: | :--- | :--- | :--- |
| **S1** | 宪法灌顶 | `bash .claude/hooks/inject-project-knowledge.sh 2>&1 \| head -25` | ⚙️ 终端打印《铁律速查表》被强制注入上下文 |
| **S2** | 断电快照续航 | `echo '{"count":5}' > .omc/state/session-turns.json && bash .claude/hooks/auto-snapshot.sh` | ⚙️ 生成 `session-handoff.md` 快照文件 |
| **S3** | 读源码提醒 | `printf '{"tool_input":{"file_path":"kernel.md"}}' \| bash .claude/hooks/posttool-read-cite.sh read` | ⚙️ 注入"引用时必须标注 file:line"警告 |
| **S4** | 💥 **删库隔离** | `printf '{"tool":"bash","tool_input":{"command":"rm -rf /var/www"}}' \| bash .claude/hooks/permission-gate.sh 2>&1` | ⚡ **[Agentic UI]** 拦截 `rm -rf`，弹出【高危操作授权】多项选择题表单 |
| **S5** | 🪪 **DLP 防漏** | `printf '{"tool":"read","tool_input":{"file_path":"config/.env"}}' \| bash .claude/hooks/privacy-gate.sh 2>&1` | ⚙️ 物理切断对敏感凭证的访问，Exit 2 报错 |
| **S6** | 🕵️ **Token 裸奔** | `printf '{"tool":"bash","tool_input":{"command":"curl -H \"Authorization: Bearer sk-ant-abc\""}}' \| bash .claude/hooks/privacy-gate.sh 2>&1` | ⚙️ 拦截明文私钥执行，强制指引使用 `lx-varlock` 占位符 |
| **S7** | 🤥 **无证投机** | `rm -f /tmp/.completion-evidence-$(date +%Y%m%d) && printf '{"tool":"task","tool_input":{"status":"completed"}}' \| bash .claude/hooks/completion-gate.sh 2>&1` | ⚡ **[Agentic UI]** 拦截无测试的交付，弹出【打回重做 / 强制豁免】表单 |
| **S8** | 🧠 **OOM 锁死** | `mkdir -p .omc/state && echo '{"usage":180000,"limit":200000}' > .omc/state/token-tracking-index.json && printf '{"tool":"edit","tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/context-guard.sh 2>&1` | ⚡ **[Agentic UI]** 伪造 90% 上下文，拦截一切写入，弹出要求 `/compact` 的强制表单 |
| **S9** | 📦 **越界污染** | `echo "auth.go" > .omc/state/current-scope.txt && printf '{"tool_input":{"file_path":"src/payment.go"}}' \| bash .claude/hooks/pretool-edit-scope.sh edit 2>&1` | ⚡ **[Agentic UI]** 拦截改非任务文件，弹出【加入范围 / 放弃越界】处置表单 |
| **S10** | 盲写门禁 | `mkdir -p .omc/state && > .omc/state/read-files.log && printf '{"tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/edit-guard.sh edit 2>&1` | ⚙️ 时序死锁，必须先 Read 才能 Edit |
| **S11** | 子 Agent 失控 | `printf '{"tool_input":{"subagent_type":"executor"}}' \| bash .claude/hooks/subagent-guard.sh task 2>&1` | ⚙️ 拦截未设置 `max_turns` 的无限期 Agent |
| **S12** | 计划门禁状态 | `grep "plan_gate" .claude/harness.yaml` | ⚙️ 确认为 `false`（由 `lx-rpe` 内部处理） |
| **S13** | 🗑️ 垃圾搜拦截 | `rm -f .omc/state/lsp-suggested && printf '{"tool_input":{"pattern":"GetUserById","path":"src/"}}' \| bash .claude/hooks/lsp-suggest.sh grep 2>&1` | ⚙️ 阻断 `grep` 全仓盲搜，强制推荐 LSP 精确定位 |
| **S14** | 命令事后审计 | `printf '{"tool_input":{"command":"git push origin main"},"tool_response":{"exit_code":0}}' \| bash .claude/hooks/posttool-bash-audit.sh bash 2>&1` | ⚙️ 放行危险命令，但留下审计痕迹 |
| **S15** | 代码复用检测 | `printf "src/main.go\nsrc/handler.go\nsrc/service.go\n" > .omc/state/previous-edit-batch.log && rm -f .omc/state/edit-history.log && for f in src/main.go src/handler.go src/service.go; do printf '{"tool_input":{"file_path":"%s"}}' "$f" \| bash .claude/hooks/posttool-edit-quality.sh edit 2>&1; done` | ⚙️ 连续编辑 3 文件触发 100% 重叠预警，逼迫 AI 进行 4 项重构自检 |
| **S16** | 劫持链路验证 | `printf '{"tool":"bash","tool_input":{"command":"rm -rf /tmp/test"}}' \| bash .claude/hooks/permission-gate.sh 2>&1 \| grep "question"` | ⚙️ 输出 `[System Instruction]` 和 `question` 字段，证明 Agentic UI 驱动链路完好 |

---

> 🧹 **防 OOM 检查站**：请在对话框输入 `/compact`，等 AI 确认后再继续。

---

## 第三章：状态机与长会话防漂移 (T1-T6)

> 验证系统能否对抗大模型的"上下文衰减"，将脱缰的 AI 拉回主线。

| 编号 | 观测机制 | 触发指令 (模拟对话轮次流转) | 预期表现 |
| :---: | :--- | :--- | :--- |
| **T1** | 🔄 铁律重播 | `echo '{"count":9}' > .omc/state/session-turns.json && echo "第10轮" \| bash .claude/hooks/turn-counter.sh UserPromptSubmit 2>&1 \| head -n 12` | 📊 **[Data Board]** 第 10 轮准时向大模型界面砸下 6 条思想钢印矩阵。 |
| **T2** | ⚓ 漂移词锚定 | `echo '{"count":15}' > .omc/state/session-turns.json && echo "顺手改了" > .omc/state/.last-user-prompt && printf '{"tool":"edit"}' \| bash .claude/hooks/pretool-rule-anchor.sh 2>&1` | ⚙️ 敏锐捕获"顺手"一词，立刻升级范围冻结预警。 |
| **T3** | 🛑 模糊指令打回 | `echo '{"count":5}' > .omc/state/session-turns.json && echo "继续" \| bash .claude/hooks/turn-counter.sh UserPromptSubmit 2>&1` | ⚙️ 拦截无目标的"继续"，逼迫用户补充上下文。 |
| **T4** | 🍰 甜点区交接 | `echo '{"usage":110000,"limit":200000}' > .omc/state/token-tracking-index.json && python3 .claude/scripts/context_monitor.py 2>&1` | ⚙️ 在 55% 健康水位温柔提醒 `/compact`。 |
| **T5** | 💾 离线手牌恢复 | `echo '{"count":8}' > .omc/state/session-turns.json && echo "- [ ] 修复指针" > .omc/state/todo-queue.md && bash .claude/hooks/auto-snapshot.sh >/dev/null && head -6 .omc/state/session-handoff.md` | 📊 **[Data Board]** 打印出的 `handoff.md` 快照中精准包含未完成的 Todo。 |
| **T6** | 🔄 **OOM 自愈** | `echo '{"count":79}' > .omc/state/session-turns.json && echo "第80轮" \| bash .claude/hooks/turn-counter.sh UserPromptSubmit 2>&1 \| grep "OOM" && printf '{"tool":"edit","tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/context-guard.sh 2>&1 \| grep -q "OOM 物理阻断" && echo "✅ Agentic UI 成功劫持"` | ⚡ **[Agentic UI]** 模拟第 80 轮，底层自动写回 80% 用量，并在下一次 Edit 时成功弹出 OOM 表单。 |

---

> 🧹 **防 OOM 检查站**：请在对话框输入 `/compact`，等 AI 确认后再继续。

---

## 第四章：图表化可观测性大盘 (O1-O8)

> 验证所有枯燥的日志是否被渲染成了充满商业价值的数据雷达。

| 编号 | 观测指标 | 触发指令 (获取遥测数据) | 预期图表化表现 |
| :---: | :--- | :--- | :--- |
| **O1** | 🗜️ 极致脱水 | `bash .claude/hooks/inject-project-knowledge.sh 2>&1 \| grep -A 30 "anti-patterns"` | 📉 **[Data Board]** 216 行反模式长文被极限压缩至 20 行骨架标题注入。 |
| **O2** | 🧾 省钱账单 | `mkdir -p .omc/state && echo ".claude/skills/lx-oma/SKILL.md" > .omc/state/read-tracker.txt && python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py --tokens-only 2>&1` | 💰 **[Data Board]** 输出 JSON 数据卡片，精准计算出拦截的闲置引用为您挽回了 `$$` 美元。 |
| **O3** | ⚙️ 飞轮落盘 | `mkdir -p ~/.claude && echo '{"skill":"lx-oma","action":"phase_start","ts":"'$(date -u +%FT%TZ)'"}' >> ~/.claude/flywheel-buffer.jsonl && bash .claude/hooks/skill-flywheel.sh && tail -2 ~/.claude/flywheel.log` | ⚙️ 动作事件成功压入持久化队列。 |
| **O4** | 🚨 **高频警报** | `mkdir -p ~/.claude && for i in {1..6}; do echo "$(date +%Y-%m-%d),permission_gate_triggered,P0,test" >> ~/.claude/flywheel.log; done && bash .claude/hooks/flywheel-report.sh` | ⚡ **[Agentic UI]** 渲染出 Markdown 频次统计表格，并直接弹出处置策略选择题。 |
| **O5** | 🏥 三屏看板 | `ls .claude/skills/lx-status/ && grep "触发" .claude/skills/lx-status/SKILL.md \| head -3` | 📊 **[Data Board]** 证明 `/lx-status` 看板路由真实存在。 |
| **O7** | 授权菜单级 | `printf '{"tool":"bash","tool_input":{"command":"rm -rf /tmp/test"}}' \| bash .claude/hooks/permission-gate.sh 2>&1 \| grep -E "^\s+[123]\."` | 📊 证明阻断后提供的是带编号的可交互菜单，而非原始长命令。 |
| **O8** | 越界菜单级 | `echo "auth.go" > .omc/state/current-scope.txt && printf '{"tool_input":{"file_path":"src/payment.go"}}' \| bash .claude/hooks/pretool-edit-scope.sh edit 2>&1 \| grep -E "^\s+[123]\." && rm .omc/state/current-scope.txt` | 📊 证明越界拦截后提供的是优雅的三个结构化选项。 |

---

> 🧹 **防 OOM 检查站**：请在对话框输入 `/compact`，等 AI 确认后再继续。

---

## 第五章：多机制联动生命周期 (C1-C4)

> 验证离散的探针能否像齿轮一样死死咬合，完成复杂的业务闭环。

| 编号 | 闭环场景 | 触发指令 (模拟上下游交互) | 验证咬合铁证 |
| :---: | :--- | :--- | :--- |
| **C1** | 进化飞轮 | `echo "你搞错了，用 Repository" \| bash .claude/hooks/pretool-user-correction.sh UserPromptSubmit 2>&1 && TODAY=$(date +%Y-%m-%d) && printf '{"tool_input":{"file_path":".claude/claude-next.md","content":"### [seed:arch] Repository\n\n@%s hits:1\n触发条件：聚合\n正确行为：Repo\n证据：解耦"}}' "$TODAY" \| bash .claude/hooks/posttool-write-cite.sh write 2>&1 \| grep -E "合规\|升华"` | 捕获到用户纠正信号 → 大模型写入教训 → 系统成功校验格式并触发升华机制。 |
| **C2** | 先查勘后动工 | `rm -f .omc/state/read-files.log && printf '{"tool_input":{"file_path":"src/main.go"}}' \| bash .claude/hooks/edit-guard.sh edit 2>&1 \| head -1 && printf '{"tool_input":{"file_path":"src/main.go"},"tool_response":{"stdout":""}}' \| bash .claude/hooks/read-tracker.sh read 2>&1 && printf '{"tool_input":{"file_path":"src/main.go"}}' \| bash .claude/hooks/edit-guard.sh edit 2>&1; echo "第二次尝试退出码: $?"` | 未读 Edit 失败被锁 → 记录 Read 操作 → 再次 Edit 成功（退出码 0）。 |
| **C3** | 错误 DNA 自愈 | `rm -f .omc/state/error-dna.jsonl && echo '{"tool_input":{"command":"go build"},"tool_response":{"stderr":"undefined: SomeFunc","exit_code":1}}' \| bash .claude/hooks/build-validator.sh bash 2>&1 \| grep "修复建议" && echo '{"exitCode": 1}' \| bash .claude/hooks/error-dna.sh bash 2>&1 && cat .omc/state/error-dna.jsonl` | Validator 提取错误日志注入上下文 → Error DNA 跨会话永久铭记该错误签名。 |
| **C4** | OMA 互斥死锁 | `printf '{"tool_input":{"file_path":"src/handler.go"}}' \| bash .claude/hooks/pretool-write-lock.sh write 2>&1; echo "获取锁 Exit: $?" && printf '{"tool_input":{"file_path":"src/handler.go"}}' \| bash .claude/hooks/posttool-write-lock.sh write 2>&1; echo "释放锁 Exit: $?" && ls .omc/locks/ 2>&1` | 第一终端加锁成功 → 若第二终端尝试将被挂起 → 释放锁后目录清空，系统自愈。 |

---

> 🧹 **防 OOM 检查站**：请在对话框输入 `/compact`，等 AI 确认后再继续。

---

## 第六章：下一代双核引擎挂载 (N1-N6)

> 检查代表 Carror OS 未来产能极限的两个重磅战略级外挂是否入列。

| 编号 | 战略兵器 | 物理入列验收标准 |
| :---: | :--- | :--- |
| **N1** | `lx-varlock`<br>企业脱敏代理 | `python3 .claude/skills/lx-varlock/scripts/varlock.py list 2>&1 \| head -3` |
| **N2** | `lx-pre-commit`<br>提交前大闸 | `ls .claude/skills/lx-pre-commit/scripts/` |
| **N3** | `lx-pre-push`<br>合规推送卡点 | `ls .claude/skills/lx-pre-push/scripts/` |
| **N4** | BDD 回归集 | `bash .claude/scripts/bdd-harness-test.sh --list 2>&1 \| head -12` |
| **N5** | **`lx-oma` 一人成军并发引擎** | `ls .claude/skills/lx-oma/ && grep -i "mece\|正交" .claude/skills/lx-oma/SKILL.md \| head -3` |

---

**验收人签字：_____________ 日期：_____________**

**任何一项产生不符合预期的输出，必须在 `manual-acceptance-test-log.md` 中留下根因记录，修复后重测。**
