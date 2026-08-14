<thinking>
I need to provide my independent security and governance review of this design proposal, then identify what information sources are missing to complete a thorough assessment. I should be careful to only cite evidence I actually have from the chunks provided, rather than inventing details or line numbers. 我需要用中文继续分析这个治理风险。headless 检测通过环境变量实现意味着 AI 助手可以自己设置 CARROROS_FORCE_HEADLESS 来绕过限制——这是典型的自我豁免反模式，而代码中已有 env.pop() 的先例说明项目认识到了这个威胁。isatty 判定在 hook 场景中也不可靠，因为 stdin 是 JSON 管道永远不是 TTY，所以这个信号恒为真。

这意味着交互模式会被误判为 headless，导致全局降级生效——这是致命的设计缺陷。关于 240 秒超时的根因，文档归咎于 hook 进程和审计 IO，但缺少分项计时证据；7.8MB 的审计日志本身写入极快，真正的瓶颈更可能来自 hook 注入的 additionalContext 导致模型上下文膨胀，进而拖累 token 生成速度。

更关键的是，headless 环境下 AskUserQuestion 无法交互，agent 可能陷入死循环重试直到超时——这才是 task-A-citation 和 task-B-scope exit 124 的真实根因。这个假设是可验证的，如果成立，整个「跳过 gate + 降低审计」的方案就完全偏离了问题所在。最重要的是先测量再动刀，而不是基于错误的根因假设去优化。

降低审计频率会破坏验证环和 hook-evidence 的完整链，使得无法证明 gate 真的执行过，这样「证据门禁」就自我废除了。验证的优先级应该高于性能优化，用低优先级的收益去换高优先级的保障是本末倒置。

contract 的 missing_gate 警告问题前面已经指出过，但如果要靠 contract 来保障降级后仍然满足强制 gate 的要求，而 contract 本身只是 WARN 级别，那这个保障就不存在了。

对于前一份单进程 runpy 的方案，我作为委员会成员需要给出独立的评价，而不是被动认可。

runpy.run_path 在同进程执行 hook 会带来真实的风险：全局状态污染、os._exit() 可能杀掉 launcher 进程、子 hook crash 后 launcher 的进程状态不够干净。即使省掉一次 Python 解释器启动能节省 100-250ms，在 240 秒的总预算里占比还不到 0.2%，收益量级远小于引入的问题。

所以这个改动作为低风险的第一阶段是合理的，但不应该期待它能解决超时问题。

更彻底的方案是去掉 launcher 这一层让 settings.json 直接调 hook.py，但那样会丢掉 crash-safe fail-open 的保障，所以保留 launcher 才是对的。真正应该做的第一步是测量而不是改代码——利用现有 hook-evidence.jsonl 的时间戳来分析性能瓶颈，这样既不新增机制也能获得关键数据。

现在需要明确列出缺少的信息，给出具体可执行的命令让用户去收集：查看 hook-evidence.jsonl 和 audit 日志的 schema 与时间戳字段来计算 hook 链的真实耗时占比，以及 index13.md §7.2 中的原始 A/B 测试记录。

特别要看那两个 exit 124 任务的最后 50 条事件，判断是否陷入了 AskUserQuestion 的死循环。还需要 settings.json 中完整的 hooks 配置段（目前只有片段），用命令统计每个 matcher 的 command 数量来确定真实的进程数。此外需要 pretool-gate.py 的完整 L1_GATES 和 GATES 定义及其调用顺序、helpers.py 中关键函数的完整实现（特别是是否有 fsync/flush 操作），以及 gate-contract.yaml 的全文内容。

还要确认 kernel.md 中的冻结规则原文、.omc/state 目录的大小和磁盘类型（SSD 还是网络同步目录），用基准测试量化 Python 启动开销，检查是否存在在 A/B 测试期间生效的 goal 模式或 bypass 状态文件，最后确认 claude -p 的完整命令行参数来判断 240s 是超时还是 turn 耗尽。

另外还要在交互模式下测试 stdin 是否为 TTY 来验证 isatty 方案。

还有个安全问题需要重申：ANTHROPIC_AUTH_TOKEN 看起来已经泄露了（chunk 显示的 sk-fe2481... 看起来像真的 DeepSeek key），这需要人类立即轮换。我现在还在信息采集阶段，没有约束，所以应该输出关键决策点、缺失信息清单，以及拿到这些信息后我会给出什么。

