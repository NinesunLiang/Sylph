# Round7 断点去重合并表（gpt_full × grok_full × opus_full → 仓库实证）

> 生成：2026-07-20 S4b。方法：三模型 *_full 逐条提取 → 仓库实证（文件/行号/调用方实测）→ 去重合并 → 冲突裁决 → 合并施工包。
> 分数口径（grok L83 裁决采纳）：**官方 baseline = scorecard.md 1920/2220 = 8.65**（冻结，AI 不动）；自评 1931 = 8.70（含 E1 幻影修复 +20，待终审认定）。目标 ≥1998/2220 = 9.00，10 个主 8 分项全部 ≥8.6。

## 一、三方共识项（去重后）

| # | 合并断点 | GPT | grok | opus | 仓库实证 | 合并裁决 |
|---|---------|-----|------|------|---------|---------|
| A | token/task 单源 | PKG-R7-A + A-R7-03/04（definitions=1, duplicates=0, 8 案例矩阵） | T1/T2/PKG-B（grep 单源 + 劫持对抗） | 方案1（新建 state_reader.py） | **PKG-1 已统一 4 reader**（task_ssot.py，7/7 绿）；**仍存 3 活体第二读法 + 1 僵尸库 + 1 死导入**（见下） | opus 新文件形式**拒绝**（第 4 套机制，违反 GPT §6.2 + grok 否决）；意图已由 task_ssot 满足。残余 → **PKG-2** |
| B | E4 惯性执行 | A-R7-06（DONE 后写→BLOCK 等 4 案例） | L116：先出示 F 才准施工 | 方案3（Gate 3 warn→block） | F **存在且今日实证**：终态 token→`_active_token`=None→Gate 4 **auto-init 误生**（今日劫持环路根因）；blocked/waiting_user 已 BLOCK（pretool-gate.py:606）；未验证推进已 BLOCK（Gate 6） | opus 的"Gate 3 warn 模式"前提**为假**（真实 Gate 5 默认 BLOCK，warn 仅 env 显式 opt-in，:647-651）。残余缺口=**终态惯性** → **PKG-3** |
| C | E7 断言可反证/校准账 | A-R7-08（复用现有 audit writer，同 entry 加字段，**禁独立 calibration 库**） | verified 必须可 overturn 统计（赞成票） | 方案2（新 PostToolUse hook + calibrate.py + confidence-claims.jsonl） | Gate 7 oracle 事件已落 audit jsonl；缺 claim_id/evidence_ids/status 关联字段 | opus 新 hook+新库形式**拒绝**；意图按 GPT 形式采纳=**现有 audit entry 加字段** → **PKG-4** |
| D | C4 写格式唯一/schema 机检 | A-R7-09（duplicate_writers=0） | C4：report/verdict/claim schema 机检，缺字段非 0 | —（Q7 降级 P2：从未发生格式错误） | token 写方：carros_base init + 水位回写（pretool-user-approve.py:187）+ 人工恢复；均无 schema 机检 | 采纳：写时 schema 校验（缺字段拒写）+ 写方清点 → **PKG-4** |
| E | 可观测性 trace | A-R7-10（timestamp/event/task_id/step_id/decision/reason + claim 字段） | O1/O2（水位+lifecycle，R6 已落地） | — | scope_violation 事件**缺 task_id/step_id**（pretool-gate.py:639-646 实证） | 采纳：audit 调用点补 task_id/step_id → **PKG-4** |
| F | 虚高刺杀 | A-R7-14（5 项抽查） | O3（≥3 刺杀：E2 变形/handoff 计数/摘 hook） | — | launcher 外部 cwd round6 已覆盖；E2 变形、handoff 计数、摘 hook、malformed fail-closed 未对抗 | 合并为第 8 套件 → **PKG-5** |
| G | 现跑全家桶 | A-R7-16（禁历史日志替代） | T3（31/31 stdout 已被 fb89180 清理，**封板前必现跑**） | 7 套 exit 0 | run-regression.sh 7 套在库 | 采纳：现跑 + 日志 SHA256 入证据包 → **PKG-7** |
| H | 僵尸机制清零 | A-R7-19 + R7-I6（接线或删除，禁 deprecated 注释糊弄） | L176：新 hook 名必须同时删/接线一个僵尸 registry | — | **carroros_hooklib.py 全库零调用方**（grep 实证）；`lifecycle_ssot.set_mode` 生产调用方=0（仅测试）；19 个 archived token | hooklib + 19 token → human-delete-manifest；**set_mode 接线**（不删）→ **PKG-6** |
| I | goal/ghost 互斥 | — | goal-ghost 互斥（既有 acceptance） | Q1 称 goal_state_machine.py:45 有 LIFECYCLE_MUTEX | **修正**：文件+行号不准；mutex 在 lifecycle_ssot.py:190-203 但**未接线=僵尸**；"无生产机械阻止"效果成立 | lx-goal/lx-ghost 入口调 set_mode → **PKG-6**（C2 守卫） |
| J | 内置安全 R6-B | A-R7-13 + §6.6（人类独占） | 人类专属 | — | owner 已裁决视为通过（3ba3d95）；rotation 仍 owner-only | 不列 AI 待办（人的决策大于 AI 决策） |
| K | settings.json 出库 | A-R7-20 | 人类专属 | — | 已完成（61ad241/9cc7278） | 机检复核即可 ✓ |
| L | 冻结文档零 AI diff | A-R7-12 | 人类专属 | — | 铁律 6 | 机检复核 ✓ |
| M | E5 根因/症状分离 | A-R7-07（**条件**：现有 schema 有根因字段才准接线，禁第二 diagnosis 库） | — | — | task/verify schema **无**根因字段 | **GPT 自设条件封锁唯一路径** → E5 本轮维持 8，延后并记录原因（诚实优于刷分）；解除选项见 H-8 |

