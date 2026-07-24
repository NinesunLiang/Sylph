# Round7 补充材料包(round2)— 三模型索取项全量应答

> 2026-07-20 kimi-k3 组装。配套文件：`snapshots/`(10 文件)、`current-score.json`、`commits-since-r6.txt`、`r6a-evidence.md`、`SHA256SUMS`。
> 上轮缺口说明：round1 材料包发出后，三模型的补充索取被记入待办但未产出——本包补齐。

## 〇、最关键口径：8.65 vs 8.70 差异(GPT #4 / grok P0-1)

| 口径 | 值 | 来源 | 状态 |
|---|---|---|---|
| 官方 SSOT | 1920/2220 = **8.65** | `scorecard.md`(R6 并账 6dcfb90) | 冻结，AI 不可改 |
| round6 自评 | 1931/2220 = **8.70** | `round6/summary.md` | **待 owner 并账裁决**(E6、C8 两项 8→9,+11 分) |

差值 = E6 自我矛盾 8→9(+7,证据 ed2fa6a kernel A/B 双表+活体 handoff grep)+ C8 可维护性 8→9(+4,lib 7 对双源 symlink 统一+复扫清零)。无重复计分：两项在官方 8.65 中均为 8。**建议三模型以 8.70 为施工基线、以 8.65 为封板底线**(grok 封板口径默认官方表)。

## 一、grok 15 问全答

**P0**
1. 24 项 scorecard → `current-score.json`(机读)+ 下方第五节速览。SSOT 见第〇节。
2. 10 个 8 分主维：**C4、E1、E4、E5、E7、G2 自动化、G3 学习笔记、G4 长期目标、G5 功能标志、G6 内置安全**;UX 两个 7 分：**UX3 交互现代化、UX5 ai智能感**。
3. R6-B 内置安全：**未闭环，owner 认领中**(Moonshot console 轮换，AI 禁代劳)。现 8 分。状态见第四节。
4. R6-A Gate7 三层(BLOCK/ESCALATE/hint)已合入评分终态(R6 并账 6dcfb90);**E7 现分 8**——三层精确 BLOCK 解决"过度自信被拦",但"自信→被推翻"校准账不存在，故不到 9。
5. 回归电池：6 套件 2026-07-20 当日 4 次全绿(round6 施工各轮+幻影修复后)。"108"为历史用例数口径，现行 6 套件 PASS/FAIL 制；`scripts/run-regression.sh` 一条命令可复现。

**P1**
6. gap-dossier 全文 → `../gap-dossier.md`(12 维：10×8 分 + 2×UX7，含幻影案例)。24 维全表在 `current-score.json`。
7. token 选任务现行实现(**注意：比材料发出时多一处发现**):
   - `pretool-gate.py:_latest_token` — mtime 序 + 终态过滤(2026-07-20 e6026aa 已修)
   - `pretool-user-approve.py:_latest_token` — 同上 + 要求 stats dict
   - `session-start.py:_active_token_brief`(L65-95)— **裸 mtime 前 5,无终态过滤(幸存副本)**
   - `statusline.py:latest_token`(L32-42)— **裸 mtime 取 candidates[0],无过滤(第 4 处，用户可见面)**
   四源同病正是 PKG-1(SSOT 统一)的施工对象。
8. feature-registry：无独立 registry 文件；auto-snapshot/turn-counter/context-guard 无此三名实体。相近实体：context_engine compact-write(handoff 快照)、prompt-ring(20 轮计数)、context-watermark(50/70/80 水位)。**无 module registry 机检正是 G5 功能标志 8 分的根因。**
9. 飞轮：升华入口 `lib/flywheel.py:94-176`(写 `.claude/references/anti-patterns.md`);`unknown` 分类在 flywheel.py:65。当前 anti-patterns.md 含 unknown 4 条；`unknown×155` 为 error_dna 历史聚合计数(30 天窗口无机读报表——本身就是缺口)。质量门=PKG-5 候选。
10. **允许动 pretool-gate.py**(e6026aa 今日刚改过，owner 提交)。冻结仅 AGENTS.md / kernel.md / index.md / scorecard.md 官方分。

**P2**
11. 目标硬双重：**加权 ≥9.0 且 24 项最低 ≥8.6**(owner 原话"平均到9分以上，最低8.6")。
12. 内置安全**计入**最低分门禁 → 因此采纳你的 G-Eng/G-Org 双门：G6 8.0 未闭合前只封 G-Eng。
13. 现 9 分维(14 个):C1 C2 C3 C5 C6 C7 C8 C9、E2 E3 E6 E8、G1 抗衰减、G7 Evaluation。虚高刺杀默认对象(与 opus 重叠):C2(goal/ghost 互斥无机械门，下述)、C6(trust E2/E3 通过判定不区分)、E3(token 无 rm 机械防护)。
14. R7 施工模型：**kimi-k3 直接施工**(本会话)，不再三分包；runtime 分层=deepseek 执行+高阶模型审计(常设)。
15. 不可碰黑名单：AGENTS.md、kernel.md、index.md、scorecard.md(官方分)、settings.json(owner 私有)、`.omc/state/tokens/`(goal 信号)。另：>5 文件 rm、git 写、密钥=物理禁区。

**E) G-Eng 先封 / G-Org 等人：接受(是)。**

## 二、GPT 7 项

