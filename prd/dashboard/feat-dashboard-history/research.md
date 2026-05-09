# Research: Dashboard Alert History

> 基于 `prd/dashboard/feat-dashboard-history/prd.md` · 2026-05-09
> Feature 职责：近 30 天告警触发历史时间线、轮询刷新、触发详情展开

---

## 关键调用链路

```
用户打开历史页面
  └─→ renderAlertHistory(user_id, date_range)
        ├─→ AbortController timeout 10s
        ├─→ GET /api/alerts/history?user_id={user_id}&from={from}&to={to}&cursor={cursor}&limit={limit}
        │     └─→ 骨架屏 (Skeleton, 6 行, aria-busy=true)
        ├─→ 成功 → 渲染历史时间线 (分页 + 日期筛选)
        │     └─→ 时间倒序, 卡片式布局
        │           └─→ 每项: symbol, price, condition_type, triggered_at, status, channels
        │                 └─→ 单击 → 展开详情 (详看下方 TriggerDetail)
        ├─→ 400 (date_range > 365d) → 提示 "最多查询近 365 天"
        ├─→ 5xx → 错误态: 重试按钮
        └─→ network error → 离线提示条 + 保留上次数据

日期范围选择
  ├─→ 快捷选项: 7 天 (默认) / 14 天 / 30 天
  ├─→ 自定义: 日期选择器 (不能 > 365 天)
  └─→ 切换 → 重新请求 → 骨架屏 → 渲染

轮询刷新 (被动更新)
  ├─→ 页面激活: 30s 定时轮询 → 合并去重 (按 alert_id + triggered_at 去重)
  ├─→ 页面非活跃 (visibilitychange): 暂停轮询
  └─→ App 从后台恢复: 立即执行一次全量刷新
        └─→ onResume: 30s 内不重复触发

触发详情展开 (TriggerDetail)
  └─→ 单击历史条目 → 展开详情卡片:
        ├─→ alert_id
        ├─→ symbol + price (触发价格)
        ├─→ condition_type (如 price_above 70000)
        ├─→ channels 投递状态 (每个通道的 delivery_status)
        ├─→ triggered_at (ISO8601, 本地时区显示)
        └─→ 再次单击 / Escape → 收起

数据流:
  用户交互 → 日期选择
    → GET /api/alerts/history (cursor, limit)
      → return { triggers: TriggerEvent[], next_cursor, total }
        → 本地排序 (triggered_at DESC)
          → 渲染时间线

  轮询刷新:
    → 30s 定时 GET /api/alerts/history (last_checked→now)
      → 新数据插入列表顶部
        → 去重: 已存在的 alert_id + triggered_at 跳过
```

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| API 响应 | < 500ms (P95) | prd.md §非功能要求 |
| WCAG 2.1 AA | 全部 | prd.md §非功能要求 |
| 数据范围 | 近 30 天 (快捷: 7/14/30, 自定义 ≤ 365 天) | prd.md §功能边界 |
| 轮询间隔 | 页面激活 30s, 非活跃暂停 | prd.md §性能 |
| 虚拟滚动 | 1000+ 条流畅 | prd.md §性能 |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | 历史数据需要实时更新？ | 轮询 30s (页面激活), 非活跃暂停 |
| Q2 | 默认日期范围？ | 近 7 天, 提供 7/14/30 快捷选项 |
| Q3 | 触发详情展示格式？ | 卡片式展开, 单击切换 |
| Q4 | 日期范围上限？ | 365 天, API 层限制 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 大范围查询慢 | 🟡 P2 | 365 天 + 高频用户 → 大量数据 | cursor 分页 + 服务端 LIMIT |
| 轮询与用户操作冲突 | 🟢 P3 | 轮询刷新覆盖用户筛选 | 去抖 300ms, 加载中禁用筛选 |
| 列表 overflow | 🟢 P3 | 虚拟滚动 1000+ 条 | react-window + 固定行高 |
| 时区显示错误 | 🟢 P3 | triggered_at UTC → 本地时区 | Intl.DateTimeFormat 本地化 |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | 日期范围校验引用 API 契约 (getAlertHistory maxDays=365) |
| 证据门禁 | "加载 < 500ms" 必须 VERIFIED: 实际计时数据 |
| 范围冻结 | 创建/编辑/列表属于其他 feature |

### kernel.md §反模式映射
- B2 (上下文漂移): 历史页面不做告警管理功能
- D3 (业务盲区): 30 天保留期参照 Alert Engine 契约, 不自定

### 反模式防范 (claude-next.md)
- [seed:typescript] API 响应完整类型: `TriggerHistoryResponse = { triggers: TriggerEvent[], next_cursor, total }`
- [seed:typescript] useEffect 依赖数组完整: 轮询 deps = [date_range, isActive], 不含闭包变量
- R27: 性能指标不自称达标, 必须引用计时证据
- R33: 30s 轮询不是实时, 标注 "非实时, 有 30s 延迟"

## 实现路径建议

1. **Phase 1**: 历史时间线列表 + 日期范围选择 (7/14/30 快捷 + 自定义 ≤365d)
2. **Phase 2**: cursor 分页 + 虚拟滚动 (1000+ 条)
3. **Phase 3**: 触发详情展开 (单击/ESC 收起, aria-expanded)
4. **Phase 4**: 轮询刷新 (30s 激活, visibilitychange 暂停, onResume 全量)
5. **Phase 5**: WCAG 2.1 AA 审计 + 键盘导航 + 屏幕阅读器
