# Plan: Notification Email Channel

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: SendGrid API 客户端 + 基本发送

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/notification/email/sendgrid-client.ts`, `src/notification/email/deliver-email.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/notification/email/` |

**验收标准：**
- [ ] SendGrid API v3 可正常发送（POST /v3/mail/send）
- [ ] API 密钥从环境变量读取（非硬编码）
- [ ] deliverEmail 返回 {delivery_id, status, latency_ms}

**边界/错误：**
- SendGrid 返回 4xx → 返回 failure，由 Dispatcher 重试
- SendGrid 返回 5xx → 返回 failure，指数退避后重试
- API Key 为空 → 启动时即 fail-fast，不运行时才报错
- delivery_id 格式: `email_{uuid_v4_short}`

### Task 2: 模板引擎 + 变量替换

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/notification/email/template-renderer.ts`, `src/notification/email/email-template-store.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/notification/email/template-renderer.ts` |

**验收标准：**
- [ ] HTML 模板变量正确替换（Handlebars 语法）
- [ ] 纯文本版本自动生成（strip HTML tags）
- [ ] XSS 防护（HTML 转义 + CSP headers）
- [ ] 模板 CRUD（EmailTemplate 实体）

**边界/错误：**
- 模板变量缺失 → 不替换（保留原始标记），不 crash
- 模板 ID 不存在 → 返回模板未找到错误
- HTML 中不可信内容 → escape/sanitize

### Task 3: Webhook 回调 + 退信管理

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/notification/email/sendgrid-webhook.ts`, `src/notification/email/bounce-manager.ts` |
| 预估行数 | ~50 行 |
| 回滚方案 | `git checkout -- src/notification/email/sendgrid-webhook.ts` |

**验收标准：**
- [ ] 签名验证（SendGrid webhook 安全）
- [ ] sg_event_id 幂等去重
- [ ] bounced → 写入 BounceRecord + 标记地址失效
- [ ] 同一地址 3 次退信后永久标记

**边界/错误：**
- 未知 event type → 记录并跳过
- Webhook 签名验证失败 → 400，不处理
- 同地址退信计数：滑动窗口 30 天内 3 次 → 永久标记

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | 模板渲染 + XSS 转义 | Jest | 正确替换, 无注入 |
| 单元 | 退信计数逻辑 | Jest | N=3 永久标记, 滑动窗口 30d |
| 单元 | 幂等去重 | Jest | sg_event_id 去重 |
| 集成 | SendGrid API (mock) | Jest | 2xx/4xx/5xx + 超时 |
| 集成 | Webhook 回调 (mock) | Jest | 签名验证, 事件分发 |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/notification/email/sendgrid-client.ts` | 新增 | SendGrid 客户端 |
| `src/notification/email/deliver-email.ts` | 新增 | 发送接口 |
| `src/notification/email/template-renderer.ts` | 新增 | 模板渲染 |
| `src/notification/email/email-template-store.ts` | 新增 | 模板存储 |
| `src/notification/email/sendgrid-webhook.ts` | 新增 | 回执接收 |
| `src/notification/email/bounce-manager.ts` | 新增 | 退信管理 |

---

## 非范围

- 不实现用户地址管理（由 User Preferences 负责）
- 不实现投递决策与重试编排（由 Dispatcher 负责）
- 不实现其他通知通道
