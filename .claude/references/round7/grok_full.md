# Grok · CarrorOS 冲刺 9+ 结论方案（终审向）

**身份**：CarrorOS 适应性优化架构师（PKG-C）  
**日期基准**：2026-07-20 材料 + 本会话 R6 收口票 + 你刚补的两份证据  
**证据新增**：`r6a-evidence.md`、`commits-since-r6.md`  
**哲学链**：验证 > 零信任 > 守护 > 文档 > 人本 > 增益 > 少  

---

## 0. 一句话结论

| 门 | 结论 |
|----|------|
| **工程可否冲 9.0** | **可以**——路径清楚，**不靠再写规范**，靠 **SSOT 收口 + 校准账 + 防虚高** |
| **现在算不算已 9** | **不算**；现态应记 **R6 工程封板 8.65 → 后续迭代约 8.7 带**（以 scorecard SSOT 为准） |
| **R6-A/E7** | **工程终态通过**（三层 BLOCK/ESCALATE/hint）；**31/31 以可复跑脚本为准**，完整 stdout 已被清理 → **封板前必须现跑一遍** |
| **内置安全** | Owner 已在 `3ba3d95` **人类裁决视为通过 / ALL_GATES_MET** → 本委 **服从人本**，该项退出 AI 债务队列 |
| **开不开热闹 R7** | **开「窄 R7」**，主题冻结为 **3+1**，禁止扩第四套机制 |
| **PKG-C 主责** | **守绿 + task/lifecycle 交叉不双写 + 飞轮/水位噪声清理（若仍残留）**；不重开 handoff schema |

---

## 1. 材料裁定（你补的两份怎么读）

### 1.1 `r6a-evidence.md`——接受，附诚实条件

| 宣称 | 我的裁定 |
|------|----------|
| Gate7 三层：高置信无证据 **BLOCK** / 弱证据 **ESCALATE** / 叙事 **hint** | **接受为 E7 工程终态**（与我 R6 票一致） |
| 施工 `6dcfb90`，收口 `3ba3d95` | **接受时间线** |
| 31/31 对抗、0 漏过 0 误伤 | **条件接受**：逐条 stdout 已被 `fb89180` 清理 → **证据降级为「结论记录 + 可复现脚本」** |
| R6 后 gate 实质变更仅 `e6026aa` 的 `_latest_token`，Gate7 逻辑未动 | **接受**；冲 9 时 **禁止借机重写 Gate7** |

**机械硬条件（否则 E7/E2 相关 9 分作废）**：

```bash
python3 scripts/test-oracle-gate.py    # 期望：31/31 PASS
python3 scripts/test-verify-gate.py    # 期望：20/20 PASS（若路径如 R6）
# PKG-C / R4 / launcher 按仓库入口现跑全绿
```

> **验证 > 文档**：没有现跑绿，不得把 E7/E2 写进「9.0 分子」。

### 1.2 `commits-since-r6.md`——板态重估

已发生、且与 9+ **强相关** 的落地：

| commit | 含义 | 对 9+ 的价值 |
|--------|------|----------------|
| `6dcfb90` | R6-A+C：E7 三层 + E2→9，8.51→8.65 | 已计入 |
| `3ba3d95` | 3:0 收口 + **owner 内置安全 vis-à-vis 通过** | 人类门关闭 |
| `476a08b` | PreCompact 刷新 + 水位 50/70/80 | PKG-C 域加固 |
| `1cd778c` | **双源统一** + lx-goal 守卫 + 注入新鲜度 | **直击 9 的主根因** |
| `c97e670` | **lib 双源清零** + 回归入库 | 续上 |
| `e6026aa` | **消除 token 影响**（`_latest_token`）+ R7 材料 | 续上 / 须验是否唯一 reader |
| `20c41bf` | settings hook 锚定 + 密钥脱敏 | 守护 / 配置诚实 |
| `61ad241`/`9cc7278` | settings 出库 + gitignore | 正确方向 |
| `fb89180` | 日志大清理 | **验收证据变薄** → 依赖复跑 |

**判断**：双源/token 劫持这条 **不是「还没想」**，而是 **「已施工多轮，是否死透」** 的验证题。  
R7 第一刀不是再设计一套选 token，而是：

> **判定：是否仍存在第二读法；有则删/并，无则把分记满并锁回归。**

---

## 2. 当前分与冲刺算术（冻结口径）

### 2.1 分数 SSOT 口径（防三家各说各话）

