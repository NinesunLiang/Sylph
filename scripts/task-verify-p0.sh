#!/usr/bin/env bash
# P0 修改验证脚本
set -euo pipefail

echo "=== P0 机制化改进 — 执行后验证 ==="
echo ""

# Phase 1: harness.yaml
echo "--- Phase 1: harness.yaml ---"
grep -q 'approved_ops_ttl: 1800' .claude/harness.yaml && echo "✅ approved_ops_ttl: 1800" || echo "❌ missing"
grep -q 'c1_whitelist: ""' .claude/harness.yaml && echo "✅ c1_whitelist: \"\"" || echo "❌ missing"
grep -q 'auto_execute: true' .claude/harness.yaml && echo "✅ auto_execute: true" || echo "❌ missing"
grep -q 'auto_kernel_draft: true' .claude/harness.yaml && echo "✅ auto_kernel_draft: true" || echo "❌ missing"
echo ""

# Phase 2: 独立修改
echo "--- Phase 2: 独立修改 ---"
grep -q 'mode_skip_' .claude/hooks/pretool-sensitive-file-guard.sh && echo "✅ sensitive-file-guard: mode degradation" || echo "❌ missing"
grep -q 'oracle-gate-required' .claude/hooks/pretool-sensitive-file-guard.sh && echo "✅ sensitive-file-guard: oracle-gate patterns" || echo "❌ missing"
grep -q '_get_mtime' .claude/hooks/auto-snapshot.sh && echo "✅ auto-snapshot: _get_mtime function" || echo "❌ missing"
grep -q 'stat -c "%Y"' .claude/hooks/ecosystem-probe.sh && echo "✅ ecosystem-probe: stat cross-platform" || echo "❌ missing"
grep -q 'GNU' scripts/package-release.sh && echo "✅ package-release: sed cross-platform" || echo "❌ missing"
grep -q 'auto_execute' .claude/hooks/knowledge-condenser.sh && echo "✅ knowledge-condenser: auto_execute config" || echo "❌ missing"
grep -q 'sublimation-log' .claude/hooks/knowledge-condenser.sh && echo "✅ knowledge-condenser: sublimation audit log" || echo "❌ missing"
grep -q 'kernel_draft_created' .claude/hooks/pretool-user-correction.sh && echo "✅ user-correction: kernel draft" || echo "❌ missing"
echo ""

# Phase 3: 依赖修改
echo "--- Phase 3: 依赖修改 ---"
grep -q 'CAPTCHA_PAIRS' .claude/hooks/pretool-approve-detect.sh && echo "✅ approve-detect: CAPTCHA_PAIRS array" || echo "❌ missing"
grep -q 'oracle-gate-approved' .claude/hooks/pretool-approve-detect.sh && echo "✅ approve-detect: oracle-gate support" || echo "❌ missing"
grep -q '_c1_block' .claude/hooks/permission-gate.sh && echo "✅ permission-gate: _c1_block function" || echo "❌ missing"
grep -q 'mode_skip_' .claude/hooks/permission-gate.sh && echo "✅ permission-gate: mode_skip_ event" || echo "❌ missing"
grep -q 'approved_ops_ttl' .claude/hooks/permission-gate.sh && echo "✅ permission-gate: configurable TTL" || echo "❌ missing"
grep -q 'oracle-gate-approved' .claude/hooks/error-dna.sh && echo "✅ error-dna: oracle-gate CAPTCHA markers" || echo "❌ missing"
echo ""

echo "=== 全部验证完成 ==="
