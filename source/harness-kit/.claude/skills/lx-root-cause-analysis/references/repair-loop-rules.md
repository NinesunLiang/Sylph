# 修复循环规则（Phase 4-5）

## 循环上限：最多 3 轮
| 轮次 | 动作|
|------|------|
|1-3 | 正常修复循环：Phase 4 修复 → Phase 5 验证 → 失败 → 返回 Phase 4|
|每次失败 | 分析：**与上一轮失败模式相同？** 是 → 预防性 Oracle 升级（忽略轮次计数）|
|触发第 4 轮 | **强制 Oracle 升级**：将所有轮次的失败证据提交给 Oracle|
|Oracle 仍失败 | **调查终止**：标记 `⛔ BLOCKED`，向用户报告，等待外部输入 |

## 每轮失败分析
每轮失败后，重试前：1. 对比本轮失败与上一轮失败2. 失败模式相同 → 同一根因反复出现 → 立即升级至 Oracle3. 失败模式不同 → 暴露了新问题 → 继续（在 3 轮上限内）

## BLOCKED 报告格式

```⛔ Root Cause Analysis BLOCKED (repair loop limit reached)- Rounds: 3/3 (exhausted)- Per-round failures: Round 1: [failure] | Mode: [new root cause / same recurrence] Round 2: [failure] | Mode: [new root cause / same recurrence] Round 3: [failure] | Mode: [new root cause / same recurrence]- Oracle consultation: [result summary]- External input needed: [specific data/access/environment required]- Suggested action: [e.g., "provide production pprof goroutine dump"]
⛔ Root Cause Analysis BLOCKED (repair loop limit reached)- Rounds: 3/3 (exhausted)- Per-round failures: Round 1: [failure] | Mode: [new root cause / same recurrence] Round 2: [failure] | Mode: [new root cause / same recurrence] Round 3: [failure] | Mode: [new root cause / same recurrence]- Oracle consultation: [result summary]- External input needed: [specific data/access/environment required]- Suggested action: [e.g., "provide production pprof goroutine dump"]
```

## 跨 Phase 一致性强制
每轮修复必须验证：- Phase 3 根因 = Phase 4 修复目标（X11 检查）- Phase 4 修复覆盖了 Phase 3 确定为根因的 Why 层级- Phase 5 免疫测试模拟 Phase 3 中确定的确切根因场景
