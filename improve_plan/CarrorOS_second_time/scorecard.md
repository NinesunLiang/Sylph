# CarrorOS 评分对账卡（scorecard）

> 创建： 2026-07-19 | 维护： Kimi K3（整合器） | 用途： /lx-goal 持续优化循环的唯一对账真相源
> 门禁： **24 项(C1-C9 + E1-E8 + 长期治理7)全部 ≥8.0；加权平均 ≥8.6**
> 口径： 以"DeepSeek-V4-Flash 执行时的实际表现"为准；每项必须附文件级证据，禁自评自夸（终裁=三模型终审）
> 基线来源： flamingo plan Part 2（文件级证据已人工核验） | 基线 commit: 91954a0 → R0 后 50619b2

## 总分看板

| 维度 | 基线 | 当前 | 目标 | 状态 |
|---|---|---|---|---|
| C1-C9 加权 | 690/1050 = **6.57** | 740/1050 = 7.05 | ≥8.6 | ⬜ |
| E1-E8 加权 | 659/1100 = **5.99** | 813/1100 = 7.39 | ≥8.6 | ⬜ |
| 长期治理 均分 | 49/70 = **7.00** | 7.00 | ≥8.6 | ⬜ |
| **24 项总加权** | 1398/2220 = **6.30** | 1602/2220 = 7.22 | **≥8.6** | ⬜ |
| **24 项最低分** | **4.0 (E3)** | 5.0 （功能标志） | **≥8.0** | ⬜ |
| UX 均分（独立，不入门禁） | 49/70 = 7.00 | 7.00 | 报告 | ⬜ |

## C 维度（权重/基线/目标/拉动轮次）

| C | 指标 | 权重 | 基线 | 当前 | 主要缺口（证据） | 拉动 |
|---|---|---|---|---|---|---|
| C1 | 指令清晰度 | 15 | 6 | 6→**8** | ~~R6 三方漂移~~(✅R1 统一白名单+语法门）；残留： lx-varlock markdown 损坏（:21,36-58)、kernel vs CHANGELOG | ~~R1~~✅+R4(S2) |
| C2 | 上下文完整度 | 15 | 7 | 7 | handoff 计数失真 0/0、三份 handoff 副本、读侧门禁死（H2 已修✓R0) | R3(grok) |
| C3 | 流程结构化 | 15 | 7 | 7 | verify 主链被架空（→R2)、gov/sync-state.md 6 行占位、路由指已归档 skill | R2+R4(S1/S7) |
| C4 | 输出规范化 | 10 | 8 | 8 | audit 日期格式双存（%Y-%m-%d vs %Y%m%d)、verify 事件双格式 | R4(H10) |
| C5 | 工具生命周期 | 10 | 6 | 6→**8** | ~~verify_gate 孤儿~~(✅R2 已接线 cmd_verify)、~~launcher fail-open~~(✅R0)；残留： 无 PreCompact/SessionEnd/SubagentStop(R3) | ~~R2~~✅+R3 |
| C6 | 知识密度 | 10 | 7 | 7→8 | anti-patterns 顶部 13 条测试垃圾（已回退✓R0)、enhance/ 三份重复、references 死代码 oracle_agent.py | R4(K2) |
| C7 | 关联编排 | 10 | 6 | 6 | lx-goal→已归档 lx-race/lx-stepwise、lx-oma→幽灵 race、skill-chaining→幽灵 lx-test-gen、goal/ghost 无互斥 | R4(S1)+R3(S5) |
| C8 | 可维护性 | 10 | 5 | 5→7 | 双源物理复制（oracle_gate 已符号链接✓R0,R1 删除）、VERSION 冻结、settings.json.hooks-on.bak 引 6 已删 hook | R1+R4(H8/K3) |
| C9 | 错误恢复 | 10 | 7 | 7→**8** | ~~verify_gate 缺失静默~~(✅R2 fail-closed BLOCKED+required_action)、降级显式留痕（verify_degraded)；残留： compact-write detached 静默（R3) | ~~R2~~✅+R3 |

## E 维度（权重/基线/目标/拉动轮次）