## 二、模型间冲突裁决

| 冲突 | 裁决 | 依据 |
|------|------|------|
| opus 新建 5 文件（state_reader/post-tool-use/calibrate/failure_tracker/anomaly_detector）vs GPT §6.2 + grok「第 4 套机制=否」 | **拒绝新文件**；意图折叠进现有模块 | GPT R7-I5/I6 + grok §11 否决表；task_ssot 已存在 |
| opus「Gate 3 warn 模式，需改 BLOCK」vs 真实门禁 | **前提为假，不施工** | 真实 Gate 5 edit-scope 默认 BLOCK（pretool-gate.py:647-651 实证）；opus 基于幻觉架构（gate_1/3/8 编号、`.omc/hooks/` 路径全假） |
| opus 45% 水位警告 +「kernel.md 声明 45/50/70/80」vs owner 规格 50/70/80 | **保 owner 规格** | pretool-user-approve.py:58-61 实证；kernel.md 无 45 声明 |
| opus failure-escalate（≥3 同签名 BLOCK→ESCALATE）新文件 vs 禁新机制 | **意图采纳，形式折叠**：逻辑进 pretool-gate 内部，读现有 audit jsonl，零新文件 | GPT §6.2 例外条款不满足（现有 gate 可承载） |
| GPT 要求先冻 source-evidence.txt 再施工 vs PKG-1 已落地 | **实质已满足**：GPT 门禁针对无仓库访问的施工者；整合者（Kimi）直接读真实文件，read-before-edit 即证据 | PKG-1 全部基于真实文件 + 7/7 现跑 |
| GPT 三包由 DeepSeek 施工 + grok PKG-A/B/C 命名 vs 现实（Kimi 整合施工） | **统一重编号 PKG-2..PKG-7**（PKG-1=SSOT 已交付） | 人的决策大于 AI 决策：owner 指令=Kimi 整合 |
| opus 审批条件「外部挑战 C2/C6/E3 ≥5/6 + 四模型终审」 | 采纳为**轮末流程门**（非施工前置） | 与 round6 终审流程一致 |

