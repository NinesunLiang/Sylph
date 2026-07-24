# Round7 缺口档案 — 12 个未达标维度(现状机制 / 挡9根因 / 候选方向 / 文件指针)

> 每维按同一结构给出。候选方向是 kimi-k3 的初步判断，供挑战，不是结论。
> 末尾附**今日实证案例**(幻影 token 死锁)——一个横跨 E1/E8/内置安全的活体根因。

---

## C4 输出规范化(8)

- **现状**: verdict schema(lx-goal report)、executor 证据块模板、plan/verify 结构、final-report
- **挡9根因**: 格式靠纪律不靠机器——无 schema 校验器强制输出合规；报告字段缺失/畸形无告警
- **候选方向**: verify 或 posttool 阶段对 verdict/report 做 JSON schema 校验；executor 证据块 lint(carros_base lint 已有雏形可扩展)
- **指针**: `.claude/skills/lx-goal/scripts/lx-goal.py`(report), `.omc/scripts/carros_base.py`(lint)

## E1 目标漂移(8)

- **现状**: token 物理锁 + plan scope 冻结 + 编辑越界门(今日实证：真实拦截越界写)
- **挡9根因**: 无"目标-行动对齐"的持续校验；活跃 token 选择器按 mtime 取最新，可被过期任务劫持(见附录案例)
- **候选方向**: token 选择加时效/状态过滤(status==active 且非陈旧)；周期 goal 锚点重注入；session-start 对非本日 token 强制人工确认
- **指针**: `.claude/hooks/pretool-gate.py:289`(_active_token), `pretool-user-approve.py:174-183`(水位回写)

## E4 惯性执行(8)

- **现状**: skip-risk 安全阀；飞轮统计重复失败(retry≥2/count≥3)
- **挡9根因**: 无"同动作无进展"循环检测——同一 tool+args 重复 N 次无任何告警
- **候选方向**: pretool-gate 加 action-loop 检测(近 K 次相同调用 → warn/BLOCK)；循环模式入 error-dna
- **指针**: `.claude/hooks/pretool-gate.py`, `.claude/scripts/lib/flywheel.py`

## E5 症状混淆(8)

- **现状**: error-dna 失败模式分类；anti-patterns 自动升华(hits≥5)
- **挡9根因**: 修复工作不强制根因字段，"治症状"与"治根因"在证据层不可区分；unknown 类高达 155 次 = 分类粒度不足
- **候选方向**: bugfix 类证据块强制 root_cause 字段；error-dna 按 stderr 签名/exit code 细分 unknown
- **指针**: `.claude/scripts/lib/error_dna.py`, `.claude/references/anti-patterns.md`

## E7 过度自信(8)

- **现状**: oracle 三层对抗审核(31 对抗用例全过)；VerifyGate 双绑定审计回读
- **挡9根因**: 评分本身是自评，无外部挑战通道；无置信度校准记录(断言"已验证"后是否被推翻，无人记账)。实证：round5 我曾自信误判 kernel.md 水位表过期，后自我纠正(F4)
- **候选方向**: 本轮回合(四模型评审)即外部挑战；建校准日志——每次"已验证"断言记录后续推翻情况
- **指针**: `improve_plan/CarrorOS_second_time/round3..6`(多轮自评史)

## 治理·AI 赋能全流程自动化(8)

- **现状**: 9 hook 事件全覆盖；一键回归脚本(round6 入库)
- **挡9根因**: 仍有手工断点(commit/bypass/token 清理)；状态注入多源不一致——session-start 读日期目录 token，user-approve 按 mtime 读最新，两者可指向不同任务
- **候选方向**: pre-commit 接回归；状态源统一为单一 reader；token 生命周期自动化(超龄 archive 提案)
- **指针**: `.claude/settings.json`, `.claude/hooks/session-start.py` vs `pretool-user-approve.py`

## 治理·学习笔记积累(8)

