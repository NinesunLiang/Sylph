# Phase 4-5: 根因消除 + 免疫防护

## Phase 4: 根因消除

加载 `@../../nodes/auto_fixer.md`，传入 `finding[]` + 修复策略。

**入口检查**：CP-3 检查点 → Phase 3 根因 = Phase 4 修复目标。不一致 → 暂停。

在根因级或系统级修复，绝不修复症状。

加载反模式：`references/anti-patterns.md` | 修复循环：`references/repair-loop-rules.md` | 危险信号：`references/checklists/danger-signals.md`

**完成标准**：
- ✅ 修复轮次 [N]/3（超过 3 次 → Oracle 升级）
- ✅ 修复层级：根因级或系统级
- ✅ 修复内容含 file:line 引用
- ✅ 验证命令已执行 + 原始输出 + 退出码
- ✅ 跨阶段一致性：Phase 3 根因 = Phase 4 修复目标
- ❌ 任何反模式触发 → 拒绝修复

## Phase 5: 免疫防护 + 验证

三重强制防护：

### 1. 测试防护
根因触发场景的自动化测试，含 `-race`

### 2. 验证防护
- Interface 约束：`var _ InterfaceName = (*ConcreteType)(nil)`
- 运行时守卫：`context.WithTimeout`、输入校验

### 3. 监控防护
- goroutine 泄漏：`runtime.NumGoroutine()` 定期检查
- 性能回归：`go test -bench` 修复前后对比

**自动化验证**（强制执行）：
```
IDENTIFY → RUN → READ → VERIFY → CLAIM
```

完成标准：所有防护缺一不可。

## Phase 5.5: 经验沉淀

RCA 通过后自动反哺 claude-next.md：
1. 读 claude-next.md → 按根因模式 + 影响包去重
2. 同类模式已有 ≥3 条 → 跳过
3. 仅记录复现性 bug，一次性不记录

模板 → `references/rca-feedback-template.md`
