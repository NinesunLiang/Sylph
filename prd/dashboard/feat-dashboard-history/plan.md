# Plan: Dashboard Alert History

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: 时间线渲染 + 日期筛选

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/dashboard/history/alert-history.tsx`, `src/dashboard/history/date-range-picker.tsx`, `src/dashboard/history/history-list.tsx`, `src/dashboard/history/history-skeleton.tsx` |
| 预估行数 | ~120 行 |
| 回滚方案 | `git checkout -- src/dashboard/history/` |

**验收标准：**
- [ ] 默认近 7 天, 快捷 7/14/30 天, 自定义 ≤ 365 天
- [ ] 时间倒序渲染, 每项: symbol, price, condition_type, triggered_at, status, channels
- [ ] 骨架屏 (6 行, aria-busy)
- [ ] 空态: "暂无触发历史"
- [ ] 错误态: 错误消息 + 重试按钮
- [ ] 日期切换 → 重新请求 → 骨架屏 → 渲染
- [ ] WCAG: role="list"/"listitem", aria-label 日期范围

**边界/错误：**
- date_range > 365 天 → 400 提示 + 阻断请求
- 日期范围跨度为 0 → 返回空 (同天无触发)
- to > now → 截断至当前时间
- to < from → 交换 (宽容处理)
- API 超时 → 骨架屏保留 + 错误态重试

### Task 2: 分页 + 虚拟滚动

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/dashboard/history/history-pagination.ts`, `src/dashboard/history/virtual-scroll.tsx` |
| 预估行数 | ~70 行 |
| 回滚方案 | `git checkout -- src/dashboard/history/virtual-scroll.tsx` |

**验收标准：**
- [ ] cursor-based 分页 (next_cursor 驱动)
- [ ] 虚拟滚动: react-window, 固定行高, 1000+ 条 60fps
- [ ] 加载更多: 滚动到底自动触发 → 骨架条加载提示
- [ ] API < 500ms (P95) — 引用测试证据

**边界/错误：**
- API 返回 next_cursor null → 无更多数据
- 快速滚动 → 跳过中间批请求, 只取最终可见范围
- 虚拟滚动容器 resize → 重新计算 visible range
- 加载更多失败 → 错误条 "加载失败, 点击重试"

### Task 3: 触发详情展开 + 轮询刷新

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/dashboard/history/trigger-detail.tsx`, `src/dashboard/history/polling.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/dashboard/history/trigger-detail.tsx` |

**验收标准：**
- [ ] 单击展开详情 (symbol, price, condition, channels, delivery_status, triggered_at)
- [ ] 再次单击/Escape → 收起 (aria-expanded 切换)
- [ ] 30s 轮询 (页面激活)
- [ ] visibilitychange → 暂停/恢复轮询
- [ ] onResume → 立即全量刷新 (kernel.md §最小影响)
- [ ] 去重: 按 alert_id + triggered_at 双重索引

**边界/错误：**
- 详情展开时轮询刷新数据 → 保留展开状态, 仅更新内容
- 轮询请求失败 → 静默, 下次继续 (不重复弹错)
- 轮询返回空 → 不操作 (无新触发)
- 页面从后台恢复 → 30s 内不重复全量刷新 (debounce)

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | 日期校验 + 范围逻辑 | Jest | ≤365d, 跨度为0, 截断 |
| 组件 | 时间线列表 + 三态 | Jest + RTL | loading/empty/error |
| 组件 | 触发详情展开收起 | Jest + RTL | aria-expanded, keyboard |
| 集成 | 分页 + 虚拟滚动 (mock API) | Jest + MSW | cursor 驱动, auto load |
| 集成 | 轮询 + visibilitychange | Jest (mock timers) | 30s 精确, paused/resume |
| 性能 | 1000 条虚拟滚动 | RTL + perf | 60fps |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/dashboard/history/alert-history.tsx` | 新增 | 历史页主组件 |
| `src/dashboard/history/date-range-picker.tsx` | 新增 | 日期选择器 (7/14/30/自定义) |
| `src/dashboard/history/history-list.tsx` | 新增 | 时间线列表 |
| `src/dashboard/history/history-skeleton.tsx` | 新增 | 骨架屏 |
| `src/dashboard/history/history-pagination.ts` | 新增 | cursor 分页 |
| `src/dashboard/history/virtual-scroll.tsx` | 新增 | 虚拟滚动 (react-window) |
| `src/dashboard/history/trigger-detail.tsx` | 新增 | 触发详情展开 |
| `src/dashboard/history/polling.ts` | 新增 | 30s 轮询 + visibility |

---

## 非范围

- 不实现历史数据持久化（由 Alert Engine 负责）
- 不实现告警创建入口（由 Alert Creator 负责）
- 不实现移动端适配（由 Dashboard Mobile 负责）
- 不实现告警列表实时更新（由 Alert List 负责）
