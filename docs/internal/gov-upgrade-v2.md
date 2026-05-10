# 长期治理升级方案 v2 — 四项提升至 80+

> 版本：v2 | 日期：2026-05-10
> 基线：长期治理 68/100 | 目标：四项全部 80+

---

## 1. 当前全景

```
长期治理能力 68/100
├─ 🛡️ 抗衰减防线  68  ← error-dna 有捕获、告警，缺自动修复闭环
├─ 🔄 飞轮自愈    63  ← flywheel_analytics 已算废弃，缺告警通道
├─ 📤 会话交接    ~82 ← session-dump + handoff + proactive 已齐 ✅
├─ 📝 学习笔记    70  ← token_writer + posttool-edit-quality，缺自动知识抽取
└─ 🔗 治理一致性  65  ← source mirror 已修，1 🟡 漂移残留
```

- 会话交接已 ≥80（US-001 已交付 session-dump.json），无需改动
- 四项待提升：抗衰减、飞轮、学习笔记、治理一致性

---

## 2. 方案 GS-001: 抗衰减防线 auto-fix 闭环

### 目标
error-dna 从"记录+告警"升级为"记录+告警+自动修复提案"。

### 设计

新增 `.claude/hooks/error-dna-auto-fix.sh` — Stop hook

```
触发: Stop（会话结束时或 /compact 前）
行为:
  1. 读 error-dna.json → 筛选条件:
     - count >= 2
     - status != fixed
     - repair_command 存在
     - fix_count < 3（未达修复上限）
  2. 按 count 降序排列
  3. 输出 additionalContext 格式:
     [error-dna auto-fix] {N} 个可自动修复的错误签名:
     ・ {signature[:16]} ×{count} — {message[:80]}
       ▶ 修复命令: `{repair_command}`  (上次失败: {last_seen})
  4. 每条输出后不执行（hook 架构限制只建议不执行）
```

### 已存在的依赖
- `error-dna.json` 已有 `repair_command`、`fix_count`、`repair_success` 字段 ✅
- error-classifier.py 已分类 error_type ✅
- `fix_count < 3` 已在 error-dna.sh 中跟踪 ✅

### 新增文件
- `.claude/hooks/error-dna-auto-fix.sh` (~40 行 shell)

### 注册
- settings.json 新增 `Stop` event
- harness.yaml `error_dna_auto_fix` 开关
- audit-hooks R35 回归

### 未覆盖
- hook 架构限制：不能自动执行 repair_command，只能通过 additionalContext 建议
- 若将来 Claude Code 开放 PostToolUse 执行命令，可升级为自动修复

---

## 3. 方案 GS-002: 飞轮自愈废弃告警

### 目标
flywheel_analytics.py 已计算废弃技能（`days_since_last_use > 30`），但告警未传递到 AI 会话。需要 Stop 时将废弃技能列表注入 additionalContext。

### 设计

修改 `.claude/hooks/skill-flywheel.sh` — Stop hook 追加段落

```
在现有 flush buffer + analytics 调用之后，追加:
  5. 读 flywheel-report.json
  6. 提取 deprecated_skills 列表
  7. 若有废弃技能:
     [flywheel] ⚠️ {N} 个技能已废弃（>30 天未使用）:
     ・ {skill_name} — 上次使用: {days_since} 天前
     ・ {skill_name} — 上次使用: {days_since} 天前
     提示: 考虑运行 /lx-validate-skill 或手动移除
```

### 已存在的依赖
- `flywheel_analytics.py` 已计算 `deprecated_skills` ✅
- `flywheel-report.json` 已写入 ✅
- skill-flywheel.sh 已调用 analytics ✅

### 变更文件
- `.claude/hooks/skill-flywheel.sh` — 追加 ~15 行

### 注册
- 已有 Stop event，无需新增注册

---

## 4. 方案 GS-003: 学习笔记自动知识抽取

### 目标
claude-next.md 中的高频模式（hits≥3）自动识别，输出升华建议。

### 设计

新增 `.claude/hooks/knowledge-condenser.sh` — Stop hook

```
触发: Stop
行为:
  1. 读 .claude/claude-next.md
  2. 正则提取所有 [seed:*] 或 *@YYYY-MM-DD hits:N* 条目
  3. 筛选 hits >= 3 的模式
  4. 检查 kernel.md 是否已包含该规则（grep 规则名或关键词）
  5. 输出 additionalContext:
     [knowledge-condenser] {N} 个高频模式可升华至 kernel.md:
     ・ {rule_name} (hits:{N}, age:{days}天) → {当前状态}
       ├ 建议: {建议动作: 升华至kernel.md / 更新kernel.md / 废弃}
       └ 证据: claude-next.md:line:{N}
```

### 升华规则