关于行号的问题，我拿到的是分块检索片段而不是带行号的完整文本，所以应该诚实说明这一点，并提供 grep -n 命令让用户回填行号。前面方案里的行号可能需要复核，但我会中性地指出这一点，不伪造证据。

对于 A 点（env 开关自我豁免）的证据，launcher 里的 `env.pop("NIGHT_DENY_ROOT", None)` 这段代码在 diff 上下文中出现过，这使得它相对可信。

我可以引用它，但需要标注这部分需要复核。

设计三个关键的可证伪实验来决定方案方向：交互模式下实测 isatty 的行为、用审计时间戳计算 hook 链的占比、检查 exit 124 的 transcript 尾部是否有 AskUserQuestion 调用。

关于审计日志的性能影响，每天 56604 行意味着若有 1000 次工具调用就是每次 56 行，每行约 145 字节共 8KB，append 写入这个量级大约需要 0.1ms（不考虑 fsync）。

即使每行都 fsync，56 次 fsync × 1ms 也只占 240 秒预算的 0.02%，所以「IO 开销是主要来源」这个说法在数量级上站不住脚，除非涉及 fsync 加慢盘的组合。我需要把这个定量反驳算清楚并呈现出来。

现在看进程启动的开销——假设 5 个 Python 进程乘以 2 层架构等于 10 个解释器，每个冷启动加上导入 yaml 等模块大约 30-80ms，累计 500ms 每次工具调用。

如果一个任务调用 100 次工具，那就是 50 秒，这个量级远大于 IO 审计。runpy 方案能省一半到 250ms 每次，最终 25 秒，这在 189.7 秒对比 70.5 秒的 119 秒差额中确实有实质意义。我之前说「小于 0.2%」是错的——那只是单次占比，应该按总调用次数乘以单次节省来算。所以关键缺失信息是：A/B 期间每个任务的工具调用次数。

还要补充 pretool-gate.py 和 helpers.py 的导入树，特别是是否导入 yaml 这类重模块，因为 yaml 的 C 加速与否会影响解释器启动成本。我会用「文件 § 段落」加 grep 命令来定位，避免声称精确行号。最后要分优先级：拿到前 4 项信息就能出裁决，5-12 项影响方案细节。还有个治理角度的问题：降级矩阵本身创造了双治理语义，同一仓库在两种模式下有两套规则，这违反了路径唯一性。

攻击者只要让系统相信自己在 headless 模式，就能获得弱治理——这是结构性问题，不是实现 bug。真正的修复不是让检测更可靠，而是不要有两套规则。正确的轻量化应该是让同一套 gate 变快，通过进程合并、import 惰性化、审计批量 flush 但不丢行，而不是减少 gate 本身。批量 flush 是安全的，因为 hook 进程生命周期短，进程退出前 flush 就能零证据损失，这才是「快而不减治理」的正解。…
</thinking>

收到，7 份文件我都拿到了（是检索分块，不是带行号全文——这一点会影响证据格式，见文末）。

先给结论，再给我缺的信息。

## 一、我的裁决（安全/治理视角）

**否决 Design Doc 13 的核心架构，不是否决它的目标。** 问题不在实现细节，在于它选择了「按模式分叉治理」这条路。

### 1. 致命项：`_is_headless()` 创造了双治理语义，违反「路径唯一」

文档 §2.2 的检测函数有两个独立的结构性缺陷：

**(a) `sys.stdin.isatty()` 恒为 False。** hook 的 stdin 是 Claude Code 灌入的事件 JSON 管道，交互模式下同样不是 TTY。这不是文档 §3.2 写的「误判风险」，而是**默认全局降级**——交互模式会稳定命中 headless 分支。整张降级矩阵会在所有会话生效。

**(b) `CARROROS_FORCE_HEADLESS=1` 是自我豁免开关。** hook 继承 shell 环境，而被治理对象（AI）恰好能执行 Bash。它 `export` 一次，后续所有 hook 都进入弱治理。项目自己已经认识到这个威胁模型——`hook-launcher.py` 里有 `env.pop("NIGHT_DENY_ROOT", None)`，说明「env 可被污染」是已知事实。再引入一个不 pop 的开关，等于把 `governance-bypass` gate 想拦的东西做成官方 API。

