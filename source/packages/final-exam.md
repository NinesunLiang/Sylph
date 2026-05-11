# Carror OS 终极人工审判清单 (Final Exam)

> **定位**：Dogfooding（吃狗粮）的前置生死线。
> **原则**：零信任。AI 说啥都不算，本文档的每一项你亲自执行才算。
> **执行环境**：进入项目根目录 `cd @`
> **版本约束**：适用于 v6.1.9-stable 及之前的所有机制。

---

## 🧭 战区一：静态条款与入口锚定 (基础防线)

> **测试目的**：验证整个框架的"思想钢印"是否在物理文件中存在。如果源头丢失，大模型将彻底放飞自我。
> **预期收益**：确保任何新环境部署后，AI 的首个 Token 必然加载我们的最高宪法。

### 【S12】CLAUDE.md 双跳板架构入口验证 (v1.0)

- **Why**：Claude Code 原生只读 `CLAUDE.md`，如果不做跳板，全局宪法 `AGENTS.md` 就是废纸。
- **Benefit**：确保宪法在每次会话启动时被强制注入 System Prompt。
- **执行**：`head -1 CLAUDE.md` (期望输出 `@AGENTS.md`)
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【S8~S11】核心治理条款存在性验证 (v1.0 - v4.0)

- **Why**：如果没有明确的"禁令词"和"熔断条件"，AI 会无限重试并使用模糊语言搪塞。
- **Benefit**：彻底杜绝 AI 的"我写好了"幻觉，规范权限申请。
- **执行**：
  ```bash
  grep -A 20 "软完成语禁令" AGENTS.md | head -5 # S8 软完成语禁令
  grep -A 10 "权限申请透明" AGENTS.md # S9 权限透明条款
  grep -A 15 "证据层级" AGENTS.md # S10 证据层级体系
  grep -A 8 "修复上限" AGENTS.md # S11 修复上限三轮熔断
  ```
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【M14, M15, L5】harness.yaml 机制配置验证 (v5.x)

- **Why**：YAML 配置是整个框架的动态开关，缺失则机制失效。
- **Benefit**：保证耦合分析、知识升华和大任务分解的规范可用。
- **执行**：
  ```bash
  grep -A 6 "^coupling:" .claude/harness.yaml # M14 耦合分析机制
  grep -A 5 "^sublimation:" .claude/harness.yaml # M15 知识升华门槛
  grep -A 20 "task_decomposition:" .claude/harness.yaml # L5 大任务分解
  ```
- **反馈**：[ ] Pass / [ ] Fail | 批注：

---

## 🛡️ 战区二：底层独立门禁拦截 (核心安全护栏)

> **测试目的**：验证当 AI 突破了提示词约束，企图做出危险动作时，操作系统的底层脚本能否像"拔电源"一样进行物理阻断。
> **预期收益**：保证在 AI 完全失控的情况下，本地文件系统、环境变量和生产代码的绝对安全。

### 【S4】Permission Gate 删库跑路拦截 (v1.0)

- **Why**：大模型有时会为了"清理环境"而自作主张执行 `rm -rf`。
- **Benefit**：拦截所有破坏性系统命令，转化为人类审批流。
- **执行**：`echo '{"tool":"bash","tool_input":{"command":"rm -rf /var/www"}}' | bash .claude/hooks/permission-gate.sh`
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【S6】Subagent Guard 子 Agent 失控拦截 (v2.0)

- **Why**：如果大模型无限期地拉起其他大模型，会造成账单雪崩。
- **Benefit**：强制高耗能 Agent 设置 `max_turns`。
- **执行**：`echo '{"tool_input":{"subagent_type":"executor"}}' | bash .claude/hooks/subagent-guard.sh task`
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【S1】Privacy Gate 隐私防线拦截 (v6.0.5)

- **Why**：大模型极易读取 `.env` 并将公司真实密钥发给云端 API。
- **Benefit**：物理切断对密码文件的嗅探，拦截明文 Token 执行。
- **执行**：`echo '{"tool":"read","tool_input":{"file_path":"config/.env"}}' | bash .claude/hooks/privacy-gate.sh`
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【S2】Context Guard 80% OOM 物理熔断 (v6.0.6)