1. gap-dossier 全文 → `../gap-dossier.md`(round1 已含，随包重发)
2. codebase-map 全文 → `../codebase-map.md`(同上)
3. brief 全文+算式 → `../brief.md`;**8.70 算式明细 = `current-score.json`**(935/1050 C + 938/1100 E + 58/70 G = 1931/2220)
4. R6 后评分表 → 第〇节差异表 + `current-score.json`;R6 官方并账 commit = 6dcfb90
5. 代码快照 → `snapshots/` 10 文件(含 settings.json **脱敏版**,取自 git 历史 20c41bf；明文不经手)。另含 active-token reader×2(audit writer 在 verify_gate.py / carros_base log_audit；提交门=run-regression.sh,pre-commit 未安装)
6. R6-A 证据 → `r6a-evidence.md`
7. R6-B 状态 → 第四节

## 三、opus Q1-Q13(可机答部分)

| Q | 答 |
|---|---|
| Q1 goal/ghost 互斥 | **二次修正(2026-07-20,此前答复有误)**：`goal_state_machine.py` **存在**于 `.omc/scripts/`(此前只搜 `.claude/scripts` 误判不存在);互斥逻辑真实位置=`.claude/hooks/lib/lifecycle_ssot.py:190-203` `set_mode()`(8 处 raise:goal-ghost 互转/idle 禁 id/缺 id 等)。**但 `set_mode` 生产调用方=0**——仅 `.claude/hooks/tests/test_pkg_c_lifecycle.py:209-243` 调用,三个 lifecycle hook(session-end/subagent-stop/precompact)只 import 其他函数。**结论:mutex 代码存在且有测试,但未接线任何生产入口=僵尸机制;"goal+ghost 同活无生产机械阻止"效果成立**。opus"goal_state_machine.py:45 有 9 处 raise"的文件+行号不准,机制存在性部分成立。接线(lx-goal/lx-ghost 入口调 set_mode)=候选施工项 |
| Q2 trust 分级消费 | verify_gate.py:20 定义 E3>E2>E1>E0 层级；:176-200 lint 消费(证据级不匹配给 warning);**通过判定不区分 E2/E3**——设计遗漏成立，区分裁决=需人类 |
| Q3 token 删除防护 | 无机械门。rm 硬边界是规则层(AGENTS.md 哲学),AI 自律+owner 逐次授权(今日 3 个 tt-e2e 孤儿锁即如此)。机制化(目录写保护)=候选，需设计裁决 |
| Q4 session-start vs user-approve 读取差异 | 见 grok-P1-7 四源表。历史事故：今日幻影 token=该差异的直接后果 |
| Q5 pre-commit 现状 | **未安装**。run-regression.sh 已入库(round6);`.git/hooks/pre-commit` 接线=人类一步(cp),PKG-3 |
| Q6 token 清理成本 | 19 个 archived 旧 token 滞留；终态过滤后已惰性(不复活);批量删=owner 一步命令 |
| Q7 audit 格式错误 | 近 3 个 jsonl 207 行机检 **0 malformed**(2026-07-20 实测) |
| Q8 AI 循环重试 BLOCK | 今日实证：scope 门对同文件连 BLOCK 3 次无升级→opus 方案 6(≥3 同签名→ESCALATE)采纳为 PKG-6 |
| Q9 141 未提交改动 | 已收口：e6026aa(owner 提交)+c97e670/61ad241/9cc7278；当前仅 2 个修改文件(.prompt-ring-state、anti-patterns，运行时产物) |
| Q10 AGENTS/kernel 追加 | 冻结(铁律 6),追加须 owner 审核合并——你的 §外部挑战记录 提案已列人类专属清单 |
| Q11 权重算式 | 加权平均=Σ(score×weight)/Σ(weight×10)×10;C/E 按各自权重，治理/UX 各维等权 10。机读明细=current-score.json |
| Q12 施工模型表现 | kimi-k3：今日幻影根因修复+3 次被自家门禁 BLOCK(门禁有效性活体证据);deepseek 执行层无异常记录 |
| Q13 top-3 优先级 | **owner 问题，AI 不代答**。AI 侧效能排序已给：PKG-1 SSOT > PKG-2 校准账 > PKG-5 飞轮质量门 |

## 四、R6-B 状态(无密钥)

- 人工吊销：**未执行**(owner 认领中，不 nag)
- 脱敏回执：20c41bf(HEAD 树 settings.json 为 REPLACE_WITH_YOUR_MOONSHOT_KEY 占位)+ 61ad241(移出版本控制)+ 9cc7278(gitignore 去重)
- 当前树扫描：`git grep "sk-Xrw" HEAD -- .claude/settings.json` → **exit=1(干净)**
- 历史扫描：近 20 commit 无命中；**全历史未做穷举扫描**——轮换前不做"历史已清"声称；轮换后旧凭证作废即全闭
- 新凭证：本地 settings.json 含真实 key(gitignore 保护，未入 Git)

## 五、24 项速览(详表=current-score.json)

- **9 分×14**:C1 C2 C3 C5 C6 C7 C8 C9 / E2 E3 E6 E8 / G1 G7
- **8 分×10**:C4 / E1 E4 E5 E7 / G2 G3 G4 G5 G6
- UX(独立，不参与总加权):7×2(UX3 UX5)+8×5 = 54/70
- 距目标：1998-1931 = **67 分**；全部 8→9 得 +112 → 9.20(G-Eng);G6 需 R6-B 人类闭环方解 8.0 封板
