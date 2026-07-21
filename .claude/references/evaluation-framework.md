# CarrorOS 科学评测框架 v1

> 目标：解决"自评缺乏外部视角，外评缺乏纵向追踪"的根本矛盾。
> 方法：**Longitude(纵向追踪) + Latitude(独立审计) + Adversarial(对抗合成)** 三元组合。

## 核心公式

```
最终分 = 纵向追踪分 × 0.6 + 独立审计分 × 0.4

纵向追踪分 = baseline + Σ(verified_delta_i) / total_target
独立审计分 = G1×0.35 + G2×0.25 + G3×0.20 + G4×0.20
```

- `baseline` = 6.30（R0 基线，已锁）
- `verified_delta_i` = 该轮提分 × 回归通过率(0 或 1) × 裁决通过率(0-1)
- 审计每 3 轮或每次重大迭代后做一次（非每次）

---

## 四层架构

```
                     ┌─────────────────────────────┐
                     │  Layer 4 对抗合成             │
                     │  分差报警 + 分歧根因分析       │
                     │  → 作为下轮改进输入            │
                     ├─────────────────────────────┤
                     │  Layer 3 独立审计 (Latitude)   │
                     │  Meta-Oracle G1-G4 框架       │
                     │  双模型交叉验证 · 每3轮一次     │
                     ├─────────────────────────────┤
                     │  Layer 2 增量提分账 (Longitude)│
                     │  scorecard.md 纵向跟踪         │
                     │  [commit, 回归证据, 裁决] 三元组│
                     ├─────────────────────────────┤
                     │  Layer 1 回归地基 (Ground Truth)│
                     │  12 套件一键跑                 │
                     │  bash scripts/run-regression.sh│
                     └─────────────────────────────┘
```

### Layer 1 — 回归地基

**什么**: 12 套自动化测试套件，一键 `bash scripts/run-regression.sh`

| # | 套件 | 文件 | 覆盖 |
|---|------|------|------|
| 1 | context-watermark | test-context-watermark.py | 水位 B 三段策略 |
| 2 | oracle-gate | test-oracle-gate.py | oracle 三层对抗审核 |
| 3 | verify-gate | test-verify-gate.py | VerifyGate 双绑定 |
| 4 | goal-mode-gate | test-goal-mode-gate.py | goal 模式降级/恢复 |
| 5 | hook-launcher | test-hook-launcher.sh | launcher 自锚定/fail-closed |
| 6 | pkg-c-lifecycle | test_pkg_c_lifecycle.py | 生命周期 pkg |
| 7 | task-ssot | test-task-ssot.py | 任务状态源 SSOT |
| 8 | e4-inertia | test-e4-inertia.py | E4 惯性执行防护 |
| 9 | audit-schema | test-audit-schema.py | 审计 schema 合规 |
| 10 | nine-challenge | test-nine-challenge.py | 9 分挑战 |
| 11 | lx-stepwise | test-lx-stepwise.py | 逐步执行 |
| 12 | lifecycle-mutex | test-lifecycle-mutex.py | 生命周期互斥 |

**规则**:
- 回归通过 = 证据硬门槛，不可绕过
- 基线首次跑录 `benchmark/runs/{date}-baseline.json`
- 每次提分时回归必须 rc=0
- `run-regression.sh --json` 输出结构化结果给下游

### Layer 2 — 增量提分账 (Longitude)

**什么**: 从基线 6.30 开始的每一次提分，有一个**三元组**证据锁死

```
每次提分必须包含:
  [commit_sha]   → "这分谁改的" —— git commit hash
  [回归证据]      → "跑通了吗" —— scripts/run-regression.sh rc=0 日志
  [裁决记录]      → "三模型认可吗" —— 终审票决记录
```

**数据源**: `improve_plan/CarrorOS_second_time/scorecard.md`

**格式规范**（每轮记录）:
```markdown
| R3 | 上下文重建/三端handoff | commit fc8d156 | A0-A12 全绿 | grok 零改动通过 |
```

**纵向分计算**:
```
delta = (当前加权 - baseline) / (目标加权 - baseline)
纵向追踪分 = 6.30 + delta × 3.70  (注: 3.70 = 10.0 - 6.30)
```

### Layer 3 — 独立审计 (Latitude)

**什么**: 使用 G1-G4 门禁框架对快照做独立外评

| 门禁 | 权重 | 内容 | 最低通过 |
|------|------|------|---------|
| G1 证据质量 | 0.35 | 每项评分必须有回归证据或 file:line 引用 | 6/10 |
| G2 范围冻结 | 0.25 | 只评声明的评估范围 | 5/10 |
| G3 验收 | 0.20 | 必须有硬指标验证（回归/命令输出） | 6/10 |
| G4 哲学一致性 | 0.20 | 评分遵循 Carror 7 哲学优先级 | 5/10 |

**审计规则**:
- 审计由 `.claude/scripts/meta_oracle.py` 执行
- 建议每 3 轮或重大架构变更后执行
- 每次审计用不同模型（防模型偏差）
- 输出写入 `.omc/state/meta-oracle-verdicts/eval-v{N}/`

