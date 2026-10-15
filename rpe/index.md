# 项目决策大脑 — CarrorOS

> 本文件是**项目级状态源**。AI 在 `lx-rpe new` 开工前**必读**。
> 维护规则见 `.claude/skills/lx-rpe/SKILL.md` §决策大脑。

## 当前阶段

- 目标：把「决策大脑」跑通——rpe 开工前读、验收后写、冲突弹人
- 非范围：不改 lx-goal（无人值守路径不受本机制影响）
- 开放问题：热区满 10 条后归档由 AI 自动做还是提醒用户做？

## Feature 清单

| Feature | 状态 | 决策区间 |
|---|---|---|
| lx-rpe 决策大脑机制 | 已完成（待验收） | DEC-001 ~ DEC-003 |

## 决策日志

> 时间倒序（最新在前）。每条 ≤ 半屏，四字段必填。

### DEC-003 冲突检测：脚本只判不可逆，语义判断交给 AI

- date: 2026-09-15
- feature: lx-rpe 决策大脑机制
- chose: 脚本 `detect_conflicts` 只确定性判「不可逆操作」（关键词表）；再由 `related_decisions` 把相关决策端到 AI 面前，语义冲突由 AI 判
- why: 首版想做全自动子串匹配，实测两次假阳性——rejected 含「各 feature 目录里各记各的」，先命中 token「feature」（拦下一切含 feature 的意图），加黑名单后又命中「目录里各记各的」。中文短语切分不可靠，子串匹配必然误报
- rejected: 脚本全自动判语义冲突 —— 假阳性比漏报致命：误拦几次用户就绕过机制，机制随即死亡。宁可脚本少判、AI 多读
- result: 假阳性归零；22 项测试全绿

### DEC-002 强制靠门禁，不靠 AI 自觉

- date: 2026-09-15
- feature: lx-rpe 决策大脑机制
- chose: 在 check_gates.py 增 P0（开工前「读了没」，查 `state/brain-read.md`）与 E11（验收后「写了没」，查 executor.md 的 `决策回写: DEC-N`）
- why: 文档机制最大的死法不是设计错，是**没人执行**。「读大脑」若只写在 SKILL.md 里要求 AI 照做，AI 会跳过且无人察觉——与 CarrorOS 零信任原则（灵魂 3：断言须独立验证）冲突
- rejected: 只在 SKILL.md 写规范、靠 AI 自觉执行 —— 这正是「死文档」的标准生成路径，文档写完即开始腐烂
- result: 实测两道门均真拦得住（无痕 FAIL / 有痕 PASS）；已固化为回归测试 test_decision_brain_gates

### DEC-001 建立 rpe 决策大脑机制（自举）

- date: 2026-09-15
- feature: lx-rpe 决策大脑机制
- chose: 在 `rpe/index.md` 建立项目级决策大脑，作为 lx-rpe 的基础机制——开工前 `read` 必读热区、`check` 冲突检测、验收后 `append` 回写
- why: 同一个瓶颈反复问 AI 会空转——它不知道上轮摔在哪，每次都从零出方案，本轮提议下轮又被否，用户被迫重复解释。决策外化成文档后，AI 每轮都长在真实轨迹上，而非每轮重置
- rejected: 散落在各 feature 目录里各记各的决策 —— 换会话/换模型后上下文全丢，且看不到跨 feature 的决策冲突
- result: 机制已落地，两轮实测 + 22 项测试通过

## 冷区：历史决策索引

> 超过 10 条的决策移到这里，只留一行摘要 + 需要时再展开。

（暂无）
