# 长期治理升级方案 v3 — 四项提升至 80+

> 版本：v3 | 日期：2026-05-10
> 基线：长期治理 68/100 | 目标：四项全部 80+
> Oracle 审核：v2 → needs_clarification → 已全部澄清

---

## 1. 当前全景

```
长期治理能力 68/100
├─ 🛡️ 抗衰减防线  68  ← error-dna 有实时修复(PostToolUse)，缺跨会话回顾聚合
├─ 🔄 飞轮自愈    63  ← flywheel_analytics 已算废弃，缺告警通道
├─ 📤 会话交接    ~82 ← session-dump + handoff + proactive 已齐 ✅
├─ 📝 学习笔记    70  ← token_writer + posttool-edit-quality，缺自动知识抽取
└─ 🔗 治理一致性  65  ← source mirror 已修，1 🟡 漂移残留 + 无自动告警
```

- 会话交接已 ≥80，无需改动
- GS-001 定位修正：现有 error-dna.sh:236-283 已有**实时** auto-fix（PostToolUse 时输出修复策略 + additionalContext），新 Stop hook 定位为**跨会话回顾**，避免与实时层重复

---

## 2. 方案 GS-001: 抗衰减防线 — 跨会话回顾聚合

### 定位说明（修正 v2）

```
现有双架构：
  Layer 1 (PostToolUse):  error-dna.sh:236-283 → 实时，当前会话内，每次失败立即输出修复建议
  Layer 2 (Stop, 新增):   error-dna-auto-fix.sh → 回顾，跨会话聚合，上次会话未修复的顽固错误
```

**去重策略**：Stop 层只输出 `fix_count > 1` 的条目（即跨会话仍然失败的），避免把 PostToolUse 已建议过的同一签名再输出一遍。`fix_count <= 1` 的条目认为"当前会话可处理"，留给 Layer 1。

### 设计

新增 `.claude/hooks/error-dna-auto-fix.sh` — Stop hook

```
触发: Stop
行为:
  1. 读 error-dna.json
  2. 筛选 → count >= 2 AND status != fixed AND repair_command 存在 AND fix_count > 1
     (fix_count > 1 = 跨会话仍失败，避免和 PostToolUse 实时层重复)
  3. 按 count 降序排列，最多输出前 3 条
  4. 只读 — 不修改 error-dna.json、不递增 fix_count（PostToolUse 层负责写）
  5. 输出 additionalContext:
     [error-dna retrospective] {N} 个跨会话失败模式:
     ・ {sig[:16]} ×{count} (已尝试修复 {fix_count} 次) — {message[:80]}
       ▶ 上次修复命令: `{repair_command}`
       └ 上次失败: {last_seen}
```

### 已存在的依赖
- `error-dna.json` 已有 `repair_command`、`fix_count`、`repair_success`、`status` ✅
- `error-dna.sh:236-283` 已有实时 auto-fix（PostToolUse 层）✅
- error_classifier.py 已分类 error_type ✅

### 新增文件
- `.claude/hooks/error-dna-auto-fix.sh` (~40 行 shell)

### 注册
- settings.json 新增 `Stop` event（排在 skill-flywheel 之后）
- harness.yaml `error_dna_auto_fix: true` 开关
- audit-hooks R35 回归：验证 Stop hook 存在 + 只读不写 + 过滤逻辑

### 未覆盖
- hook 架构限制：不自动执行 repair_command，只建议
- 若未来 Claude Code 开放 PostToolUse 执行命令，可升级 Layer 1 为自动执行

---

## 3. 方案 GS-002: 飞轮自愈废弃告警

### 边界处理
`flywheel_analytics.py:18-20` 在 flywheel.log 缺失时返回 `{"error": "flywheel.log not found", ...}`。修改后的 skill-flywheel.sh 必须检测 non-standard JSON（无 `deprecated_skills` 字段），静默跳过而不崩溃。

### 设计

修改 `.claude/hooks/skill-flywheel.sh` — Stop hook 追加段落

```
在现有 analytics 调用 (#42-44) 之后, 追加:
  5. REPORT=".omc/state/flywheel-report.json"
  6. if [ -f "$REPORT" ]; then
       python3 -c "import json; d=json.load(open('$REPORT')); print(json.dumps(d.get('deprecated_skills',[])))" |
       while read -r dep_list; do
         if [ "$dep_list" != "[]" ] && [ -n "$dep_list" ]; then
           echo "additionalContext: [flywheel] ⚠️ 技能废弃检测: $dep_list"
         fi
       done
     fi
  7. 若无废弃或无报告 → 静默退出（不输出 additionalContext）
```