### Layer 4 — 对抗合成 (Adversarial Synthesis)

**什么**: 比较纵向分与审计分，量化内外差异

```
Δ = |纵向追踪分 - 独立审计分|

Δ < 0.5 → 可信区间，内外一致
0.5 ≤ Δ < 1.0 → 注意，建议查明差异来源
Δ ≥ 1.0 → 报警，显著分歧
```

**分歧分类**:
| 模式 | 含义 | 处理 |
|------|------|------|
| 纵向高 × 审计低 | 自评盲点（系统可能不如自评好） | 确认是否存在未被发现的退化 |
| 纵向低 × 审计高 | 审计漏证据（外评没读到位） | 补充审计深度 |
| 大部分一致 × 少数偏移 | 局部偏差 | 对齐单项分数 |

**输出**: 每次合成都写入 `eval-report.md`，包含最终得分、分歧分析、下一轮建议

---

## 评分表（沿用 scorecard 口径）

### 能力维度 C1-C9

| C | 指标 | 权重 | 基线 | 当前 | 目标 | 状态 |
|---|------|------|------|------|------|------|
| C1 | 指令清晰度 | 15 | 6 | 9 | ≥9 | ✅ |
| C2 | 上下文完整度 | 15 | 7 | 9 | ≥9 | ✅ |
| C3 | 流程结构化 | 15 | 7 | 9 | ≥9 | ✅ |
| C4 | 输出规范化 | 10 | 8 | 8 | ≥9 | ⬜ |
| C5 | 工具生命周期 | 10 | 6 | 9 | ≥9 | ✅ |
| C6 | 知识密度 | 10 | 7 | 9 | ≥9 | ✅ |
| C7 | 关联编排 | 10 | 6 | 9 | ≥9 | ✅ |
| C8 | 可维护性 | 10 | 5 | 8 | ≥9 | ⬜ |
| C9 | 错误恢复 | 10 | 7 | 9 | ≥9 | ✅ |

### 错误防护 E1-E8

| E | 指标 | 权重 | 基线 | 当前 | 目标 | 状态 |
|---|------|------|------|------|------|------|
| E1 | 目标漂移 | 20 | 6 | 8 | ≥9 | ⬜ |
| E2 | 幻觉输出 | 20 | 6 | 9 | ≥9 | ✅ |
| E3 | 虚假完成 | 15 | 4 | 9 | ≥9 | ✅ |
| E4 | 惯性执行 | 12 | 7 | 8 | ≥9 | ⬜ |
| E5 | 症状混淆 | 10 | 7 | 8 | ≥9 | ⬜ |
| E6 | 自我矛盾 | 13 | 5 | 9 | ≥9 | ✅ |
| E7 | 过度自信 | 10 | 7 | 8 | ≥9 | ⬜ |
| E8 | 上下文遗忘 | 10 | 7 | 9 | ≥9 | ✅ |

### 长期治理（7 维）

| 维度 | 基线 | 当前 | 目标 |
|------|------|------|------|
| 抗衰减防线 | 7 | 9 | ≥9 |
| AI 赋能全流程自动化 | 8 | 8 | ≥8 |
| 学习笔记积累 | 6 | 8 | ≥9 |
| 长期目标一致性 | 8 | 8 | ≥8 |
| 功能标志分明 | 5 | 8 | ≥9 |
| 内置安全与洞察 | 6 | 8 | ≥9 |
| Evaluation 评测框架 | 9 | 9 | ≥9 |

---

## 裁定标准

| 条件 | 判定 |
|------|------|
| 回归全部通过 | 通过 |
| 24 项加权 ≥ 8.6 | 通过 |
| 最低单项 ≥ 8.0 | 通过 |
| Δ < 1.0 | 可信 |
| 上三者 + Δ < 0.5 | **GREEN** |
| 上三者 + 0.5 ≤ Δ < 1.0 | **YELLOW** |
| 有回归失败 / Δ ≥ 1.0 | **RED** |

---

## 使用流程

```text
1. 提分施工 → git commit + 跑回归: bash scripts/run-regression.sh
2. 回归全过 → 写 scorecard.md 记录三元组
3. 每 3 轮 → 独立审计: python3 .claude/scripts/meta_oracle.py aggregate --policy duo
4. 合成报告: python3 scripts/eval-aggregate.py --scorecard X --meta-verdict Y
5. 读 eval-report.md: 得分 + 分歧分析 + 下轮建议
6. Δ ≥ 1.0 必须查明原因后才可继续迭代
```

---

## 文件清单

| 文件 | 职责 |
|------|------|
| `.claude/references/evaluation-framework.md` | 本文件——框架规范 |
| `scripts/run-regression.sh` | 回归地基（已有，维持） |
| `scripts/eval-aggregate.py` | 合成器——读 scorecard + 审计 → 出报告 |
| `.claude/scripts/meta_oracle.py` | 审计器——G1-G4 框架（已有，维持） |
| `improve_plan/CarrorOS_second_time/scorecard.md` | 纵向账本（已有，维持） |
| `benchmark/runs/` | 基准回归存档（已有，维持） |

---

> schema_version: evaluation-framework.v1
> 创建: 2026-07-21
