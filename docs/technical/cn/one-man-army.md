# ⚔️ Carror OS 核心架构深度解析：一人成军 (One-Man Army)

> **版本归属**：v6.1.8（v6.1.5 首发）
> **核心理念**：用文本文件（Markdown）承载系统状态；用文件系统锁（File Mutex）协调 AI 并发。
> **实现状态**：⚠️ 核心锁原语已实现(`oma_lock_manager.py`)，但生产级生命周期增强待完成。已知问题：`posttool-write-lock.sh` 嵌入式换行符 Bug 导致 `release_lock()` 永不被调用 → 孤儿锁；`acquire_lock()` TOCTOU 竞争条件；60s 超时对于复杂任务过短。上述问题将在 RPE-014 中统一修复。

“一人成军 (One-Man Army, OMA)” 是 Carror OS 为协调多终端 AI 并发而设计的**去中心化架构**。它通过 `/lx-oma` 指令将宏大需求（Master PRD）降维拆解为互相隔离的子模块目录（`rpe/feat-X/`），允许开发者同时开启多个终端，并发运行各自的 `/lx-rpe` 流水线。
以下是关于并发冲突与状态管理的核心架构 Q\&A：

---

## ❓ Q1：100% 正交的 Feature 真的存在吗？如果两个 Feature 并发修改同一个基础函数导致逻辑 Bug，怎么防？

**结论：在真实的业务屎山里，完美的正交（MECE）是不存在的。两个 Feature 并发修改同一个基础文件（如 `utils.go` 或 `user_model.ts`）是必然事件。**
Carror OS 的微内核并发锁（`oma_lock_manager.py`）**只解决了“物理写冲突”**（防止两个进程同时往一个文件写字节导致文件乱码损坏），但它解决不了“语义逻辑冲突”（如 Feature A 删除了某个字段，Feature B 还在尝试调用）。
为此，Carror OS 设计了**四大纵深防御网（Defense in Depth）**来防止“撞车”：

### 🛡️ 第一道防线：降维拆解的“拓扑排序” (Topological Split)在 `/lx-oma` 的大脑设计中，不仅是横向切分（API / UI / DB），更强迫 AI 提取出一个 **`feat-00-core`（核心基座）**。拆解报告会明确提示开发者：“**请先单独运行 `/lx-rpe feat-00-core`**，完成数据库表结构和公共 Utility 的奠基。完成后，再**同时并发**运行 `feat-auth`、`feat-payment`。”通过时序依赖，在物理层面隔离掉 80% 最危险的底层修改冲突。

### 🛡️ 第二道防线：编辑工具的“天然免疫力” (Stale Context Rejection)如果 Feature B 等了 3 分钟才拿到 `main.go` 的物理锁，此时 `main.go` 已经被 Feature A 改得面目全非了怎么办？**大模型的 `Edit/Replace` 工具是天然防呆的。** 它在修改前必须匹配具体的代码片段上下文（`oldString`）。如果 Feature A 改了这段代码，Feature B 在拿到锁执行替换时，底层会直接抛出错误：`Error: target string not found`。大模型收到报错后，会**被迫重新 `Read` 这个文件**，从而刷新它脑子里的上下文！这是一种”因祸得福”。

### 🛡️ 第三道防线：编译与测试门禁 (Build-Validator Gate)退一万步说，就算两者都修改成功了，但逻辑上出现了不兼容的 Bug（如接口缺字段）。此时 Carror OS 的 `build-validator`（构建验证器）和 `completion-gate`（证据门禁）会拔出屠刀。只要 `go build` 或 `npm test` 报错，大模型就**无法标记自己为 DONE**，它会被困在当前 Step，乖乖把编译错误修好为止。

### 🛡️ 第四道防线：A→B→A 交叉验证强校验在代码 `git commit` 提交前，`subagent_reviewer` 会拉起一个全新上下文的验证官（Sub-agent）。它会站在全局视角审视这两个 Feature 拼合后的全量 Diff 代码，任何因并发导致的未闭环逻辑，都会被它毫不留情地打回重做。

---

## ❓ Q2：一人成军架构是否符合 Carror OS 的核心理念？是否真正做到了“以文档为状态机”？

**结论：这符合 Carror OS “先守护，后武装 (Guard First, Arm Later)” 与 “少即是多 (The Less, The More)” 哲学。**
它契合了**”以文档为状态机 (Document as State Machine)”**的设计：

### 1. 解耦与去中心化 (Decentralization)在传统的 Multi-Agent 框架（如 AutoGen、CrewAI）中，必须有一个中心化的 Python Manager 进程在后台跑着，盯住所有 Agent 的状态。一旦主进程崩溃或 OOM，所有 Agent 全军覆没。**但在“一人成军 (OMA)”架构中，没有中心大脑！** `/lx-oma` 只是一个无情的脚手架工人。它生成了 `rpe/feat-1/executor.md`、`rpe/feat-2/executor.md` 之后，就挥一挥衣袖下班了。所有的终端各自为战，互不干涉。

### 2. 真正的“文档即状态” (Document as State Machine)你开启 5 个终端，分别运行 `/lx-rpe feat-1` 到 `feat-5`。它们各自的 AI 只盯着自己目录下的那个 `executor.md`（进度表）和 `.omc/state/todo-queue.md`。如果某个终端突然断电关闭、或者被 80% Context-Guard 物理熔断了怎么办？**什么进度都不会丢失。** 你只需要重新打开终端，再次输入 `/lx-rpe feat-3`。大模型重新读取 `rpe/feat-3/executor.md`，发现”昨天卡在 Step 3 的 Debug 上”，然后继续。文档，就是状态本身。

### 3. 符合 UNIX 哲学的物理锁 (Primitive Mutex)面对复杂的并发修改，我们没有去安装臃肿的 Redis，也没有写复杂的 RPC 通信服务来实现并发同步。我们仅仅用了一个约 300 行的 `.claude/scripts/oma_lock_manager.py`，利用操作系统内核级原子操作（`os.O_CREAT | os.O_EXCL`）。它像一个简单的机械锁，无论多少个大模型终端来抢占文件，都只是挂起它们再放行。

**用文本文件（Markdown）承载系统状态；用文件系统锁（File Mutex）协调 AI 并发。**
