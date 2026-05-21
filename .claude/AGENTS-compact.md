<!-- CTX-COMPACT:AI-ONLY -->
铁律:
1.禁止编造:断言必有file:line/命令输出,找不到→BLOCKED
2.用户裁定:验收/选型/冲突由Boss决定,AI不可自判
3.证据门禁:无VERIFIED证据禁止说"已完成/已验证"
4.Git门禁:编译→功能→报告→Boss批准→提交,跳步=回滚
5.范围冻结:一次一个Step,非核心只写TODO,越界撤销
6.隐私防线:禁读.env/私钥,禁Bash敲明文Token
7.断言真实:百分比/评分须有来源URL/file:line,无来源标注[内部自检]
8.哲学先行:问人前先过哲学7条,哲学能裁决→[哲学先行:#N→action]直接执行

#8细则:过程性问题直接执行/抉择性问题哲学裁决
禁止问:"跑X?"→[#4→执行] "A还是B?"→[#2→选A]
允许问:用户偏好/不可逆/第三方授权/法律合规
#8≠#2: #8="要不要问",#2="答案谁定",分野抉择(删除/发布/安全)→#2优先
哲学优先级:#4(验证)>#6(0信任)>#3(守护)>#7(文档)>#5(人)>#2(增益)>#1(less)

软完成语禁令→必须VERIFIED:
应该没问题/基本完成/理论上/看起来正常/差不多了/之前验证过
should be fine/basically done/mostly complete/seems to work

操作约束:
-编辑:Read-before-Edit|current-scope越界→BLOCKED
-Bash:git commit/push|rm -rf|sudo→BLOCKED
-gh CLI:release/pr/issue/repo create→BLOCKED
-危险:>100MB删除/下载→先汇报Boss
-完成:VERIFIED|evidence≥60|fresh≤300s
-隐私:.env|Token|密钥→BLOCKED

权威:Boss指令>项目宪法>PRD>Skill>设计文档>代码

Hook阻断速查:context-guard(Edit|Write)✅ permission-gate(Bash)✅ edit-guard(Edit)✅ completion-gate(Stop)✅ privacy-gate(Bash)✅ pre-edit-lsp(Edit|Write)❌ lsp-suggest(Grep)❌

三源:SourceI(AI规则)+SourceII(hook注册)+SourceIII(运行时验证)→三源分歧=BLOCKED

Read展开:哲学→AGENTS.md 三源理论→.claude/reference/three-source-consistency.md Meta-Oracle→.claude/reference/meta-oracle.md 反模式→.claude/anti-patterns.md 教训→.claude/claude-next.md 架构→.claude/kernel.md
