# Round7 联合优化方案 — 四模型收敛执行计划

> 来源：opus-4.8 / gpt-5.6Sol / grok-4.5 三模型产出(round7/opus.md·gpt.md·grok.md)+ kimi-k3 可行性核验(feasibility.md)
> 纪律：采纳 GPT 18 禁止/10 准入——改生产路径非旁路 demo、每项 ≥1 正向 + ≥2 对抗测试、无第二真相源、回归随每项走
> 口径：Grok G-Eng/G-Org 双门——内置安全(R6-B,owner 认领中)未闭合前，只宣称 G-Eng，不宣称"全面 9+"

## PKG 总表(按收敛度×效能排序)

| PKG | 内容 | 模型共识 | 目标分 | 状态 |
|---|---|---|---|---|
| 1 | 状态 SSOT:`lib/task_ssot.py` 统一 active-token reader，三钩委托 | 3/3 P0 | 治理·自动化 8→9 | **首批** |
| 2 | E7 校准账：audit 复用 claim_id/refutes_claim_id + 机读报表(GPT 轻量版) | 3/3 | E7 8→9 | 二批 |
| 3 | pre-commit 接 run-regression.sh(人类安装 hook，脚本侧就绪) | 3/3 | 支撑自动化 | 二批 |
| 4 | C4 输出 schema 机检(stdlib，挂 cmd_lint) | 3/3 | C4 8→9 | 二批 |
| 5 | 飞轮升华质量门：unknown 降权/细分(flywheel.py:176 前过滤) | grok | 学习笔记 8→9 | 二批 |
| 6 | E4:gate 同签名失败≥3→ESCALATE + 水位 45% 预警层 | opus | E4 8→9 | 三批 |
| 7 | 对抗测试扩充：goal/ghost 互斥、E2/E3 trust、malformed JSON、终态 token 复活 | 3/3 | 护全表 | 随各 PKG |
| 8 | E5 root_cause 字段(plan 审计链) | 候选 | E5 8→9 | 三批 |

## PKG-1 设计(首批施工，本文件即其方案)

**问题**：三处 token 读取逻辑各自为政。今日幻影修复只覆盖两处(pretool-gate/user-approve 的 `_latest_token`);`session-start.py:68` 仍裸 mtime 无终态过滤——同类事故的幸存副本。

**施工**：
1. 新建 `.claude/scripts/lib/task_ssot.py`——单一真相源：
   - `TERMINAL_STATUS = ("archived", "done", "completed")`
   - `latest_active_token(tokens_dir, *, require_stats=False) -> Path | None`(mtime 序 × 终态过滤 × task-dict 校验 × 可选 stats 要求)
   - `read_token(path) -> dict | None`(容 malformed JSON)
2. `pretool-gate.py:_latest_token` → 委托(保 stats 要求)
3. `pretool-user-approve.py:_latest_token` → 委托(保 stats 要求)
4. `session-start.py:_active_token_brief` → 委托 + 保留其 staleness 展示逻辑
5. 导入路径：hooks 以 `ROOT/.claude/scripts` 入 sys.path(hooks 已有 ROOT 推导)

**验证**：
- 正向：active token mtime 旧于 archived → 仍取 active
- 对抗 1：仅 archived/malformed/non-task 三类 token 存在 → 返回 None(今日幻影形态全灭)
- 对抗 2：构造 archived token mtime 最新 → 被跳过，取次新 active
- 回归：6 套件全绿

## 人类专属清单(不可代劳)

| 项 | 内容 |
|---|---|
| R6-B | Moonshot console token 轮换(owner 认领中) |
| pre-commit 安装 | `cp scripts/pre-commit .git/hooks/`(脚本侧二批备好) |
| AGENTS.md §外部挑战记录 | 冻结文档，opus 提案待裁决 |
| E2/E3 trust_level 区分设计 | 设计裁决 |
| E3 token 目录机械写保护 | 设计裁决(rm 硬边界目前是规则层) |
| UX 两维 | 真实 UX 证据或"维度不适用"裁决 |
| 19 个 archived 旧 token 批量删除 | >5 文件 rm；过滤器落地后已惰性，可不做 |

## 分数路径(诚实账)

```
1931(8.70) → +E1(幻影修复在录,+20) → 1951(8.79)
  → PKG-1 自动化 +10 → 1961(8.83)
  → PKG-5 学习笔记 +10 → 1971(8.88)
  → PKG-2 E7 +10 → 1981(8.92)
  → PKG-4 C4 +10 → 1991(8.97)
  → PKG-6 E4 +12 → 2003(9.02) ← G-Eng 过 9.0 线
  → PKG-8 E5 +10 → 2013(9.06)
G-Org:内置安全 8.0(R6-B 人类)→ 不宣称全面 9+
```


---

# 第二轮更新(2026-07-20 S4b): *_full 断点去重合并完成

**主表 → `breakpoint-merge.md`**(三方共识 13 项去重 / 冲突裁决 7 项 / opus 幻觉清单 6 条 / PKG-2..PKG-7 施工包 / 人类清单 H-1..H-11)。

关键变更(相对本文件第一轮):
1. **分数口径统一为官方 baseline 1920/2220=8.65**(grok L83:以 scorecard.md 加权和为准;本文件第一轮的 1931 系自评含 E1 幻影 +20,待终审认定)
2. **施工包重编号**:第一轮 PKG-2..PKG-8 作废,以 breakpoint-merge.md §四 PKG-2..PKG-7 为准(PKG-1 状态SSOT 已交付,7/7 绿)
3. **opus 方案形式大量拒绝**(5 个新文件=第 4 套机制,违 GPT §6.2+grok 否决;其 gate 编号/路径/45% 水位/kernel.md 声明均系幻觉,见合并表 §三);意图折叠:校准账→现有 audit 加字段,failure-escalate→pretool-gate 内置,pre-commit 模板→人类清单 H-5
4. **PKG-1 后新揪出 3 活体第二读法 + 1 僵尸库 + 1 死导入**:posttool `_active_task`(:59-77)/precompact `_latest_token`(:33-48)/meta-oracle `_latest_task_id`(:31-45) 仍按 mtime 无终态过滤;carroros_hooklib.py 全库零调用方;posttool-gate.py:144 `from lib.error_dna import` 模块不存在=error DNA 静默死 → PKG-2 清零
5. **E4 真缺口定位**:终态 token→auto-init 误生(今日劫持环路根因),非 opus 所称 warn 模式 → PKG-3
6. **E5 一票断点**:GPT A-R7-07 自设条件(现有 schema 无根因字段→禁接线)封锁 E5 唯一提分路径 → 8.6 最低线门禁本轮不可达,解除裁决列 H-8
7. **材料纠错**:supplement-round2.md Q1「goal_state_machine.py 不存在」有误——文件存在于 .omc/scripts/;mutex 在 lifecycle_ssot.py:190-203 但生产零调用(僵尸) → PKG-6 接线
