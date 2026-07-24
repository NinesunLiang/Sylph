# Round7 可行性核验 — 三模型提案 × 仓库真态对账

> 四态判定：可行 / 已存在 / 撞约束 / 需人类。关键背景：三模型产出基于材料包，**不知 2026-07-20 下午的幻影修复**(e6026aa)，涉及时序的提案已全部重订基线。

## 一、三模型共识项(3/3 同指)

| # | 提案 | 判定 | 对账 |
|---|---|---|---|
| 1 | 统一 active-token 单一 reader(SSOT) | **可行** | 幻影根因(mtime 自续命)今日已修： pretool-gate 与 user-approve 的 `_latest_token` 已加终态过滤(e6026aa)。**但 session-start.py:68 仍用裸 mtime 无过滤** → 正解=抽 `lib/task_ssot.py`,三钩委托 |
| 2 | E7 校准账(claim→overturned) | **可行，采 GPT 轻量版** | Opus 版新增 hook+独立 DB,且 PostToolUse 看不到助手文本(需 transcript 解析，过重);GPT 版复用 audit(claim_id/refutes_claim_id)+机读报表，零新库 |
| 3 | pre-commit 接回归 | **可行** | `scripts/run-regression.sh` 已存在(round6)，只剩 `.git/hooks/pre-commit` 接线(人类安装) |
| 4 | C4 输出 schema 机检 | **可行，stdlib 版** | jsonschema 外部依赖不确定 → stdlib 手写必填校验；挂在既有 `cmd_lint`(carros_base.py:1136) |

## 二、单模型提案

| 提案 | 来源 | 判定 | 对账 |
|---|---|---|---|
| E4 scope 门 warn→BLOCK | opus | **已存在** | 今日实证：scope 门硬 BLOCK 我方 3 次(plan.md/executor.md/brief.md);warn 仅在 CARROROS_EDIT_SCOPE=warn 或 goal 模式 |
| 水位 45% 预警层 | opus | 可行 | 小改，只读阈值前早告警 |
| gate 失败≥3 次同签名→ESCALATE | opus | 可行 | 今日实证需求：同文件连续 3 次 BLOCK 无升级机制 |
| 飞轮升华质量门(unknown 降权/细分) | grok | 可行 | flywheel.py:176 写入前加过滤；unknown×155 低信噪实证 |
| 对抗测试扩充(goal/ghost 互斥、E2/E3 trust、token-rm、malformed JSON) | 3/3 | 可行 | 并入现有套件；launcher cwd 项 round6 已覆盖 |
| session-end 清洁 hook | opus | 可行(P2 缓) | 价值次要 |
| anomaly_detector 日报 | opus | 可行(P2 缓) | 与失败升级部分重叠 |
| AGENTS.md §外部挑战记录 | opus | **需人类** | 冻结文档(铁律 6) |
| UX 两维提分 | gpt/grok | **需人类裁决** | GPT：须真实 UX 证据或人类"维度不适用"裁决；禁止后端治理证据冒充 |
| R6-B token 轮换 | 3/3 | **需人类** | owner 认领中 |
| 批量删 19 个 archived 旧 token | kimi 补充 | **需人类** | >5 文件 rm 硬边界；过滤器落地后已惰性，非必需 |
| E1/E5 排除(Opus)与 E4 拒伪施工(grok) | — | 采纳 | E1 缺口已由今日修复闭合(幻影=在录事故);E5 root_cause 字段保留为候选 |

## 三、对抗审查响应(三模型共指 9 分虚高疑点)

| 疑点 | 处置 |
|---|---|
| C2 goal/ghost 互斥未对抗覆盖(opus) | **修正(2026-07-20)**：mutex 存在于 `lifecycle_ssot.set_mode`(:190-203)但生产调用方=0(仅测试)=**僵尸机制**；处置=接线(lx-goal/lx-ghost 入口调 set_mode)+对抗扩充(双 token 期望拒绝),二选一裁决；opus 指的文件+行号(goal_state_machine.py:45)不准,机制存在性部分成立 |
| C6 trust_level E2/E3 不区分+audit 无完整性(opus) | 入对抗扩充包；E2/E3 区分设计裁决 → 需人类 |
| E3 token 可被 AI rm(opus) | 今日实证成立(我经授权删了 3 个);rm 硬边界是规则层非机械门 → 机制化(目录写保护门)列入候选，需设计裁决 |
| GPT 十分准入 10 条/18 禁止 | 采纳为施工纪律(尤其：改生产路径非旁路 demo、≥1 正向+≥2 对抗、无第二真相源) |

## 四、分数账(诚实口径,Grok G-Eng/G-Org 双门)

- 当前 1931/2220=8.70；今日幻影修复可证 E1 8→9(+20)→1951=8.79
- 全落 PKG-1..6+8：治理自动化+10、学习笔记+10、E7+10、C4+10、E4+12、E5+10 → 2053/2220=**9.25(G-Eng)**
- 内置安全 8.0 不动(R6-B 需人类)→ **G-Org 最低分卡住，不宣称"全面 9+"**(采纳 grok 双门)
- UX 两 7 独立，待人类裁决
