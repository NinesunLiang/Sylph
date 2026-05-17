# claude-next.md — AI 学习笔记

> 上次升华: 2026-05-17 — 9 条通用铁律升华到 [kernel.md](kernel.md), ~81 条归档到 [lessons-archive.md](archive/lessons-archive.md)
> 当前保留: 2026-05-17 活跃条目（DG-80/DG-81/DG-82/DG-83/DG-84/DG-85/DG-86/DG-87）
>
> 升华规则: 条目≥20 | 年龄≥10天 | hits≥5 — 满足任一条件进入升华候选

---

## 🏍️ 祝贺张雪机车4冠！！！(@LuangSir)

@2026-05-17 hits:1
🎉🎉🎉 张雪机车勇夺第四冠！！！历史性时刻！！！

---

## 2026-05-17 狗粮 — ROI 量化系统 + flywheel 埋点

### 🐶 [DG-80] 批量自动化替换必须区分注释和代码 — 正则替换第一个匹配太粗暴 (@LuangSir)

@2026-05-17 hits:1
触发条件：自动脚本用 str.replace('exit 2', 'flywheel_event...\nexit 2') 替换第一个 'exit 2'，结果命中了注释里的 'exit 2'
正确行为：替换 exit 2 前必须：(a) 跳过注释行 (b) 只替换独立成行的 exit 2 (c) 替换后用 bash -n 逐文件验证
证据：completion-gate.sh/feature-probe.sh/plan-gate.sh 等 6 个文件的注释被损毁，3 个 hook 的 flywheel_event 掉进 exit 0 后的注释里变成死代码

### 🐶 [DG-81] 治理文件变更必须检查所有 profile 变体 — 不能只改 root (@LuangSir)

@2026-05-17 hits:1
触发条件：删除 pretool-ask-guard 时清理了 root 的 harness.yaml/settings.json/feature-registry.yaml，但漏了 profiles/base × 3、lx-skills-v5 × 1、auto-score.sh × 2
正确行为：任何 hook 的增删改必须：grep -r hook_name 全项目 → 列出所有命中文件 → 逐一清理 → 再次 grep 确认零引用
证据：DG-16 重复犯案 (profiles/base 未同步) + Oracle 发现 20+ 处遗漏

### 🐶 [DG-82] ROI 测量必须先埋点再评分 — 无数据 = 无测量 ≠ 无价值 (@LuangSir)

@2026-05-17 hits:1
触发条件：39/44 个 hook 不写 flywheel.log → intercept_count 全为 0 → ROI 虚低 → 去留建议错误
正确行为：量化体系上线前必须先确保数据采集覆盖所有被评估对象。未埋点组件的 intercept_count 应标注「数据缺失」而非「0 次拦截」
证据：Oracle C1 发现: flywheel 测量偏差使 39 个 hook 的 ROI 系统性偏低 — 这不是性能差，是没测量

### 🐶 [DG-83] 反模式框架应从历史事故反向校验覆盖率 — 而非凭感觉写规则 (@LuangSir)

@2026-05-17 hits:1
触发条件：新增反模式类别前，先盘点全部历史 DG/ED/DF 事故，按事故类型聚类，识别未被现有框架覆盖的模式簇
正确行为：任何文档框架升级必须先做覆盖率审计：列出全部历史事故 → 映射到现有类别 → 识别零覆盖的事故簇 → 为每个簇新增类别 → 验证覆盖率提升幅度。不凭直觉加规则，用历史数据驱动
证据：anti-patterns.md 变更前 16 条子模式仅 ~6 条命中历史事故，新增 7 条精确对齐 20 次独立事故，覆盖率跃升至 ~87%

### 🐶 [DG-84] 文档框架升级必须评估「可物化性」— 区分可 hook 化和设计流程问题 (@LuangSir)

@2026-05-17 hits:1
触发条件：新增反模式/规则后未评估能否被自动检测拦截
正确行为：每条新规则附加「可物化性」评级。可直接 hook 拦截（如 I1 零命中告警、J2 bash -n 验证、L1 pipefail）→ 优先实现；属于设计流程问题（如 I2 软约束、K2 审查衰减）→ 标记为流程约束，不投入 hook 化资源。资源永远先投向可自动检测的项
证据：4/7 新子模式可被现有 hook 部分覆盖（posttool-bash-audit 覆盖 I1/J2/L1，posttool-subagent-audit 覆盖 K1），I2/K2 标记为设计流程问题

### 🐶 [DG-85] 新增反模式类别必须附带狗粮证据链 — 每条子模式追溯具体 DG/ED/DF 编号 (@LuangSir)

