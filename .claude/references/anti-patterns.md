# Anti-Patterns — 经验沉淀

_Updated: 2026-07-27T17:30+00:00 (Phase0-A baseline recovery complete)_

**Phase0-A 状态更新 (2026-07-27)**:
- K1/K2: 已确认在 posttool-claim-audit.py 中实现 (G1_PSEUDO_INTEGRITY + E6_EDIT_REPEAT), 测试 7/7 PASS
- I1 timeout: carros_base.py 已使用动态 timeout (10-300s), 非系统性问题
- J1/J2: posttool-bash-audit 已 disabled, 有 28 项测试 (启用后可直接覆盖 Bash 分类)
- 详见: `.omc/docs/phase0a-baseline.md` / `.omc/docs/phase0a-disabled-hooks.md`

[来源：Phase0-A 真实基线分析，内部自检，非行业标准]

---

## 已识别模式

- **assertion_recurring** (step=RPE-C-S1, retry=2)
  - `RPE-C controlled recurring path expectation failure: expected .omc/scripts but observed stale .claude/scripts path; attempt to reload`

---

## 历史记录

方案只做一次就提交。
→ against: 至少 5 轮迭代再定稿。 [来源：内部自检，非行业标准]

---

## E. 闭环失败（Loop Failure）

### E1 不回查
做完了不回去验证。
→ against: smok-test + audit-hooks 全绿才提交。

### E2 不记录失败
犯错后不写 claude-next.md。
→ against: 每次失败立即写 DG-xxx 条目。

### E3 不升华
重复犯相同错误。
→ against: 知识升华管道，≥20条或年龄≥10天或hits≥5进入升华候选。 [来源：.omc/knowledge/index.md 升华规则]

### E4 编译盲修
编译不过但盲目重试不改代码。
→ against: 先读编译错误，分析具体问题再改。

---

## F. 工具误用（Tool Misuse）

### F1 用 shell 读文件
用 cat/grep 代替 read_file。
→ against: 用 read_file 读，patch 写，search_files 搜。

### F2 硬编码路径
在代码中写死绝对路径。
→ against: 使用 PROJECT_ROOT 环境变量或相对路径。

---

## G. 继承失效（Inheritance Breakage）

### G1 忽略 AGENTS.md
不读治理文档直接执行。
→ against: 每次会话开头加载 AGENTS.md。

### G2 不继承上下文
新会话不读交接文件。
→ against: 每次启动读 session-handoff.md。

---

## H. 安全忽视（Security Neglect）

### H1 泄露密钥
敲明文 token/密码。
→ against: 隐私防线 hook 阻断。

### H2 未授权操作
没经确认就执行删除/发布。
→ against: permission-gate + 三次确认。

---

## I. 运行稳定性（Runtime Instability）

### I1 S1 步骤 30 秒超时熔断
在 step S1 中反复出现 `TimeoutError: test timed out after 30s`，累计 16 次（2026-07-12 ~ 07-19），每个 session 至少触发一次。 [来源：.omc/knowledge/claude-next.md 时间戳匹配]
→ 根因推测：S1 在 RPE-C-S1 或通用 S1 步骤中执行了长时间挂起操作，默认 30 秒超时不足。 [来源：.omc/knowledge/claude-next.md timeout 条目时间戳]
→ 解决思路：
   1. 增大 S1 步骤的超时配置（从 30s 提升至 120s 或配置化） [来源：内部自检，非行业标准]
   2. 或拆分 S1 步骤为多个子步骤，单个子步骤不超 30s [来源：内部自检，非行业标准]
   3. 或添加心跳/进度汇报机制以区分"慢"和"死"

---

## J. 分类缺失（Classification Gap）

以下模式虽经升华管道检出（hits 远超阈值），但原始错误数据过于泛化，无法提取可复用的具体预防规则。

### J1 未分类错误膨胀（unknown, hits=155） [来源：.omc/knowledge/sublimation-log.jsonl]
claude-next 中 `unknown` 模式以 "Test error"、"err2" 和 `[Bash] {"stdout": "", "stderr": "command failed", "exit_code": 1}` 三类泛化信息为主，提示 error-dna 分类引擎未覆盖常见的 Bash 失败和测试骨架错误。
→ against: 将 `[Bash] {"stderr": "command failed"}` 映射为具体分类（如 `bash_command_failure`），为每个 error-dna 步骤注册已知失败签名。

### J2 未分类循环膨胀（unknown_recurring, hits=124） [来源：.omc/knowledge/sublimation-log.jsonl]
关联 `unknown` 的循环版本，以 "err3"、"err4" 占位符为主。所有 unclassified 模式一旦未注册，即会在后续 session 中反复以 recurring 形态重现。
→ against: 与 J1 同源解决；J1 修复后此模式自动消失。

