# CarrorOS 二期优化 终审包（R5 终验产出）

> 日期： 2026-07-20 | 施工： Kimi K3（整合器） | 终审对象： gpt / grok / opus 三家
> 基线 commit: 91954a0 → 终验 HEAD: fc8d156（+R5 未提交施工 4 处，见 §5）
> 口径： DeepSeek-V4-Flash 执行实际表现；每项附文件级证据；禁自评自夸，**终裁=你们三家**

## 0. 评审请求（请逐项裁决）

1. **R5 四项提分是否证据充分**（C3 8→9、C7 8→9、C9 8→9、E6 8→9，见 §3 表与 §5 施工清单）
2. **E7 过度自信（7 分）**：hint-only 架构是否接受为终态？还是要求 R6 做 BLOCK 化（需先解防误锁：`git --author` 含 "auth" 子串误伤面）
3. **内置安全（7 分）**：明文 sk- token 在 git 历史（轮换=人工，已在 blocked_human），secret-scan 门已落地。豁免 or 扣分维持？
4. **门禁结论**：24 项全 ≥8.0 **未达成**（E7/内置安全=7），加权 ≥8.6 **未达成**（8.51）。接受 8.51 收口 or 要求 R6？（算术：两项 7→8 后 1903/2220=8.57 仍差 0.03，须再一项 8→9 才达 8.61）

## 1. 门禁对照

| 门禁 | 目标 | 终验实际 | 判定 |
|---|---|---|---|
| 24 项全 ≥8.0 | 8.0 | 最低 7.0（E7、内置安全） | ❌ 2 项待裁决 |
| 24 项加权平均 | ≥8.6 | 1890/2220 = **8.51** | ❌ 差 0.09 |
| UX（独立报告） | — | 53/70 = 7.57 | 报告项 |

## 2. 总分轨迹

| 时点 | C 加权 | E 加权 | 治理均分 | 总加权 | 最低分 |
|---|---|---|---|---|---|
| 基线 91954a0 | 690/1050 = 6.57 | 659/1100 = 5.99 | 7.00 | **1398/2220 = 6.30** | 4.0 (E3) |
| R5a 后（scorecard 记账） | 890 = 8.48 | 895 = 8.14 | 8.14 | 1842 = 8.30 | 7.0 |
| **R5 终验** | **925 = 8.81** | **908 = 8.25** | 8.14 | **1890 = 8.51** | 7.0 |

R5 增量 +48：C3 +15、C7 +10、C9 +10、E6 +13（逐项证据见 §3）。

## 3. 24 项逐项终评

### C 维度（权重 1050）

