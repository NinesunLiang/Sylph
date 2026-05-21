<!-- CTX-COMPACT:AI-ONLY -->
反模式速查→完整版:Read .claude/anti-patterns.md
A假完成:无证据说完成,demo:应该没问题/基本完成
B功能蔓延:一次改太多,demo:跨5+文件无Step拆分
C破坏性hook:exit2阻断正常,demo:非关键场景exit2
D隐私泄露:.env/密钥被读,demo:Bash明文Token
E跳过门禁:绕过verification,demo:不跑test说VERIFIED
F幻觉路径:编造不存在文件,demo:引用从未创建的文件
G上下文污染:冗余淹没规则,demo:重复注入相同长文本
H权威颠倒:AI自判优先级,demo:忽略Boss即时指令
I1机制影壁:hook无flywheel埋点,demo:跑了无日志
I2纯软约束:只提醒不阻断,demo:AI可忽略的hook提示
L1静默失败:hook静默跳过,demo:set -e下单命令失败整体exit0
R规则漂移:文档≠代码,demo:harness.yaml true但hook不存在
S语义作弊:形式合规内容空,demo:VERIFIED:前面无证据
每反模式=至少1hook触发,发现→查harness-smoke-test对应