---

## K. 虚假数值断言（Pseudo-Integrity）

### K1 G1_PSEUDO_INTEGRITY：断言无来源
**描述**：AI 输出中包含未标注来源的数值断言（如"30个stale worktree"、"108KB噪声"、"14条软完成语"），违反铁律#1。本模式在本 session 中**触发最频繁**，覆盖 executor.md 和 anti-patterns.md 的多次 Edit/Write。
**检测信号**：`⚠️ G1_PSEUDO_INTEGRITY: 数值断言(N 条)无来源` 出现在 PostToolUse hook 输出中。
**首次发现**：2026-07-27 CarrorOS 独立评分会话，executor.md 初始 Write 时触发 [来源：本会话首轮 PostToolUse hook 告警，内部自检，非行业标准]
**对比「数值来源映射表」（mate-oracle-evaluation-20260724.md:12-28）**：该表预定义了 24 条映射规则。但本 session 的多次触发说明执行级仍会遗漏；规则存在但 AI 执行时不自检。
**触发条件**：AI Edit/Write 中包含无 `[来源:file:line]` 或 `[内部自检，非行业标准]` 标注的任意数值。
**→ against**：所有数值断言（文件大小/行数/条目数/得分）必须带来源标注。无法提供确切来源时标注 `[内部自检，非行业标准]` 并附推算依据。本规则应当在输出前自检阶段（evidence_gate）执行，而非被动等待 hook 事后抓。
**严重度**：high。直接违反铁律#1，且本 session hook 证明了这是最常触发的违规类型。

### K2 E6_SELF_CONTRADICTION：编辑未收敛
**描述**：同一文件在短期内被连续 Edit 多次导致签名不一致——代表 AI 边写边改、方向摇摆，而非一次定稿。本 session 中 executor.md 被 Edit 约 20+ 次、anti-patterns.md 被 Edit 4 次后才被本机制纠正为 Write 收敛。
**检测信号**：`⚠️ E6_SELF_CONTRADICTION: [E6] EDIT_REPEAT: …编辑 N 次，N 个签名，可能未收敛`。
**首次发现**：2026-07-27 CarrorOS 独立评分会话，executor.md 按行修补导致 9+ 签名 [来源：本会话 PostToolUse hook E6_EDIT_REPEAT 实时告警，内部自检，非行业标准]
**触发条件**：同一文件被 Edit 工具连续修改 >=3 次且签名数 >= 编辑次数。
**→ against**：复杂内容（含数值/多段评估/结构化表格）优先用 Write 一次写出，避免逐行 Edit 修补。Edit 仅用于精确的单句修正。检测到 E6_EDIT_REPEAT 告警后应立即将剩余编辑转换为一次 Write。
**严重度**：medium。不会造成逻辑错误，但产生过多 hook 检查和审计噪声，延长 session 耗时。

### K3 E6_CONTENT_FLIP：前后内容方向摇摆
**描述**：同一文件最近 3 次编辑的 hash 各不相同，且编辑方向不一致——先写 A 内容，然后改成 B，再改回 A。表明 AI 在内容方案之间反复，而非渐进式改进。
**检测信号**：`⚠️ E6_SELF_CONTRADICTION: [E6] CONTENT_FLIP: …最近3次编辑hash均不同，方向摇摆`。
**首次发现**：2026-07-27 CarrorOS 独立评分会话，anti-patterns.md 和 executor.md 均触发 [来源：本会话 PostToolUse hook E6_CONTENT_FLIP 实时告警，内部自检，非行业标准]
**触发条件**：同一文件 Edit >= 3 次且最新 3 次 hash 二进制内容不一致（非单纯签名差异）。
**与 K2 的边界**：
  - K2（EDIT_REPEAT）：聚焦编辑**次数**超标 → 应该用 Write 代替 Edit
  - K3（CONTENT_FLIP）：聚焦编辑**方向**摇摆 → 写之前应该先在别处打好草稿
→ against: 在做出重大方向变更前，先在草稿文件或 executor.md 中收敛方案，再 Edit 目标文件。编辑决策链：读完现状 → 决定方向 → 一次性 Write 成文。

---

## Meta: 本文件本身的写入方式就是 K2/K3 的活案例

本文件（anti-patterns.md）在本 session 开始时由 2 次 Edit 添加 K1/K2（触发了一次 E6_EDIT_REPEAT），然后改为 Write 整篇重构——这本身就是 K2 的修复演示：检测到告警 → 转换为 Write 收敛。