| hits | age | 当前状态 | 建议 |
|------|-----|---------|------|
| ≥5 | ≥10天 | 已在 kernel.md | 更新 kernel.md 后可从 claude-next.md 移除 |
| ≥5 | ≥10天 | 不在 kernel.md | 升华至 kernel.md |
| ≥3 | ≥5天 | 已在 kernel.md | 更新 kernel.md（修复表述/添加证据） |
| ≥3 | ≥5天 | 不在 kernel.md | 建议升华，标记待确认 |
| ≥3 | <5天 | 任何 | 标记"待稳定后再升华" |
| <3 | 任何 | 任何 | 忽略（频率不足，继续积累） |

### 新增文件
- `.claude/hooks/knowledge-condenser.sh` (~60 行)

### 注册
- settings.json 新增 `Stop` event
- harness.yaml `knowledge_condenser` 开关
- audit-hooks R36 回归

### 状态迁移

```
claude-next.md 条目生命周期:
  创建 (hits:1) → 积累 (hits:2) → 高频 (hits≥3) → 升华候补 (hits≥5, age≥10d)
                                                          ↓
                                                    更新 kernel.md
                                                          ↓
                                                    从 claude-next.md 移除
```

---

## 5. 方案 GS-004: 治理一致性修复

### 5.1 漂移修复
当前 1 个 🟡 漂移：posttool-read-cite.sh 在 settings.json 注册 `PostToolUse` 但 harness.yaml 中 `posttool_read_cite=false`。

**修复**：在 harness.yaml 中将 `posttool_read_cite` 设为 `true`（与 settings.json 注册一致）。

### 5.2 自动告警
增强 `audit-hooks.sh` 输出 additionalContext，在 SessionStart 时自动报告治理一致性状态。

### 变更文件
- `.claude/harness.yaml` — 改 1 行

---

## 6. 文件变更汇总

| 文件 | 类型 | GS# |
|------|------|-----|
| `.claude/hooks/error-dna-auto-fix.sh` | 新增 | GS-001 |
| `.claude/hooks/skill-flywheel.sh` | 修改 | GS-002 |
| `.claude/hooks/knowledge-condenser.sh` | 新增 | GS-003 |
| `.claude/harness.yaml` | 修改 | GS-004 |
| `.claude/settings.json` | 修改 | GS-001, GS-003 注册 Stop |
| `.claude/scripts/audit-hooks.sh` | 修改 | GS-004 R35/R36 回归 |
| `.claude/scripts/harness-smoke-test.sh` | 修改 | GS-004 新增回归 case |
| `source/harness-kit/` | 同步 | 全部 |

---

## 7. 验证方案

| # | 检查项 | 命令/方法 |
|---|--------|----------|
| V1 | error-dna.json 含 repair_command 的条目 | `python3 -c "import json; d=json.load(open('.omc/state/error-dna.json')); print([k for k,v in d['error_signatures'].items() if v.get('repair_command')])"` |
| V2 | auto-fix Stop hook 语法通过 | `bash -n .claude/hooks/error-dna-auto-fix.sh` |
| V3 | flywheel-report.json deprecated 字段 | `python3 -c "import json; print(json.load(open('.omc/state/flywheel-report.json')).get('deprecated_skills'))"` |
| V4 | knowledge-condenser hits≥3 检测 | `python3 -c "import re; c=open('.claude/claude-next.md').read(); print(len(re.findall(r'hits:([3-9]|\d{2})',c)))"` |
| V5 | harness.yaml posttool_read_cite=true | `grep 'posttool_read_cite' .claude/harness.yaml` |
| V6 | source mirror 一致 | `bash .claude/scripts/audit-hooks.sh --check-source-mirror` |
| V7 | harness-smoke 回归 | `bash .claude/scripts/harness-smoke-test.sh` |
| V8 | 全部 .sh 语法 | `bash -n .claude/hooks/*.sh .claude/scripts/*.sh` |

---

## 8. 风险与回退

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Hook 脚本语法错误阻断 Stop | 低 | 低 | `exit 0` 兜底 |
| knowledge-condenser 误报升华 | 中 | 低 | 只建议不执行，由用户确认 |
| 新 Stop hook 增加会话结束延迟 | 低 | 低 | 各自 <100ms |
| 回退: git revert + source mirror sync | — | — | commit 前验证源镜像一致 |

---

## 9. 预估提升

| 维度 | 基线 | 目标 | 杠杆 |
|------|------|------|------|
| 抗衰减防线 | 68 | **82** | +14: auto-fix 告警闭环 |
| 飞轮自愈 | 63 | **80** | +17: 废弃告警注入 |
| 学习笔记积累 | 70 | **82** | +12: 自动知识抽取 |
| 治理一致性 | 65 | **85** | +20: 漂移修复 + 自动告警 |
| **加权综合** | **68** | **~82** | **+14** |