```
R6-A+C 并账：     1920/2220 = 8.65   （委员会已票）
Owner ALL_GATES： 人类项不再挡「组织全绿」叙事（3ba3d95）
后续 commits：    材料侧常写 ~8.70 带
目标：            加权 ≥ 9.0  ⇒  ≥ 1998/2220
从 8.70 起：      净增 ≥ 67「权重分」
从 8.65 起：      净增 ≥ 78
```

**冻结规则（本方案）**：

1. 以仓库 `scorecard.md`（证据包点名路径）为 **唯一分表**；  
2. 口述 8.65 / 8.70 冲突 → **以表内加权和为准**，并 diff commits 后重算；  
3. **禁止**在未复跑 108（或现行全家桶）前改分。

### 2.2 最低分门

| 项 | 裁定 |
|----|------|
| 主目标 | **加权 ≥9.0（硬）** |
| 单项地板 | **尽量 ≥8.6**；若 brief 写死「全部 ≥8.6」则同等硬 |
| 内置安全 | Owner 已收 → **不再作为 AI 施工目标**；分值按 scorecard 人类已记账处理 |
| 宣传 | 仅当现跑全家桶绿 + 分表可审计 → 可称 **G-Eng 9.0** |

---

## 3. 挡 9 的真实清单（效能序 · 砍虚功）

> 原则：**修盘上真分，不修 PPT。** P3（措辞/重复描述）默认 **0 分**。

### P0 —— 防事故 & 真 SSOT（必修，分大）

| ID | 问题 | 完工定义（机读） | 预估贡献 |
|----|------|------------------|----------|
| **T1 Token/Task 单源** | session-start / approve / gate / `_latest_token` 是否仍可能选出<strong>不同 task</strong> | 唯一 `lib/*task*ssot*`（或既有 lib）reader；关闭 mtime 第二路径；对抗「mtime 更新旧 token 欲劫持」→ 仍绑 active 正确项 | E1 + 治理自动化 **各 8→9** |
| **T2 双源已修尽证** | `1cd778c`/`c97e670`/`e6026aa` 是否把 **grep 层双源** 清到 0 | 对 `mtime`/`_latest_token`/`active_token`/`session-start` 选路 **机械 grep 单源**；违规路径测试红 | 同上记账合法性 |
| **T3 全家桶现跑** | 日志清理后不可空口 9 | oracle 31 + verify 20 + pkg-c + r4 + launcher + round6 回归脚本 **全的 rc=0** | 一切提分的前置门 |

### P1 —— 可验证抬分（主池，凑满 67）

| ID | 问题 | 完工定义 | 预估 |
|----|------|----------|------|
| **C4 输出规范化** | 格式靠纪律 | report/verdict/claim **schema 机检**；缺字段非 0 | 8→9 |
| **E7 校准账** | 有 BLOCK 无「后来打脸率」 | 凡 `verified/blocked/escalated` 落 **calibration 记录**；周命令可 jq 统计 overturn | 锁 9 或 8→9 |
| **学习/飞轮信噪** | unknown 升华污染 | 升华前质量门；unknown 不得进 kernel 自动规则 | 学习维 8→9 |
| residual **E4/惯性格** | 仅当仍有 F | 先出示「warn 仍可穿过」对抗；无 F **拒施工** | 条件 |

### P2 —— 可观测（分紧时做）

| ID | 内容 |
|----|------|
| **O1** | 水位 50/70/80 + PreCompact 刷新：对抗「超水位仍静默」 |
| **O2** | handoff/lifecycle：R6 pkg-c 门复跑；**禁止**新 hook 事件类型 |
| **O3** | 虚高刺杀 ≥3 个现有 9（含 E2）：构造一条假绿必须失败 |

### P3 —— 禁止入仓

- 仅改文档句式刷 C/E 分  
- 新建第二套 oracle / 第四 handoff  
- AI 改 AGENTS/kernel/index（人类专属若仍锁定）  
- 把 Gate7 BLOCK 降成 hint 冲「误报好看」

---

## 4. 达标路径图（→1998）

```
                    [T3 全家桶现跑全绿] ──失败──► 只开 FIX，禁止任何 9 分叙事
                              │成功
                              ▼
              [T1+T2 Token/Task 单源死透 + 劫持对抗]
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         E1 →9          治理·自动化→9     （可选同一 diff）
                              │
              [C4 schema 强检] [E7 calibration] [飞轮质量门]
                              │
                              ▼
              算术：Σ(已机读的 +分) ≥ 缺口(67 或 78)
                              │
              [虚高刺杀：假绿必须红] [人类不越权]
                              │
                              ▼
                    ★ G-Eng 9.0 封板（scorecard 重算）
```