@2026-05-17 hits:1
触发条件：写反模式描述时用模糊语言（「源自 7+ 次独立事故」）但未列出具体编号
正确行为：每条新反模式子模式的「狗粮证据」字段必须列出具体 DG/ED/DF 编号，不可用「多次事故」「多次触发」等模糊表述。证据链让后来者可以追溯原始事故，判断该反模式是否仍然活跃
证据：I1 证据链: ED-01/DG-25/DG-30/DG-74/DG-82；I2: DG-09/DG-47/DG-62/DG-58；J1: DG-33/DF-04/DG-68/DG-80；J2: DG-80；K1: DG-44/DG-63/DG-61/DG-67；K2: DG-61/DG-64/DG-67；L1: DG-36/DG-54/DG-60/DG-32

### 🐶 [DG-007] JSON 修复用 roundtrip 而非 raw text replace —— 多层转义陷阱 (@lucas.liang)

@2026-05-17 hits:1
触发条件：当 jsonl/json 文件中存在需要修改的字面文本时
正确行为：不要用字符串替换操作修改 JSON 文件内容。正确做法：parse JSON → 递归修改 decoded Python 对象中的字符串值 → json.dumps 重新序列化。JSON 中 `\\uD800`（valid escaped）和 `\uD800`（invalid escape）在原始字节层面有不同数量的反斜杠，raw text replace 容易只替换部分导致残留
证据：修复 lone surrogate API 400 错误时，raw text replace 在 transcript 遗留 13 处未替换，改用 JSON roundtrip 后一次清除

### 🐶 [DG-008] 跨 session bug 需追踪 hook 注入链 —— error-signals 是隐藏传播源 (@lucas.liang)

@2026-05-17 hits:1
触发条件：bug 在新 session/终端中反复出现时
正确行为：不仅检查当前 session 的 jsonl，还要检查：(1) `.omc/state/error-signals.jsonl` — hook 注入的 `<system-reminder>` 源 (2) `~/.claude/transcripts/*.jsonl` — OpenCode session transcript (3) 子 agent 的 `subagents/` 目录 (4) 任何 hook 脚本引用并注入的文件
证据：修复了当前 session 后 bug 仍复发，追踪到 error-signals.jsonl (6 处) 和 transcript (66 处) 后彻底解决

### 🐶 [DG-009] AI 诊断输出会自指复现 bug —— 避免在诊断文本中引用 bug 模式 (@lucas.liang)

@2026-05-17 hits:1
触发条件：AI assistant 在诊断问题时，回复中包含与 bug 模式相同的字面文本
正确行为：诊断时避免在回复中直接包含触发 bug 的字面文本。使用替代表示法（如 `U+D800` 代替 `\uD800`，`&lt;` 代替 `<` 等），防止"解释 bug → 回复中包含 bug 模式 → 下轮请求触发同一个 bug"的自指循环
证据：assistant 回复"孤立的 `\uD800` 这类东西" → 该回复被序列化到下一轮 API 请求 → 触发同一个 lone surrogate 错误

### 🐶 [DG-86] Oracle 超时必须有降级协议 — 不能直接跳自检代替裁决 (@LuangSir)

@2026-05-17 hits:1
触发条件：Oracle agent 超时/失败未返回裁决时，AI 直接用自检代替 Oracle 裁决
正确行为：Oracle 超时/失败 → 不直接自检代替 → 触发 Meta-Oracle 终审（G3 路径）→ Meta-Oracle 裁决为最终裁决。DG-67 要求机制变更必须 Oracle+Meta-Oracle 双签，自检不是 Oracle 的合法替代品
证据：本次 Oracle agent 超时后直接自检，违反 DG-67 双签要求，需补 Meta-Oracle 终审纠正

### 🐶 [DG-87] Meta-Oracle agent 执行路径需要 API bug fallback — 手动方法论降级路径 (@LuangSir)

@2026-05-17 hits:1
触发条件：Meta-Oracle agent 因 API 级错误（lone surrogate / context overflow 等）无法完成时
正确行为：Meta-Oracle agent 失败 → 不放弃终审 → 降级为手动执行 Meta-Oracle 运行时方法论：(1) 独立逐项验证而非依赖 agent 上下文 (2) 运行时验证 > 静态检查 (3) 对抗性审查 > 合规检查 (4) 裁决留痕到 meta-oracle-verdicts.md
证据：Meta-Oracle agent 遭遇 lone surrogate API 400 错误（DG-007 同类），agent 上下文过大导致 JSON 序列化失败。手动执行方法论完成 ADVISORY 裁决（C/E/G 加权 7.62/10）

---

### [2026-05-17] 用户纠正: 不对
@2026-05-17 hits:1
**触发场景**：检测到纠正信号「不对」（你错了，这个不对）
**问题**：（待本对话补充具体纠正内容）
**纠正**：（AI 完成任务前应引用此记录并补充根因分析）