## 三、opus 幻觉清单（施工时禁止采信）

1. `gate_1_goal_mode_restrictions`/`gate_3_edit_scope`/`gate_8_xxx` 编号体系——真实 GATES 注册表见 pretool-gate.py:1080+（watermark/context-critical/sensitive/fallback/action/secret-scan/plan/edit-scope/verify/oracle/document/g2/g3/g5/g6）
2. `.omc/hooks/*.py`、`.omc/scripts/run-regression.sh`、`.omc/tests/` 路径——真实为 `.claude/hooks/`、`scripts/run-regression.sh`、`scripts/test-*.py`
3. 「session-start.py:50-60 自行 glob token」「user-approve.py:120-135 按 mtime」——PKG-1 已委托 SSOT，陈旧快照
4. 「kernel.md 声明 45/50/70/80 水位」——无此声明；owner 规格 50/70/80 在 pretool-user-approve.py:58-61
5. 「goal_state_machine.py:45 LIFECYCLE_MUTEX 9 处 raise」——真实 lifecycle_ssot.py:190-203，8 处 raise，生产零调用
6. 方案内自算「+60 → 1991」与「+67 → 1998」两处不一致——以逐维 verdict 实算为准（GPT A-R7-24 采纳：分数禁手填）

## 四、合并施工包（PKG-2..PKG-7）

| PKG | 内容 | 文件（真实路径） | 维度 | 自估提分 |
|-----|------|----------------|------|---------|
| **PKG-2** reader 清零二期 | posttool `_active_task`(:59-77) + precompact `_latest_token`(:33-48) + meta-oracle `_latest_task_id`(:31-45) 委托 task_ssot；修 `lib.error_dna` 死导入（posttool-gate.py:144，hooks/lib 无 error_dna.py→error DNA 静默死）；carroros_hooklib → human-delete-manifest；test-task-ssot 扩充 GPT 矩阵缺项（同 task 多 token/跨天/外部 cwd/显式 task 不一致）+ grok 契约测试（task_ssot 选出 id == lifecycle/handoff 绑定 id） | 3 生产文件 + scripts/lib + 测试 | 治理·自动化 8→9、治理·模块化 8→9、E1 加固 | G-auto +10、G-mod +10 |
| **PKG-3** E4 终态惯性 BLOCK | Gate 4 区分「无 token（全新仓库）」vs「最新 token 已终态」：后者 BLOCK/ESCALATE 替代 auto-init；failure-escalate（≥3 同签名 BLOCK→ESCALATE）内置于 pretool-gate（读现有 audit，零新文件）；对抗：done 后写→BLOCK、auto-init 仅在真空触发 | pretool-gate.py + task_ssot（暴露 latest_terminal）+ 测试 | E4 8→9、C9 加固 | E4 +12 |
| **PKG-4** audit schema 升级 | 全部 gate 事件补 task_id/step_id；claim 类事件加 claim_id/evidence_ids/status（E7 校准账，jq 可统计 overturn）；token/verdict 写时 schema 机检（缺字段拒写） | pretool-gate.py _append_audit 调用点 + verify_gate.py verdict 写点 + carros_base.py | 可观测性 8→9、E7 8→9、C4 8→9 | G-obs +10、E7 +10、C4 +10 |
| **PKG-5** 虚高刺杀套件 | 第 8 套件 test-nine-challenge.py：E2 变形（间接 shell/引号嵌套/env 边界）、handoff 计数三角造假、摘 settings 中某 hook→注册测试必须红、VerifyGate 生产接线证明、malformed payload fail-closed | scripts/test-nine-challenge.py + run-regression.sh | 守卫现有 9 分（E2/E3/C2/handoff） | +0（守卫） |
| **PKG-6** lifecycle mutex 接线 | lx-goal cmd_on/cmd_off + lx-ghost 入口调 `set_mode`（goal/ghost/idle）；对抗：goal 活时 ghost on → raise 机械拒绝；僵尸机制转活体 | .claude/skills/lx-goal/scripts/lx-ghost 入口 + 测试 | C2 守卫（僵尸清零） | +0（守卫） |
| **PKG-7** 现跑全家桶+证据包 | 全 8 套现跑；日志+SHA256 入 `round7/evidence/`；human-delete-manifest.json（carroros_hooklib + 19 archived token）；终态回归 0 败 0 跳 | scripts/ + evidence/ | 一切提分的前置门 | 前置 |

