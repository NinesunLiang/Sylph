# CarrorOS 评分对账卡（scorecard）

> 创建： 2026-07-19 | 维护： Kimi K3（整合器） | 用途： /lx-goal 持续优化循环的唯一对账真相源
> 门禁： **24 项(C1-C9 + E1-E8 + 长期治理7)全部 ≥8.0；加权平均 ≥8.6**
> 口径： 以"DeepSeek-V4-Flash 执行时的实际表现"为准；每项必须附文件级证据，禁自评自夸（终裁=三模型终审）
> 基线来源： flamingo plan Part 2（文件级证据已人工核验） | 基线 commit: 91954a0 → R0 后 50619b2

## 总分看板

| 维度 | 基线 | 当前 | 目标 | 状态 |
|---|---|---|---|---|
| C1-C9 加权 | 690/1050 = **6.57** | 850/1050 = 8.10 | ≥8.6 | ⬜ |
| E1-E8 加权 | 659/1100 = **5.99** | 875/1100 = 7.95 | ≥8.6 | ⬜ |
| 长期治理 均分 | 49/70 = **7.00** | 55/70 = 7.86 | ≥8.6 | ⬜ |
| **24 项总加权** | 1398/2220 = **6.30** | 1780/2220 = 8.02 | **≥8.6** | ⬜ |
| **24 项最低分** | **4.0 (E3)** | 7.0 (C2/E7/E8/抗衰减/内置安全) | **≥8.0** | ⬜ |
| UX 均分（独立，不入门禁） | 49/70 = 7.00 | 53/70 = 7.57 | 报告 | ⬜ |

## C 维度（权重/基线/目标/拉动轮次）

| C | 指标 | 权重 | 基线 | 当前 | 主要缺口（证据） | 拉动 |
|---|---|---|---|---|---|---|
| C1 | 指令清晰度 | 15 | 6 | 6→**9** | ~~R6 三方漂移~~(✅R1)；~~lx-varlock 损坏~~(✅R4 S2)；~~kernel vs CHANGELOG~~(✅R4 K3,全仓无 7.1.0 残留） | ~~R1~~✅+~~R4~~✅ |
| C2 | 上下文完整度 | 15 | 7 | 7 | handoff 计数失真 0/0、三份 handoff 副本、读侧门禁死（H2 已修✓R0) | R3(grok) |
| C3 | 流程结构化 | 15 | 7 | 7→**8** | ~~verify 主链架空~~(✅R2)、~~路由指已归档 skill~~(✅R4 S1)；残留： gov/sync-state.md 6 行占位 | ~~R2~~✅+~~R4~~✅ |
| C4 | 输出规范化 | 10 | 8 | 8 | ~~audit 日期双存~~(✅R4 H10 %Y%m%d 统一）;verify 事件双格式=读取兼容设计（保留） | ~~R4~~✅ |
| C5 | 工具生命周期 | 10 | 6 | 6→**8** | ~~verify_gate 孤儿~~(✅R2)、~~launcher fail-open~~(✅R0)；残留： 无 PreCompact/SessionEnd/SubagentStop(R3) | ~~R2~~✅+R3 |
| C6 | 知识密度 | 10 | 7 | 7→**9** | ~~anti-patterns 垃圾~~(✅R0)、~~enhance 三份重复~~(✅R5a K2 字节级相同+零入边）、~~oracle_agent.py 死代码~~(✅R5a 委托目标不存在） | ~~R0~~✅+~~R5a~~✅ |
| C7 | 关联编排 | 10 | 6 | 6→**8** | ~~lx-goal→已归档 lx-race/lx-stepwise~~(✅R4 S1a 原生并行/串行 direct)、~~lx-oma 幽灵 race~~(✅S1b)、~~chaining 幽灵 lx-test-gen~~(✅S1c)、~~deps race 标 archived~~(✅S1d)；残留： goal/ghost 互斥（R3 S5) | ~~R4~~✅+R3 |
| C8 | 可维护性 | 10 | 5 | 5→**8** | ~~双源物理复制~~(✅R0/R1)、~~VERSION 冻结~~(✅R4 K3 v7.2.0+CHANGELOG)、~~hooks-on.bak 引 6 已删 hook~~(✅R4 H8) | ~~R1~~✅+~~R4~~✅ |
| C9 | 错误恢复 | 10 | 7 | 7→**8** | ~~verify_gate 缺失静默~~(✅R2 fail-closed)、降级留痕（verify_degraded)；残留： compact-write detached 静默（R3) | ~~R2~~✅+R3 |

