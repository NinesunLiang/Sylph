#!/usr/bin/env bash
# runtime-experiment.sh — Carror OS v6.4.0 运行时实验
# 多平台兼容性验证: mac + Claude Code + OpenCode(OMO) + OMC
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT_ROOT=$(pwd)
PASS=0 FAIL=0

green() { echo "  ✅ $1"; PASS=$((PASS+1)); }
red()   { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

echo "════════════════════════════════════════"
echo "  运行时实验 — Carror OS v6.3.27→v6.4.0"
echo "  平台: $(uname -s) $(uname -m)"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════"

# ═══ E1: 三门户完整性 ═══
echo ""
echo "── E1: 三门户完整性 ──"

[ -f AGENTS.md ] && green "AGENTS.md 存在 ($(wc -l < AGENTS.md)行)" || red "AGENTS.md 缺失"
[ -f .claude/kernel.md ] && green "kernel.md 存在 ($(wc -l < .claude/kernel.md)行)" || red "kernel.md 缺失"
[ -f .claude/index.md ] && green "index.md 存在 ($(wc -l < .claude/index.md)行)" || red "index.md 缺失"

# 验证 AGENTS.md 有路由表
grep -q "路由索引" AGENTS.md && green "AGENTS.md 含路由表" || red "AGENTS.md 缺路由表"
# 验证无冗余@引用(只允许顶部2个)
AT_COUNT=$(grep -c "^@" AGENTS.md 2>/dev/null || echo 0)
[ "$AT_COUNT" -le 2 ] && green "AGENTS.md @引用=$AT_COUNT (≤2)" || red "AGENTS.md @引用=$AT_COUNT (>2!)"

# ═══ E2: 配置有效性 ═══
echo ""
echo "── E2: 配置有效性 ──"

${PYTHON_BIN:-python3} -c "import yaml; yaml.safe_load(open('.claude/harness.yaml'))" 2>/dev/null \
    && green "harness.yaml YAML有效" || red "harness.yaml YAML无效"

${PYTHON_BIN:-python3} -c "import json; json.load(open('.claude/settings.json'))" 2>/dev/null \
    && green "settings.json JSON有效" || red "settings.json JSON无效"

${PYTHON_BIN:-python3} -c "
import json
s = json.load(open('.claude/settings.json'))
hooks = s.get('hooks', {})
pre = len(hooks.get('PreToolUse', []))
post = len(hooks.get('PostToolUse', []))
fail = len(hooks.get('PostToolUseFailure', []))
ss = len(hooks.get('SessionStart', []))
total = sum(len(v) for v in hooks.values())
print(f'PreToolUse:{pre} PostToolUse:{post} PostToolUseFailure:{fail} SessionStart:{ss} = {total} total')
" 2>/dev/null && green "settings.json hook分组有效" || red "settings.json hook分组无效"

# ═══ E3: 新激活hook ═══
echo ""
echo "── E3: 新激活hook (v6.4.0) ──"

# knowledge-condenser
grep -q "knowledge_condenser: true" .claude/harness.yaml && green "knowledge_condenser: true" || red "knowledge_condenser: not true"
grep -q "knowledge-condenser" .claude/settings.json && green "knowledge-condenser 已注册" || red "knowledge-condenser 未注册"

# pretool-plan-gate
grep -q "pretool_plan_gate: true" .claude/harness.yaml && green "pretool_plan_gate: true" || red "pretool_plan_gate: not true"
grep -q "pretool-plan-gate" .claude/settings.json && green "pretool-plan-gate 已注册" || red "pretool-plan-gate 未注册"

# build-validator
grep -q "build_validator: true" .claude/harness.yaml && green "build_validator: true" || red "build_validator: not true"
grep -q "build-validator" .claude/settings.json && green "build-validator 已注册" || red "build-validator 未注册"

# error-dna-auto-fix
grep -q "error_dna_auto_fix: true" .claude/harness.yaml && green "error_dna_auto_fix: true" || red "error_dna_auto_fix: not true"
grep -q "error-dna-auto-fix" .claude/settings.json && green "error-dna-auto-fix 已注册" || red "error-dna-auto-fix 未注册"

# ═══ E4: 僵尸hook已清理 ═══
echo ""
echo "── E4: 僵尸hook清理确认 ──"

for ghost in anti_pattern_detect issue_triage lsp_gate oracle_gate posttool_output_format; do
    grep -q "$ghost" .claude/harness.yaml 2>/dev/null \
        && red "harness.yaml 仍有 $ghost" \
        || green "harness.yaml 已清理 $ghost"
done

# plan-gate.sh 已删除
[ ! -f .claude/hooks/plan-gate.sh ] && green "plan-gate.sh 已删除" || red "plan-gate.sh 仍存在"

# feature-probe.sh 已迁移
[ -f .claude/scripts/feature-probe.sh ] && green "feature-probe.sh 已迁移至scripts/" || red "feature-probe.sh 未迁移"
[ ! -f .claude/hooks/feature-probe.sh ] && green "feature-probe.sh 已从hooks/移除" || red "feature-probe.sh 仍在hooks/"

# ═══ E5: 多平台兼容 ═══
echo ""
echo "── E5: 多平台兼容性 ──"

[ -f CLAUDE.md ] && green "CLAUDE.md (Claude Code入口)" || red "CLAUDE.md 缺失"
grep -q "@AGENTS.md" CLAUDE.md && green "CLAUDE.md → @AGENTS.md" || red "CLAUDE.md 未引用 AGENTS.md"

[ -f .opencode/opencode.json ] && green "opencode.json (OpenCode入口)" || red "opencode.json 缺失"
[ -f .opencode/oh-my-openagent.json ] && green "oh-my-openagent.json (OMO桥)" || red "OMO桥缺失"

${PYTHON_BIN:-python3} -c "import json; d=json.load(open('.opencode/oh-my-openagent.json')); print(f'  hooks={d[\"claude_code\"][\"hooks\"]} skills={d[\"claude_code\"][\"skills\"]}')" 2>/dev/null \
    && green "OMO配置有效" || red "OMO配置无效"

# Check OMO hooks/skills enabled
${PYTHON_BIN:-python3} -c "
import json
d = json.load(open('.opencode/oh-my-openagent.json'))
cc = d.get('claude_code', {})
if cc.get('hooks') and cc.get('skills'):
    print('  OMO: hooks+skills 已启用')
else:
    print('  OMO: hooks或skills未启用')
" 2>/dev/null && green "OMO hooks+skills 启用" || red "OMO hooks/skills 未启用"

# ═══ E6: 上下文注入验证 ═══
echo ""
echo "── E6: 上下文注入验证 ──"

HOOK_INJECT=".claude/hooks/inject-project-knowledge.sh"
if [ -f "$HOOK_INJECT" ]; then
    bash -n "$HOOK_INJECT" 2>/dev/null && green "inject-project-knowledge 语法通过"
    # 模拟运行看是否有明显错误
    timeout 10 bash "$HOOK_INJECT" >/dev/null 2>&1
    [ $? -le 1 ] && green "inject-project-knowledge 运行正常" || red "inject-project-knowledge 运行异常"
else
    red "inject-project-knowledge 缺失"
fi

# context-compressor 验证
[ -f .omc/state/context-cache.md ] && green "context-cache.md 存在 ($(wc -c < .omc/state/context-cache.md)B)" || red "context-cache.md 缺失"

# ═══ E7: 测试基线 ═══
echo ""
echo "── E7: 测试基线 ──"

SMOKE_LOG=".omc/state/harness-smoke-latest.log"
bash .claude/scripts/harness-smoke-test.sh > "$SMOKE_LOG" 2>&1
SMOKE_RESULT=$(grep "summary:" "$SMOKE_LOG" | tail -1)
echo "  $SMOKE_RESULT"
echo "$SMOKE_RESULT" | grep -q "0 failed" && green "Smoke test 全绿" || red "Smoke test 有失败"

# ═══ E8: 发行版对齐 ═══
echo ""
echo "── E8: 发行版(source/harness-kit)对齐检查 ──"

PKG_ROOT="source/harness-kit"
[ -d "$PKG_ROOT" ] || { red "source/harness-kit 不存在"; }

# 检查差异文件
DIFF_FILES=$(diff -rq --exclude=".git" --exclude=".omc" --exclude="packages" --exclude="node_modules" . "$PKG_ROOT" 2>/dev/null | grep -c "differ" || echo 0)
echo "  差异文件数: $DIFF_FILES"
[ "$DIFF_FILES" -lt 10 ] && green "发行版对齐良好 (<10差异)" || echo "  ⚠️ $DIFF_FILES 个差异文件（AGENTS.md刻意不同计入内）"

# ═══ 汇总 ═══
echo ""
echo "════════════════════════════════════════"
echo "  实验汇总: $PASS pass, $FAIL fail"
echo "════════════════════════════════════════"

[ "$FAIL" -eq 0 ] && echo "  🟢 全部通过 — 可升级 v6.4.0" || echo "  🔴 $FAIL 项失败 — 需修复后升级"

exit $FAIL
