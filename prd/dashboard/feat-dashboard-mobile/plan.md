# Plan: Dashboard Mobile

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: RN 项目初始化 + 告警列表页

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/dashboard/mobile/App.tsx`, `src/dashboard/mobile/alert-list.tsx`, `src/dashboard/mobile/api-adapter.ts`, `src/dashboard/mobile/skeleton.tsx` |
| 预估行数 | ~140 行 |
| 回滚方案 | `git checkout -- src/dashboard/mobile/` |

**验收标准：**
- [ ] React Native 项目可运行 (iOS + Android)
- [ ] 告警列表 API 正常调用 (axios, baseURL from env, timeout 10s)
- [ ] FlatList 虚拟列表 + 骨架屏 loading 态
- [ ] Pull-to-refresh (RefreshControl)
- [ ] 空态: "暂无告警"; 错误态: 重试 + 离线提示
- [ ] < 2 秒加载 100 条 (低端设备)
- [ ] 离线缓存: AsyncStorage (alerts_cache_{user_id}), 断连时显示缓存

**边界/错误：**
- baseURL env 缺失 → fail-fast 启动报错 (kernel.md §非硬编码)
- API 401 → 重定向登录 (React Navigation)
- 网络不可用 → 从 AsyncStorage 读取缓存 + "离线模式" 条
- FlatList 空数据 → 空态组件 (非白屏)
- 下拉刷新中 → 禁用重复触发

### Task 2: 多页面适配 (创建/编辑/历史)

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/dashboard/mobile/alert-creator.tsx`, `src/dashboard/mobile/alert-history.tsx`, `src/dashboard/mobile/responsive.ts`, `src/dashboard/mobile/layout.tsx` |
| 预估行数 | ~100 行 |
| 回滚方案 | `git checkout -- src/dashboard/mobile/alert-creator.tsx` |

**验收标准：**
- [ ] 创建页: WebView 嵌入 Web 创建向导 (v1)
- [ ] 历史页: 同列表风格, 带日期范围选择
- [ ] 响应式适配 320px-2560px (react-native-safe-area-context)
- [ ] 触摸交互: tap, swipe, pull-to-refresh
- [ ] 底部 Tab 导航: 列表 / 历史 / 设置

**边界/错误：**
- WebView 加载慢 → loading 指示条 (非白屏)
- 屏幕旋转 → 自动调整布局 (useWindowDimensions)
- 键盘弹出 → 不遮挡输入 (KeyboardAvoidingView)
- 创建页提交 → 跳转回列表 + 成功的 Toast
- 设置页: 通知偏好 + 2FA (跳转 User Preferences)

### Task 3: 推送通知 + App 内展示

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/dashboard/mobile/push-handler.ts`, `src/dashboard/mobile/notification-toast.tsx`, `src/dashboard/mobile/event-subscriber.ts`, `src/dashboard/mobile/deep-link.ts` |
| 预估行数 | ~80 行 |
| 回滚方案 | `git checkout -- src/dashboard/mobile/push-handler.ts` |

**验收标准：**
- [ ] FCM onMessage 前台 → App 内 Toast (auto-dismiss 5s)
- [ ] FCM onNotificationOpenedApp → deep link /alerts/{alert_id}
- [ ] SSE EventSource polyfill → AlertTriggered/DeliveryFailed 事件处理
- [ ] 点击推送 → 导航到对应告警详情
- [ ] App 从后台恢复 (onResume) → 强制全量刷新
- [ ] 推送 handler 永不 crash (try/catch 兜底, kernel.md §Hook 永不阻塞)

**边界/错误：**
- 推送权限被拒 → 静默降级, 不弹引导 (kernel.md §隐私防线)
- 推送 payload 缺少 alert_id → LOG_WARNING + 丢弃
- SSE polyfill 不可用 → polling 降级 (30s)
- deep link 目标 alert_id 不存在 → 导航到列表页 + toast "告警不存在"
- 推送 token 刷新 → 调 registerToken API (claude-next.md: typescript seed)

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | push handler + deep link | Jest | payload 解析正确 |
| 组件 | 列表 + 骨架屏 + 三态 | RNTL | loading/empty/error |
| 集成 | API 交互 (mock axios) | Jest + MSW | CRUD 正确 |
| 集成 | SSE 事件订阅 | Jest (mock EventSource) | 4 种事件处理 |
| 平台 | iOS + Android 构建 | Metro bundler | 双平台通过 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/dashboard/mobile/App.tsx` | 新增 | 移动端入口 + Navigation |
| `src/dashboard/mobile/alert-list.tsx` | 新增 | FlatList 告警列表 |
| `src/dashboard/mobile/api-adapter.ts` | 新增 | axios 适配器 (env baseURL) |
| `src/dashboard/mobile/skeleton.tsx` | 新增 | 骨架屏组件 |
| `src/dashboard/mobile/alert-creator.tsx` | 新增 | WebView 创建页 |
| `src/dashboard/mobile/alert-history.tsx` | 新增 | 历史页 |
| `src/dashboard/mobile/responsive.ts` | 新增 | 响应式工具 (dimensions) |
| `src/dashboard/mobile/layout.tsx` | 新增 | Layout + Tab nav |
| `src/dashboard/mobile/push-handler.ts` | 新增 | FCM 推送处理 |
| `src/dashboard/mobile/notification-toast.tsx` | 新增 | App 内通知 Toast |
| `src/dashboard/mobile/event-subscriber.ts` | 新增 | SSE + polling 事件订阅 |
| `src/dashboard/mobile/deep-link.ts` | 新增 | deep link 路由 |

---

## 非范围

- 不实现离线模式 (v2 计划)
- 不实现 Web 版 UI (由各 Web feature 负责)
- 不实现告警业务逻辑 (由 Alert Engine 负责)
- 不实现原生创建向导 (v1 WebView, v2 原生)