### 已存在的依赖
- `flywheel_analytics.py:72` deprecated_skills 计算 ✅
- `skill-flywheel.sh:42-44` 现有 analytics 调用 ✅
- `flywheel-report.json` 已写入 `.omc/state/` ✅

### 变更文件
- `.claude/hooks/skill-flywheel.sh` — 追加 ~15 行

### 注册
- 已有 Stop event，无需新增注册

---

## 4. 方案 GS-003: 学习笔记自动知识抽取

### 格式兼容

claude-next.md 混合两种格式：

| 格式 | 示例 | 正则 |
|------|------|------|
| `[seed:*]` 条目 | `[seed:typescript] hits:3 @2026-01-01` | `/\[seed:\w+\].*?hits:(\d+)/` |
| 日期条目 | `@2026-05-10 hits:1` | `/@\d{4}-\d{2}-\d{2}.*?hits:(\d+)/` |

### kernel.md 匹配策略

按关键词全文搜索（非手动映射）：
1. 提取 claude-next.md 条目的第一行标签（`[seed:typescript]` → `typescript`，或 `[rpe-014]` → `rpe-014`）
2. `grep -i "{tag}" kernel.md` — 若匹配到任何行，认为"已在 kernel.md"
3. 若未匹配 → 标记"不在 kernel.md"

### 设计

新增 `.claude/hooks/knowledge-condenser.sh` — Stop hook (~70 行 shell)

```
触发: Stop
行为:
  1. 读 .claude/claude-next.md
  2. 正则匹配两种格式 ([seed:*] 和 @YYYY-MM-DD)
  3. 提取每条: 标签(tag) + hits(N) + 创建日期 + 描述
  4. age = (当前日期 - 创建日期).days
  5. 筛选 hits >= 3
  6. 对每条: grep -i "{tag}" kernel.md → 判断是否已在 kernel.md
  7. 按升华规则表分类
  8. 输出 additionalContext (最多 5 条):
     [knowledge-condenser] {N} 个高频模式:
     ・ {tag} (hits:{N}, {age}天) → {建议动作}
       证据: claude-next.md:line:{N}, kernel.md: {found|missing}
  9. 无高频条目 → 静默退出
```

### 升华规则

| hits | age | 已在 kernel.md | 建议 |
|------|-----|---------------|------|
| ≥5 | ≥10天 | 是 | 更新 kernel.md（规则已存在但需补证据） |
| ≥5 | ≥10天 | 否 | **升华至 kernel.md** |
| ≥3 | ≥5天 | 是 | 更新 kernel.md（补证据/修表述） |
| ≥3 | ≥5天 | 否 | 建议升华，标记"待确认" |
| ≥3 | <5天 | 任意 | 标记"待稳定后再升华" |
| <3 | 任意 | 任意 | 忽略 |

### 新增文件
- `.claude/hooks/knowledge-condenser.sh` (~70 行 shell)

### 注册
- settings.json 新增 `Stop` event（排在 error-dna-auto-fix 之后）
- harness.yaml `knowledge_condenser: true` 开关
- audit-hooks R36 回归

### 状态迁移
```
claude-next.md 条目生命周期:
  创建 (hits:1) → 积累 (hits:2) → 高频 (hits≥3) → 升华候补 (hits≥5, age≥10d)
                                                          ↓
                                                    更新 kernel.md
                                                          ↓
                                                    从 claude-next.md 移除（手动）
```

### 回退
升华建议仅通过 additionalContext 输出，不自动修改 kernel.md。AI 读到建议后仍需用户确认才执行。若用户拒绝，不写回 claude-next.md，下次仍会建议。

---

## 5. 方案 GS-004: 治理一致性修复

### 5.1 漂移修复
当前 1 个 🟡 漂移：settings.json:134-146 已为 Read 注册 `posttool-read-cite.sh`（PostToolUse），但 harness.yaml:116 `posttool_read_cite: false`。

**修复**：harness.yaml 改 1 行 `posttool_read_cite: false` → `true`。

### 5.2 自动告警（机制明确）

**方案**：集成到现有的 `.claude/hooks/inject-project-knowledge.sh`（SessionStart hook）。