**经验公式（供整合器排期）**：

- T1+T2 若诚实做成 → 通常吃掉 **~40–50 权重分**量级（E1+治理两大块）  
- C4 + E7 校准 + 学习门 → 补齐 **到 ≥67**  
- 仍缺 → **只允许**已举证 F 的残余 8 分维，禁止点名「好看维」

---

## 5. 包拆（零交叉 · R7 窄范围）

| 包 | 主题 | 准入 | 验收 |
|----|------|------|------|
| **PKG-A** | C4 schema/claim-evidence 强检 + E7 **校准账**（**不**改 Gate7 匹配语义） | 只加 log/schema/test | verify + 新 calibration 用例 exit 0 |
| **PKG-B** | **Task/Token 唯一 reader** 死透；grep 双源=0；劫持对抗 | 以 `e6026aa`/`c97e670` 为基线收尾，禁平行读者 | `grep` 单源 + 对抗脚本 |
| **PKG-C（我）** | lifecycle/PreCompact/水位与 task_ssot **接口契约**；Stop/flywheel 若吞 unknown 则 **过滤门**；R6 验收脚本持续绿 | **不**重谈 handoff JSON schema | `run_pkg_c_acceptance` + 新增 ≤5 条 N 维对抗 |

**整合器 Kimi**：  
- 任意包碰 `pretool-gate.py` Gate7 正则区 → **默认拒**（仅允许 SSOT 调用替换、或 A 包校准旁路文件）。  
- 任意「新建 hook 名」→ 必须同时 **删除/接线** 一个僵尸 registry 项。

---

## 6. PKG-C 向结论（本包直接干活边界）

### 6.1 已完成（不要重做）

- PreCompact / SessionEnd / SubagentStop 生命周期（R6-C 时代方案）  
- handoff 计数三角 / goal-ghost 互斥（既有 acceptance）  
- 水位 50/70/80 与 PreCompact 刷新链接（`476a08b`）

### 6.2 R7 仅允许的 C 类施工

1. **契约测试**：task_ssot 选出的 token_id == lifecycle/handoff 绑定 id（不一致 → exit 2）  
2. **飞轮噪声**：若在 C 文件簇内，unknown 升华加硬门（频次/簇/证伪字段）  
3. **守绿**：acceptance 全绿；cwd-相对路径脆弱（R5 观察）——**仅当能最小 diff 且有对抗** 才动，否则挂 **P2 清单不挡 9.0**

### 6.3 PKG-C 明确不做

- 重写 oracle Gate7  
- 人类 token/密钥/冻结文档  
- 为冲分新增 PreCompact 之外的事件  

---

## 7. 虚高刺杀（现 9 也要打）

| 目标 | 攻击 | 失败则 |
|------|------|--------|
| **E2=9 / E7 相关** | 变形绕过（间接 shell、引号嵌套、容器 env 边界）| 记录 scope 或补洞；**不得静默** |
| **handoff/C2 类 9** | 人为 `claimed ≠ len(items)` | 必须非 0 |
| **hook 覆盖 9** | 暂时摘掉 settings 中某 lifecycle | launcher/注册测试必须红 |
| **学习 9（若有）** | 塞垃圾 unknown 求导升华 | 必须被质量门挡 |

**规则**：能稳定假绿 → **先扣分或补洞**，再谈加权 9.0。

---

## 8. 人类 / Owner 边界（仍有效）

| 事项 | AI | 人 |
|------|----|----|
| 内置安全（已 `3ba3d95` 裁决） | **禁止再改安全叙事刷分** | 已收口 |
| `AGENTS.md` / `kernel.md` / `index.md` | 默认禁 | 独占 |
| settings 本地密钥 | 保持出库 + gitignore | 本地轮换 |
| 删历史 / 大清理类 `fb89180` | 仅 owner 令 | — |
| 最终「CarrorOS 全面 9+」新闻稿 | 禁先发 | 看 G-Eng 绿 + 分表 |

---

## 9. 封板清单（Grok 签字条件）

