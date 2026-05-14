# Error DNA v3 设计提案

> 目标：将 Error DNA 从"只记账不学习"的零价值机制，转为"捕获→分析→学习"的有价值闭环。
> Oracle 审核要点：ROI 是否足够高？是否值得实施？

---

## 背景

- Error DNA 当前捕获 Bash 错误到 JSONL + retry-budget，但消费端 3 条路径 2 条已死
- 83.5% 噪声率（gate 正常操作被记录为"错误"）
- 无教训升华机制，compact 后归零，跨 session 无记忆
- v1 过度内联（400 行），v2 过度瘦身（228 行只捕获不消费），v3 应走中间路线

## 目标

- 实施成本：≤250 行新代码
- 维持收益：每次 SessionStart 注入 ≤3 条可行动错误教训
- 噪声率：注入前过滤 ≥90% gate 噪声
- 持久收益：重复错误自动写为 claude-next.md 条目，hits ≥1

## 设计

### 三层管线

```
Layer 1: CAPTURE — PostToolUse 热路径
  现有 error-dna.sh 不动（228 行，够轻量）
  → JSONL 追加 + retry-budget.json（签名+重试计数）

Layer 2: ANALYZE — Stop hook 触发（新脚本 ~100 行 python）
  error-dna-analyzer.sh
  1. 读 retry-budget.json
  2. 过滤噪声签名（gate 操作、工具误操作）
  3. 按严重度排序：build/test > runtime > 工具错误 > 门禁(丢弃)
  4. 输出 error-dna-lessons.json（轻量，≤10 条高频签名）
  
Layer 3: LEARN — SessionStart 注入（修改 inject-project-knowledge.sh ~30 行）
  1. 读 error-dna-lessons.json
  2. 读 retry-budget.json 检查重试 ≥3 的签名
  3. 输出"错误教训"区块到 AI 上下文
  4. 高频签名(≥3) → 写入 claude-next.md 作为新教训条目
```

### 产出格式

```
[错误教训]
  · ⚠ 运行时 ×7 — `ls: /path: No such file or directory`
    上次修复尝试: 1 次 (成功)
  · 🔴 构建 ×3 — `go build: undefined: XxxFunc`
    上次修复尝试: 3 次 (本轮第 3 次成功)
    已学入 claude-next.md R-ED-001
---
```

### 噪声识别规则

| 模式 | 严重度 | 注入行为 |
|------|--------|---------|
| 命令含 `sensitive-edit`/`context-guard`/`pretool-` | **丢弃** | 不注入 |
| exit_code=-1（工具错误）且消息含 `File does not exist` / `modified since read` | **低** | 聚合计数，不单独列出 |
| error_type=build/test | **高** | 必须注入，优先学习 |
| error_type=runtime 且 retry ≥2 | **中** | 注入摘要 |
| retry_count ≥3 | **高** | 自动写入 claude-next.md |
| 噪声类别占比 >80% 总记录 | 标记 | 注入时注明 "当前记录以门禁操作占主导" |

### 实施范围

```
新建: .claude/scripts/error-dna-analyzer.sh   ~100 行 python
修改: .claude/hooks/inject-project-knowledge.sh  ~30 行（替换 222-278 逻辑）
修改: .claude/hooks/stop-drain.sh                ~10 行（触发 analyze）
```

不动：`error-dna.sh`、`harness.yaml`、`settings.json`。

## ROI 评估

| 维度 | 当前 | v3 目标 |
|------|------|--------|
| 代码量 | 228 行 (只捕获) | +140 行 (捕获+分析+学习) |
| 每次 SessionStart 注入量 | 0 条可行动信息 | ≤3 条错误教训 |
| 噪声率 | 83.5% | <10% (注入时) |
| cross-session 受益 | 无 | 重试 ≥3 自动学入 claude-next.md |
| 维护成本 | ~50 lines/quarter | ~100 lines/quarter |
| 实现工时 | — | ~30 分钟 |

### 收益-噪声自检（哲学门禁）

**1. 收益可证伪吗？**
- 成功信号：SessionStart 注入出现 `[错误教训]` 区块，内容随实际错误变化
- 失败信号：SessionStart 无错误教训区块，或总是显示空集
- 测量方式：grep SessionStart 输出中的 `[错误教训]`

**2. 噪声上限明确吗？**
- 噪声来源：gate 操作误判为真错误
- 缓解：分析层按严重度分层过滤，gate 模式直接丢弃
- 上限：注入内容中门禁相关教训 ≤1 条/次，超过则整体降至"仅摘要"
- 关闭条件：连续 10 次 SessionStart 注入全是缓存旧教训 → 自动暂停

**3. 如果 0 收益，多久能发现？**
- 观察期：3 次完整开发 session（~1 天）
- 终止条件：3 次 session 后仍然 0 条可行动错误教训 → 标记 `ROI_LOW`，下次审计时清理
- 回滚成本：删除 2 个新脚本，回退 inject + stop-drain 修改，<5 分钟
