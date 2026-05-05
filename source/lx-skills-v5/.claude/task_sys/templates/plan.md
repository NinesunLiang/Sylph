# plan.md 模板

```
mark
down# Plan: {task_name}
## 背景/目标
- target: ...
## Role（已确认/待确认）
- ...
## 验收标准（AC）
- AC1: ...（check: ... expected: ...）
- AC2: ...
## Steps
- [ ] 1. Research（文件/接口定位）→ 验收：列出关键 file:line 证据 → 回退：无
- [ ] 2. Design（方案与影响范围）→ 验收：得到用户确认 → 回退：撤销方案变更
- [ ] 3. Implement（最小改动）→ 验收：build/test 命令通过 → 回退：git restore ...
- [ ] 4. Verify（按 AC 逐条验证）→ 验收：验收报告 → 回退：回到 Implement
## 影响范围（预估文件清单）
- ...
## 风险与降级
- ...
## Checklist（执行中追加证据）
- [ ] 每步证据已记录（file:line / 命令输出）
```