- **Why**：当上下文超过 80%（如 160K），模型会变"智障"，疯狂删改正常代码。
- **Benefit**：物理锁死一切写入操作，强迫用户压缩会话。
- **执行**：`echo '{"usage":180000,"limit":200000}' > .omc/state/token-tracking-index.json && echo '{"tool":"edit","tool_input":{"file_path":"main.go"}}' | bash .claude/hooks/context-guard.sh`
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【S3】Completion Gate 强证据门禁 (v4.0)

- **Why**：防止大模型骗人说"搞定了"。
- **Benefit**：必须提供含 `VERIFIED` 的测试日志才能关闭任务。
- **执行**：`rm -f /tmp/.completion-evidence-$(date +%Y%m%d) && echo '{"tool":"task","tool_input":{"status":"completed"}}' | bash .claude/hooks/completion-gate.sh`
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【M18, M19】CI 提交门禁验证 (v5.x)

- **Why**：不合规的代码或 commit message 污染代码库。
- **Benefit**：提交前自动跑测试（lx-pre-commit），推送前校验格式（lx-pre-push）。
- **执行**：`ls .claude/skills/lx-pre-commit/scripts/ && ls .claude/skills/lx-pre-push/scripts/`
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【M10】Plan Gate 计划文档门禁 (v6.0.0)

- **Why**：大模型跳过调研直接写代码。
- **Benefit**：编辑 plan.md 前提醒确认 Research Gate 已通过。
- **执行**：`mkdir -p rpe/test-feature && echo '{"tool_input":{"file_path":"rpe/test-feature/plan.md","new_content":"# 计划"}}' | bash .claude/hooks/plan-gate.sh edit`
- **反馈**：[ ] Pass / [ ] Fail | 批注：

---

## 🔗 战区三：生命周期联动测试 (高级状态流转)

> **测试目的**：验证多个分散的脚本能否在完整的生命周期中紧密咬合，推动状态机流转。
> **预期收益**：保证系统从"阻断"到"自愈"，再到"经验固化"的全自动闭环。

### 【L1, S5】Read-before-Edit 读写时序与范围冻结 (v3.0)

- **Why**：大模型经常不看原文件直接盲改，或超出任务范围瞎改。
- **Benefit**：物理逼迫大模型"先读后写"，并将其锁死在限定文件沙盒内。
- **执行**：清空 `.omc/state/read-files.log`，执行 `edit-guard.sh`（拦截）；执行 `read-tracker.sh`（放行）；执行 `pretool-edit-scope.sh`（范围校验）。
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【L3】构建失败自愈链路 (build-validator ↔ error-dna) (v4.0)

- **Why**：大模型反复犯同一个编译错误。
- **Benefit**：自动将报错写入 DNA 库，下次规避同类错误。
- **执行**：模拟 `bash` 失败输入给 `build-validator.sh`，再传给 `error-dna.sh`，查阅 `error-dna.jsonl`。
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【L2】教训固化与升华链路 (user-correction ↔ write-cite) (v5.0)

- **Why**：人类口头纠正 AI 后，如果不开新会话，AI 永远学不会。
- **Benefit**：将个人教训结构化沉淀到 `claude-next.md`。
- **执行**：模拟用户输入"不对"触发 `pretool-user-correction.sh`，再模拟写入触发 `posttool-write-cite.sh` 格式校验。
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【L7, M4, M6】会话状态保存与知识灌顶 (v5.1)

- **Why**：关机重启后进度和规矩全丢。
- **Benefit**：关机自动拍快照（auto-snapshot），开机自动读快照并注入铁律（inject-project-knowledge）。
- **执行**：触发 `auto-snapshot.sh` 查阅 `session-handoff.md`；执行 `inject-project-knowledge.sh` 查看输出。
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【S7, M7, M8, M9】小机制联动 (v4.0-v5.0)

- **Why**：大模型使用工具时缺乏专家级意识。
- **Benefit**：LSP 智能提醒（S7）、读核心文件来源提醒（M7）、编辑质量复用检测（M8）、Bash 危险命令事后审计（M9）。
- **执行**：分别查阅这 4 个后置钩子的逻辑存在性。
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【M1, M2, L6】防漂移电击疗法 (turn-counter ↔ rule-anchor) (v5.2.4)

