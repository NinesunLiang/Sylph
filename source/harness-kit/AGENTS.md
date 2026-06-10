@.claude/kernel.md
@.claude/index.md

# Carror OS — 行为治理路由

| 域 | 说明 | 引用 |
|:---|:---|:---|
| 哲学铁律 | 7条哲学+8条铁律+冲突裁决, 机制→哲学双向追溯见 .claude/reference/philosophy-mechanism-matrix.md | AGENTS.md §哲学铁律 |
哲学优先级:#4(验证)>#6(0信任)>#3(守护)>#7(文档)>#5(人)>#2(增益)>#1(less)

铁律:
1.禁止编造:断言必有file:line/命令输出→BLOCKED,回滚+重做
2.用户裁定:验收/选型/冲突由Boss决定→AI不可自判,等待指令
3.证据门禁:无VERIFIED证据禁止说"已完成/已验证"→重新验证
4.Git门禁[auto]:编译→功能→报告→Boss批准→提交,跳步=回滚
5.范围冻结[auto]:一次一Step,非核心→TODO,越界→撤销
6.隐私防线:禁读.env/私钥,禁Bash敲明文Token→强阻断
7.断言真实[auto]:百分比/评分须有来源URL/file:line,无→标注[内部自检]
8.哲学先行:问人前先过哲学7条,能裁决→[哲学先行:#N→action]直接执行;仅偏好/不可逆/授权/合规可例外
9.读操作不阻断[auto]:Read/Grep/非写Bash 永不阻断，仅在敏感路径( .env/密钥 )保留隐私拦截。所有 hook 不得因读操作 exit(2)，违者 P0

#8细则:过程性→直接执行；抉择性→按决策树裁决
决策树：
  操作是否不可逆/删除/发布/涉及安全？
  ├─ YES → #2 用户裁定 → 问 Boss
  └─ NO  → 技术或过程性决策？
       ├─ 过程性(已验证路径) → 直接执行
       └─ 技术选择 → #2 最小改动原则选方案，标注理由
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
    L1单步→直接（简单）|L2多步→Step清单（中等）|L3+→需审核（复杂）
    审核门:L2+非琐碎→审核,通过→继续,修改→重审,拒绝→报Boss
    7-step:三级渐进(认知→编码→验证),绕不开的黄金弧,每个Step有具体产出物
    triple_gate:Oracle审(每阶段)→Meta-Oracle审(G1-G4触发)→Human终审(Release),三重保底

──────────────────────
路由索引（Read on demand，无@展开；但 skill body.md 是强制执行合约，hook 自动注入）
──────────────────────
name            | 场景                    | where
─────────────────────────────────────────────────────────────
铁律压缩         | /compact后知识恢复       | .omc/state/context-cache.md
接入表           | 查hook触发链             | .claude/index.md
Skills(26个)     | 选型/编排               | .claude/skills/ + docs/guides/cn/skills-catalog.md
Skill依赖图      | 查skill链式调用          | .claude/reference/skill-graph.md
Nodes            | 20个原子工作流组件        | .claude/nodes/README.md
Feature Registry | hook功能注册+哲学归属     | .claude/feature-registry.yaml
Schemas          | 数据结构校验              | .claude/schemas/registry.yaml
Profiles         | 5语言治理配置             | .claude/profiles/
发布流水线       | 发版/打包                | scripts/package-release.sh
Source Mirror    | 打包前检查                | .claude/reference/source-mirror-discipline.md
狗粮Triage       | 问题诊断                  | .claude/skills/lx-dogfood/SKILL.md
Red Team         | 防御升级                  | .claude/reference/red-team.md
三源一致性       | 一致性验证                | .claude/reference/three-source-consistency.md
审核门           | 架构/PRD/高分/发版时      | .claude/reference/meta-oracle.md
五阶工作流 v4.0  | L2+任务前                | .claude/workflow-standard/README.md
UI还原工作流     | UI还原                   | .claude/docs/ui-restoration-workflow.md
执行模式         | 模式选择（Race/Stepwise 状态机）      | .claude/reference/execution-modes.md
执行模式矩阵     | RPE/Ghost/Goal/监督模式选 race/stepwise | docs/technical/cn/execution-mode-matrix.md
自主决策链       | 无人值守决策              | .claude/reference/autonomous-decision-chain.md
Task系统         | RPE任务模板               | .claude/task_sys/
Race检测         | 并行冲突检测              | .claude/race/state-machine.md
RaceSwarm并行(v1) | 旧race_swarm.py兼容   | .claude/scripts/race_swarm.py
RaceSwarm并行(v2) | 文档驱动并行(新)        | packages/carroros-gov/src/scripts/race-tool.py + .claude/reference/race-subagent-protocol.md
编码规范         | 写hook/Bash前             | .claude/rules/
反模式           | 17种AI失败模式+对策       | .claude/anti-patterns.md
学习笔记         | 历史踩坑记录               | .claude/claude-next.md
机制矩阵         | 规则实现追溯 / 哲学一致性回顾  | .claude/reference/philosophy-mechanism-matrix.md
Hook配置         | 排查hook不触发             | .claude/settings.json
治理开关         | 调整参数                   | .claude/harness.yaml
会话交接         | compact后/跨会话恢复        | .omc/state/session-handoff.md
subagent状态     | 子agent调用记录+状态同步    | .omc/state/subagent-state.md + subagent-usage.jsonl
用户文档         | 入门/进阶/LSP              | .claude/reference/docs-index.md
架构铁律         | 执行前快速复核              | .claude/kernel.md
跨平台路由       | 跨平台切换                | .claude/scripts/ + packages/carroros-gov/
Agent 路由       | 选择agent                 | .claude/scripts/context.py
Thinking Gate    | thinking过滤               | .claude/reference/thinking-content-gate.md
─────────────────────────────────────────────────────────────
