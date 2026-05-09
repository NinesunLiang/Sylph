# Research: Dashboard Alert Creator

> 基于 `prd/dashboard/feat-dashboard-creator/prd.md` · 2026-05-09
> Feature 职责：4 步告警创建向导、Tier 感知条件筛选、表单校验、草稿持久化

---

## 关键调用链路

```
用户打开创建向导
  └─→ 检查 localStorage 草稿 → 有草稿 → 恢复 Step + 数据
  │                               无草稿 → Step 1
  │
  ├─→ Step 1: StepSymbol — 选择交易对
  │     ├─→ symbol 搜索 + 自动补全 (debounce 300ms)
  │     ├─→ 实时校验: regex /^[A-Z]{2,5}\/[A-Z]{2,5}$/
  │     ├─→ 联加载态 + 无结果态 + 错误态 (三态覆盖)
  │     └─→ WCAG: aria-label, role="combobox", 键盘上下选
  │
  ├─→ Step 2: StepCondition — 选择条件类型
  │     ├─→ Tier 感知筛选 (从 UserTierCache 读取 tier:{user_id})
  │     │     ├─→ Free: price_above / price_below / price_crosses
  │     │     └─→ Premium: 全部含 technical_indicator / ai_pattern_detection
  │     ├─→ 非 Premium 点击指标/AI → 升级引导弹窗 (含 upgrade_url)
  │     ├─→ 指标参数配置: threshold/period 实时校验
  │     └─→ WCAG: aria-checked, role="radio", 键盘导航
  │
  ├─→ Step 3: StepChannels — 选择通知通道
  │     ├─→ Push/Email/SMS 独立开关
  │     ├─→ SMS → 检查 2FA 已认证 (调用 getPreferences)
  │     │     └─→ 未认证 → 引导跳转 2FA 设置页
  │     ├─→ 校验: 至少一个通道
  │     └─→ WCAG: aria-pressed, role="switch"
  │
  └─→ Step 4: StepPreview — 确认 + 提交
        ├─→ 展示完整摘要 (symbol, condition, channels, tier)
        ├─→ 调用 createAlert API (POST /api/alerts)
        ├─→ 成功 → 清空草稿 + 跳转列表 + Toast (auto-dismiss 5s)
        │     └─→ 防重复提交: submitRef 原子锁
        ├─→ 400 → 内联错误提示 (字段级别)
        ├─→ 409 (限额) → 升级引导
        └─→ 5xx → Toast + 重试按钮

入站事件 — Tier 实时刷新
  └─→ PremiumTierChanged (inbound: user_id, old_tier, new_tier)
        └─→ 刷新 Step 2 条件筛选列表 (不中断当前编辑)
              └─→ 降级: SSE 断连 → 静默用 last known tier

草稿恢复 (draft recovery):
  ├─→ 保存: 每个 Step 切换时写入 localStorage (key: alert_draft_{user_id})
  │     └─→ JSON: { step, data, last_updated: ISO8601 }
  ├─→ 恢复: 加载向导时检查草稿 && last_updated < 24h → 恢复
  └─→ 清理: 提交成功 / 用户显式放弃 / >24h → 清除

状态管理:
  FormContext (React Context)
    ├─→ step: 1-4 (当前步骤)
    ├─→ data: { symbol, condition_type, threshold, channels, ... }
    ├─→ validators: per-step 校验函数 (返回 field-level errors)
    ├─→ tier: current tier (由 PremiumTierChanged 事件驱动)
    └─→ draft: { saved, last_updated }
```

## 表单校验规则

| 字段 | 规则 | 错误码 | 校验时机 |
|------|------|--------|---------|
| symbol | /^[A-Z]{2,5}\/[A-Z]{2,5}$/ | INVALID_SYMBOL | Step 1 blur + submit |
| condition_type | 必须选择一项 | MISSING_CONDITION | Step 2 submit |
| threshold | > 0, Decimal | INVALID_THRESHOLD | Step 2 onInput |
| channels | 至少一个 | NO_CHANNEL | Step 3 submit |
| tier × condition | tier 允许类型 | TIER_RESTRICTED | Step 2 submit 前 |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 创建耗时 | < 30 秒完成 | prd.md §非功能要求 |
| WCAG 2.1 AA | 全部 | prd.md §非功能要求 |
| 屏幕阅读器 | 创建全流程 (aria-labels, role, focus management) | prd.md §非功能要求 |
| API 响应 | createAlert < 500ms (P95) | prd.md §非功能要求 |
| 键盘导航 | Tab / Enter / Escape 全流程 | prd.md §非功能要求 |
| 草稿保存 | Step 切换时自动持久化 | claude-next.md §R33 |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | Step 切换保留状态？ | React Context, 切换不丢失 (claude-next.md: useEffect 依赖完整) |
| Q2 | Tier 升级后是否需要刷新？ | PremiumTierChanged 事件驱动刷新, 静默降级 last known |
| Q3 | 草稿保留时长？ | 24h, 超时自动清除 |
| Q4 | 条件参数默认值？ | price_above: threshold=0; RSI: period=14 |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 表单数据丢失 | 🟡 P1 | 页面意外刷新 → 进度丢失 | localStorage 草稿 (step-level) |
| Tier 门禁 UI bypass | 🟡 P2 | 客户端劫持显示非授权条件 | 服务端二次校验 (fail fast, kernel.md §防御性规则) |
| Step 跳跃 | 🟢 P3 | 直接 URL 跳深层 step | Gate 守卫: 未完成前置 step → Step 1 |
| 重复提交 | 🟡 P1 | 用户双击/网络慢 | submitRef 原子锁 + 按钮 disabled 态 |
| useEffect 无限循环 | 🟡 P2 | 依赖数组不完整 → 重复渲染 | 完整依赖 + eslint-plugin-react-hooks (claude-next.md) |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | API 响应类型 `CreateAlertResponse` 必须从 Alert Engine 契约导入, 不可自造 (claude-next.md: typescript seed) |
| 范围冻结 | 不实现移动端/历史, 记 TODO |
| 证据门禁 | 创建成功必须 VERIFIED: response.alert_id 非空 |

### kernel.md §反模式映射
- anti-pattern B1 (过度工程): 4-step wizard 不抽象通用 Step 容器, 各 step 独立组件
- anti-pattern C2 (类型错误连锁): createAlert API 响应类型变更需查所有调用方
- anti-pattern D1 (上下文丢失): Step 切换不依赖 React 记忆, 全量 Context

### 反模式防范 (claude-next.md)
- [seed:typescript] API 响应必须定义完整类型: `CreateAlertResponse = { alert_id, status, ... }`
- [seed:typescript] useEffect 依赖数组完整: Step 守卫 deps = [step, data]
- R27: 性能报告 < 2s 声明必须有测试证据, 不自称达标
- R24: 构建脚本中 `for x in $FILES` 加双引号

## 实现路径建议

1. **Phase 1**: 4-step Wizard 容器 + FormContext + StepSymbol (含 symbol autocomplete + 三态)
2. **Phase 2**: StepCondition (含 Tier 感知 + 升级引导) + StepChannels (含 2FA 门禁)
3. **Phase 3**: StepPreview + 创建提交 (含重复提交锁 + Toast)
4. **Phase 4**: PremiumTierChanged 事件消费 + localStorage 草稿 (24h)
5. **Phase 5**: WCAG 2.1 AA 全流程审计 + 键盘导航 + 屏幕阅读器
