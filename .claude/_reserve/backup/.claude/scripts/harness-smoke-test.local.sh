#!/usr/bin/env bash
# harness-smoke-test.local.sh — 用户自定义冒烟测试用例
#
# 本文件在 harness-smoke-test.sh 末尾被自动 source，安装升级时保留不会覆盖。
# TOTAL 和 FAILED 变量继承自父脚本，直接追加测试用例即可。
#
# 使用方式：
#   1. 在此文件添加测试用例（参考下方示例）
#   2. 运行 bash .claude/scripts/harness-smoke-test.sh
#   3. summary 行会自动包含本文件的测试结果
#
# 命名约定：
#   测试用例编号建议使用 U- 前缀（User-defined），避免与官方 R-/DG-/US- 冲突
#   例如：U-001, U-002, ...

# ── 示例测试用例（取消注释即可使用）──
# TOTAL=$((TOTAL + 1))
# if [ -f ".claude/hooks/context-guard.sh" ]; then
#     log "  🟢 PASS: U-001 context-guard hook exists"
# else
#     log "  🔴 FAIL: U-001 context-guard hook missing"
#     FAILED=$((FAILED + 1))
# fi
