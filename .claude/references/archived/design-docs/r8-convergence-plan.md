# CarrorOS 收敛+巩固方案 (R8)

> 背景：冷启动31维评测加权7.12/10，目标门禁≥8.6。
> 战略：不新增功能、不新增Gate。只修复现有机制的断裂点、清理技术债、关闭文档-代码落差。

---

## 问题树

```
7.12 → 8.6 (+1.48 = +320/2150分)
├── 可快速收敛项 (+220分)
│   ├── E1(20w) 6→8: edit-scope 从WARN升格为真实BLOCK
│   ├── C6(10w) 6→8: error-dna error_type 分类引擎实装
│   ├── E5(10w) 6→8: 同上（共享改善）
│   ├── G3(1s) 5→8: sublimation→kernel-candidates 管道通
│   ├── G5(1s) 6→8: harness.yaml 死配置清理
│   ├── G6(1s) 7→8: blast_radius 代码实装
│   └── G2(1s) 6→8: carros_base auto 链实现
├── 重构项 (+120分)
│   ├── C7(10w) 7→9: pretool-gate 模块拆分
│   ├── C8(10w) 7→9: 同上
│   └── G7(1s) 7→9: eval-aggregate.py + 框架路径修复
└── 数据积累项（需时间）
    ├── C2(15w) 7→8: handoff 质量提升
    └── E8(10w) 7→8: read-tracker 跨会话
```

---

## R8.1 — 快速收敛（P0级，依次执行）

### 1. edit-scope → 真实BLOCK
**当前**: WARN+逃逸升级（前2WARN→3+BLOCK）。ai_self_decision.md Rule 2 说"非高危不打断"。
**收敛方向**: 将 scope 越界重新分级——**治理文件路径**直接 BLOCK（#6零信任），其他路径保持逃逸升级不变。
**改动**: pretool-gate.py `_check_edit_scope()` 增加治理文件路径前置判断
**预计提分**: E1 +1 (+20pts)

### 2. error_type 分类引擎实装
**当前**: `error_rulers.json` 已有 17 条规则（commit 0572264），但 `error-dna.jsonl` 197 条记录全部 `error_type="?"` — 新引擎写了但未接入运行时。
**收敛方向**: 排查新引擎接入断点，确保 error-dna.py 运行时调用规则分类器。
**改动**: error-dna.py 采集管线的分类器路由
**预计提分**: C6/E5 +2 (+40pts)

### 3. sublimation 通堵
**当前**: 管道修复了(`kernel-candidates.md` 已创建)但 claude-next 只有 9+5 条种子数据，升华阈值 5 条远高于输入。
**收敛方向**: 将升华阈值从 5 降到 3，让 seed 数据更快进入管道。
**改动**: stop-flywheel.py `SUBLIMATION_HITS = 5 → 3`
**预计提分**: G3 +2

### 4. harness.yaml 死配置清理
**当前**: 50 个 hook disabled（oracle_gate/plan_gate/edit_guard/lsp_suggest 等），标注"低ROI — 关闭"但从未删除。
**收敛方向**: 列出 2 年内无计划的死 toggle，batch 移除。
**改动**: .claude/harness.yaml 删 40+ 行死配置
**预计提分**: G5 +2

### 5. blast_radius 实装
**当前**: harness.yaml:62 `blast_radius: true` 但代码不存在（仅在 worktree 存档中有）。
**收敛方向**: 把 worktree 中的 `pretool-blast-radius.py` 逻辑（检测 `git checkout .` / `rm -rf` 全量操作→提示用选择性路径）合并入 pretool-gate.py。
**改动**: pretool-gate.py +40 行
**预计提分**: G6 +1

### 6. carros_base auto 链
**当前**: init→tick→verify→archive 全是分段 CLI 命令。
**收敛方向**: 加一个 `carros_base.py auto` 命令，一键走完完整闭环。
**改动**: carros_base.py +30 行
**预计提分**: G2 +2

---

## R8.2 — 代码重构（P1级）

### 7. pretool-gate 模块拆分
**当前**: 2290 行单文件，含 22 个 gate 函数 + 5 个辅助模块。
**收敛方向**: 拆成 3 个文件：
- `pretool-core.py` — 共享逻辑(SSOT/audit/token/streak/in_scope)
- `pretool-gates.py` — 22 个 gate 函数
- `pretool-gate.py` — 主入口(路由表+main loop)
**改动**: 新加 2 文件，遗留入口不变
**预计提分**: C7/C8 +2 (+40pts)

### 8. eval-aggregate.py 补全
**当前**: evaluation-framework.md step 5 引用了此脚本但不存在。
**收敛方向**: 实现 60 行聚合脚本，读 scorecard + meta-oracle → eval-report
**改动**: 新文件 `.claude/scripts/eval-aggregate.py`
**预计提分**: G7 +2

---

## 提分计算

| 轮次 | 项 | 加分 | 新总分 |
|:----:|:---|:----:|:------:|
| 基线 | — | — | **7.12** |
| R8.1.1 | E1 +1 (20pts) | +0.01 | 7.13 |
| R8.1.2 | C6/E5 +2 (40pts) | +0.02 | 7.15 |
| R8.1.3 | G3 +2 (+2s) | +0.01 | 7.16 |
| R8.1.4 | G5 +2 (+2s) | +0.01 | 7.17 |
| R8.1.5 | G6 +1 (+1s) | +0.005 | 7.18 |
| R8.1.6 | G2 +2 (+2s) | +0.01 | 7.19 |
| **R8.1小计** | **~7项** | **+0.075** | **~7.20** |
| R8.2.1 | C7/C8 +2 (40pts) | +0.02 | 7.22 |
| R8.2.2 | G7 +2 (+2s) | +0.01 | 7.23 |
| **R8总计** | **~9项** | **+0.11** | **~7.23** |

---

## 诚实说

**R8 收敛到 7.23~7.25 合理，到 8.6 不够。**

需要的真实差距：+320 分 / 2150。收敛只能拉 ~+100 分。
余下的 +220 分需要结构性改善(C2 handoff 质量/C6 管道数据积累/C8 模块化等)，是**时间问题**不是代码问题。

**建议**: R8 走收敛路线拿到 ~7.23 后先锁版，跑 2-3 周让管道产生真实数据，再用数据驱动第二次提分。

---

## 三模型审问

请三位老师审以下三个问题，给 verdict + 依据：

1. **收敛方向正确吗？** R8.1(快速收敛6项)+R8.2(重构2项) 是否抓住了当前从 7.12→8.6 最关键的杠杆？漏了什么？过度设计了什么？

2. **edit-scope 到真实 BLOCK 可行吗？** ai_self_decision.md Rule 2 说"非高危不打断"，但当前系统 154 条 scope_violation 记录证明 WARN 不够。治理文件路径直接 BLOCK vs 非治理路径逃逸升级——这个两分法合理吗？

3. **收敛到 7.23 后是否应该锁版积累数据？** 还是应该继续施工直到 8.6？
