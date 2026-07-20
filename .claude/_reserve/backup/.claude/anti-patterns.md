# AI 治理反模式手册

> 审阅: 2026-05-26 — A~H 8 类 18 种反模式
> 更新: AI 审核+CarrorOS hooks自动阻断

## A. 虚假完成（Hallucinated Completion）

### A1 软完成语
用"理论上可以了"代替硬证据。
→ against: 禁止软完成语，必须有 VERIFIED 证据。

### A2 跳过步骤
自认为"做完"但没编译/验收。
→ against: 5 步完成清单，每步确认。

### A3 镜像骗分
把推测输出当事实。
→ against: 断言必须 file:line 或命令输出。

## B. 范围偏移（Scope Creep）

### B1 一步做多件事
一次改动多个无关区域。
→ against: 范围冻结，一次一 Step。

### B2 越界修改
在修复任务中改不相关代码。
→ against: 核对范围声明后再改动。

### B3 修改后不回溯
改完 A 忘记检查 B 是否受影响。
→ against: 写 blast-radius 注释，改后全量回归。

## C. 上下文滥用（Context Abuse）

### C1 过度加载
一次注入数万 token 的无关上下文。
→ against: AGENTS.compact.md + 渐进披露。

### C2 记忆滥用
把任务进度存在 memory 中。
→ against: session-handoff.md + session_search。

### C3 不验证断言
口头说"应该没问题"却无证据。
→ against: 断言必须文件路径 + 输出验证。

## D. 设计缺失（Design Deficit）

### D1 无方案直接开干
跳过架构设计直接写代码。
→ against: L3+ 任务必须有 PRD/Oracle 审核。

### D2 不验收就交
"做完了"但实际没测。
→ against: 证据门禁 + 验收清单。

### D3 不迭代直接终版
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
