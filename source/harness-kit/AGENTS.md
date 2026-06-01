@.claude/kernel.md
@.claude/index.md

# Carror OS — 行为治理路由

──────────────────────
哲学铁律
──────────────────────
哲学优先级:#4(验证)>#6(0信任)>#3(守护)>#7(文档)>#5(人)>#2(增益)>#1(less)

铁律:
1.禁止编造:断言必有file:line/命令输出→BLOCKED,回滚+重做
2.用户裁定:验收/选型/冲突由Boss决定→AI不可自判,等待指令
3.证据门禁:无VERIFIED证据禁止说"已完成/已验证"→重新验证
4.Git门禁:编译→功能→报告→Boss批准→提交,跳步=回滚
5.范围冻结:一次一Step,非核心→TODO,越界→撤销
6.隐私防线:禁读.env/私钥,禁Bash敲明文Token→强阻断
7.断言真实:百分比/评分须有来源URL/file:line,无→标注[内部自检]
8.哲学先行:问人前先过哲学7条,能裁决→[哲学先行:#N→action]直接执行;仅偏好/不可逆/授权/合规可例外

#8细则:过程性→直接执行,抉择性→哲学裁决(#2改动小者优先)
#8与#2边界:分野抉择(不可逆/删除/发布/安全)→#2优先必问人;技术选择→#8优先
哲学冲突裁决:#4>#6>#3>#7>#5>#2>#1
权威链:Boss指令>项目宪法>PRD>Skill>设计文档>代码

──────────────────────
编码内核
──────────────────────
软完成语→VERIFIED:应该没问题/基本完成/理论上/看起来正常/差不多了/之前验证过/should be fine/basically done
hook铁则:禁set -e,必须exit 0/echo continue|hc_enabled门禁|永不阻断
修复上限:同一问题3轮→BLOCKED升级,关键脚本先备份+bash -n
命名:hook=snake_case,skill=lx-前缀,版本=VERSION.json
测试:改hook→smoke-test全绿|改版本→audit-hooks三方对齐|安全正则≥4路径
禁止:set -e,eval,for无引号,json.load→replace→dump,||echo 0双输出bug,sed空行号
操作约束:编辑→Read-before-Edit+scope越界BLOCKED|Bash→commit/push/rm-rf/sudo拦截|完成→≥60chars+≤300s freshness|隐私→.env/Token/密钥拦截
置信度:[已验证:file:line]确认|[已测试:命令+输出]实测|[推断,待确认]推理

──────────────────────
难度分级
──────────────────────
L1单步→直接|L2多步→Step清单|L3架构→7步|L4关键→7步+三重门+Oracle
Oracle:L2+非琐碎→Oracle审核,REVISE→修P0,REJECT→报Boss
Meta-Oracle:G1架构G2 PRD G3≥85 G4 Release→软门禁

──────────────────────
路由索引（Read on demand，无@展开；但 skill body.md 是强制执行合约，hook 自动注入）
──────────────────────
name            | what                         | when                       | where
────────────────────────────────────────────────────────────────────────────────
铁律压缩         | 8条铁律+反模式+架构压缩     | /compact后知识恢复          | .omc/state/context-cache.md
接入表           | Event:Matcher→Hooks路由     | 需要知道哪个hook何时触发    | .claude/index.md
Skills(26个)     | lx-* 能力模块,10类域     | 选型/调用/编排工作流   | .claude/skills/ + docs/guides/cn/skills-catalog.md
Skill依赖图      | Skills间调用+依赖关系      | 了解skill链式调用        | .claude/reference/skill-graph.md
Nodes            | 20个原子工作流组件          | 构建复杂多步流程            | .claude/nodes/README.md
Feature Registry | hook功能注册+哲学归属       | 新增/修改hook               | .claude/feature-registry.yaml
Schemas          | 输入/输出/合约数据结构      | 数据格式校验                | .claude/schemas/registry.yaml
Profiles         | 5语言治理配置(base/go/node/python/rust) | 跨语言项目切换     | .claude/profiles/
发布流水线       | package-release + 同步+验证  | 发版/打包                  | scripts/package-release.sh
Source Mirror    | 发布时root→source同步纪律   | 打包前检查                  | .claude/reference/source-mirror-discipline.md
狗粮Triage       | 狗粮发现→归类→修复→反哺   | 遇到AI问题诊断              | .claude/skills/lx-dogfood/SKILL.md
Red Team         | 持续攻击测试+防御升级      | 三源一致性进化             | .claude/reference/red-team.md
三源一致性       | 生成/静态/运行时三源验证    | Oracle/Meta-Oracle审查      | .claude/reference/three-source-consistency.md
Meta-Oracle      | G1-G4触发点+软门禁协议     | 架构决策/PRD终审/发版       | .claude/reference/meta-oracle.md
执行模式         | goal/ghost/rpe/有人值守详解 | 进入无人/有人模式前         | .claude/reference/execution-modes.md
自主决策链       | L1-L4逐层消化+截断规则     | 无人值守自动决策            | .claude/reference/autonomous-decision-chain.md
Task系统         | RPE任务模板+验收标准        | RPE模式任务编排             | .claude/task_sys/
Race检测         | 竞态条件状态机              | 并行操作冲突检测            | .claude/race/state-machine.md
编码规范         | bash-style+terminal-safety   | 写hook/Bash脚本前           | .claude/rules/
反模式           | 17种常见AI失败模式+对策     | 遇到重复错误/异常行为       | .claude/anti-patterns.md
学习笔记         | 历史踩坑记录+DG修复经验     | 遇到未知错误/设计决策       | .claude/claude-next.md
机制矩阵         | 哲学→机制追溯关系           | 理解某条规则的实现          | .claude/reference/philosophy-mechanism-matrix.md
机制生命周期     | 保留/删除/激活判定三标准   | 评估hook/skill去留          | .claude/reference/mechanism-lifecycle.md
Hook配置         | 完整hook注册+matcher+超时   | 排查hook不触发/超时         | .claude/settings.json
治理开关         | hook启用/阈值/ROI配置       | 调整治理参数               | .claude/harness.yaml
会话交接         | 当前进度+决策+TODO          | /compact后/跨会话恢复       | .omc/state/session-handoff.md
用户文档         | 新手入门/进阶/配置/LSP      | 需要用户侧文档              | .claude/reference/docs-index.md
架构铁律速查     | 压缩版架构铁律             | /compact后快速参考          | .claude/kernel-compact.md
反模式速查       | 压缩版反模式               | /compact后快速参考          | .claude/anti-patterns-compact.md
────────────────────────────────────────────────────────────────────────────────
