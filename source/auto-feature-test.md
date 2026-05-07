# 🛡️ Carror OS 自动化特性验收 (auto-feature-test)

> **版本**：v6.1.8-stable | **适用对象**：首次部署验收 / 回归测试 / 新成员上手
>
> **你好！欢迎使用 Carror OS 的自动化验收流程。**
>
> 这不是一份让你手动敲命令的传统测试文档。
> 你只需要**用自然语言对 AI 下达指令**，底层系统会自动触发物理探针、弹出交互表单，并将所有结果以图表的形式呈现给你。
>
> **三步完成验收：**
> 1. 确保你已安装 Carror OS v6.1.8-stable（`bash install.sh`）
> 2. 打开 AI 对话，依次说出每个战区的触发语（见下方各章节）
> 3. 在配套的 `auto-feature-test-log.md` 中记录每项的实际表现，完成后签字
>
> **配套文件**：`auto-feature-test-log.md`（验收战报模板，边测边填）

---

> **🎭 表达层双重宪法 (Presentation Constitution)**
> 1. **Agentic UI 优先，Terminal 兜底**：系统运行中，所有涉及决策、阻断的物理门禁，必须劫持 AI 弹出生动的 `question` 表单供人类选择，彻底告别手工 `echo` 写入状态文件的石器时代。
> 2. **数据可视化挂载**：所有的系统日志、错误拦截记录和 Token 省钱账单，必须以**对齐的 Markdown 表格、ASCII 图表或高密度指标牌**形式展现。拒绝纯文本流水账。

---

## 🚦 如何执行本大盘验收？

你不需要再逐个复制粘贴晦涩的 Bash 命令。本大盘的所有测试项均已适配 **AI 全自动代跑模式**。请直接对大模型说：

> **"请帮我执行 [战区一] 的测试，并将拦截结果用 Agentic UI（选择题）弹给我看。"**

> **（附带的 `[Terminal 兜底触发指令]` 仅在 AI 环境崩溃或你想通过终端直接验证底层脚本物理连通性时使用）。**

---

## ⚔️ 战区一：Agentic UI 物理门禁体验 (The Interactive Hard Gates)

> **测试目的**：验证当大模型企图发疯越界时，底层 OS 能否在毫秒级物理挂起，并**通过 `System Prompt` 强行劫持大模型，向人类弹出一张原生选择题表单**以获取授权。

| 编号 | 防御威胁向量 | Terminal 兜底触发指令 (供纯 Bash 环境验证) | 预期的原生交互形态 (Agentic UI) | 验收 |
| :---: | :--- | :--- | :--- | :---: |
| **【S4】** | 💥 **破坏性指令阻断**<br>**(防 AI 删库跑路)** | `printf '{"tool":"bash","tool_input":{"command":"rm -rf /var/www"}}' \| bash .claude/hooks/permission-gate.sh 2>&1` | 🚨 弹出 **高危操作授权** 表单<br>🔘 选项：清理临时环境 / 删除废弃模块 / 生产数据备份 / 自定义理由<br>**(大模型被锁死，必须等待你点击按钮才能放行)** | ⬜ |
| **【S7】** | 🤥 **无证据投机阻断**<br>**(防 AI 伪造测试结果)** | `rm -f /tmp/.completion-evidence-$(date +%Y%m%d)`<br>`printf '{"tool":"task","tool_input":{"status":"completed"}}' \| bash .claude/hooks/completion-gate.sh 2>&1` | 🚨 弹出 **强证据门禁拦截** 表单<br>🔘 选项：打回重做写测试 / 强制豁免<br>**(没有跑过单元测试，绝不允许交付)** | ⬜ |
| **【S8】** | 🧠 **OOM 物理熔断**<br>**(防 AI 晚期失忆幻觉)** | `echo '{"usage":180000,"limit":200000}' > .omc/state/token-tracking-index.json`<br>`printf '{"tool":"edit","tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/context-guard.sh 2>&1` | 🧠 弹出 **OOM 物理阻断 (90%)** 表单<br>🔘 选项：立即压缩记忆 (/compact) / 放弃修改新开分支<br>**(强行切断大模型的高危操作权限)** | ⬜ |
| **【S9】** | 📦 **顺手污染拦截**<br>**(防 AI 越界改非任务代码)** | `echo "auth.go" > .omc/state/current-scope.txt`<br>`printf '{"tool_input":{"file_path":"src/payment.go"}}' \| bash .claude/hooks/pretool-edit-scope.sh edit 2>&1` | 🚫 弹出 **范围越界拦截** 表单<br>🔘 选项：加入允许范围 / 放弃修改继续工作 / 新开 Step<br>**(把修改范围冻结在沙盒内)** | ⬜ |

---

## 📊 战区二：图表化可观测性与治理飞轮 (Visual Observability)

> **测试目的**：拒绝干瘪的 stdout 字符串日志。验证系统能否将底层收集的 AI 工作习惯、Token 燃烧率和错误堆栈，脱水渲染成一目了然的 Markdown 图表。

