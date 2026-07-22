# Flywheel System — 飞轮系统方案

## 目标

每次任务执行后自动采集知识，日终升华到 kernel.md，让 AI 越用越懂项目。

## 架构

```
执行结束 → 采集 → 本地存储 → 日终升华 → kernel.md
            ↓
   [token预算门禁]
```

## 数据采集（每次任务后自动）

| 数据源 | 内容 | 上限 | 存储位置 |
|:------|:----|:----|:--------|
| **决策日志** | 本次执行的 key decisions + 为什么选这个方案 | 500 chars | `.omc/flywheel/decision-log.jsonl` |
| **.claude-next.md** | 新学到的项目知识（架构/约定/API 用法）| 2K tokens | `.claude/claude-next.md` |
| **.error-dna** | 失败模式（error type → root cause → fix → prevent）| 1K tokens | `.claude/error-dna.jsonl` |
| **anti-patterns** | 什么方式在这个项目里不 work | 1K tokens | `.claude/anti-patterns.md` |

## 升华管道（每日 cron）

### 数据源 → LLM 提炼 → HITL 审核 → kernel.md 写入

1. **读取**：从四数据源读取当日新增内容
2. **提炼**：高阶模型（Opus/GPT）聚合 → 去重 → 摘要
3. **冲突检测**：新内容与 kernel.md 现有知识有无矛盾
4. **HITL 门禁**：
   - 无冲突 → 自动追加到 kernel.md
   - 有冲突 → 记录到 `.omc/flywheel/conflicts/`，等人工裁决
5. **写入**：通过门禁 → 追加到 kernel.md 对应章节

### Cron 计划

```yaml
# ~/.hermes/cron/flywheel-daily.yml
schedule: "0 22 * * *"  # 每晚10点
mode: no_agent
script: .claude/scripts/flywheel-daily.sh
```

## 采集触发器

在 lx-goal 退出前验证的 Step 6 执行采集：

```bash
# 采集决策要点
python3 .claude/scripts/flywheel-collect.py --from executor.md
# 追加到 claude-next
flywheel log --type knowledge "新知识摘要"
# 记录失败
flywheel log --type error "错误模式+修复" 
```

## 文件结构

```
.omc/flywheel/
  decision-log.jsonl    # 决策日志（append only）
  conflicts/            # 冲突记录（待人工裁决）
  daily/                # 日终升华产物
  
.claude/
  claude-next.md        # 正向知识（≤2K tokens）
  error-dna.jsonl       # 错误模式（≤1K tokens）
  anti-patterns.md      # 无效模式（≤1K tokens）
```

## 实施步骤

| Step | 内容 | 工作量 |
|:----:|:----|:-----:|
| 1 | 创建 `flywheel-collect.py` 采集脚本 | 小 |
| 2 | 创建 `flywheel-daily.sh` 升华脚本 | 中 |
| 3 | 注册 cron job | 小 |
| 4 | HITL 冲突检测逻辑 | 中 |

## 风险

| 风险 | 缓解 |
|:----|:-----|
| kernel.md 被污染 | HITL 门禁 + 冲突检测 |
| 数据膨胀超 token 预算 | 按数据源硬上限截断 |
| 重复知识积累 | LLM 聚合时去重 |
