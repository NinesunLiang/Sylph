# Plan: Dashboard Alert Creator

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: Wizard 容器 + FormContext + StepSymbol

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/dashboard/creator/alert-creator-wizard.tsx`, `src/dashboard/creator/form-context.ts`, `src/dashboard/creator/step-symbol.tsx`, `src/dashboard/creator/draft-store.ts` |
| 预估行数 | ~120 行 |
| 回滚方案 | `git checkout -- src/dashboard/creator/` |

**验收标准：**
- [ ] 4-step 导航 (上一步/下一步), Step Guard: 未完成前置不可跳转
- [ ] FormContext 保持全量状态 (step, data, validators, tier)
- [ ] symbol 自动补全 + 格式校验 (/^[A-Z]{2,5}\/[A-Z]{2,5}$/) + debounce 300ms
- [ ] 三态覆盖: loading/empty/error (claude-next.md: typescript strict)
- [ ] localStorage 草稿: Step 切换时自动保存 + 24h 清理
- [ ] WCAG: role="combobox", aria-label, 键盘上下选

**边界/错误：**
- symbol 输入为空 → 禁用下一步 + 提示
- 搜索无结果 → 空态: "未找到交易对"
- API 搜索失败 → 错误态: 重试按钮 (kernel.md §修复 3 轮上限)
- localStorage 满 → try/catch 跳过草稿 (不阻断主流程)
- 草稿 > 24h → 静默清除, 从 Step 1 开始

### Task 2: StepCondition + StepChannels

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/dashboard/creator/step-condition.tsx`, `src/dashboard/creator/condition-selector.tsx`, `src/dashboard/creator/tier-gate-ui.ts`, `src/dashboard/creator/step-channels.tsx` |
| 预估行数 | ~120 行 |
| 回滚方案 | `git checkout -- src/dashboard/creator/step-condition.tsx` |

**验收标准：**
- [ ] Free: 仅 price_above/below/crosses, Premium: 全指标+AI
- [ ] Free 点指标/AI → 升级引导弹窗 (含 upgrade_url)
- [ ] threshold 实时校验 (> 0, Decimal)
- [ ] Push/Email/SMS 独立开关, 至少一个通道
- [ ] SMS → 2FA 认证检查, 未认证 → 引导跳转设置
- [ ] PremiumTierChanged → 刷新条件列表 (不中断编辑)
- [ ] WCAG: role="radio"/"switch", aria-checked/pressed

**边界/错误：**
- tier cache miss → 静默使用 last known tier, 异步刷新
- SMS 2FA API 不可用 → SMS 显示 "暂不可用", 不阻断其他通道
- channels 全关 → 校验阻止提交 + 字段级提示
- threshold=0 → 不允许 (price 不能 0 阈值)
- 指标参数 (如 period=14) → 有默认值, 用户可修改

### Task 3: StepPreview + 提交 + WCAG

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/dashboard/creator/step-preview.tsx`, `src/dashboard/creator/submit-handler.ts`, `src/dashboard/creator/wcag-focus.ts` |
| 预估行数 | ~80 行 |
| 回滚方案 | `git checkout -- src/dashboard/creator/submit-handler.ts` |

**验收标准：**
- [ ] 预览完整摘要: symbol, condition, channels, tier
- [ ] createAlert 调用 (async, 含 loading 态)
- [ ] 防重复提交: submitRef 原子锁 + 按钮 disabled
- [ ] 成功 → 清空草稿 + 跳转列表 + Toast (auto-dismiss 5s)
- [ ] 400 → 内联字段级错误; 409 → 升级引导; 5xx → Toast + 重试
- [ ] WCAG: 焦点管理 (提交后焦点到 Toast), aria-live="polite"
- [ ] keyboard: Tab 按 Step 顺序, Enter 提交, Escape 关闭弹窗

**边界/错误：**
- API 超时 (> 5s) → 显示 "请求超时", 重试按钮 (kernel.md §修复上限)
- 网络断连 → Toast "网络连接断开", 保存草稿, 不丢失数据
- 级联失效: createAlert 成功 → 跳转失败 → 仍清空草稿 (幂等)
- 并发提交: 第 2 次被 submitRef 阻止 (kernel.md §Error DNA 日志)

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | FormContext + 校验函数 | Jest | 字段级错误映射 |
| 组件 | 各 Step 组件 + 三态 | Jest + RTL | loading/empty/error |
| 集成 | Wizard 全流程 (mock API) | Jest + MSW | 创建成功/400/409/5xx |
| 集成 | localStorage 草稿持久化 | Jest | 保存/恢复/24h 清理 |
| 无障碍 | WCAG 2.1 AA | axe-core | 无违规 |
| 安全 | 重复提交 | Jest | submitRef 锁 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/dashboard/creator/alert-creator-wizard.tsx` | 新增 | Wizard 容器 + Step Guard |
| `src/dashboard/creator/form-context.ts` | 新增 | 表单状态 (React Context) |
| `src/dashboard/creator/draft-store.ts` | 新增 | localStorage 草稿 |
| `src/dashboard/creator/step-symbol.tsx` | 新增 | Step 1: symbol 选择 (三态) |
| `src/dashboard/creator/step-condition.tsx` | 新增 | Step 2: 条件类型 (Tier 感知) |
| `src/dashboard/creator/condition-selector.tsx` | 新增 | 条件选择器组件 |
| `src/dashboard/creator/tier-gate-ui.ts` | 新增 | Tier 门禁 UI |
| `src/dashboard/creator/step-channels.tsx` | 新增 | Step 3: 通道选择 (2FA) |
| `src/dashboard/creator/step-preview.tsx` | 新增 | Step 4: 确认提交 |
| `src/dashboard/creator/submit-handler.ts` | 新增 | createAlert 调用 |
| `src/dashboard/creator/wcag-focus.ts` | 新增 | WCAG 焦点管理 |

---

## 非范围

- 不实现高级条件 AND/OR（由 Alert Engine 负责）
- 不实现移动端适配（由 Dashboard Mobile 负责）
- 不实现创建后即时跳转历史（由 Alert History 负责）