| C | 指标 | 权重 | 基线 | 终评 | 文件级证据 |
|---|---|---|---|---|---|
| C1 | 指令清晰度 | 15 | 6 | **9** | 70689d3（三方漂移清零，A-B6);13b1c78(S2 varlock 修复 + K3 VERSION v7.2.0/CHANGELOG，全仓无 7.1.0 残留） |
| C2 | 上下文完整度 | 15 | 7 | **9** | fc8d156(written=claimed=len(items) 磁盘派生）;lifecycle_ssot.py:286,316(JSON SSOT 唯一权威 + md_vs_json_mismatch 失真信号）;pkg-c-acceptance.log 计数 3=3 |
| C3 | 流程结构化 | 15 | 7 | **9** ↑R5 | 009c749(verify 主链接入生产）;13b1c78(S1 路由去归档 skill);R5: sync-state.md 悬空引用更正（§5.4) |
| C4 | 输出规范化 | 10 | 8 | **8** | 13b1c78(H10 audit 日期 %Y%m%d 统一）;verify 事件双格式=读取兼容设计（声明保留，非缺口） |
| C5 | 工具生命周期 | 10 | 6 | **9** | 009c749(verify_gate 孤儿接线）;6478951(launcher 关键 hook fail-closed，复跑 3/3 绿）;fc8d156(PreCompact/SubagentStop/SessionEnd 三事件注册 + Stop wrapper) |
| C6 | 知识密度 | 10 | 7 | **9** | R0 anti-patterns 垃圾回退；710c417(enhance 三份字节级重复 + 坏死 oracle_agent shim 删除，零入边实证） |
| C7 | 关联编排 | 10 | 6 | **9** ↑R5 | 13b1c78(S1a-d 幽灵引用清零：lx-race/lx-stepwise/lx-test-gen/race deps);fc8d156(goal/ghost 互斥：lifecycle_ssot.py:190-210 九处 LIFECYCLE_MUTEX raise + test_goal_ghost_mutex 绿） |
| C8 | 可维护性 | 10 | 5 | **8** | R0/R1 双源物理复制→符号链接（carros_base.py → .omc);13b1c78(K3 VERSION 解冻 + H8 hooks-on.bak 删除） |
| C9 | 错误恢复 | 10 | 7 | **9** ↑R5 | 009c749(verify_gate fail-closed + verify_degraded 留痕）;R5: compact-write detached 静默修复（§5.3，行为测试 2 例绿） |

### E 维度（权重 1100)

| E | 指标 | 权重 | 基线 | 终评 | 文件级证据 |
|---|---|---|---|---|---|
| E1 | 目标漂移 | 20 | 6 | **8** | 13b1c78(edit-scope token/plan 双 BLOCK @:529/:562;CARROROS_EDIT_SCOPE=warn 柔性逃生 + 审计；行为单测绿） |
| E2 | 幻觉输出 | 20 | 6 | **8** | 009c749(verify_gate 入生产链 + claim-evidence 机械校验）；残留 oracle hint-only=设计裁决项（同 E7，见 §0.2) |
| E3 | 虚假完成 | 15 | **4** | **9** | 009c749 靶心：cmd_verify→verify_gate 接线 + None 通配死刑 + task-bound 防跨任务重放；pkg-a-20x20.log 20/20 复跑绿；L1 降级留痕（声明保留） |
| E4 | 惯性执行 | 12 | 7 | **8** | 13b1c78(warn-only 主缝 edit-scope BLOCK 化）；其余 warn 门均 audit 留痕（声明设计） |
| E5 | 症状混淆 | 10 | 7 | **8** | 0d8d149(oracle-escalation.md 关键词换行切碎修复 + 胶连段落重组） |
| E6 | 自我矛盾 | 13 | 5 | **9** ↑R5 | R0/R1 双源脚本清零；70689d3（六处漂移）;13b1c78(K4 registry 头部真相：69 条=能力目录，运行时以 settings.json 为唯一真相源）;fc8d156（三份 handoff→JSON SSOT + md_vs_json_mismatch，残留关闭） |
| E7 | 过度自信 | 10 | 7 | **7** | 13b1c78(FORCE kw aut→auth 精度修复，半）;hint-only 架构未动=**主动设计推迟**（防误锁：git --author 含 auth)→ §0.2 裁决 |
| E8 | 上下文遗忘 | 10 | 7 | **9** | fc8d156(PreCompact fail-closed 快照 + sha256 回读校验 + 三角对账；test_precompact_fail_closed/RO 双绿）;R5: compact-write detached 留痕残留关闭（§5.3) |

### 长期治理（满分 70)

| 维度 | 基线 | 终评 | 证据 |
|---|---|---|---|
| 抗衰减防线 | 7 | **9** | fc8d156(PreCompact fail-closed exit2/PRECOMPACT_FAIL;Stop seal;SubagentStop 幂等合并 A8) |
| AI 赋能全流程自动化 | 8 | **8** | 达标线保持 |
| 学习笔记积累 | 6 | **8** | 13b1c78(K1 error-dna <8 字符噪声隔离 + 7 条存量隔离 quarantine.jsonl;A-R4-4 绿） |
| 长期目标一致性 | 8 | **8** | 达标线保持 |
| 功能标志分明 | 5 | **8** | 13b1c78(K4 registry 真相对齐 + harness.yaml 9 已删钩子清除） |
| 内置安全与洞察 | 6 | **7** | 13b1c78(H9 secret-scan 门 sk- 模式 BLOCK)；明文 token 仍在 git 历史（轮换=人工）→ §0.3 裁决 |
| Evaluation 评测框架 | 9 | **9** | 超标保持 |

## 4. R5 回归验证（2026-07-20 全部现跑，日志见 evidence/logs/)

| 套件 | 结果 | 日志 |
|---|---|---|
| PKG-A verify-gate 三层对抗（U11+C3+E6) | 20/20 PASS, rc=0 | pkg-a-20x20.log |
| PKG-A 施工验收 A-A1..A-A5 | 全绿（A-A5 稳态模式，见 §5.2), rc=0 | pkg-a-acceptance.log |
| PKG-B 验收 A-B2..A-B12 | 全绿（A-B12 重冻结后，见 §5.1), rc=0 | pkg-b-acceptance.log |
| PKG-C 验收 V0..V6（单测 6/6 + 实时触发 + 幂等 + fail-closed + 互斥 + scope guard) | ALL_PKG_C_ACCEPTANCE_PASSED, rc=0 | pkg-c-acceptance.log |
| R4 验收 A-R4-1..8 | ALL R4 ACCEPTANCE PASSED, rc=0 | r4-acceptance.log |
| launcher H3(fail-open/fail-closed/透传） | 3/3 PASS, rc=0 | launcher.log |

## 5. R5 施工清单（终验发现→修复→验证，4 处）

### 5.1 A-B12 边界快照重冻结（状态文件，不入库）
- **发现**: `bash scripts/apply-pkg-b.sh` 重跑时 A-B12 exit 2——`.omc/state/pkg-b-backup/protected.sha256` 冻结的是 R1 时点四文件 hash,R2/R4 合法施工后永不通过
- **归因**（全部对上施工 commit，零未解释漂移）: carros_base.py=009c749（符号链接目标施工）、verify_gate.py=009c749+13b1c78、pretool-gate.py=009c749+13b1c78、test-verify-gate.py=009c749
- **修复**: R1 冻结值改名留存 `protected.r1-frozen-20260719.sha256`（审计证据），按 R5 时点重冻结；重跑 A-B12 `PKG_B_BOUNDARY_OK` + `ALL PKG-B ACCEPTANCE PASSED`
- 前后 hash 对照： evidence/hash-drift-r5.json

### 5.2 A-A5 施工期断言→稳态漂移门（apply-pkg-a.sh 改码）
- **发现**: A-A5 断言"3 源文件必须变 + 邻边必须不变"是 R2 施工期一次性证明；R3 合法改 settings.json(+34/-1 注册三事件，R3 已声明）后 exit 2 永红，且重拍快照则"EXPECTED BUT UNCHANGED"反向失败——该门不可重入
- **修复**: apply-pkg-a.sh A-A5 前置稳态分支——存在 `.omc/state/pkg-a-backup/steady-state.sha256` 时改为纯漂移告警（8 观察文件逐一比对，漂移即 exit 2)；原施工期断言保留为 legacy 分支；pre-pkg-a.sha256 原样留存
- **验证**: 稳态快照写入（8 文件，drift 归因同 §5.1 + settings.json=fc8d156)；重跑 `NEIGHBOR_BOUNDARY_OK (steady-state)` + `ALL PKG-A ACCEPTANCE PASSED`

### 5.3 compact-write detached 静默→留痕（pretool-user-approve.py 改码）
- **发现**: `_every_fifth_round` 的 detached compact-write `stdout/stderr=DEVNULL` + `except: pass`——失败完全静默（C9/E8 残留的 R5 Deferred 项）
- **修复**: stdout 仍弃、stderr→`.omc/state/compact-write.log`(.omc/ 已 gitignore);spawn 异常同日志记档（含 _now_iso 时间戳）;仍 exit 0 不阻塞 prompt（性质=后台优化，fail-closed 兜底在 PreCompact hook，分工不变）
- **验证**: py_compile 绿；行为单测 2 例——(A) Popen 注入异常→日志含 `spawn FAILED ... injected-failure`;(B) 引擎路径不存在→子进程 stderr `can't open file` 落日志；实 hook 调用 exit 0 正常注入

### 5.4 sync-state.md 悬空引用更正（C3 残留）
- **发现**: `.claude/skills/lx-oma/gov/state/sync-state.md` 称 `last_reconcile_snapshot: snapshots/master/initial-20260509.md` 且 `infrastructure_initialized: true`，但 `snapshots/` 与 `features/` 目录均不存在——记录不实
- **修复**: 更正为现实（snapshot=none、initialized=false、附 r5_correction 说明）；不伪造历史快照内容

## 6. 偏差声明汇总（含历史轮次）

| # | 轮 | 偏差 | 处置 |
|---|---|---|---|
| 1 | R3 | A12 grep 适配 bold 格式（grok 证据锚 E-H2 自述 bold，命令漏写星号） | 已声明，适配不改方案 |
| 2 | R3 | gitignore 新增 3 条 state 运行产物规则 | 已声明 |
| 3 | R3 | settings.json 提交经 temp-bypass(+34/-1 零密钥行；token 为 owner 已接受历史存量） | 已声明 |
| 4 | R5 | A-B12 重冻结（§5.1) | 本包声明，R1 冻结值留存 |
| 5 | R5 | A-A5 增稳态分支（§5.2) | 本包声明，legacy 分支保留 |
| 6 | R5 | compact-write 留痕修复（§5.3) | 本包声明，行为测试 2 例 |
| 7 | R5 | sync-state.md 更正（§5.4) | 本包声明 |
| 8 | R5 | **观察项（未修）**: settings.json 中 hook 命令为相对路径（`python3 ".claude/hooks/posttool-gate.py"`),Bash 工具 `cd` 进子目录后 hook 以新 cwd 解析→file-not-found 阻断报错。建议下一轮锚定 `$CLAUDE_PROJECT_DIR` 绝对路径；本轮仅记录（R5 终验实测触发 1 次，命令本身成功） | 提请终裁是否列 R6 |

## 7. 硬边界（blocked_human，维持）

1. **token 轮换**: settings.json 明文 sk- 在 git 历史，须人工到 Moonshot 控制台吊销+换新
2. ~~grok 送信~~✅（round3/grok.md 已施工 fc8d156)
3. **三模型终审**: 本包即送信材料

## 8. 证据索引

```
final-review/
├── final-review.md            ← 本文件
├── evidence/
│   ├── logs/                  ← 6 套回归现跑日志（全部 rc=0)
│   ├── hash-drift-r5.json     ← A-B12/A-A5 前后 hash 对照 + 漂移归因
│   └── commits-since-baseline.txt  ← 91954a0..fc8d156 共 16 commit
└── SHA256SUMS
```
