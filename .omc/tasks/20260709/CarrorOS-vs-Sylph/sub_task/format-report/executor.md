# SubAgent: 

## 产出

# CarrorOS vs Sylph 对比分析报告

## CarrorOS 优势

1. **架构精简** — **18** 个 hooks（pretool/posttool）vs Sylph 的 **92** 个 .py 脚本，降低一半治理负担
2. **Goal 状态机** — CLARIFY→PLANNING→EXECUTING→VERIFYING→ARCHIVING 完整闭环，优于 Sylph 的 L1/L2 平面工作流
3. **SubAgent 主从架构** — carros_base.py(**64K**) + sub_agent_manager.py(**33K**) + sub_agent_executor.py(**9K**)，三层职责分明
4. **前置门+后置闸统一化** — pretool-gate.py 把 **7** 个单独 hook 合并成 **1** 个单进程，减少 **6** 倍进程开销
5. **证据账本** — executor_ledger.py 标准化 E0-E3 证据等级

## CarrorOS 劣势

- SubAgent 仍不够「纯」 — executor.py 的 SUBAGENT_SYSTEM_PROMPT 写着「不读文件、不分析架构」，但实际还是让 subagent 做推理
- 缺乏大规模发布/安装机制 — 没有 Sylph 那种 **100+** tar.gz 版本的发布流水线
- Skills 生态不成熟 — 没有 Sylph 的 **31** skill + **20** node 体系
- 缺少 **15** 维能力矩阵测试 — 没有 capability-matrix-test.sh 这种大规模验证
- 测试体系单薄 — 对比 Sylph 的 **42K** 行 capability-matrix-test.sh + **104K** 行 harness-smoke-test.sh

## Sylph 优势

1. **完整发布流水线** — v6.2.8 到 v7.0.2，**100+** 个 tar.gz 版本迭代
2. **巨型测试覆盖网** — capability-matrix-test.sh(**42K**) + harness-smoke-test.sh(**104K**) + auto-score.sh(**55K**)
3. **成熟 Skill/Node 生态** — **31** skill + **20** node，三源一致性
4. **多模型适配** — 从 v6.2 到 v7.0 见证了 Opus→GPT-4→DeepSeek 迁移历程

## Sylph 劣势

- **严重膨胀** — **607** 行 settings.json，**92** 个 hooks，单文件最大 **104K** 行
- **没有 Goal 状态机** — 还在用 L1/L2 base/enhance 平面工作流
- **SubAgent 机制简陋** — dispatch-subagent.py(**7K**) + poll-subagent.py(**3.7K**) vs CarrorOS 的三层架构
- **治理开销过高** — completion-gate.py(**703**行)做 **20+** 验证，每次 TaskUpdate 都要过一遍

## 适配对比表

| 维度 | CarrorOS→DeepSeek-V4-Flash | Sylph→Opus/GPT-5.5 |
|------|---------------------------|-------------------|
| 治理复杂度 | ✅ 精简，DeepSeek 长上下文友好 | ❌ 膨胀，高阶模型上下文被治理吞噬 |
| SubAgent 架构 | ✅ 三层主从清晰 | ❌ 简陋，难以发挥高阶模型推理 |
| 发布能力 | ❌ 无发布流水线 | ✅ 完整版本管理 |
| 测试覆盖 | ❌ 薄弱 | ✅ 15维矩阵+冒烟+评分 |
| Goal 自闭环 | ✅ 有 | ❌ 无 |
| Context 效率 | ✅ 高（少而精） | ❌ 低（多而杂） |

## 核心结论

CarrorOS 的架构方向是对的——精简、Goal 状态机、SubAgent 主从，非常适合 DeepSeek-V4-Flash 的性价比路线（低推理成本 × 高效治理）。Sylph 的测试/发布生态是 CarrorOS 需要吸收的，但其膨胀度不适合 DeepSeek 这类模型——Sylph 更适合 Opus/GPT-5.5 这种能扛住大上下文的模型。