```
在现有知识注入之后追加:
  调用 .claude/scripts/audit-hooks.sh --check-source-mirror --json
  解析 JSON 输出:
    if drift_count > 0 → additionalContext:
      [governance-drift] 治理一致性告警:
      ・ {N} 个 🟡/🔴 漂移（运行 audit-hooks.sh 查看详情）
      ・ 最后同步时间: {timestamp}
    else → 不输出（无漂移，静默）
```

**理由**：集成到 inject-project-knowledge.sh 无需新增 event registration，复用现有 SessionStart 通道。inject-project-knowledge.sh 本身就是在每个会话开始时注入上下文摘要，治理一致性状态自然属于"需要知道的上下文"。

**audit-hooks.sh 增强**：新增 `--json` flag，输出 JSON 格式的漂移报告供脚本消费。

### 变更文件
- `.claude/hooks/inject-project-knowledge.sh` — 追加 ~15 行
- `.claude/scripts/audit-hooks.sh` — 新增 `--json` flag，R35/R36 回归 case
- `.claude/scripts/harness-smoke-test.sh` — 新增 R35/R36 回归
- `.claude/harness.yaml` — 改 1 行

---

## 6. Stop Hook 执行顺序

settings.json 中 Stop event 的注册数组顺序决定执行顺序：

| 序号 | Hook | 注册来源 | 定位 |
|------|------|---------|------|
| 1 | auto-snapshot.sh | 已有 | 会话快照（状态持久化） |
| 2 | skill-flywheel.sh | 已有 | 飞轮 flush + 废弃告警 |
| 3 | error-dna-auto-fix.sh | 新增 GS-001 | 跨会话错误回顾 |
| 4 | knowledge-condenser.sh | 新增 GS-003 | 知识升华建议 |
| 5 | stop-drain.sh | 已有 | 会话 draining |

**追加策略**：在 settings.json Stop 数组末尾追加 2 个新钩子（error-dna-auto-fix → knowledge-condenser），不改变已有顺序。实际执行顺序：auto-snapshot → stop-drain → skill-flywheel → error-dna-auto-fix → knowledge-condenser。

各 hook 输出不同的 JSON namespace key（`flywheel`, `error-dna`, `knowledge-condenser`），不会互相覆盖。

---

## 7. 回归测试定义

### R35 — error-dna-auto-fix 回归（audit-hooks.sh + harness-smoke）

| Case | 测试内容 | 期望 |
|------|---------|------|
| R35a | `bash -n .claude/hooks/error-dna-auto-fix.sh` | exit 0 |
| R35b | hook 仅读 error-dna.json，不写 | 验证无 `write`/`open('w')`/`json.dump(` 调用 |
| R35c | 无 error-dna.json 时静默退出 | exit 0 |
| R35d | empty error-dna.json 时静默退出 | exit 0 |
| R35e | 有 fix_count<=1 条目不输出 | 过滤正确 |
| R35f | 有 fix_count>1 条目输出附加上下文 | 输出含 `[error-dna retrospective]` |
| R35g | hc_enabled 开关关闭时不执行 | exit 0 |

### R36 — knowledge-condenser 回归（audit-hooks.sh + harness-smoke）

| Case | 测试内容 | 期望 |
|------|---------|------|
| R36a | `bash -n .claude/hooks/knowledge-condenser.sh` | exit 0 |
| R36b | 无 claude-next.md 时静默退出 | exit 0 |
| R36c | 所有条目 hits<3 时不输出 | 无 additionalContext |
| R36d | 有 hits≥3 条目时输出升华建议 | 输出含 `[knowledge-condenser]` |
| R36e | 对 [seed:*] 格式正确提取 | 匹配 tag + hits |
| R36f | 对 @YYYY-MM-DD 格式正确提取 | 匹配 tag + hits |
| R36g | kernel.md 存在性 grep 正确 | `found`/`missing` 标注 |
| R36h | hc_enabled 开关关闭时不执行 | exit 0 |

---

## 8. 源镜像同步程序

所有文件变更后执行：

