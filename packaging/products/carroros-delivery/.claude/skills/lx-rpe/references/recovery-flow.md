# 恢复流程（默认行为）

```
0. 若 ARG 含 /（如 prd/payment/checkout）→ BASE_DIR = ARG/，跳到 3
1. 搜索实例目录：ls rpe/ prd/*/
2. 多实例→列出选择；指定名称→BASE_DIR = rpe/{name}/；唯一→自动加载
3. readFile {BASE_DIR}state/progress.md → 提取当前阶段/步骤/任务/阻塞
4. 上下文校验：
   Phase 2+ 但 research 空→回退 P1
   Phase 3 但 plan 空→回退 P2
   主循环无任务→回退 P3 入口
5. 恢复入口：Phase 1/2/3 或主循环步骤或 Gate-X 暂停
6. 输出恢复摘要（当前阶段 + 任务 + 上次下一步 + 阻塞）
7. → 进入对应阶段/步骤
```
