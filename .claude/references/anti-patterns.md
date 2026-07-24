# Anti-Patterns — 经验沉淀

_Updated: 2026-07-24T12:00:00+00:00_ (sublimation processed: timeout→I1 promoted, unknown→J1 archived, unknown_recurring→J2 archived)

## 已识别模式

- **assertion_recurring** (step=RPE-C-S1, retry=2)
  - `RPE-C controlled recurring path expectation failure: expected .omc/scripts but observed stale .claude/scripts path; atte`


## 历史记录

方案只做一次就提交。
→ against: 至少 5 轮迭代再定稿。 [来源：内部自检，非行业标准]

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

## I. 运行稳定性（Runtime Instability）

### I1 S1 步骤 30 秒超时熔断
在 step S1 中反复出现 `TimeoutError: test timed out after 30s`，累计 16 次（2026-07-12 ~ 07-19），每个 session 至少触发一次。 [来源：.omc/knowledge/claude-next.md 时间戳匹配]
→ 根因推测：S1 在 RPE-C-S1 或通用 S1 步骤中执行了长时间挂起操作，默认 30 秒超时不足。 [来源：.omc/knowledge/claude-next.md timeout 条目时间戳]
→ 解决思路：
   1. 增大 S1 步骤的超时配置（从 30s 提升至 120s 或配置化） [来源：内部自检，非行业标准]
   2. 或拆分 S1 步骤为多个子步骤，单个子步骤不超 30s [来源：内部自检，非行业标准]
   3. 或在 S1 步骤内添加心跳/进度汇报机制以区分"慢"和"死"

## J. 分类缺失（Classification Gap）—— 元模式（Meta-Pattern）

以下模式虽经升华管道检出（hits 远超阈值），但原始错误数据过于泛化，无法提取可复用的具体预防规则。它们的信号本身指向同一个元问题：

### J1 未分类错误膨胀（unknown, hits=155） [来源：.omc/knowledge/sublimation-log.jsonl]
claude-next 中 `unknown` 模式以 "Test error"、"err2" 和 `[Bash] {"stdout": "", "stderr": "command failed", "exit_code": 1}` 三类泛化信息为主，提示 error-dna 分类引擎未覆盖常见的 Bash 失败和测试骨架错误。
→ against: 将 `[Bash] {"stderr": "command failed"}` 映射为具体分类（如 `bash_command_failure`），为每个 error-dna 步骤注册已知失败签名。

### J2 未分类循环膨胀（unknown_recurring, hits=124） [来源：.omc/knowledge/sublimation-log.jsonl]
关联 `unknown` 的循环版本，以 "err3"、"err4" 占位符为主。所有 unclassified 模式一旦未注册，即会在后续 session 中反复以 recurring 形态重现。
→ against: 与 J1 同源解决；J1 修复后此模式自动消失。