## E 维度（权重/基线/目标/拉动轮次）

| E | 指标 | 权重 | 基线 | 当前 | 主要缺口（证据） | 拉动 |
|---|---|---|---|---|---|---|
| E1 | 目标漂移 | 20 | 6 | 6→**8** | ~~edit-scope 越界仅 WARN~~(✅R4: token-scope+plan-scope 双 BLOCK,:529/:562;CARROROS_EDIT_SCOPE=warn 柔性逃生+审计；行为单测绿） | ~~R4~~✅ |
| E2 | 幻觉输出 | 20 | 6 | 6→**8** | ~~verify_gate 不在生产链路~~(✅R2)、claim-evidence 机械校验生效；残留： oracle hint-only | ~~R2~~✅ |
| E3 | 虚假完成 | 15 | **4** | 4→**9** | ~~cmd_verify 不调 verify_gate~~(✅R2)、~~None 通配~~(✅)、~~跨任务 S1 重放~~(✅ task-bound)；扣分项： L1 降级路径仍在（留痕） | **~~R2~~✅ 靶心已中** |
| E4 | 惯性执行 | 12 | 7 | 7→**8** | ~~warn-only 主缝=edit-scope~~(✅R4 BLOCK 化）；其余 warn 门均 audit 留痕 | ~~R4~~✅ |
| E5 | 症状混淆 | 10 | 7 | 7→**8** | ~~oracle-escalation.md 关键词换行切碎~~(✅R5a 重组： 触发条件/模板/后续动作/关键规则） | ~~R5a~~✅ |
| E6 | 自我矛盾 | 13 | 5 | 5→**8** | ~~双源脚本~~(✅R0/R1)、~~六处漂移~~(✅R1)、~~registry 20+ vs 6 hook~~(✅R4 K4 真相对齐）；残留： 三份 handoff(R3) | ~~R1~~✅+~~R4~~✅ |
| E7 | 过度自信 | 10 | 7 | 7 | FORCE kw aut→auth 精度修复（✅R4);hint-only 架构未动——BLOCK 化需防误锁（git --author 含 auth),skip-risk 推迟 | R4（半）+设计待定 |
| E8 | 上下文遗忘 | 10 | 7 | 7 | 计数失真、compact-write 静默、无 PreCompact 兜底 | R3(grok) |

## 长期治理（基线/目标/拉动）

| 维度 | 基线 | 当前 | 主要缺口 | 拉动 |
|---|---|---|---|---|
| 抗衰减防线 | 7 | 7 | PreCompact 缺失 + detached 静默失败 | R3 |
| AI 赋能全流程自动化 | 8 | 8 | （达标线）保持 | — |
| 学习笔记积累 | 6 | 6→**8** | ~~error-dna 无噪声过滤~~(✅R4 K1 <8字符隔离+7 条存量隔离至 quarantine.jsonl) | ~~R4~~✅ |
| 长期目标一致性 | 8 | 8 | （达标线）保持 | — |
| 功能标志分明 | 5 | 5→**8** | ~~registry 20+ vs 6 hook~~(✅R4 K4 头部真相对齐： 69 条=能力目录，运行时以 settings.json 为唯一真相源）;~~harness.yaml 9 已删钩子~~(✅H8 删除） | ~~R4~~✅ |
| 内置安全与洞察 | 6 | 6→**7** | H9 secret-scan 门✅R4(sk- 模式 BLOCK)；明文 token 仍在库（轮换=人工⚠️)、env 外移推迟（高风险） | ~~R4（半）~~✅+人工轮换 |
| Evaluation 评测框架 | 9 | 9 | （超标）保持 | — |

## UX（独立评分，不入门禁，同轮顺带拉动）

| 维度 | 基线 | 拉动 |
|---|---|---|
| 长期目标一致性 | 8 | — |
| 用户心智负担减轻 | 6→7 | ~~R1（矛盾清理）~~✅+~~R4(K4 registry 真相）~~✅;handoff 统一待 R3 |
| 交互现代化 | 7 | — |
| 用户掌控感 | 8 | — |
| ai 智能感 | 7 | R2（双审判真实接线） |
| 行为可预测 | 6→8 | ~~R0(H3 fail-closed)~~✅+~~R1~~✅+~~R4(edit-scope BLOCK 确定性）~~✅ |
| 人机权限分明 | 7→8 | ~~R2~~✅(verify 不再可自证： 无证据不 [x],降级留痕） |

## 轮次日志

| 轮 | 内容 | 完成证据 | 预估拉动 |
|---|---|---|---|
| R0 | 在途清点： 6+1 组 commit(50619b2 前 7 个）;H2/H3/H6-lite 落地；anti-patterns 垃圾回退；gitignore 精准化 | git log 91954a0..50619b2 | C5 6→7、C6 7→8、C8 5→7、学习笔记 6→7、行为可预测 6→7 |
| R1 | PKG-B 契约统一（gpt) | commit 70689d3;A-B2/3/6/7/8(21脚本）/9/10/11/12 全绿；PKG-A 边界 sha256 未动；scripts/apply-pkg-b.sh 幂等可重跑 | E6 5→8✅、C1 6→8✅ |
| R2 | PKG-A 验证链（整合器施工） | commit 009c749;U11+C3+E6=20/20 PASS;A-A1..A-A5 全绿；scripts/apply-pkg-a.sh 幂等；发现 carros_base 符号链接并适配 | E3 4→9✅、E2 6→8✅、C5→8✅、C9→8✅、人机权限 7→8✅ |
| R3 | PKG-C 生命周期（grok,⏸ 等用户送信） | （待填） | C2→9、E8→9、抗衰减→9、C7+ |
| R4 | 补缺： S1/S2/K1/H8/H9半/K3/K4/E1门/H10/S7(moot) | commit 13b1c78;23 处编辑+7 条 error-dna 隔离+hooks-on.bak 删除；A-R4-1..8 全绿（py_compile x3/行为单测/20-20 回归/launcher/幽灵 grep/diff --check);apply-pkg-r4.sh 幂等（首轮 S2a 锚/E1b 假 SKIP 已修） | C1→9✅、C3→8✅、C7→8✅、C8→8✅、E1→8✅、E4→8✅、功能标志→8✅、学习笔记→8✅、内置安全→7✅ |
| R5a | E5 修复 + K2 去重 | commit 0d8d149(oracle-escalation 重组）+710c417(enhance 三份字节级重复+坏死 shim 删除，零入边实证） | E5→8✅、C6→9✅ |
| R5 | 终验： 24 项重评+终审包 | （待填） | — |

## 硬边界（需人类，已记录 blocked_human）

1. **token 轮换**: settings.json 明文 sk- 已在 git 历史，须人工到 Moonshot 控制台吊销+换新（R4 做 env 外移+secret-scan 门，轮换本身只能人工）
2. **grok 送信**: `round2/materials/pkg-c-evidence/pkg-c-evidence.tar.gz` + `round2/integrator-to-grok.md` → grok;方案回 `round3/grok.md`
3. **三模型终审**: 宣称达标后由用户把终审包发三家
