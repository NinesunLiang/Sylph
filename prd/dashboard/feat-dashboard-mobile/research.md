# Research: Dashboard Mobile

> 基于 `prd/dashboard/feat-dashboard-mobile/prd.md` · 2026-05-09
> Feature 职责：React Native 移动端告警仪表盘、推送通知接收、App 内展示

---

## 关键调用链路

```
用户打开移动端 App
  └─→ React Native 仪表盘加载 (App.tsx)
        ├─→ 初始化: API 适配器 (api-adapter.ts, axios + retry)
        │     └─→ baseURL 从 env 读取, 超时 10s (kernel.md: 非硬编码)
        ├─→ 拉取告警列表: listAlerts(user_id) → GET /api/alerts
        │     ├─→ < 2 秒 100 条 (FlatList + 骨架屏)
        │     ├─→ 401 → 重定向登录
        │     └─→ 网络断连 → 离线提示 + 缓存数据 (AsyncStorage)
        └─→ 响应式布局: 320px-2560px (useWindowDimensions)

入站事件 — 实时更新 (SSE + 推送)
  ├─→ AppsFlyer 事件订阅 (SSE EventSource polyfill for RN)
  │     ├─→ AlertTriggered → App 内推送通知弹窗 + 列表高亮
  │     │     └─→ 前台: 顶部通知条 (auto-dismiss 5s)
  │     └─→ DeliveryFailed → 投递失败告警条 (手动消除)
  │
  └─→ FCM 推送 (App 后台/关闭)
        └─→ 点击推送通知 → 打开对应告警详情 (deep link: /alerts/{alert_id})

移动端页面结构:
  ├─→ 告警列表页: FlatList, 虚拟列表, 下拉刷新 (RefreshControl)
  ├─→ 告警创建页: WebView 承载 Web 版创建向导 (暂时)
  ├─→ 告警历史页: 同列表风格, 参数传递
  └─→ 设置页: 通知通道偏好 + 2FA 设置 (跳转 User Preferences)

状态同步:
  ├─→ 前台: SSE 实时更新 + 30s polling 兜底
  ├─→ 后台恢复 (onResume): 强制全量刷新
  │     └─→ 策略: AppState.addEventListener('change', state → active → refresh)
  ├─→ 离线: 缓存上次数据 (AsyncStorage, key: alerts_cache_{user_id})
  └─→ 本地持久化: AsyncStorage (告警列表缓存, 草稿, 用户偏好)

推送通知处理:
  └─→ Firebase Messaging onMessage/onNotificationOpenedApp
        ├─→ 前台: 不显示 OS 通知, 仅 App 内 Toast
        └─→ 后台: 显示 OS 通知, 点击 → deep link /alerts/{alert_id}
```

## 平台差异

| 特性 | iOS | Android | 处理 |
|------|-----|---------|------|
| 推送 | APNs via FCM | FCM 直连 | Firebase SDK 统一 |
| 后台任务 | BGTaskScheduler | WorkManager | v1 不实现 |
| 本地存储 | AsyncStorage | AsyncStorage | 统一 |
| 深链接 | Universal Link | App Link | 统一 schema: carroros:// |
| 响应式 | safe-area-inset | statusBarHeight | react-native-safe-area-context |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 加载时间 | < 2 秒 (100 条) | prd.md §非功能要求 |
| 响应式 | 320px - 2560px | prd.md §非功能要求 |
| WCAG 2.1 AA | 全部 | prd.md §非功能要求 |
| 推送通知 | AlertTriggered + DeliveryFailed | prd.md §功能边界 |
| 离线缓存 | v1 不强制, v2 规划 | prd.md §功能边界 |
| 触摸交互 | Tap/Swipe/Pull-to-refresh | prd.md §非功能要求 |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | 移动端复用 Web API？ | 是, 复用 Alert Engine API, 仅 UI 独立 |
| Q2 | 离线模式支持？ | v1 不强制 (仅缓存), v2 完整离线 |
| Q3 | 推送通知点击行为？ | deep link: /alerts/{alert_id} |
| Q4 | 创建向导复杂 → 移动端方案？ | v1 WebView 嵌入 Web 版, v2 原生重写 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 推送通知延迟 | 🟡 P2 | FCM 延迟不确定 | 列表 30s polling 兜底 |
| 低端设备性能 | 🟡 P2 | 低 RAM 设备列表卡顿 | FlatList + 虚拟列表 + 懒加载图片 |
| 状态同步滞后 | 🟢 P3 | App 后台恢复 → 数据过时 | onResume 强制全量刷新 |
| SSE RN 兼容性 | 🟡 P2 | EventSource 原生不支持 | polyfill + polling 降级 |
| 推送权限被拒 | 🟢 P3 | 用户拒绝通知权限 | 静默降级, 不弹权限引导 |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | API baseURL 从 env 读取, 非硬编码 |
| 证据门禁 | "加载 < 2s" VERIFIED: 低端设备数据集 |
| 隐私防线 | FCM token 不写日志, 不传第三方 |

### kernel.md §错误处理铁律
- Hook 永不阻塞: 推送 handle 不允许 crash (try/catch 兜底)
- Error DNA: 推送接收失败记录至 error-dna.jsonl
- 严禁硬编码: baseURL, FCM senderID 从 env 读取

### 反模式防范 (claude-next.md)
- R24: 构建脚本 `for x in $FILES` → `set -f`
- R31: gh release upload 推送 IPA/APK 需 permission-gate
- [seed:typescript] any 禁止: FCM remoteMessage.data 类型守卫
- [seed:typescript] API 响应类型复用 Web 版契约 (claude-next.md: typescript seed)

## 实现路径建议

1. **Phase 1**: RN 项目初始化 + 告警列表页 (FlatList + 骨架屏 + pull-to-refresh)
2. **Phase 2**: 创建/编辑/历史页面适配 + 响应式布局 (safe-area + dimensions)
3. **Phase 3**: SSE EventSource polyfill + App 内推送通知 (onMessage)
4. **Phase 4**: FCM 推送接收 + deep link (/alerts/{alert_id})
5. **Phase 5**: 离线缓存 (AsyncStorage) + onResume 同步 + WCAG 审计
