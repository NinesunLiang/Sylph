# 沙箱内长任务模式（Sandbox Long Task Pattern）

> 适用：Claude Code / DSH 沙箱环境下，任何需等待 > 60 秒的操作。

## 沙箱超时限制（实测）

| 沙箱 | Bash 命令默认超时 | 单次 sleep 限制 |
|---|---|---|
| Claude Code（CC）| 120 秒 | 单次 sleep 撞 120s 触发 Exit 143 |
| DSH（DeepSeek Harness）| 60 秒 | 单次 sleep 撞 60s 触发 kill |
| CI 沙箱 | 通常 60-300 秒 | 因平台而异 |

**根因**：沙箱防止无限阻塞——这是机制设计，不是 bug。**改用法，不绕机制**。

## 模式 1：分批 sleep（最简单）

```bash
# ❌ 错：单次 sleep 撞线
sleep 110  # 触发 "Command timed out after 2m 0s"

# ✅ 对：分批 sleep
sleep 50 && sleep 50 && sleep 10
# 或更明确地轮询
for i in {1..6}; do
  if check_done; then break; fi
  sleep 20
done
```

**关键**：`&&` 串联**仍在同一个 Bash 调用**——超时是单次命令的，不是累积的。

## 模式 2：后台运行（推荐）

```bash
# ✅ 后台跑（run_in_background: true）
# 工具调用参数：
#   run_in_background: true
#   command: "long_task.sh"

# 之后查询状态：
jobs  # 列出后台任务
# 或查文件
test -f /tmp/done.flag && echo "completed"
```

**优势**：
- 不阻塞当前会话
- 可用 jobs 查询状态
- 失败不浪费超时

## 模式 3：轮询代替 sleep

```bash
# ✅ 等待文件出现（轮询 + 短 sleep）
for i in {1..30}; do
  if [ -f /tmp/result.json ]; then
    cat /tmp/result.json
    break
  fi
  sleep 5
done
```

**优势**：CPU 友好，任务完成立即继续。

## 模式 4：分阶段任务

```bash
# ❌ 错：单命令 10 个操作
command1 && command2 && ... && command10

# ✅ 对：拆成多个 Bash 调用
# 每次 Bash 调用只做 2-3 个操作，分批提交
```

**优势**：
- 每个调用 < 60 秒
- 失败定位精确
- 可恢复

## 模式 5：异步 + 短轮询

```bash
# ✅ 启动后台 + 立即返回
nohup ./long_task.sh > /tmp/long.log 2>&1 &
echo "PID=$!"

# 后续查询：
ps -p $PID > /dev/null && echo "running" || echo "done"
tail /tmp/long.log
```

**优势**：
- 命令立即返回（不撞超时）
- 后续灵活查询

## 实操判断

**单次 Bash 持续时长预估**：

| 操作类型 | 通常时长 | 沙箱内做法 |
|---|---|---|
| 单元测试（< 50 文件）| 5-15 秒 | 直接跑 |
| 集成测试（< 200 文件）| 30-60 秒 | 跑，监控 |
| 全量回归（500+ 文件）| 60-300 秒 | **必须分批或后台** |
| 长时编译（大型项目）| 60-600 秒 | **必须后台 + 轮询** |
| 数据库迁移 | 30-120 秒 | 后台 + 进度文件 |
| 网络下载大文件 | 10-300 秒 | 后台 + 进度 |

**判断原则**：
- 预估 > 60 秒 → 后台跑
- 预估 30-60 秒 → 直接跑但监控
- 预估 < 30 秒 → 直接跑

## 反模式（不要做）

| 反模式 | 后果 |
|---|---|
| `sleep 110` 等后台任务 | Command timed out |
| `command1 && command2 && ... && command10`（单条链 10 操作）| 单步失败全失败，定位难 |
| 长时编译/测试单条 Bash | 60-300 秒撞线 |
| `tail -f` 永久阻塞 | 永久等 |

## 跨沙箱一致模式

不论 Claude Code / DSH / CI 沙箱，**模式相同**：
- 后台 + 轮询 = 通用解
- 分批 = 通用解
- 单次 < 60 秒 = 通用安全

## 相关反模式

见 `anti-patterns.md` §L5 SLEEP_OVERSIZE。