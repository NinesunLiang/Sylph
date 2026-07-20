# CarrorOS 设计落地 — Plan

## Task 列表

### Task 1: Phase 0 — 修复致命断裂（生产阻塞）
- AC1.1: `context_engine.py` 创建，支持 compact-check/resume-check/state-injection
- AC1.2: `userprompt-session-start.py` 新建（从 session-resume 迁移，去掉 stamp）
- AC1.3: `settings.json` 注册 SessionStart hook，UserPromptSubmit 移除 session-resume
- AC1.4: 验证：新会话启动不阻塞，context_engine 返回有效 JSON
- 测试策略：`echo '{"prompt":"test"}' | python3 .claude/hooks/userprompt-session-start.py`
- 回滚方案：git revert + 旧 settings.json 恢复

### Task 2: Phase 1 — VerifyGate 完成门
- AC2.1: `verify_gate.py` 创建（5.md spec：VERIFIED/WARN/BLOCKED/REJECTED）
- AC2.2: `pretool-verify-gate.py` 新建，注册到 PreToolUse
- AC2.3: `posttool-completion-gate.py` 保留在 Stop 做辅助检查
- AC2.4: 验证：写操作前检查当前 step 是否已验证
- 测试策略：mock 一个 executor.md 带 E3 evidence → verify_gate 返回 VERIFIED
- 回滚方案：settings.json 删除 pretool-verify-gate 注册

### Task 3: Phase 2 — Output Compression
- AC3.1: `output_compress.py` 创建，>2000 chars 头尾裁剪
- AC3.2: `posttool-output-compress.py` 注册到 PostToolUse
- AC3.3: 验证：2000+ chars 命令输出被正确截断
- 回滚方案：settings.json 删除该 hook

### Task 4: Phase 3 — Fallback 熔断
- AC4.1: `fallback_engine.py` 重写（8.md spec，15 failure types，4 裁决）
- AC4.2: `pretool-fallback-check.py` 重写（去掉 stamp，真检测）
- AC4.3: 验证：oracle_unavailable + medium risk → ASK_USER
- 回滚方案：git revert fallback 文件

### Task 5: Phase 4 — Context Engine 完整
- AC5.1: `context_engine.py` 补齐所有命令（已在 Task 1 创建）
- AC5.2: `context_watermark.py` 输出对齐 6.md
- AC5.3: 验证：L1 15 turn → COMPACT_SOON，L2 watermark 72 → COMPACT_SOON
- 回滚方案：git revert，但 context_engine 已在 Phase 0 存在

### Task 6: Phase 5 — Oracle/Meta-Oracle 接入
- AC6.1: `oracle_engine.py` 创建（7.md spec，L2 pass-curve 7 维度）
- AC6.2: `pretool-oracle-gate.py` 注册 PreToolUse（L2 only）
- AC6.3: 验证：模拟 L2 task → oracle 输出 ACCEPT/WARN/REJECT
- 回滚方案：settings.json 删除 oracle hook

### Task 7: Phase 6 — Archive Engine 完整
- AC7.1: `archive_engine.py` 验证对齐 10.md §11
- AC7.2: `posttool-archive-check.py` 注册 PostToolUse
- AC7.3: 验证：所有 step VERIFIED → ARCHIVED；缺 Oracle → BLOCKED
- 回滚方案：settings.json 删除 archive hook

### Task 8: Phase 7 — PreActionGate 完善
- AC8.1: `pre_action_gate.py` 按 3.md §11 补齐 9 action types
- AC8.2: `pretool-action-gate.py` 补齐裁决矩阵
- AC8.3: 验证：sensitive path → BLOCK，scope out write → ASK_USER
- 回滚方案：保留旧文件

### Task 9: Phase 8 — 强证据验证
- AC9.1: `feature_verify.py` 重写（每条检查项实际运行目标代码）
- AC9.2: `randomized_bench.py` 重写（不清理中间状态，测试真正 hook 链）
- AC9.3: `verify_tests.py` 新建（每个模块独立测试函数）
- AC9.4: 验证：运行 feature_verify.py 5 次，无 lambda True

## 影响范围

### 新建文件
| 文件 | 所属 Task | 来源 |
|------|-----------|------|
| `.claude/scripts/context_engine.py` | Task 1 | 6.md §13 完整代码 |
| `.claude/scripts/verify_gate.py` | Task 2 | 5.md §12 完整代码 |
| `.claude/scripts/output_compress.py` | Task 3 | 新写 |
| `.claude/scripts/oracle_engine.py` | Task 5 | 7.md §14 完整代码 |
| `.claude/scripts/verify_tests.py` | Task 8 | 新写 |
| `.claude/hooks/userprompt-session-start.py` | Task 1 | 从 session-resume 迁移 |
| `.claude/hooks/pretool-verify-gate.py` | Task 2 | 新写 |
| `.claude/hooks/posttool-output-compress.py` | Task 3 | 新写 |
| `.claude/hooks/pretool-oracle-gate.py` | Task 5 | 新写 |
| `.claude/hooks/posttool-archive-check.py` | Task 6 | 新写 |

### 修改文件
| 文件 | Task | 变更 |
|------|------|------|
| `.claude/settings.json` | Task 1 | SessionStart 注册 + UserPromptSubmit 修正 |
| `.claude/hooks/userprompt-session-resume.py` | Task 1 | 降级为辅助，不再被 settings.json 直接调用 |
| `.claude/hooks/posttool-completion-gate.py` | Task 2 | 保留 Stop 模式 + 补充 PreToolUse 兼容 |
| `.claude/hooks/pretool-fallback-check.py` | Task 4 | 重写去 stamp |
| `.claude/hooks/pretool-action-gate.py` | Task 7 | 补齐 9 action types |
| `.claude/scripts/fallback_engine.py` | Task 4 | 重写按 8.md spec |
| `.claude/scripts/pre_action_gate.py` | Task 7 | 对齐 3.md §11 |
| `.omc/scripts/feature_verify.py` | Task 8 | 重写 |
| `.omc/scripts/randomized_bench.py` | Task 8 | 重写 |

### 删除文件
无。新引擎走独立路径，旧文件在稳定后逐步拆除。

## AC 清单
- [x] Task 1: Phase 0 — 修复致命断裂
- [ ] Task 2: Phase 1 — VerifyGate 完成门
- [ ] Task 3: Phase 2 — Output Compression
- [ ] Task 4: Phase 3 — Fallback 熔断
- [ ] Task 5: Phase 4 — Context Engine 完整
- [ ] Task 6: Phase 5 — Oracle/Meta-Oracle
- [ ] Task 7: Phase 6 — Archive Engine
- [ ] Task 8: Phase 7 — PreActionGate 完善
- [ ] Task 9: Phase 8 — 强证据验证

## 测试策略
每个引擎文件创建后立即运行：
```bash
python3 -m py_compile .claude/scripts/<file>.py   # 语法检查
python3 .claude/scripts/<engine>.py --help         # 入口检查
```
每个 hook 创建后运行 mock 测试：
```bash
echo '{"tool_name": "Bash", "tool_input": {"command": "echo test"}}' | python3 .claude/hooks/<hook>.py
```

## 回滚方案
```bash
git checkout -- .claude/settings.json     # 恢复 hooks 注册
git revert HEAD                          # 回退最新提交
```

## 非范围
- OpenCode SQLite observer（已确认不启用）
- `.omc/scripts/carros_base.py` 旧文件删除（逐步替换，不在本 RPE 删除）
- Install.sh / 发布系统
- 跨平台兼容（macOS only）