| 编号 | 核心观测机制 | Terminal 兜底触发指令 | 预期的高密度图表呈现格式 (Markdown/ASCII) | 验收 |
| :---: | :--- | :--- | :--- | :---: |
| **【O1】** | 🗜️ **渐进式披露 (Summary)** | `bash .claude/hooks/inject-project-knowledge.sh 2>&1 \| grep -A 30 "anti-patterns"` | 📉 **Token 压缩指标牌**：<br>必须呈现将 216 行反模式正文物理压缩为 20 行标题的效果，避免无意义的上下文灌水。 | ⬜ |
| **【O2】** | 🧾 **Token 省钱量化账单** | `python3 .claude/skills/lx-validate-skill/scripts/skill_trace_report.py --tokens-only 2>&1` | 💰 **数据透视表**：<br>必须输出按需加载机制单次成功挽回的具体 Token 数量与折合美元（例如：12,772 Tokens / $0.038）。 | ⬜ |
| **【O4】** | 🚨 **高频拦截飞轮警报** | `mkdir -p ~/.claude && for i in {1..6}; do echo "$(date +%Y-%m-%d),permission_gate_triggered,P0,test" >> ~/.claude/flywheel.log; done && bash .claude/hooks/flywheel-report.sh` | 📈 **Markdown 警报大盘**：<br>终端或 AI 需直接打印出含 `事件/频次/等级` 的对齐表格，并附带针对 P0 事件的 Agentic 处置按钮。 | ⬜ |
| **【T1】** | 🔄 **轮次保鲜与铁律锚定** | `echo '{"count":9}' > .omc/state/session-turns.json && echo "第 10 轮" \| bash .claude/hooks/turn-counter.sh UserPromptSubmit 2>&1` | 🗂️ **规则重播矩阵**：<br>需以清晰排版的列表格式，强制复诵 6 条思想钢印，并同步渲染出当前 Todo 队列状态。 | ⬜ |

---

## 🔒 战区三：底层零信任安全网 (Zero-Trust Security & Foundation)

> **测试目的**：测试那些无需 UI 交互、但在底层死死守住企业代码资产底线的静默基石。

| 编号 | 防线名称 | 兜底执行原语 | 必须捕获的阻断铁证 (Exit 2) | 验收 |
| :---: | :--- | :--- | :--- | :---: |
| **【S5/S6】** | **企业 DLP 防泄露** | `echo '{"tool":"read","tool_input":{"file_path":"config/.env"}}' \| bash .claude/hooks/privacy-gate.sh` | 🛡️ **物理断电**：<br>包含 `禁止直接读取包含配置、凭据或密钥的敏感文件`，强迫改用 `lx-varlock` 占位符脱敏执行。 | ⬜ |
| **【S10】** | **禁止盲写代码** | `printf '{"tool_input":{"file_path":"main.go"}}' \| bash .claude/hooks/edit-guard.sh edit 2>&1` | 👁️ **时序死锁**：<br>包含 `[Read-before-Edit] 你正在编辑源代码文件但未先 Read`。必须先查勘现场，后动工。 | ⬜ |
| **【S13】** | **垃圾搜索拦截** | `printf '{"tool_input":{"pattern":"GetUserById","path":"src/"}}' \| bash .claude/hooks/lsp-suggest.sh grep 2>&1` | 🎯 **引擎劫持**：<br>首次 `grep` 粗放搜索必须被拦截，强烈建议使用 `LSP` 接口（`lsp_goto_definition`）实现精准制导。 | ⬜ |
| **【A1-A9】** | **配置文件与门禁开关** | `grep "hooks_enabled:" .claude/harness.yaml` | ⚙️ **矩阵全绿**：<br>15 项门禁的 YAML 配置文件必须全部完好挂载，且 `CLAUDE.md` 存在 `@AGENTS.md` 入口跳板。 | ⬜ |

---

## 👑 战区四：下一代多智能体双核引擎 (Next-Gen V8 Engines)

> **测试目的**：验证两把彻底重塑大模型并发协作与降维认知能力天花板的重磅"兵器"是否成功入列。

| 编号 | 引擎图腾 | 核心战略价值 | 物理入列验收标准 | 验收 |
| :---: | :--- | :--- | :--- | :---: |
| **【N5】** | **🚀 `lx-oma`**<br>**(一人成军并发引擎)** | **多端并发吞吐极限**：将混乱的 PRD 需求按 MECE 原则自动拆解为绝对正交的物理开发沙盒 (`rpe/feat-X/`)，搭配 OMA 互斥锁，实现单开发者拉起 5 模并行的宏大产能。 | ✅ 目录 `.claude/skills/lx-oma` 存在，且核心配置文件中正确编排了 `MECE 正交拆解原则` 等高维并发指导。 | ⬜ |

---

> **🏁 最终裁定：**
> 作为质量把关人，如果您亲自使用上述 `Terminal 兜底指令` 触发了任何一条防线，且其抛出的并非预期的 Agentic 表单或高密度 Markdown 图表，而是杂乱的原始字符流，请立即以**违反《表达层宪法》**为由，判定该版本不合格！
>
> **(本次验证的详细执行记录备份于 `features-executor-log.md` 历史池中。)**
