<!-- CTX-COMPACT:AI-ONLY -->
教训速查→完整版:Read .claude/claude-next.md,每R=一个生产事故
R22:bash set -e空变量→hook静默退出→用${var:-default}
R23:磁盘脚本+settings.json+harness.yaml三方一致→audit-hooks校验
R24:bash glob污染→set -f防御,所有hook第一行
R26:matcher扩大→审查脚本内白名单,两层过滤语义一致
R29:.* matcher→自锁危机,禁万能matcher
R31:gh CLI→permission-gate盲区,显式拦截gh write
R33:compact-detect→知识注入丢失,每次compact后重注入
R34:"系统没这问题"→逐文件验证,grep一遍≠验证
R39:注入预算120行→超限硬截断,优先核心文件
R40:Ghost mode→门禁降级,永不阻断read/diagnostic
R41:off-by-one→error-dna 99%数据丢失,轮转边界验证
原则:发现bug→写R教训→补hook/smoke test→永不重犯
