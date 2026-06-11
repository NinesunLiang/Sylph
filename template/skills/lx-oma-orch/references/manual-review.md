# 人工审核模板

每次 advance 后输出阶段转换报告：

```
=== 阶段转换 ===
从: {from} → 到: {to}
Gate: {og-id} → {approved/rejected}

[ ] 上游 gate 状态正确？
[ ] 子 skill 结果正确？
[ ] 无异常/漂移？

确认: /lx-oma-orch gate {og-id} approve
```
