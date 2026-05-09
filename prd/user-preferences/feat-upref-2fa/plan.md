# Plan: UpRef SMS 2FA

> 基于 `research.md` · 2026-05-09
> Phase 2 — 实施计划

---

## 任务分解

### Task 1: setup2FA + 验证码生成/发送

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/user-preferences/2fa/setup-2fa.ts`, `src/user-preferences/2fa/verification-code.ts`, `src/user-preferences/2fa/user-2fa-store.ts` |
| 预估行数 | ~60 行 |
| 回滚方案 | `git checkout -- src/user-preferences/2fa/` |

**验收标准：**
- [ ] setup2FA 校验 E.164 格式 (/^\+[1-9]\d{1,14}$/)
- [ ] 已验证用户重复 setup → 409 ALREADY_CONFIGURED
- [ ] 6 位验证码: crypto.randomInt(100000, 999999), bcrypt hash 存储
- [ ] 验证码 TTL 5min (Redis: 2fa_code:{user_id} EX 300)
- [ ] SMS 发送 (经 Notification Delivery), 发送失败不保留 pending
- [ ] User2FA(status=pending) 写入 PostgreSQL

**边界/错误：**
- 手机号格式非法 → 400 VALIDATION_ERROR (具体: "手机号需以 + 开头")
- SMS 发送失败 → 500 SMS_SEND_FAILED (不创建 pending 记录)
- 重复调用 setup2FA (pending 状态) → 重新生成验证码 + 更新
- 已验证用户再次 setup → 409 (必须先 disable)
- 验证码 hash: bcrypt compare 时不泄露明文

### Task 2: verify2FA + timingSafeEqual

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/user-preferences/2fa/verify-2fa.ts` |
| 预估行数 | ~40 行 |
| 回滚方案 | `git checkout -- src/user-preferences/2fa/verify-2fa.ts` |

**验收标准：**
- [ ] crypto.timingSafeEqual 比较 (Node.js crypto 原生)
- [ ] 验证通过 → User2FA(status=verified, verified_at=NOW())
- [ ] 一次性验证码: 使用后 Redis DEL
- [ ] 验证码过期 → 410 CODE_EXPIRED

**边界/错误：**
- code 格式非法 (非 6 位数字) → 400 VALIDATION_ERROR (早退, 不计尝试)
- 验证码已过期 → 410 CODE_EXPIRED (不计尝试)
- code hash 类型不匹配 → bcrypt.compare 返回 false → 401
- timingSafeEqual 的输入长度必须相同 → 先校验长度
- 验证码明文不入日志 (kernel.md §隐私防线)

### Task 3: 错误锁定 + SMS 门禁

| 属性 | 内容 |
|------|------|
| 影响文件 | `src/user-preferences/2fa/lockout-manager.ts`, `src/user-preferences/2fa/sms-gate.ts` |
| 预估行数 | ~40 行 |
| 回滚方案 | `git checkout -- src/user-preferences/2fa/lockout-manager.ts` |

**验收标准：**
- [ ] 5 次连续错误 → locked_until = now + 30min (Redis atomic INCR)
- [ ] 锁定中 → 423 LOCKED + remaining_minutes
- [ ] 30 分钟后自动解锁 (locked_until 过期校验)
- [ ] SMS 门禁: updatePreferences(sms.enabled=true) 检查 User2FA.verified

**边界/错误：**
- 锁定中继续尝试 → 423 (不计入尝试计数)
- 解锁后从头计数 (attempt_count reset)
- INCR 原子递增 (并发攻击不绕过)
- SMS 门禁: Redis or PostgreSQL 查询 verified 状态

## 测试策略

| 层级 | 范围 | 工具 | 标准 |
|------|------|------|------|
| 单元 | 验证码生成 + bcrypt hash | Jest | 6 位, 可 compare |
| 单元 | timingSafeEqual | Jest | 相同 true, 不同 false, 等长 |
| 单元 | 锁定逻辑 + 自动解锁 | Jest | 5 次→30min, 解锁 reset |
| 集成 | setup→verify 流程 (mock SMS) | Jest | 完整链路 |
| 集成 | SMS 门禁集成 | Jest | updatePreferences 校验 |
| 安全 | 验证码不入日志 | Jest | 搜索 code 路径无 console.log |

## 影响范围

| 文件 | 变更 | 说明 |
|------|------|------|
| `src/user-preferences/2fa/setup-2fa.ts` | 新增 | 绑定 + E.164 校验 |
| `src/user-preferences/2fa/verification-code.ts` | 新增 | crypto.randomInt + bcrypt |
| `src/user-preferences/2fa/user-2fa-store.ts` | 新增 | PostgreSQL + Redis |
| `src/user-preferences/2fa/verify-2fa.ts` | 新增 | timingSafeEqual |
| `src/user-preferences/2fa/lockout-manager.ts` | 新增 | 5→30 INCR |
| `src/user-preferences/2fa/sms-gate.ts` | 新增 | SMS 门禁 (verified check) |

---

## 非范围

- 不实现 SMS 通知投递（由 Notification Delivery 负责）
- 不实现 Premium 订阅校验（由 feat-upref-premium 负责）
- 不实现通知偏好管理（由 feat-upref-channels 负责）
- 不实现 TOTP/App 2FA（v2 计划）
