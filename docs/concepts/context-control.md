# Context Control (上下文控制)

> **The fuse that prevents the AI from burning itself out.**

---

## The Problem

Large language models suffer from a well-documented failure mode called **Lost in the Middle**: as the conversation grows, the model's ability to attend to earlier context degrades. Beyond a certain token threshold, the AI becomes unreliable -- it hallucinates, deletes working code, and contradicts itself.

In AI-assisted development, this means:

- A refactoring session that spans 30+ rounds produces a broken codebase.
- The AI confidently states "I have completed the task" while having silently removed critical functions.
- Every new round of instructions makes the hallucination worse, not better.

Prompt engineering cannot fix this. Telling the AI "stay focused" in a system prompt does not prevent context decay.

---

## Two-Layer Defense

### Sweet Spot Warning (Soft Gate)

When context consumption exceeds the **warn threshold** (default 50%), Carror OS triggers a **voluntary handoff**:

1. The current session summarizes its state into a handoff document.
2. A new session starts with a fresh, clean context.
3. The handoff document is the only knowledge carried over -- not degraded conversation fragments.

This happens at the **attention sweet spot** -- before decay begins, not after the damage is done.

### Physical Fuse (Hard Gate)

If the session reaches the **danger threshold** (default 80% real token consumption), the `context-guard` hook fires a hard stop:

- All write and execute commands are blocked.
- The process exits with code 2.
- No amount of AI prompting can bypass this.

The danger threshold is a physical circuit breaker, not a soft warning. It protects your codebase from the terminal phase of AI hallucination.

### Configuring Thresholds

All thresholds and configurable values are set via `.claude/harness.yaml`:

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
  evidence_dir: ".omc/state"              # 证据文件存放目录
  evidence_freshness_sec: 300             # 证据文件新鲜度窗口，默认 300s

error_dna:
  enabled: true
  max_entries: 100
  rotation_size_bytes: 1048576  # 日志轮转触发大小，默认 1MB
  archive_count: 3              # 归档保留份数，默认 3

flywheel_report:
  report_window_days: 30        # 频率分析窗口，默认 30 天
  default_snooze_days: 7        # 默认稍后提醒天数，默认 7
  p0_warning_threshold: 5       # P0 告警计数阈值，默认 5

read_tracker:
  rotation_line_count: 500      # 读取记录轮转行数，默认 500
  archive_generations: 4        # 归档代数，默认 4

posttool_bash_audit:
  fail_streak_threshold: 3      # 连续构建失败告警阈值，默认 3

oma_lock_manager:
  max_observability_events: 500 # 锁观测事件上限，默认 500
  initial_backoff: 0.1          # 初始退避秒数，默认 0.1
  max_backoff: 1.0              # 最大退避秒数，默认 1.0
```

**场景适配示例（context_guard）：**

| 上下文窗口 | warn_threshold | danger_threshold | 说明 |
|-----------|---------------|-----------------|------|
| 200K（默认） | 50 | 80 | 默认值，已验证 |
| 1M | 30 | 50 | 甜点区前移 |
| 关闭甜点告警 | 100 | 80 | warn 永远不会触发 |
| 完全关闭 | — | — | 设置 `hooks_enabled.context_guard: false` |

所有配置修改后无需重启，harness-config 缓存自动重建生效。

---

## Progressive Disclosure (Token Economy)

Carror OS does not load all rules at once. Instead, it uses a **reference library** system:

- Security rules load only when a security scan runs.
- Commit format rules load only when a commit is requested.
- Code style rules load only when new code is written.

This keeps the active context clean and the signal-to-noise ratio high. The result is not just lower token costs -- it is higher instruction compliance, because the AI has fewer competing directives to track.

---

## Related

- [Gates: context-guard](./gates.md) -- the 80% hard fuse implementation
- [Workflow: RPE Handoff](./workflow.md) -- how the 50% active handoff integrates with RPE
