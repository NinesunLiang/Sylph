# Round6 基线 — 评分(post-round5 落树态)

> 2026-07-20 | 口径: 独立自评+文件级证据,不动 scorecard.md | 起点: round5 终值 8.59 + round5 收口 4 commit 已落树

## 一、基线核对(落树验证)

| 核对项 | 结果 |
|---|---|
| round5 4 commit(d2d8022/1cd778c/ed2fa6a/81b6716) | ✅ 在树,工作区干净 |
| context_watermark.py symlink 模式 | ✅ git 120000 入库 |
| .omc lib 双 symlink(flywheel/error_dna) | ✅ 指向 .claude 单源 |
| kernel.md 双水位表 | ✅ ed2fa6a 已提交 |
| 活体 handoff 幽灵声称("AGENTS.md 已 @") | ✅ 已自愈(02:27 compact-write 无该行,grep rc=1) |
| 回归六套件 | 沿用 round5 S4 证据(落树内容不变,FINAL_RC=0) |

**E6 复评**: 自我矛盾两根因(kernel.md 口径歧义 + handoff 幽灵声称)均已消除 → **E6 8→9**

## 二、基线分数

### 能力维度 C1-C9(权重 15/15/15/10/10/10/10/10/10)

| C | 指标 | 得分 | 依据(沿 round5,无新变化) |
|---|------|------|------|
| C1 | 指令清晰度 | 9 | AGENTS/kernel/index 三层指令链完整 |
| C2 | 上下文完整度 | 9 | round5 迭代3: 注入新鲜度校验(STALE 横幅+token 年龄) |
| C3 | 流程结构化 | 9 | L1/L2 工作流+token 生命周期 |
| C4 | 输出规范化 | 8 | verdict schema+executor 证据块 |
| C5 | 工具生命周期 | 9 | 9 hook 事件+statusLine 全覆盖 |
| C6 | 知识密度 | 9 | knowledge/ 飞轮+anti-patterns 升华 |
| C7 | 关联编排 | 9 | skill 路由+子代理调度记录 |
| C8 | 可维护性 | 8 | round5 迭代1: 三处双源愈合;lib 7 对相同副本仍存(见 F1) |
| C9 | 错误恢复 | 9 | 飞轮+error-dna+stall 接管 |

C 加权: **925/1050 = 8.81**

### 错误防护 E1-E8(权重 20/20/15/12/10/13/10/10)

| E | 指标 | 得分 | 依据 |
|---|------|------|------|
| E1 | 目标漂移 | 8 | goal 模式 token 锁+progress 强制 |
| E2 | 幻觉输出 | 9 | 证据门禁+oracle 三层 |
| E3 | 虚假完成 | 9 | VerifyGate+物理锁"存在即未完成" |
| E4 | 惯性执行 | 8 | skip-risk 安全阀 |
| E5 | 症状混淆 | 8 | error-dna 分类 |
| E6 | 自我矛盾 | **8→9** | kernel.md 双表落库(ed2fa6a)+幽灵 handoff 自愈,口径矛盾消除 |
| E7 | 过度自信 | 8 | oracle 对抗验证 |
| E8 | 上下文遗忘 | 9 | 水位 50/70/80+handoff 链 |

E 加权: **938/1100 = 8.53**(↑ from 8.41)

### 长期治理(7 维,均分)

| 维度 | 得分 | 依据 |
|------|------|------|
| 抗衰减防线 | 9 | 水位双制+staleness 守卫 |
| AI 赋能全流程自动化 | 8 | hook 链全自动;相对路径锚定缺口(见 F2) |
| 学习笔记积累 | 8 | K1 过滤全侧生效(round5 迭代1) |
| 长期目标一致性 | 8 | improve_plan 五轮延续 |
| 功能标志分明 | 8 | skill/hook/script 分层 |
| 内置安全与洞察 | 8 | owner 裁决维持(R6-B 回执待) |
| Evaluation 评测框架 | 9 | 六套件回归 battery |

治理均分: **58/70 = 8.29**

### 总分

| 维度 | 分 |
|---|---|
| **24 项总加权** | **1921/2220 = 8.65**(round5 终值 8.59 + E6 解锁 +13 分) |
| 24 项最低分 | 8.0 |
| 与 R6 官方 8.65 | **并账达成**(机制口径;官方分变动仍需 R6-B 回执,owner 专属) |

### UX(独立口径,7 维)—— 基线沿用 round5 终值 **54/70 = 7.71**

长期目标一致性 8 / 心智负担减轻 8 / 交互现代化 7 / 用户掌控感 8 / ai智能感 7 / 行为可预测 8 / 人机权限分明 8

## 三、本轮新发现(迭代候选证据)

| # | 发现 | 类别 | 证据 |
|---|---|---|---|
| F1 | `lib/` 7 对相同双源副本(autonomy/handoff_writer/hot_card/oracle_gate_light/phase3_oracle/tool_store/water_level) | C8/防回退 | diff 全同,但任一侧未来编辑即静默分裂(round5 F4 同类温床) |
| F2 | settings.json 10 条命令全相对路径(9 hook+statusLine) | 安全/E 类 | 子目录启动时 hook spawn 失败=fail-open,pretool-gate 等门禁静默失效;`$CLAUDE_PROJECT_DIR` 为官方 hook 环境变量 |
| F3 | `.omc/tokens/20260720/` 3 个 tt-e2e 孤儿锁(json 已无) | 卫生 | 锁泄漏: 删 token 未连带删锁;rm 属硬边界,本轮仅记录 |

## 四、ROI 排序(实际效能口径)

1. **F2 hook 锚定** — 门禁静默失效是 CarrorOS 核心承诺(守护)的破洞;10 处编辑,成本极小 → **迭代1**
2. **F1 lib 双源统一** — 完成 round5 未竟的双源免疫类,防 8.65 回退;7 个 symlink,零行为变化 → **迭代2**
3. **回归脚本入库** — round5 实证痛点(stash 舞蹈失败两轮才跑绿);固化为 scripts/run-regression.sh,未来每轮一键 → **迭代3**