```bash
# Step 1: 校验主目录与 source 镜像差异
.claude/scripts/audit-hooks.sh --check-source-mirror

# Step 2: 若存在 drift，手动同步新增/修改文件到 source/harness-kit/
# 新增 hook: cp .claude/hooks/error-dna-auto-fix.sh source/harness-kit/.claude/hooks/
# 新增 hook: cp .claude/hooks/knowledge-condenser.sh source/harness-kit/.claude/hooks/
# 修改 hook: cp .claude/hooks/skill-flywheel.sh source/harness-kit/.claude/hooks/
# 修改 hook: cp .claude/hooks/inject-project-knowledge.sh source/harness-kit/.claude/hooks/
# 脚本: cp .claude/scripts/audit-hooks.sh source/harness-kit/.claude/scripts/
# 脚本: cp .claude/scripts/harness-smoke-test.sh source/harness-kit/.claude/scripts/
# yaml: cp .claude/harness.yaml source/harness-kit/.claude/
# json: cp .claude/settings.json source/harness-kit/.claude/

# Step 3: 二次校验
.claude/scripts/audit-hooks.sh --check-source-mirror
```

---

## 9. 文件变更汇总

| 文件 | 类型 | GS# |
|------|------|-----|
| `.claude/hooks/error-dna-auto-fix.sh` | **新增** | GS-001 |
| `.claude/hooks/skill-flywheel.sh` | 修改 (+15 行) | GS-002 |
| `.claude/hooks/knowledge-condenser.sh` | **新增** | GS-003 |
| `.claude/hooks/inject-project-knowledge.sh` | 修改 (+15 行) | GS-004 5.2 |
| `.claude/scripts/audit-hooks.sh` | 修改 (+--json flag, R35/R36) | GS-004 |
| `.claude/scripts/harness-smoke-test.sh` | 修改 (+R35/R36 cases) | GS-004 |
| `.claude/harness.yaml` | 修改 (1 行 + 2 开关) | GS-004 + GS-001/003 |
| `.claude/settings.json` | 修改 (2 个 Stop 注册) | GS-001, GS-003 |
| `source/harness-kit/` | 同步 (8 文件) | 全部 |

---

## 10. 验证方案

| # | 检查项 | 命令/方法 |
|---|--------|----------|
| V1 | error-dna-auto-fix.sh 只读不写 | `grep -c 'write\|open.*w\|json.dump' .claude/hooks/error-dna-auto-fix.sh` = 0 |
| V2 | fix_count>1 过滤 | 脚本内 assert filter 逻辑 |
| V3 | Stop hook 语法 | `bash -n .claude/hooks/*.sh` |
| V4 | flywheel-report.json deprecated 字段 | `python3 -c "import json; print(json.load(open('.omc/state/flywheel-report.json')).get('deprecated_skills'))"` |
| V5 | knowledge-condenser 双格式解析 | `python3 -c "import re; c=open('.claude/claude-next.md').read(); print(len(re.findall(r'hits:([3-9]|\d{2})',c)))"` |
| V6 | harness.yaml posttool_read_cite=true | `grep 'posttool_read_cite: true' .claude/harness.yaml` |
| V7 | source mirror 一致 | `bash .claude/scripts/audit-hooks.sh --check-source-mirror` — 0 漂移 |
| V8 | harness-smoke 回归 | `bash .claude/scripts/harness-smoke-test.sh` — 全部 pass |
| V9 | 全部 .sh 语法检查 | `bash -n .claude/hooks/*.sh .claude/scripts/*.sh` |

---

## 11. 风险与回退

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Hook 语法错误阻断 Stop | 低 | 低 | 全部 `exit 0` 兜底 |
| knowledge-condenser 误报升华 | 中 | 低 | 只建议不执行，额外增加 "已在 kernel.md" 校验 |
| Stop hook 输出过多浪费上下文 | 低 | 中 | 各自限 top 3-5 条 + 无符合条件时静默退出 |
| 源镜像手动同步遗漏 | 中 | 中 | commit 前二次校验 + R37 回归 |
| **回退**: `git revert` + 重新 `source/harness-kit/` 同步 | — | — | 全程保留 source mirror 一致性 |

---

## 12. 预估提升

| 维度 | 基线 | 目标 | 杠杆 |
|------|------|------|------|
| 🛡️ 抗衰减防线 | 68 | **82** | +14: 跨会话回顾聚合 |
| 🔄 飞轮自愈 | 63 | **80** | +17: 废弃告警注入 |
| 📝 学习笔记积累 | 70 | **82** | +12: 自动知识抽取 |
| 🔗 治理一致性 | 65 | **85** | +20: 漂移修复 + SessionStart 自动告警 |
| **加权综合** | **68** | **~82** | **+14** |