| E | 指标 | 权重 | 基线 | 当前 | 主要缺口（证据） | 拉动 |
|---|---|---|---|---|---|---|
| E1 | 目标漂移 | 20 | 6 | 6 | edit-scope 越界仅 WARN 不阻断（pretool-gate.py:540) | R4(WARN→BLOCK) |
| E2 | 幻觉输出 | 20 | 6 | 6→**8** | ~~verify_gate 不在生产链路~~(✅R2 接线）、claim-evidence 机械校验生效（E3>E2>E1>E0 层级，软完成 REJECTED)；残留： oracle hint-only | ~~R2~~✅ |
| E3 | 虚假完成 | 15 | **4** | 4→**9** | ~~cmd_verify 不调 verify_gate~~(✅R2)、~~_check_verified(None) 通配~~(✅R2 双绑定）、~~跨任务 S1 重放~~(✅R2 task-bound)；扣分项： L1 无规则降级路径仍在（留痕） | **~~R2~~✅ 靶心已中** |
| E4 | 惯性执行 | 12 | 7 | 7 | warn-only 门给惯性留缝 | R4 |
| E5 | 症状混淆 | 10 | 7 | 7 | oracle-escalation.md 关键词被换行切碎 | R4(S2 类） |
| E6 | 自我矛盾 | 13 | 5 | 5→**8** | ~~双源脚本~~(✅R0 符号链接+R1 双删）、~~六处重复验证契约~~(✅R1 R6/pipeline/降级统一）；残留： 三份 handoff(R3)、registry 20+ vs 6 hook(K4) | ~~R1~~✅+R4(K4) |
| E7 | 过度自信 | 10 | 7 | 7 | pretool oracle-gate 仅 hint 从不阻断（:607) | R4（候选，需设计） |
| E8 | 上下文遗忘 | 10 | 7 | 7 | 计数失真、compact-write 静默、无 PreCompact 兜底 | R3(grok) |

## 长期治理（基线/目标/拉动）

| 维度 | 基线 | 当前 | 主要缺口 | 拉动 |
|---|---|---|---|---|
| 抗衰减防线 | 7 | 7 | PreCompact 缺失 + detached 静默失败 | R3 |
| AI 赋能全流程自动化 | 8 | 8 | （达标线）保持 | — |
| 学习笔记积累 | 6 | 6→7 | error-dna 无噪声过滤（存量垃圾已清✓R0)、无防再染 | R4(K1-过滤） |
| 长期目标一致性 | 8 | 8 | （达标线）保持 | — |
| 功能标志分明 | 5 | 5 | registry 20+ 特性 vs 实际 6 hook;harness.yaml 列 9 已删钩子 | R4(K4) |
| 内置安全与洞察 | 6 | 6 | 明文 token 在库（轮换=人工⚠️)、launcher fail-open(✓R0)、settings 不入库 | R4(H9 半）+人工轮换 |
| Evaluation 评测框架 | 9 | 9 | （超标）保持 | — |

## UX（独立评分，不入门禁，同轮顺带拉动）

| 维度 | 基线 | 拉动 |
|---|---|---|
| 长期目标一致性 | 8 | — |
| 用户心智负担减轻 | 6 | R1（矛盾清理）+R3(handoff)+R4(K4) |
| 交互现代化 | 7 | — |
| 用户掌控感 | 8 | — |
| ai 智能感 | 7 | R2（双审判真实接线） |
| 行为可预测 | 6 | R0✓(H3 fail-closed)+R1+R4 |
| 人机权限分明 | 7→8 | ~~R2~~✅(verify 不再可自证： 无证据不 [x],降级留痕） |

## 轮次日志

| 轮 | 内容 | 完成证据 | 预估拉动 |
|---|---|---|---|
| R0 | 在途清点： 6+1 组 commit(50619b2 前 7 个）;H2/H3/H6-lite 落地；anti-patterns 垃圾回退；gitignore 精准化 | git log 91954a0..50619b2 | C5 6→7、C6 7→8、C8 5→7、学习笔记 6→7、行为可预测 6→7 |
| R1 | PKG-B 契约统一（gpt) | commit 70689d3;A-B2/3/6/7/8(21脚本）/9/10/11/12 全绿；PKG-A 边界 sha256 未动；scripts/apply-pkg-b.sh 幂等可重跑 | E6 5→8✅、C1 6→8✅ |
| R2 | PKG-A 验证链（整合器施工） | commit 009c749;U11+C3+E6=20/20 PASS;A-A1..A-A5 全绿；scripts/apply-pkg-a.sh 幂等；发现 carros_base 符号链接并适配 | E3 4→9✅、E2 6→8✅、C5→8✅、C9→8✅、人机权限 7→8✅ |
| R3 | PKG-C 生命周期（grok,⏸ 等用户送信） | （待填） | C2→9、E8→9、抗衰减→9、C7+ |
| R4 | 补缺： S1/S2/K1/H8/H9半/K3/K4/E1门/H10/S7 | （待填） | C3/C4/C7/C8/E1/E4/E5/功能标志/学习笔记/内置安全 |
| R5 | 终验： 24 项重评+终审包 | （待填） | — |

## 硬边界（需人类，已记录 blocked_human）

1. **token 轮换**: settings.json 明文 sk- 已在 git 历史，须人工到 Moonshot 控制台吊销+换新（R4 做 env 外移+secret-scan 门，轮换本身只能人工）
2. **grok 送信**: `round2/materials/pkg-c-evidence/pkg-c-evidence.tar.gz` + `round2/integrator-to-grok.md` → grok;方案回 `round3/grok.md`
3. **三模型终审**: 宣称达标后由用户把终审包发三家
