# Plan: Dashboard Alert List

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: 列表渲染 + 骨架屏 + 分页

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/dashboard/list/alert-list.tsx`, `src/dashboard/list/alert-list.hooks.ts`, `src/dashboard/list/pagination.ts`, `src/dashboard/list/skeleton.tsx` |
| 预估行数 | ~140 行 |
| 回滚方案 | `git checkout -- src/dashboard/list/` |

**验收标准：**
- [ ] 100 条告警 < 2 秒加载 (P95)
- [ ] cursor-based 分页正常
- [ ] 骨架屏 loading 态 (8 行 Skeleton)
- [ ] 空态: 插画 + "暂无告警, 创建第一个?" → 跳转创建
- [ ] 错误态: 错误消息 + 重试按钮
- [ ] AbortController 10s 超时保护
- [ ] WCAG: role="list"/"listitem", aria-busy, aria-live="polite"

**边界/错误：**
- user_id 为空 → 不发起请求 (防御)
- API 返回空数组 → 空态 (非 loading 循环)
- 401 → 重定向登录 (不修改列表)
- 网络断连 → 断连提示条 + 静默保留上次数据
- 分页 overflow → last cursor 不重复请求

### Task 2: SSE 事件订阅 + 实时更新

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/dashboard/list/event-subscriber.ts`, `src/dashboard/list/event-handlers.ts`, `src/dashboard/list/throttle.ts` |
| 预估行数 | ~100 行 |
| 回滚方案 | `git checkout -- src/dashboard/list/event-subscriber.ts` |

**验收标准：**
- [ ] SSE /api/events?user_id= 连接成功
- [ ] AlertTriggered → 列表高亮 (3s 消退) + badge +1
- [ ] AlertStateChanged → 状态 badge 更新
- [ ] DeliveryConfirmed → ✅ badge; DeliveryFailed → 异常条
- [ ] 300ms 行情节流 (同一 alert_id 覆盖合并)
- [ ] 重连: 1s→2s→4s→8s→max 30s (kernel.md §修复 3 轮上限)
- [ ] 全部重连失败 → polling 降级 (5s)

**边界/错误：**
- SSE 连接初始化失败 → 立即 polling 降级
- event.data 格式非法 → LOG_WARNING + 跳过 (不崩溃, claude-next.md: `unknown`)
- alert_id 在当前页不存在 → 仅更新计数 badge, 不操作 DOM
- 重连中 → 显示 "重连中..." 指示条 (非阻断)
- 4 次重连失败 → 降级 polling + 日志告警

### Task 3: 批量操作 + 二次确认 + Undo

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/dashboard/list/batch-ops.tsx`, `src/dashboard/list/batch-select.ts`, `src/dashboard/list/undo-toast.tsx` |
| 预估行数 | ~80 行 |
| 回滚方案 | `git checkout -- src/dashboard/list/batch-ops.tsx` |

**验收标准：**
- [ ] 全选/多选 (checkbox + Shift+Click 范围选)
- [ ] 批量暂停/删除 → 二次确认弹窗
- [ ] Optimistic update: 先更新 UI → 后台执行 → 失败回滚
- [ ] Undo Toast: 5s 内可撤销 (确保幂等)
- [ ] WCAG: aria-checked, role="checkbox", Ctrl+A 全选

**边界/错误：**
- 选中 0 条 → 批量按钮 disabled
- 批量操作中选中项变更 → 以点击确认时的 selection 为准
- Optimistic rollback → Toast "操作失败, 已还原"
- undo 窗口过期 → Toast "操作已生效, 无法撤销"
- 批量删除 undo → 重新创建告警 (恢复至 active 态)

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | 事件 handler + throttle | Jest | 300ms 合并正确, 4 种事件 |
| 组件 | 列表渲染 + 骨架屏 + 三态 | Jest + RTL | loading/empty/error UI |
| 组件 | 批量操作 + undo | Jest + RTL | 确认弹窗 + undo 5s |
| 集成 | SSE 事件订阅 (mock EventSource) | Jest | 4 种事件 + 重连 + 降级 |
| 集成 | 批量操作 Optimistic update | Jest + MSW | 成功/失败/rollback |
| 性能 | 虚拟滚动 + 100 条渲染 | RTL + perf | < 2s |
| 无障碍 | WCAG 2.1 AA | axe-core | 无违规 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/dashboard/list/alert-list.tsx` | 新增 | 列表主组件 |
| `src/dashboard/list/alert-list.hooks.ts` | 新增 | 数据 Hook (abort, retry) |
| `src/dashboard/list/pagination.ts` | 新增 | cursor-based 分页 |
| `src/dashboard/list/skeleton.tsx` | 新增 | 骨架屏组件 |
| `src/dashboard/list/event-subscriber.ts` | 新增 | SSE 订阅 + 重连 |
| `src/dashboard/list/event-handlers.ts` | 新增 | 4 种事件 handler |
| `src/dashboard/list/throttle.ts` | 新增 | 300ms 节流 |
| `src/dashboard/list/batch-ops.tsx` | 新增 | 批量操作组件 |
| `src/dashboard/list/batch-select.ts` | 新增 | 全选/Shift+Click |
| `src/dashboard/list/undo-toast.tsx` | 新增 | Undo Toast (5s) |

---

## 非范围

- 不实现创建向导（由 Alert Creator 负责）
- 不实现移动端适配（由 Dashboard Mobile 负责）
- 不实现历史时间线（由 Alert History 负责）
- 不实现 WebSocket (v2)
