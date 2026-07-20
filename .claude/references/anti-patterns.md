# Anti-Patterns — 经验沉淀

_Updated: 2026-07-14T16:20:56.799910+00:00_

## 已识别模式

- **assertion_recurring** (step=RPE-C-S1, retry=2)
  - `RPE-C controlled recurring path expectation failure: expected .omc/scripts but observed stale .claude/scripts path; atte`


## 历史记录

方案只做一次就提交。
→ against: 至少 5 轮迭代再定稿。

## E. 闭环失败（Loop Failure）

### E1 不回查
做完了不回去验证。
→ against: smok-test + audit-hooks 全绿才提交。

### E2 不记录失败
犯错后不写 claude-next.md。
→ against: 每次失败立即写 DG-xxx 条目。

### E3 不升华
重复犯相同错误。
→ against: 知识升华管道，≥20条或年龄≥10天或hits≥5进入升华候选。

### E4 编译盲修
编译不过但盲目重试不改代码。
→ against: 先读编译错误，分析具体问题再改。

## F. 工具误用（Tool Misuse）

### F1 用 shell 读文件
用 cat/grep 代替 read_file。
→ against: 用 read_file 读，patch 写，search_files 搜。

### F2 硬编码路径
在代码中写死绝对路径。
→ against: 使用 PROJECT_ROOT 环境变量或相对路径。

## G. 继承失效（Inheritance Breakage）

### G1 忽略 AGENTS.md
不读治理文档直接执行。
→ against: 每次会话开头加载 AGENTS.md。

### G2 不继承上下文
新会话不读交接文件。
→ against: 每次启动读 session-handoff.md。

## H. 安全忽视（Security Neglect）

### H1 泄露密钥
敲明文 token/密码。
→ against: 隐私防线 hook 阻断。

### H2 未授权操作
没经确认就执行删除/发布。
→ against: permission-gate + 三次确认。
### unknown（飞轮升华 2026-07-20）
- 来源：claude-next 自动升华，hits=155（阈值≥5）
- 触发条件：error-dna 中反复出现的 `unknown` 失败模式
- 正确行为：见 .omc/knowledge/claude-next.md 相关条目；晋升 kernel.md 需人类裁决

### unknown_recurring（飞轮升华 2026-07-20）
- 来源：claude-next 自动升华，hits=124（阈值≥5）
- 触发条件：error-dna 中反复出现的 `unknown_recurring` 失败模式
- 正确行为：见 .omc/knowledge/claude-next.md 相关条目；晋升 kernel.md 需人类裁决

### timeout（飞轮升华 2026-07-20）
- 来源：claude-next 自动升华，hits=16（阈值≥5）
- 触发条件：error-dna 中反复出现的 `timeout` 失败模式
- 正确行为：见 .omc/knowledge/claude-next.md 相关条目；晋升 kernel.md 需人类裁决