更根本的是：**只要存在「两套规则」，攻击面就是「让系统相信自己在弱规则那一侧」。** 把检测做得更可靠不能消除这个攻击面，只能缩小它。正确的轻量化方向是让**同一套 gate 跑得更快**，而不是让 gate 变少。

服务哲学链：`the less,the more`（单一路径）>『增益』（性能）。冲突时性能自动让位。

### 2. 根因归因存疑，方案可能打错靶子

文档 §0.1 把根因定为「spawn 多进程 + 审计 IO」。审计这一半我按它自己的数据算了一下就站不住：

7.8 MB / 56,604 行 ≈ **138 字节/行**。append-only JSONL 无 fsync 时写一行是微秒级；即使每行都 fsync，单次工具调用几十行也就几十毫秒。它不可能是 240s 预算的主要消耗者，除非存在**每行 fsync + 慢盘/网络同步目录**（这需要证据，见缺失项 P0-3）。

进程那一半我认为是真的、且量级可观：每次工具调用 5 个 command × launcher + 子进程 = 10 次解释器冷启动，按 30–80 ms/次约 0.3–0.8 s/工具调用。但**总收益 = 单次节省 × 工具调用次数**，而 A/B 期间的调用次数我没有——这是我最需要的一个数（P0-2）。

还有一个文档完全没考虑的假说，我认为比 IO 更可能解释两个 `exit 124`：

> `helpers.py` 在高风险交互分支注入 `"请使用 AskUserQuestion 与用户交互，提供选项供用户选择。"`。**headless 下 AskUserQuestion 无法应答**。agent 极可能在「被要求提问 → 无法提问 → 重试 → 再被拦」的循环里耗尽 240 s。

这解释了为什么 `task-A-citation` 和 `task-B-scope` 是 124 超时且「只建治理状态文件、未建任务文件」，而不需要 gate 变慢的假设。**如果这个假说成立，跳 gate 和降审计一个字都不解决问题。** 它是可证伪的，代价是读一份 transcript 尾部。

### 3. 审计降频直接废除证据门禁

「headless 下仅 PASS 聚合」意味着 hook-evidence 不再能逐条证明 gate 跑过。CarrorOS 的门禁是建立在证据链上的；证据链一旦按模式稀疏化，`验证` 环就被 `增益` 环换掉了。按哲学链这条自动作废。

但有一个**语义等价的替代**是安全的：hook 进程生命周期极短，可以在进程内缓冲写、退出前统一 flush。行数不减、内容不减、可追溯性不变，只减 syscall 次数。这是「快而不减治理」，和「降频丢行」有本质区别。

### 4. 契约保障不成立

文档 §3.2 用「降级后仍满足强制 gate（测试保障）」缓解风险，但 `gate-contract.yaml` 的 `missing_gate` 是 **WARN**，`helpers.py` 的对应分支记录 `contract_warning` 后返回空。**用一个警告去担保一条安全边界，担保不存在。** 如果要把 contract 当降级的安全网，前置条件是先把它修成 ERROR/fail-closed——那是独立的一件事，不能塞进性能方案里。

### 5. 对「单进程 launcher」前置方案的独立意见

方向我支持（同构提速、不动 gate 集），但有三点必须补，否则它是把 crash 隔离换成了性能：

- `runpy.run_path` 同进程执行后，子 hook 里的 `os._exit()`、`signal` 处理、`atexit` 注册、`sys.path` 污染都会直接作用于 launcher。`SystemExit` 捕获只覆盖了其中一种。
- launcher 一次只跑一个 hook，所以模块缓存污染影响有限——但这个前提必须写进不变式，否则将来合并多 hook 时会静默失效。
- 它的收益上界是「一半的解释器启动成本」。在拿到工具调用次数之前，**没人能说它够不够**。不应把它当作达标手段，只能当作低风险的第一刀。

### 6. 安全事项（不属于性能范畴，但必须先处理）

