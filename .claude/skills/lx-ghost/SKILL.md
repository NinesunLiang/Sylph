---
name: lx-ghost
version: v1.1.0
description: "幽灵模式 — 方向驱动的自主探索。给 AI 一个方向，AI 自主探索修复，安全网降级不干扰人。"
when_to_use: "Use when user says 'ghost mode', '幽灵模式', '自主探索', 'lx-ghost', /lx-ghost"
model: sonnet
argument-hint: "[方向描述] [轮询间隔秒数=600] [过期小时=3]"
harness_version: ">=1.1.0"
role: "Direction-driven autonomous exploration mode"
execution_mode: stepwise
triggers:
  - "/lx-ghost"
---

# lx-ghost — 方向驱动自主探索

> **一次确认 → 全自动探索**：用户确认方向后，AI 自主探索修复到过期或方向达成。
> Gate 降级为 warn-only，遇到风险记录 `skipped_risks` 继续执行，不暂停问人。

## 立即执行（本 skill 加载后立刻执行）

本 skill 加载时立即检查调用参数：

**有参数** → 先执行方向自检：

```
方向自检：这个方向适合 ghost mode？
├─ "探索/扫描/修复/迭代" 等增量关键词 → ✅ ghost mode
├─ "分析/报告/评估/阅读" 等一次性关键词 → ⚠️ 建议改用 goal mode
└─ 区分不清 → 问用户
```

通过自检后激活：
```bash
bash .claude/skills/lx-ghost/scripts/lx-ghost.sh on "参数1" [参数2] [参数3]
```
然后按探索→轮询→报告的流程运行，直到过期或方向达成。

> **⚠️ 间隔秒数不可为 0**：`0s` = 不轮询，违背 ghost 增量探索设计。最小值 30s，默认 600s。

**无参数** → 先问用户方向，出方案后等用户确认，确认后全自动执行。

---

## 执行流程

### 1. 激活幽灵模式（1 次人工确认）
```bash
bash .claude/skills/lx-ghost/scripts/lx-ghost.sh on "方向描述" [间隔秒数] [过期小时]
```
用户确认方向后 → 全自动执行，不再请求任何确认。

### 2. 全自动轮询（确认后不再停顿）
```
/loop <间隔秒数>s lx-ghost poll
```
例如 `/loop 600s lx-ghost poll` 每 10 分钟轮询一次。

每轮 poll 全自动：
1. 读 `lx-ghost.json` 确认方向未变
2. **方向漂移自检**：当前要执行的这一步，是否还在原始方向范围内？
   - ✅ 是 → 执行
   - ❌ 偏离方向 → 记录到 `skipped_risks`，**不要做**，尝试更具相关性的下一步
   - ❌ 完全漂移（如方向是"测 ghost 机制"但启动了系统级分析）→ 停用，向用户报告方向误判
3. **每轮只做一步**：不启动并行 agent，不读 10 个文件再分析。一步 poll = 一个操作
4. 遇到危险 → `skip-risk` 记录，**不中断，继续执行**
5. 遇到歧义 → 自行决策，记录到 `skipped_risks`，**不暂停问人**
6. 更新状态

### 3. 停用（自动或手动）
- **自动**：过期后 `is_mode_active()` 自动清理
- **手动**：
  ```bash
  bash .claude/skills/lx-ghost/scripts/lx-ghost.sh off
  ```
- 方向达成后也手动关。

---

## 脚本引用

完整子命令参见 `.claude/scripts/lx-ghost.sh`（直接运行查看帮助）。

| 子命令 | 作用 |
|--------|------|
| `on "方向" [间隔] [小时]` | 激活幽灵模式 |
| `off` | 关闭 |
| `status` | 查看状态 |
| `poll` | 轮询入口 |
| `skip-risk "描述"` | 记录跳过的风险 |
| `retry` | 重试计数+1 |
| `set <key> <value>` | 修改 JSON 字段 |

---

## 哲学

| # | 哲学 | 物化 |
|---|------|------|
| #3 | 先守护 | gate 降级为 warn-only，不硬阻断 |
| #4 | 没验证=没做 | 每轮 poll 报告执行状态 |
| #6 | 0 信任 | 危险操作记录 skipped_risks |
| #2 | 少量大增益 | 只做方向相关的事 |

---

## 错误恢复

| 场景 | 处理 |
|------|------|
| 方向不明确 | 停用，让用户补充 |
| 修复阻塞（3 次） | `skip-risk` 记录 |
| token 过高 | 增加 poll 间隔或提前关停 |
| 与 goal 冲突 | 先关另一个再开 |
