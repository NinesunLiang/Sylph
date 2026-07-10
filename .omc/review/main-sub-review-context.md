# CarrorOS Step 2 Main-Sub 架构评审上下文

## 架构概览

```
carros_base.py (Main Agent CLI, 1859行)
 ├── cmd_clarify → clarify_engine.py → spec.md
 ├── cmd_plan    → task_planner.py  → plan.json
 ├── cmd_auto    → sub_agent_manager.py → auto_run
 │                  ├── distribute() → sub_task/{step}/token.json + result.json
 │                  ├── _wait_all() → poll() + spawn sub_agent_executor.py
 │                  ├── collect() → main executor.md
 │                  └── retry_failed() → 最多3次
 └── cmd_verify/archive (沿用 Goal 状态机)
```

### 5 个核心文件

| 文件 | 行数 | 职责 |
|------|------|------|
| `task_planner.py` | 333 | spec.md → plan.json 原子任务分解 |
| `sub_agent_manager.py` | 930 | Main-Sub 编排器：分发/轮询/并发/重试/回收 |
| `sub_agent_executor.py` | 425 | SubAgent 运行器：spawn `claude -p --bare --print` |
| `sub_agent_recovery.py` | 342 | compact checkpoint → resume 恢复 |
| `carros_base.py` (增量) | +200 | cmd_plan / cmd_auto 集成 |

---

## 待决策问题

### Q1: SubAgent 执行方案
SubAgent 通过 `claude -p --bare --print` 非交互执行，通过文件契约通信。
- sub_agent_executor.py 构造 prompt 传给 `claude`
- subagent 执行后在文件系统写 result.json + executor.md
- main agent 轮询读取结果

**需要确认：**
- `--bare` 模式是否真的不加载 AGENTS.md/hooks？会不会遗漏必要的治理约束？
- 文件契约的延迟（subagent 写完后 main poll 读到）在 10s poll 间隔下是否稳定？
- subagent 如果长时间运行时被 compact，谁负责恢复？

### Q2: 并发控制
SubAgentManager 的 `_wait_all()` 每轮 poll 时检测 pending step 就 spawn。
- 通过 `_count_running()` 做并发限流（默认 cc=3）
- 使用 `subprocess.Popen` 做 detach 后台进程
- 超时默认 5min，然后标记 timeout

**需要确认：**
- 这个 spawn 模式会不会因为 poll 间隔短导致重复 spawn？
- spawned_procs 字典只用于记录，没有 wait/reap 机制，会不会积累 zombie 进程？

### Q3: 重试策略
SubAgent 失败自动重试（最多 3 次）：
1. sub_agent_executor.py 失败 → result.json status=failed, retry_count+1
2. sub_agent_manager.py retry_failed() 检测到失败 → 重置 status=running, 清空 executor.md
3. _wait_all 的下一轮 poll 检测到 running → 跳过 spawn（已加 spawned set）
4. 重新尝试的 sub_agent_executor.py 会被 spawn 吗？——不会，因为 spawned set 已包含该 step

**需要确认：**
- 重试时 spawned set 已包含 step → 不会再 spawn → 那谁来重新执行？
- 重试机制实际上没有工作，因为 _spawn_subagent 只在 "pending" 状态触发，但重试后是 "running"

### Q4: SubAgent prompt 设计
sub_agent_executor.py 构造的 prompt 包含:
- token.json 的 goal/ACs/files
- 父任务的 plan.md/spec.md 上下文
- 输出格式要求（写 executor.md + 更新 result.json）

**需要确认：**
- subagent 是否真的能理解并遵守写文件的指令？
- `claude -p --bare` 下有没有 Read/Write/Edit/Bash 工具可用？

### Q5: auto_run 的 verify + archive 阶段
cmd_auto 在 sub_agent_manager.auto_run 完成后调用 carros_base 的 cmd_verify 和 cmd_archive。
- 但 verify 只递增 main token 的 done 计数器
- archive 做 lint + token 归档 + Goal 状态机推进

**需要确认：**
- 子任务的 executor.md 证据是否应该自动汇入主任务的 verify？
- 当前 collect() 做了追加到 main executor.md，但 verify 只看 plan.md 的 checkbox

---

## 已验证通过的项目

- ✅ Bench 7/7 PASS（原有功能未退化）
- ✅ task_planner L1/L2 spec 分解正确（支持中文标题+括号）
- ✅ sub_agent_manager plan/check/poll/collect 命令独立可运行
- ✅ sub_agent_manager plan 分发 → 正确创建 token/result/executor
- ✅ sub_agent_recovery status/generate-resume 正确
- ✅ clarify → plan 链路完整（Goal 状态机自动推进）
- ✅ 所有 5 个文件 Python 编译 0 错误
- ✅ `subprocess.Popen` 后台调用 executor 不阻塞主进程
- ✅ 并发限流 `_count_running()` 读 result.json status=running
- ✅ 超时检测 `_check_one()` 计算 started_at 到现在的秒数

## 已知风险和盲区

1. **重试循环未闭环** — 重设 status=running 后 spawned set 已包含该 step，不会再 spawn executor
2. **zombie 进程** — Popen 的 proc 存了但没有 wait() 回收
3. **sub_agent_executor.py 硬编码 `claude` command** — 如果 claude CLI 升级/路径变化会失败
4. **`--allowedTools` 参数** — sub_agent_executor.py L248 写死了 `Read,Write,Edit,Bash,Grep,FileEdit`，但 claude CLI 实际的参数名可能是 `--allowedTools` 还是 `--allowed-tools`？
5. **subagent 的输出解析** — sub_agent_executor.py 当前依赖 subagent 自己写 result.json，如果 subagent 不写（或写失败），fallback 逻辑只取 stdout[:100] 作为 summary
6. **无日志** — sub_agent_executor.py 把 stdout/stderr 都指向 DEVNULL，调试困难
7. **AGENTS.md 中缺少 cmd_plan/cmd_auto 路由** — 需要在 AGENTS.md 添加新命令说明
