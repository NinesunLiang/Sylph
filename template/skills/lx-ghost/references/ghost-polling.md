# Ghost 全自动轮询

> 间隔默认 600s，最小 30s，不可为 0。

## 每轮 Poll 流程

```
1. 读 lx-ghost.json 确认方向
2. iterations_completed++
3. 方向漂移自检 → 偏离则修正，完全漂移则停用
4. 每轮只做一步 — 不并行 agent，不做大规模分析
5. 危险 → 走裁决链；歧义 → 自主判断
6. 更新状态
```

## 方向漂移自检

每轮 poll 开始前检查当前工作是否偏离原始方向。轻微偏离 → 记录 + 修正方向。完全漂移（方向已无交集）→ 触发自动退出。

## min_iterations 强制探索

> 解决「一次性做完就停」的过早收敛。

```
有工作 → 执行一步
无工作 + iterations < min_iterations:
  → 拓宽探索半径 — 扫描 side findings / 边缘问题 / Oracle minor 项 / 相邻文件调用方
  → 仍无 → skip-risk 记录"方向枯竭，强制拓宽"，继续
无工作 + iterations >= min_iterations:
  → 自检: 方向目标是否达成？
  → 是 → 自动退出 + 退出报告
  → 否 → 报告差距，可延长
```

## 风险与退出

- 方向漂移 → skip-risk 记录，修正方向
- 修复阻塞（3 次）→ skip-risk，换方向继续
- Context Guard 阻断 → override + Bash
- Permission Gate 拦截 → 走三级裁决链
- 发现范围外问题 → 记入附带发现
- 令牌过高 → 增加间隔或提前关闭
- 硬边界触发 → 立即跳过 → hard-boundary-hit → 继续其他
