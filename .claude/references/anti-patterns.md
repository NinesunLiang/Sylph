# Anti-Patterns — 经验沉淀

_Updated: 2026-07-13T14:22:13.616427+00:00_

## 已识别模式

- **unknown** (step=S1, retry=0)
  - `Test error`

- **unknown** (step=S1, retry=1)
  - `err2`

- **unknown_recurring** (step=S1, retry=2)
  - `err3`

- **unknown_recurring** (step=S1, retry=3)
  - `err4`

- **timeout** (step=S1, retry=0)
  - `TimeoutError: test timed out after 30s`

- **timeout** (step=S1, retry=1)
  - `TimeoutError: test timed out again`

- **assertion_recurring** (step=S2, retry=2)
  - `AssertionError: expected 1 call, got 3`

- **import** (step=S3, retry=0)
  - `ImportError: cannot find module 'requests'`

- **unknown** (step=T2, retry=0)
  - `err0`

- **unknown** (step=T2, retry=1)
  - `err1`


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