## 五、分数路径（官方 baseline 1920，逐维 verdict 实算，禁手填）

| 项 | delta | 依据 PKG |
|----|-------|---------|
| E1 8→9 | +20 | PKG-1（幻影修复，已交付）+ PKG-2 加固 |
| 治理·自动化 8→9 | +10 | PKG-2 |
| 治理·模块化 8→9 | +10 | PKG-2（第二读法清零 + 僵尸库删除清单） |
| E4 8→9 | +12 | PKG-3 |
| 治理·可观测性 8→9 | +10 | PKG-4 |
| E7 8→9 | +10 | PKG-4（校准账） |
| C4 8→9 | +10 | PKG-4 |
| **合计** | **+82** | 1920+82 = **2002/2220 = 9.01** |
| E5 维持 8 | +0 | GPT 条件封锁，延后（诚实记录） |
| 内置安全 | 维持 | R6-B owner-only |

主项最低线：E5=8.0 < 8.6 → **8.6 最低线门禁本轮不可达**（E5 唯一路径被 GPT 自设条件封锁；解除需 owner 裁决：允许 verify schema 加可选 root_cause 字段=同库加字段，类比 A-R7-08 对 audit 的豁免）。此为一票断点，列入人类清单 H-8。

## 六、人类专属清单（合并去重后）

| # | 事项 | 来源 |
|---|------|------|
| H-1 | R6-B token 吊销/轮换（Moonshot 控制台） | 三方共识 |
| H-2 | 冻结文档（AGENTS/kernel/index）修改 | 三方共识 |
| H-3 | rm：carroros_hooklib.py（零调用方僵尸库）+ 19 个 archived 旧 token | GPT A-R7-19 + 实测 |
| H-4 | git add/commit（迭代期不 commit，结束给清单） | 站立裁决 |
| H-5 | pre-commit 安装：`cp scripts/pre-commit .git/hooks/`（opus 方案8 模板意图采纳，需适配真实 8 套 runner） | opus 方案8 |
| H-6 | UX 两项 7 分独立评审 | GPT L44 |
| H-7 | token 目录机械写保护设计裁决 | opus 方案5 意图 |
| H-8 | **E5 一票断点**：是否允许 verify verdict schema 加可选 root_cause 字段（同库加字段，非第二库） | 本表 §五 |
| H-9 | settings.json AUTO_COMPACT_WINDOW=1048576 调整/移除（auto-compact 兜底） | 此前答复 |
| H-10 | E2/E3 trust 分级消费设计裁决 | 此前清单 |
| H-11 | scorecard.md 终分登记（轮末四模型终审后） | grok/GPT |

## 七、施工纪律（三方禁令交集，S4b 全程有效）

1. 测试必须调生产入口，禁复制生产判定逻辑自证（GPT A-R7-17）
2. 故障注入不得静默放行；skipped>0 不接受（GPT A-R7-18）
3. 禁 `|| true` 包裹验收；禁删失败日志；exit code + 副作用双查（GPT §6.5）
4. Gate 7 正则区默认拒碰（grok L175）；禁新 hook 事件类型（grok L123）
5. 分数从 verdict 实算，禁手填（GPT A-R7-24）；未现跑全家桶不得改分（grok L84）
6. rm/git 写/密钥/明文 token/冻结文档 = 物理禁区（owner 站立指令）