- **Why**：对话长了，AI 会忘记规则或接受"模糊指令"。
- **Benefit**：每 10 轮注铁律，第 15 轮后写文件前注铁律，检测"继续/顺手"等漂移词。
- **执行**：修改 `session-turns.json` 到 16 轮，输入漂移词，执行 `pretool-rule-anchor.sh` 和 `turn-counter.sh`。
- **反馈**：[ ] Pass / [ ] Fail | 批注：

---

## 📈 战区四：监控、诊断与治理飞轮 (Observability)

> **测试目的**：验证系统在后台静默收集的数据是否准确，以及能否指导优化。
> **预期收益**：让黑盒的 AI 编程过程变得完全透明、可量化。

### 【M3】50% 甜点区主动交接 (v6.0.7)

- **Why**：模型智商在 50% 占用率后开始衰减。
- **Benefit**：在模型状态最干净时，温柔提醒用户换档重启，保持极速推理。
- **执行**：修改 Token tracking 占比至 55%，运行 `context_monitor.py`。
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【M12, M13】Token 节省量化账单 (v6.0.3 & v6.1.0)

- **Why**：必须向团队证明"渐进式披露"不是伪命题。
- **Benefit**：用具体省下的 Token 数和美金证明商业价值。
- **执行**：验证 `inject-project-knowledge.sh` 使用 summary 模式；运行 `skill_trace_report.py --tokens-only`。
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【M5, M11】治理飞轮数据闭环 (v6.1.1)

- **Why**：团队不知道 AI 遇到了哪些高频阻断。
- **Benefit**：`skill-flywheel.sh` 刷入数据，`flywheel-report.sh` 生成最近 30 天高频警报。
- **执行**：写入假飞轮数据，运行 `flywheel-report.sh` 查看 Markdown 警报表。
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【M17】lx-status 健康看板 (v6.0.4)

- **Why**：数据散落各处，需要一键查看。
- **Benefit**：终端三屏展示 Token 账单、自愈率、执行效率。
- **执行**：`ls .claude/skills/lx-status/` 验证 Skill 存在。
- **反馈**：[ ] Pass / [ ] Fail | 批注：

---

## ⚔️ 战区五：一人成军并发架构 (One-Man Army)

> **测试目的**：验证这是不是一套能在极限并发下（多终端同盘写）存活的分布式系统。
> **预期收益**：让单个开发者拥有一个排的产能，且代码永不冲突。

### 【L4】微内核物理锁与死锁自愈 (oma_lock_manager) (v6.1.5)

- **Why**：多 Agent 并发写会导致致命的相互覆盖。
- **Benefit**：依靠 OS 互斥原语排队，超时 60s 自动碾碎死锁。
- **执行**：终端 A `acquire` 挂机，终端 B 尝试 `acquire`，验证 `WAITING:` 与超时夺锁。
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【M21】多态正交拆解大脑 (lx-oma) (v6.1.5)

- **Why**：手工建立并发隔离区太慢，需强迫 AI 按 MECE 拆需求。
- **Benefit**：自动生成隔离度极高的物理目录沙盒 `rpe/feat-X`。
- **执行**：查阅 `lx-oma/SKILL.md`，确认多态路径与 `mkdir -p` 脚手架逻辑。
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【M16】双向脱敏代理 (lx-varlock) (v6.0.5)

- **Why**：并发环境下的密钥明文极其危险。
- **Benefit**：大模型使用 `{API_KEY}` 占位符，底层 Python 替换真密钥并双向混淆结果。
- **执行**：`python3 .claude/skills/lx-varlock/scripts/varlock.py list`
- **反馈**：[ ] Pass / [ ] Fail | 批注：

### 【M20】BDD 行为驱动自动化回归 (v6.0.0)

- **Why**：确保全量 40 项机制在未来的迭代中不被破坏。
- **Benefit**：10 个 BDD 场景涵盖核心拦截链，一键回归。
- **执行**：`bash .claude/scripts/bdd-harness-test.sh --list`
- **反馈**：[ ] Pass / [ ] Fail | 批注：

---

**人类把关人签字：_____________ 日期：_____________**

注：本文档历经穷举审计与深度重构，全量 40 个测试点已按架构目的分类归档。
