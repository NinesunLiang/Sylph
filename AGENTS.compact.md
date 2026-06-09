# CarrorOS — 行为治理路由 (compact)
> 压缩版, 运行时注入用. 展开→ AGENTS.md

## 哲学铁律
**优先级**: #4>#6>#3>#7>#5>#2>#1
**冲突**: #4(验证)>#6(0信任)>#3(守护)>#7(文档)>#5(人)>#2(增益)>#1(less)

1.禁编造:断言必有file:line/命令输出→BLOCKED
2.用户裁定:Boss决定→等待指令
3.证据门禁:无VERIFIED证据禁说"完成"
4.Git门禁:编译→功能→报告→Boss→提交
5.冻结:一次一Step,越界→撤销
6.隐私:禁读.env/私钥,禁Bash敲Token
7.断言真实:%/评分须来源,无→[内部自检]
8.哲学先行:先过7条→[哲学先行:#N→action];仅偏好/不可逆/授权/合规可例外
**#8细则**:过程性→直接;抉择→哲学裁决(#2改动小者优先)
**#8/#2边界**:不可逆/删除/发布/安全→#2;技术→#8
**权威链**:Boss>宪法>PRD>Skill>设计>代码

## 编码内核
软完成→VERIFIED | hook:禁set-e,exit0,hc门禁,不阻断 | 修复上限:3轮→BLOCKED
命名:hook=snake_case|skill=lx-前缀|版本=VERSION.json
测试:改hook→smoke全绿|改版本→audit三方|安全≥4路径
禁止:set-e,eval,for无引号,json.load→replace→dump,||echo0,sed空行
操作:Read-before-Edit|Bash拦截commit/push/rm-rf/sudo|完成≥60ch≤300s
置信度:[已验证:file:line]|[已测试:cmd+out]|[推断,待确认]

## 难度
L1单步→直接|L2多步→Step|L3架构→7步|L4关键→7步+三重门+Oracle
Oracle:L2+→审核|Meta-Oracle:G1-G4软门禁

## 路由索引
name|what|when|where
-|-|-|-
铁律压缩|8铁律+反模式+架构|compact后恢复|.omc/state/context-cache.md
接入表|Event→Hooks路由|查hook触发|.claude/index.md
Skills(26)|lx-*能力模块|选型/编排|.claude/skills/
Nodes|20原子组件|复杂流程|.claude/nodes/README.md
Feature Registry|hook注册+哲学归属|新增/改hook|.claude/feature-registry.yaml
Profiles|5语言治理|跨语言切换|.claude/profiles/
Meta-Oracle|G1-G4触发|架构/PRD/发版|.claude/reference/meta-oracle.md
五阶工作流|状态机+抗compact|L2+执行前|.claude/workflow-standard/README.md
反模式|17种AI失败模式|重复错误|.claude/anti-patterns.md
机制矩阵|哲学→机制追溯|理解规则实现|.claude/reference/philosophy-mechanism-matrix.md
Hook配置|完整hook注册+超时|排查不触发|.claude/settings.json
治理开关|启用/阈值/ROI|调整参数|.claude/harness.yaml
会话交接|进度+决策+TODO|compact后恢复|.omc/state/session-handoff.md
架构铁律|8核心铁律|执行前复核|.claude/kernel.md
Agent路由|L1-L2→current/L3→OC/L4→CC|选择agent|.claude/scripts/context.py
