#!/usr/bin/env bash
# P1~P3 修改验证脚本
set -euo pipefail
echo "=== P1~P3 机制化改进 — 执行后验证 ==="
echo ""

echo "--- Phase 1: 文档修改 ---"
grep -q 'REVISE/REJECT in autonomous mode' .claude/reference/autonomous-decision-chain.md && echo "✅ decision-chain: Oracle截断" || echo "❌ missing"
grep -q 'Re-submitting to Oracle after REVISE/REJECT' .claude/reference/autonomous-decision-chain.md && echo "✅ decision-chain: Forbidden补充" || echo "❌ missing"
grep -q 'mechanization_status' .claude/anti-patterns.md && echo "✅ anti-patterns: 机制化状态" || echo "❌ missing"
echo ""

echo "--- Phase 2: 独立文件修改 ---"
grep -q 'skipped-errors.md' .claude/hooks/pretool-retry-check.sh && echo "✅ retry-check: mode degradation记录" || echo "❌ missing"
grep -q 'auto_release' .claude/hooks/fuzzy-block.sh && echo "✅ fuzzy-block: 智能恢复" || echo "❌ missing"
grep -q 'autonomous mode skip' .claude/hooks/context-guard.sh && echo "✅ context-guard: critical mode degradation" || echo "❌ missing"
[ -f .claude/hooks/cross-platform-smoke-test.sh ] && echo "✅ cross-platform-smoke-test: 文件存在" || echo "❌ missing"
echo ""

echo "--- Phase 3: 新增hook ---"
[ -f .claude/hooks/phase-state-tracker.sh ] && echo "✅ phase-state-tracker: 文件存在" || echo "❌ missing"
[ -f .claude/hooks/pretool-b1-detect.sh ] && echo "✅ pretool-b1-detect: 文件存在" || echo "❌ missing"
[ -f .claude/hooks/pretool-git-gate.sh ] && echo "✅ pretool-git-gate: 文件存在" || echo "❌ missing"
[ -f .claude/hooks/pretool-scope-gate.sh ] && echo "✅ pretool-scope-gate: 文件存在" || echo "❌ missing"
[ -f .claude/hooks/permission-frequency-tracker.sh ] && echo "✅ permission-frequency-tracker: 文件存在" || echo "❌ missing"
echo ""

echo "--- Phase 4: 配置注册 ---"
grep -q 'cross_platform_smoke_test' .claude/harness.yaml && echo "✅ harness: cross_platform_smoke_test" || echo "❌ missing"
grep -q 'phase_state_tracker' .claude/harness.yaml && echo "✅ harness: phase_state_tracker" || echo "❌ missing"
grep -q 'pretool_b1_detect' .claude/harness.yaml && echo "✅ harness: pretool_b1_detect" || echo "❌ missing"
grep -q 'pretool_git_gate' .claude/harness.yaml && echo "✅ harness: pretool_git_gate" || echo "❌ missing"
grep -q 'pretool_scope_gate' .claude/harness.yaml && echo "✅ harness: pretool_scope_gate" || echo "❌ missing"
grep -q 'permission_frequency_tracker' .claude/harness.yaml && echo "✅ harness: permission_frequency_tracker" || echo "❌ missing"
grep -q 'cross-platform-smoke-test' .claude/settings.json && echo "✅ settings: cross-platform-smoke-test" || echo "❌ missing"
grep -q 'pretool-b1-detect' .claude/settings.json && echo "✅ settings: pretool-b1-detect" || echo "❌ missing"
grep -q 'pretool-git-gate' .claude/settings.json && echo "✅ settings: pretool-git-gate" || echo "❌ missing"
grep -q 'pretool-scope-gate' .claude/settings.json && echo "✅ settings: pretool-scope-gate" || echo "❌ missing"
grep -q 'permission-frequency-tracker' .claude/settings.json && echo "✅ settings: permission-frequency-tracker" || echo "❌ missing"
echo ""

echo "--- 文档整合 ---"
grep -q '权威源声明' .claude/reference/structured-execution-protocol.md && echo "✅ 五阶段权威源声明" || echo "❌ missing"
echo ""

echo "=== 全部验证完成 ==="