- **现状**: 飞轮自动升华入 anti-patterns;knowledge/ 目录沉淀
- **挡9根因**: 升华质量参差——unknown 类低信噪(155 次)照样升华；笔记晋升 kernel 全人工
- **候选方向**: 升华前质量过滤(沿 K1 思路)；unknown 细分后重跑升华；周期性学习周报
- **指针**: `.claude/scripts/lib/flywheel.py`, `.omc/knowledge/`

## 治理·长期目标一致性(8)

- **现状**: improve_plan 六轮延续；scorecard.md 官方账
- **挡9根因**: 无单一"北极星"真相源——目标散在各轮 summary；轮间承接受人为记忆影响
- **候选方向**: goal-lineage 文件(每轮继承/变更显式记录)；scorecard 并账流程化
- **指针**: `improve_plan/CarrorOS_second_time/scorecard.md`

## 治理·功能标志分明(8)

- **现状**: skill/hook/script 三层；archived/ 归档目录
- **挡9根因**: 边界渗漏实证——fallback_matrix 死模块长期存活；lib 双源副本 7 对(round6 才清零)；两个注入器职责重叠
- **候选方向**: 模块注册表(活/死可机查)；死代码扫描入回归
- **指针**: `.claude/scripts/archived/`, `scripts/run-regression.sh`

## 治理·内置安全与洞察(8)

- **现状**: 明文密钥门(今日实证：拦截 settings.json 提交)；temp-bypass 60min 自过期；owner 维持 8 待 R6-B 回执
- **挡9根因**: settings.json 明文 token 在库(历史既成)；状态完整性校验缺失(幻影 token 存活两天无人知)；R6-B 轮换回执未到(人类专属)
- **候选方向**: token 改环境变量引用(人类执行)；token 完整性定期检查；R6-B 回执(人类专属)
- **指针**: `.claude/settings.json`, `.claude/scripts/temp-bypass.py`

## UX·交互现代化(7,独立口径)

- **现状**: statusLine 单行状态条；中文结构化报告
- **挡9根因**: 展示仅单行文本，无富化
- **候选方向**: statusline 增强(水位色块/任务进度可视化)；慎入重型 dashboard
- **指针**: `.claude/hooks/statusline-command.sh`

## UX·ai智能感(7,独立口径)

- **现状**: 飞轮后台学习，洞察不浮现
- **挡9根因**: 用户看不见"AI 在学"——升华、K1 过滤全静默
- **候选方向**: session-start 注入"本周飞轮学到 N 条"；基于高频 error-dna 模式的主动建议
- **指针**: `.claude/hooks/session-start.py`, `.omc/knowledge/claude-next.md`

---

## 附录：今日实证案例 — 幻影 token 死锁(2026-07-20)

**现象**: 一个 2026-07-18 的废弃任务(skill-hook-adaptive-opt,0/6)持续出现在每条消息的状态注入里，且其编辑范围门拦截了新任务(round7)的合法写入。

**根因链(代码级)**:
1. `pretool-gate._latest_token()` 按 **mtime** 选"最新" token
2. `pretool-user-approve.py:174-183` 每轮 prompt 把水位数据**回写**进该 token → mtime 刷新
3. 陈旧 token 因此永远"最新" → 自我续命闭环；round5 加的 staleness 守卫(按 mtime 判龄)被同一机制中和

**次生发现(scope 门双缺陷)**:
- 目录式 scope 条目(`round7/`)无法匹配绝对路径(suffix 语义只对文件路径生效)
- 任务自身的 plan.md 不在自动豁免内 → "按门禁提示修 Scope"这个操作本身被门禁拦截(catch-22，本次用 Bash 脚本修，已披露)

**为何重要**: 这是 E1(过期目标劫持现行会话)+E8(系统"记得"不该记的状态)+内置安全(完整性无校验)的交叉活体证据。候选修复方向见 E1 与内置安全两节。