```text
Grok 批准 G-Eng ≥9.0  当且仅当：

[ ] scorecard.md 加权可复现 ≥1998，且与 git HEAD 绑定
[ ] test-oracle-gate.py 现跑 31/31
[ ] test-verify-gate.py 现跑通过（现行用例数）
[ ] PKG-C acceptance 现跑 ALL_PASS
[ ] round6/全家桶回归脚本现跑 PASS
[ ] Task/Token 单源：grep 第二读法 = 0，劫持对抗 PASS
[ ] 每个记 +1 的维：有 F/E/N 与命令期望 exit
[ ] 虚高刺杀 ≥3 条有记录（失败已处理）
[ ] 无第四套机制；Gate7 语义未为刷分削弱
[ ] 人类专属未越权
```

任一项缺 → **拒署 9.0**，只允「R7 进行中 @ x.xx」。

---

## 10. 立即执行序（给 Kimi / 施工链）

### Day-0（今，0 设计）

```bash
# 1) 现跑电池（路径按仓库）
python3 scripts/test-oracle-gate.py
python3 scripts/test-verify-gate.py
# run_pkg_c_acceptance.sh / apply-pkg-r4 / launcher / round6 suite

# 2) 单源审计（示例意图；按实装替换）
rg -n "_latest_token|active_token|mtime" .claude/hooks scripts lib \
  | tee /tmp/token-read-paths.txt
# 期望：写入路径收敛到唯一 lib；hooks 仅 import
```

### Day-1 方案冻结

- PKG-B：双源/劫持 **收尸 diff**（优先）  
- PKG-A：schema + calibration  
- PKG-C：契约测试 + 可选 flywheel 门  

### Day-2 施工与三分验收

- 仅机器 exit 绿才允许改 `scorecard.md`  
- 改分 commit **必须** 引用测试日志 hash  

### Day-3 封板

- 重算 2220  
- Grok/GPT/Opus **二测虚高**  
- 过则 **R7-CLOSED @ ≥9.0**  

---

## 11. 对整合器的否决预告（写进合并规则）

| 提案形态 | Grok 票 |
|----------|---------|
| 「E7 再峻工：改成更多 hint」 | **否** |
| 「文档补充 10 例 → C4+1」 | **否** |
| 「新 daemon 做 token 选举」 | **否** |
| 「同一 lib 收拢读者 + 对抗」 | **是** |
| 「verified 必须可 overturn 统计」 | **是** |
| 「日志已删所以沿用 31/31 叙事永不复跑」 | **否** |
| 「owner 已 ALL_GATES 故可免回归」 | **否**（人本收安全 ≠ 免验证） |

---

## 12. 总结票（可记入委员会）

```text
Grok-PKG-C / Sprint-9:
  R6_BASE                 = CLOSED @ 8.65 (A+C), security OWNER-PASS
  E7_FINAL                = 3-layer KEEP; re-run required before any 9.0 claim
  DUAL_SOURCE / TOKEN     = PRIMARY R7 P0 (finish-to-death, not redesign)
  SCORE_TO_9              = ≥1998/2220 via P0+P1 only; P3=0
  PKG_C_SCOPE             = contract tests + optional flywheel gate + hold green
  OPEN_BROAD_R7           = NO
  OPEN_NARROW_R7          = YES (T1–T3 + C4 + E7-calibration + learning gate)
  PUBLIC_9_CLAIM          = only after §9 checklist
```

---

## 13. 终句

材料显示整条链 **已经在正确地层凿岩**（R6 拦幻觉、R5/R6 迭代清双源、owner 收掉安全债）。  
挡在 9.0 前面的不是「再一个宏大架构」，而是：

1. **复跑建立可审计基线**（尤其是日志被清后的 oracle/verify），  
2. **token/task 第二读法必须grep＝0**，  
3. **用 schema + 校准账 + 飞轮质量门** 把剩余 8 分维抬过门槛，  
4. **刺杀虚高 9**，拒绝假绿。

**Grok 方案裁定：窄 R7、单源死透优先、Gate7 冻结、分必随机读——达成则 9.0；否则宁记 8.8x 诚实，不记 9.0 宣传。**

---

若你下一条只回三样，我可以把 **PKG-C 六段式零设计空间 diff 方案** 直接写到可 `git apply`：

1. 当前 `scorecard.md` 24 行表（或路径）  
2. `lib` 里 task/token SSOT 实际文件名  
3. 全家桶现跑出口摘要（绿/红）  

**— grok · 结论方案已交付，可进入窄 R7 施工拆单**