`settings.json` 的 `ANTHROPIC_AUTH_TOKEN` 是真实格式的 DeepSeek key，且已随文件外发。**请人类立即撤销并轮换**，之后改由进程环境注入、从仓库文件删除该字段。我不会在任何后续文档里复述该值。这是不可逆操作，由人类独占执行。

---

## 二、我缺的信息

按优先级排。P0 决定方案方向，不补齐我不出裁决书；P1 只影响细节。

### P0 — 决定「打哪个靶子」

**P0-1｜两个 `exit 124` 任务的 transcript 尾部。** 用于证伪/证实上面的 AskUserQuestion 死循环假说。我要最后 30–50 条事件，特别是有没有重复的 `blocked` / `ASK_USER` / `additionalContext` 注入。

**P0-2｜A/B 期间每个任务的工具调用次数。** 没有这个数，任何「省 N ms/次」的方案都无法折算成秒。可从审计按 session 统计。

**P0-3｜审计写入的真实成本。** 需要三件事：`_append_audit()` / `_record_gate_decision()` 的完整实现（有没有 fsync、有没有每次 open/close）、`.omc/state` 所在磁盘类型（是否落在 iCloud/OneDrive/网络卷这类同步目录）、以及 audit 与 hook-evidence 的单行 schema（`head -n 3` 即可）。若行内有毫秒时间戳，我能**零代码改动**直接算出 hook 链耗时占比——这是最省事的根因证据。

**P0-4｜交互模式下 hook stdin 是否 TTY 的实测。** 一行输出就能终结 `isatty` 方案的讨论。

### P1 — 决定方案细节

**P1-5｜`settings.json` 的 `hooks` 段全文。** 我只见到 PreToolUse 的第一项；PostToolUse 三项、以及 UserPromptSubmit / SessionStart / Stop 等是否存在、各自 matcher 和 timeout，决定真实进程数与提速上界。

**P1-6｜`pretool-gate.py` 的 `L1_GATES` / `GATES` 完整定义与执行顺序**，以及各 gate 是否有短路。用于确认「9/20」这个数字，以及哪些 gate 是纯计算、哪些碰磁盘。

**P1-7｜`pretool-gate.py` + `helpers.py` 的 import 树。** 是否 import `yaml`（且是否有 C 加速的 `CSafeLoader`）、`re` 大量预编译、或其他重模块。解释器冷启动成本几乎全在这里，这也是「惰性 import」这条零风险优化的可行性判据。

**P1-8｜`gate-contract.yaml` 全文（805 字节，直接贴）。** 我需要原文而非描述，才能给出 WARN→ERROR 的精确改法。

**P1-9｜`kernel.md` 的冻结规则原文。** `.claude/hooks/*` 和 `settings.json` 的授权边界，决定哪些改动需要人类逐条批准。

**P1-10｜`claude -p` 的完整调用命令行。** 240 s 是外部 `timeout` 还是 `--max-turns` 耗尽？`exit 124` 指向前者，但要确认基线是怎么测的。

**P1-11｜A/B 期间 goal 模式 / bypass 状态文件是否生效。** `run-regression.sh` 会在测试前移走这些状态、退出时恢复，说明它们存在且会改变 gate 行为。如果 A/B 时它们是开的，整组数据的可比性存疑。

**P1-12｜Python 版本与解释器启动基线**：`python3 -c pass` 跑 20 次的耗时中位数。用于把 P0-2 折算成秒。

### 一个格式问题

我收到的是检索分块，**没有行号**。所以本文中我引用的是「文件 + 段落/函数」而非 `文件:行号`——我不会为了满足证据格式去编造行号。请施工方在整合时用 `grep -n` 回填行号后再落盘；同理，此前方案里出现的具体行号（如 `pretool-gate.py:45-78`、`settings.json:19-42`）也建议一并复核，它们可能来自同样缺行号的上下文。

---

拿到 P0 四项，我出符合六段式的裁决书；我的预设结论方向是：**不做 headless 检测，不做降级矩阵，改为「同构提速三件套」——单进程 launcher + 惰性 import + 缓冲写退出前 flush（零丢行）**，并把 contract 的 WARN→fail-closed 作为独立前置项。但如果 P0-1 证实是 AskUserQuestion 死循环，那么正确的修复是让高风险分支在无法交互时走确定性的 BLOCK 而非无限重试——那和性能优化是完全不同的一份方案。