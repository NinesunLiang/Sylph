# Web Research — Immature Features (Oracle Round 2 Prep)

> 生成日期：2026-05-04
> 用途：为 3 项不成熟特性提供 3+ 候选方案，供 Oracle Round 2 独立评审

---

## 1. Error DNA — 跨会话错误记忆

### 问题
error-dna.sh 4 bug 完全不可用。需跨会话错误持久化、去重聚合、会话注入。

### 候选方案 A：Beads 模式（Git-versioned JSONL + SQLite）
- **参考工具**：[Steve Yegge's Beads](https://github.com/steveyegge/beads) — Git-friendly issue tracker for AI agents
- **核心思路**：error-dna.jsonl（追加日志）+ error-dna.db（SQLite 去重聚合），两者都 git-versioned
- **优势**：SQLite 单文件去重查询极快，git diff 可追踪错误演变
- **劣势**：依赖 sqlite3 CLI（需预装），比纯文件方案重
- **适用**：已有 SQLite 环境的项目

### 候选方案 B：Recall MCP 模式（纯 Bash + curl + Redis）
- **参考工具**：[Recall MCP](https://www.libhunt.com/posts/1483767-show-hn-recall-persistent-memory-for-claude-code-via-mcp-hooks) — MCP memory server
- **核心思路**：hooks 纯 bash + curl 向 MCP 服务发送错误记录，Redis 持久化，支持语义搜索
- **优势**：跨团队共享错误记忆，AES-256 加密，语义搜索可关联相似错误
- **劣势**：需要运行 MCP 服务进程，增加了系统复杂度
- **适用**：团队协作环境，需要跨会话错误语义搜索

### 候选方案 C：Sentinel File + JSONL Dual Format（轻量方案）
- **参考工具**：Crosslink sentinel-file 模式 + Fleet-Commander 三层日志
- **核心思路**：纯文件系统方案
  - `.omc/state/error-dna.jsonl` — 追加日志（APPEND-ONLY）
  - `.omc/state/error-dna.json` — 合并状态（去重聚合）
  - `.omc/state/.error-dna-sentinel` — 哨兵文件（防重复注入快速检查）
- **优势**：零依赖，纯 Bash + Python 实现，~45 行核心逻辑
- **劣势**：无语义搜索，无跨团队共享
- **适用**：单机 CLI 工具场景（Carror OS 当前形态）

### 方案比对

| 维度 | A: Beads | B: Recall MCP | C: Sentinel (推荐) |
|------|---------|---------------|-------------------|
| 依赖 | sqlite3 CLI | Redis + MCP server | 零依赖 |
| 去重能力 | SQL 聚合强 | 语义搜索强 | JSON merge 中等 |
| 跨会话 | git-versioned | Redis 持久化 | 文件持久化 |
| 实现复杂度 | 中 | 高 | **低** |
| 团队共享 | git push | MCP 网络 | git push |

---

## 2. Loading Benchmark — 渐进式披露 Token 测量

### 问题
L1 声称 ~120 行实际 251 行；19,280/75% 数字完全虚假。需要真实 token 测量方法论。

### 候选方案 A：cc-healthcheck 模式（零依赖 Python）
- **参考工具**：[cc-healthcheck by Genie-J](https://github.com/Genie-J/cc-healthcheck) — 单文件 Python，零依赖
- **核心思路**：读 .claude/ 目录、hooks 列表、session 快照，输出 token 预算使用率
- **测量方式**：`chars / 4` 启发式估算 + 按文件类型加权（JSON ×2, prose ×1）
- **精度**：~80-85%（代码），~95%（自然语言）
- **优势**：零依赖，无需安装 tokenizer 包
- **劣势**：启发式而非真实 token 化，不适合需要精确数字的场景

### 候选方案 B：Scopeon 模式（tiktoken 真实 Token 化 + 缓存 ROI）
- **参考工具**：[Scopeon by sorunokoe](https://github.com/sorunokoe/Scopeon) — Rust 实现，缓存命中率分析
- **核心思路**：使用 tiktoken cl100k_base encoding 真实 token 化，按 turn 分解 token 消耗，计算缓存 ROI（重复加载文件的 token 节省）
- **测量方式**：`scripts/loading_benchmark.py` + `tiktoken` 包
- **精度**：~95%（真实 tokenizer，接近 API 实际值）
- **优势**：真实 token 数，可计算缓存 ROI
- **劣势**：需要 pip install tiktoken，多一层依赖
- **输出**：
  ```
  L1: X tokens (Y on-disk lines, Z effective with session-init)
  L2: A tokens, L3: B tokens
  Full-context: C tokens (n=10)
  Progressive: D tokens (n=10)
  Savings: E tokens/session (95% CI [lower, upper]), F%
  ```

### 候选方案 C：codeprobe 模式（多维度 Benchmark + heatmap）
- **参考工具**：[codeprobe by VOrbis](https://www.npmjs.com/package/codeprobe) — Context Engineering Toolkit
- **核心思路**：多维度 benchmark：context（当前预算）. simulate（模拟多轮对话）. heatmap（热点文件识别）
- **测量方式**：完整 pipeline — 文件扫描 → token 化 → 按 phase 分组 → 热点检测
- **额外维度**：heatmap 识别哪些文件被最高频读取（需优化目标），simulate 预测 N 轮后上下文状态
- **优势**：提供优化优先级（哪些文件最高频最应该精简）
- **劣势**：Node.js 工具链（与 Python 生态分离），需要 npm install

### 方案比对

| 维度 | A: cc-healthcheck | B: Scopeon/tiktoken | C: codeprobe |
|------|------------------|-------------------|-------------|
| 精度 | ~80-85% | **~95%** | ~90% |
| 依赖 | 零 | pip install tiktoken | npm install -g codeprobe |
| 真实 Token 化 | ❌ | ✅ | ✅ |
| 缓存 ROI | ❌ | ✅ | ❌ |
| 热点检测 | ❌ | ❌ | **✅** |
| 实现复杂度 | **低** | 中 | 中 |

---

## 3. OMA Lock — TOCTOU + Heartbeat

### 问题
oma_lock_manager.py:50-52 TOCTOU 竞争条件；60s 超时过短；锁可观测性缺失。

### 候选方案 A：flock 方案（Linux 内核级锁）
- **参考**：[BashFAQ/045](http://mywiki.wooledge.org/BashFAQ/045) — flock 是 shell 锁最佳实践
- **核心思路**：Python 调用 `fcntl.flock(fd, LOCK_EX | LOCK_NB)` 替代 O_EXCL
- **优势**：内核自动释放锁（进程崩溃也不残留），支持超时等待（LOCK_NB + 轮询）
- **劣势**：Linux-only（不跨平台），但 Carror OS 已是 macOS/Linux
- **修改范围**：oma_lock_manager.py acquire_lock() 重构

### 候选方案 B：mkdir + Heartbeat 方案（POSIX 兼容）
- **参考**：POSIX mkdir 原子性 + heartbeat 过期检测
- **核心思路**：
  - `mkdir` 充当锁目录（原子操作）
  - 持有者定期更新锁目录内 `.heartbeat` 文件的时间戳
  - 竞争者检查 `.heartbeat` 时间戳，超时则 `rmdir` 旧锁
- **优势**：POSIX 兼容（macOS + Linux），零依赖，改进 OMA 当前 O_EXCL 模式
- **劣势**：需要 heartbeat 后台线程，比 flock 多一个额外线程
- **修改范围**：oma_lock_manager.py 增加 heartbeat watcher 线程

### 候选方案 C：FIle Descriptor Inheritance + Timeout 方案（当前 O_EXCL 增强）
- **参考**：Electrum btc O_EXCL + Python lockfile 实践
- **核心思路**：保留当前 O_EXCL 模式，增加：
  - 锁文件存储 PID + 时间戳（而非空的）
  - 获取锁前检查 PID 是否存活（`kill -0 $PID`），不存活则回收
  - 超时重试从 60s → 可配置（默认 300s）
  - `.omc/state/locks.json` 锁可观测性仪表盘
- **优势**：对现有代码改动最小，保留 Python 跨平台性
- **劣势**：不解决 SIGKILL 残留（无内核自动释放），但 PID 检查可缓解

### 方案比对

| 维度 | A: flock | B: mkdir+heartbeat | C: O_EXCL+增强(推荐) |
|------|---------|-------------------|-------------------|
| 跨平台 | Linux-only | ✅ POSIX | ✅ Python |
| 内核自动释放 | ✅ | ❌ | ❌ |
| SIGKILL 安全 | ✅ | ❌（heartbeat 缓解） | ❌（PID 检查缓解） |
| 代码改动量 | **中** | 中 | **小** |
| 可观测性 | 需额外 | 需额外 | **内置 lock.json** |

---
