# Research: Dashboard Alert List

> 基于 `prd/dashboard/feat-dashboard-list/prd.md` · 2026-05-09
> Feature 职责：告警列表渲染、实时状态更新 (SSE)、批量操作、三态覆盖

---

## 关键调用链路

```
仪表盘加载
  └─→ listAlerts(user_id, status?, page, limit) → GET /api/alerts
        ├─→ 骨架屏渲染 (SkeletonPlaceholder × N 行)
        ├─→ 请求超时保护 (AbortController, timeout 10s)
        ├─→ 成功 → 渲染告警列表 (分页 + 筛选 + 排序)
        │     └─→ 虚拟列表 (react-window) 支持 500+ 条
        ├─→ 401 → 重定向登录
        ├─→ 5xx → 错误态: 重试按钮 + 错误消息
        └─→ 网络断连 → 断连提示条 + 自动重连 (exponential backoff)

入站事件 — 实时更新 (SSE)
  ├─→ SSE 连接: EventSource /api/events?user_id={user_id}
  │     └─→ 重连策略: 1s → 2s → 4s → 8s → max 30s (kernel.md §修复上限)
  │           └─→ 全部失败 → 降级 polling (5s 间隔)
  │
  ├─→ AlertTriggered (event: alert_id, symbol, price, condition_type, user_id, channels)
  │     └─→ 列表高亮 (3s 后消退) + 统计 badge +1
  │     └─→ 行情节流: 300ms 窗口内多事件合并为一次渲染
  │
  ├─→ AlertStateChanged (event: alert_id, user_id, old_status, new_status)
  │     └─→ 更新对应行状态 badge (active/paused/triggered/expired)
  │
  ├─→ DeliveryConfirmed (event: delivery_id, alert_id, channel, timestamp)
  │     └─→ 更新投递状态 badge → ✅ 已送达
  │
  └─→ DeliveryFailed (event: delivery_id, alert_id, channel, error, retry_count)
        └─→ 显示投递异常提示条 (channel + error) + 手动重试按钮

批量操作
  └─→ 全选 / 多选 (checkbox, Shift+Click 范围选)
        └─→ 批量暂停 POST /api/alerts/batch/pause  {alert_ids: [...]}
        └─→ 批量删除 POST /api/alerts/batch/delete {alert_ids: [...]}
        └─→ 二次确认弹窗:
              ├─→ "确定对 N 条告警执行暂停操作?"
              ├─→ 确认 → 执行 → Optimistic update → 失败回滚
              └─→ undo 窗口 (5s): Toast "已暂停 N 条告警" + [撤销]

空态/错误态/loading 态
  ├─→ loading: 骨架屏 (Skeleton, 8 行)
  ├─→ empty: 空态插画 + "暂无告警, 创建第一个?" → 跳转创建
  └─→ error: 错误插画 + 错误消息 + "重试" 按钮
        └─→ 静默错误: 事件消费失败 → Toast "部分更新失败" (不阻塞列表)
```

## 事件订阅方案

| 方案 | 优点 | 缺点 | 优先级 |
|------|------|------|--------|
| SSE (EventSource) | 轻量, 原生支持, 自动重连 | 单向, 仅 text | P0 (首选) |
| WebSocket | 双向, 低延迟 | 重连需手动实现 | P1 (v2) |
| Polling (5s) | 兼容性好, 简单 | 延迟高, 请求浪费 | 降级 |

v1 首选 SSE, WebSocket 不可用时降级 polling (5s)。

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 加载时间 | < 2 秒 (100 条, P95) | prd.md §非功能要求 |
| API 响应 | < 500ms (P95) | prd.md §非功能要求 |
| WCAG 2.1 AA | 全部 | prd.md §非功能要求 |
| 响应式 | 320px-2560px | prd.md §非功能要求 |
| 事件节流 | 300ms 窗口合并 | prd.md §性能 |
| 键盘导航 | Tab / Shift+Tab / Enter / Space / Escape | prd.md §非功能要求 |
| 虚拟滚动 | 500+ 条流畅 | prd.md §性能 |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | 事件订阅方式？ | SSE v1, WebSocket v2, polling 降级 |
| Q2 | 批量操作确认？ | 二次确认弹窗 + undo 5s Toast |
| Q3 | 分页方式？ | cursor-based (偏移量性能问题 → 游标) |
| Q4 | 行情节流粒度？ | 300ms 窗口, 同一 alert_id 覆盖更新 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 事件风暴 → UI 卡顿 | 🟡 P1 | 大量告警同时触发 | 300ms 节流 + 批量合并渲染 |
| SSE 断连 → 数据滞后 | 🟡 P2 | 实时更新中断 | exponential backoff 重连 + polling 兜底 |
| 列表溢出 → 滚动卡顿 | 🟢 P3 | >500 条告警 | 虚拟滚动 (react-window) |
| API 超时 → 白屏 | 🟡 P1 | 首次请求慢 | 骨架屏 + AbortController 10s |
| WebSocket → SSE 降级抖动 | 🟢 P3 | 频繁切换 | 稳定态保持, 不来回切 |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | API 响应类型 `ListAlertsResponse` 从 Alert Engine 契约导入 |
| 范围冻结 | 创建向导/历史属于其他 feature, 只渲染列表 |
| 证据门禁 | "加载 < 2s" 必须 VERIFIED: 100 条 mock 数据计时 |
| 断言真实 | 性能指标有测试证据, 不自称达标 (R27) |

### kernel.md §反模式映射
- B1 (过度工程): 列表不抽象通用 DataTable 组件, 直接实现
- C2 (类型连锁): SSE 事件 payload 变更需同步所有 handler (claude-next.md: typescript seed)
- E1 (暴力搜索): 事件 handler 注册用 `switch` 而非动态反射

### 反模式防范 (claude-next.md)
- [seed:typescript] any 禁止: SSE event.data parse 用 `unknown` + 类型守卫
- [seed:typescript] useEffect 依赖数组: SSE 连接 deps = [user_id]
- R24: 构建脚本 `for x in $SRC_FILES` → `set -f`
- R29: context-guard matcher Edit|Write, 不阻断 Read/Bash 诊断

## 实现路径建议

1. **Phase 1**: 列表渲染 + 骨架屏 + 分页 + 排序筛选
2. **Phase 2**: SSE 事件订阅 + 实时更新 + 节流 (300ms)
3. **Phase 3**: 批量操作 + 二次确认 + undo 5s + Optimistic update
4. **Phase 4**: 虚拟滚动 (react-window, 500+ 条) + 空态/错误态
5. **Phase 5**: SSE 重连 exponential backoff + polling 降级
