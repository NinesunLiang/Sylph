<!-- CTX-COMPACT:AI-ONLY -->
<!-- kernel.md — AI执行内核（压缩版） -->
<!-- 完整版 → Read .claude/kernel.md -->

架构铁律:
-hook不可失败:禁止set -e,必须exit 0/echo '{"continue":true}'
-hc_enabled门禁:hc_enabled "feature"||exit 0
-修复上限:同一问题3轮→BLOCKED升级
-harness.yaml整数:bash整数比较用60不用0.6,浮点导致[静默失败(DG-54)
-发行包路径:开发机绝对路径禁入packages/,占位符__PROJECT_ROOT__→install.sh替换(DG-31)

命名:hook=snake-case(context-guard.sh),py=snake_case,skill=lx-前缀,yaml=snake_case,版本=6.3.27VERSION.json

错误处理:hook永不阻塞(exit0),证据门禁优先(VERIFIED后标completed),Error DNA自动记录(error-dna.jsonl),3轮上限,禁绕过门禁(需用户"确认放行"),原生批准优先(permissionDecision:ask),关键脚本修改前cp备份+bash -n验证(DG-13,DF-04)

测试:修改hook→harness-smoke-test.sh全绿,修改版本号→audit-hooks.sh三方对齐,安全正则→≥4种路径(裸/相对/绝对/点路径)(DG-29)

禁止:set -e,eval,无file:line断言,for x in $VAR无引号(R24),json.load→str.replace→json.dump损坏转义(DF-04,DG-12),grep -c||echo 0双输出bug→用VAR="${VAR:-0}"(DG-36),sed -i空行号→[ -n "$LINE" ]前置检查(DG-68),macOS sed \+量词→用sed -E或POSIX兼容写法(DG-77)
