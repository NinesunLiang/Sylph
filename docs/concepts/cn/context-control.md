# 上下文控制（Context Control）

> **防止 AI 自我燃烧的保险丝。**

---

## 问题

大语言模型有一个被充分记录的失效模式叫 **Lost in the Middle（中部迷失）**：随着对话增长，模型关注早期上下文的能力下降。超过某个 Token 阈值后，AI 变得不可靠——它会产生幻觉、删除正常代码、自相矛盾。

在 AI 辅助开发中，这意味着：

- 跨越 30+ 轮的重构会话产出损坏的代码库
- AI 自信地说"任务已完成"，同时静默删除了关键函数
- 每一轮新指令都让幻觉更严重，而非改善

Prompt 工程无法解决这一点。在系统提示词中告诉 AI"保持专注"并不能阻止上下文衰减。

---

## 双层防御

### 甜点区警告（软门禁）

当上下文消耗超过**警告阈值**（默认 50%）时，Carror OS 触发**自愿交接**：

1. 当前会话将状态总结为交接文档
2. 新会话以干净的上下文启动
3. 交接文档是唯一传递的知识——而非已衰减的对话碎片

这在**注意力甜点区**发生——在衰减开始之前，而非损害已经造成之后。

### 物理熔断（硬门禁）

如果会话达到**危险阈值**（默认 80% 真实 Token 消耗），`context-guard` Hook 触发硬停止：

- 所有写入和执行命令被阻断
- 进程以代码 2 退出
- AI 无论如何提示都无法绕过

危险阈值是物理断路器，而非软警告。它保护你的代码库免受 AI 幻觉末期阶段的破坏。

### 配置阈值

所有阈值通过 `.claude/harness.yaml` 配置：

```yaml
context_guard:
  warn_threshold: 50    # 甜点区告警线，默认 50%
  danger_threshold: 80  # 硬阻断线，默认 80%

proactive_handoff:
  context_threshold: 50       # 主动交接触发线，默认 50%
  executor_freshness_sec: 300 # executor.md 新鲜度窗口，默认 300s

token_tracking:
  limit: 200000              # token 用量上限，默认 200000

completion_gate:
  min_evidence_chars: 20     # 证据文件最少字符数
  required_keyword: "VERIFIED"
  evidence_dir: ".omc/state"
  evidence_freshness_sec: 300

error_dna:
  enabled: true
  max_entries: 100
  rotation_size_bytes: 1048576  # 日志轮转触发大小，默认 1MB
  archive_count: 3              # 归档保留份数，默认 3

flywheel_report:
  report_window_days: 30
  default_snooze_days: 7
  p0_warning_threshold: 5

read_tracker:
  rotation_line_count: 500
  archive_generations: 4

posttool_bash_audit:
  fail_streak_threshold: 3

oma_lock_manager:
  max_observability_events: 500
  initial_backoff: 0.1
  max_backoff: 1.0
```

**场景适配示例（context_guard）：**

| 上下文窗口 | warn_threshold | danger_threshold | 说明 |
|-----------|---------------|-----------------|------|
| 200K（默认） | 50 | 80 | 默认值，已验证 |
| 1M | 30 | 50 | 甜点区前移 |
| 关闭甜点告警 | 100 | 80 | warn 永不触发 |
| 完全关闭 | — | — | 设置 `hooks_enabled.context_guard: false` |

所有配置修改后无需重启，harness-config 缓存自动重建生效。

---

## 渐进式披露（Token 经济）

Carror OS 不会一次性加载所有规则。它使用**引用库**系统：

- 安全规则只在安全扫描运行时加载
- 提交格式规则只在提交请求时加载
- 代码风格规则只在新代码写入时加载

这保持了上下文的干净和高信噪比。结果不仅是更低的 Token 成本，更是更高的指令遵从度——因为 AI 需要跟踪的竞争指令更少。

---

## 相关

- [Gate：context-guard](./gates.md) — 80% 硬熔断实现
- [工作流：RPE 交接](./workflow.md) — 50% 主动交接如何与 RPE 集成
