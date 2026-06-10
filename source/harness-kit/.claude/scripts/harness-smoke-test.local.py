#!/usr/bin/env python3
"""harness-smoke-test.local.py — 用户自定义冒烟测试用例

本文件在 harness-smoke-test.py 末尾被自动导入，安装升级时保留不会覆盖。
TOTAL 和 FAILED 变量在父脚本的作用域中，直接追加测试用例即可。

使用方式：
  1. 在此文件添加测试用例（参考下方示例）
  2. 运行 python3 .claude/scripts/harness-smoke-test.py
  3. summary 行会自动包含本文件的测试结果

命名约定：
  测试用例编号建议使用 U- 前缀（User-defined），避免与官方 R-/DG-/US- 冲突
  例如：U-001, U-002, ...
"""

# 示例测试用例（取消注释即可使用）
# TOTAL += 1
# if Path(".claude/hooks/context-guard.py").is_file():
#     log("  🟢 PASS: U-001 context-guard hook exists")
# else:
#     log("  🔴 FAIL: U-001 context-guard hook missing")
#     FAILED += 1
