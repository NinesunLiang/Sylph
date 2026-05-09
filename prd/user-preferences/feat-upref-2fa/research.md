# Research: UpRef SMS 2FA

> 基于 `prd/user-preferences/feat-upref-2fa/prd.md` · 2026-05-09
> Feature 职责：SMS 双因素认证设置与验证

---

## 关键调用链路

```
用户绑定手机号 (setup2FA)
  └─→ POST /api/2fa/setup {user_id, phone}
        ├─→ 校验: phone E.164 格式 (regex /^\+[1-9]\d{1,14}$/)
        ├─→ ALREADY_CONFIGURED 检查:
        │     └─→ User2FA.status = verified → 409 ALREADY_CONFIGURED
        ├─→ 生成 6 位验证码 (crypto.randomInt(100000, 999999))
        │     └─→ 存储: code_hash = bcrypt(code), TTL 5min (Redis: 2fa_code:{user_id})
        ├─→ SMS 发送验证码 (通过 Notification Delivery SMS 通道)
        │     └─→ 失败 → 500 SMS_SEND_FAILED (不会保存 pending)
        ├─→ 写入 User2FA (PostgreSQL):
        │     user_id, phone, status=pending, attempt_count=0, created_at
        └─→ 返回 {status: "pending", phone_masked: "+1****5678"}

用户验证验证码 (verify2FA)
  └─→ POST /api/2fa/verify {user_id, code}
        ├─→ 锁定检查:
        │     └─→ locked_until > now → 423 LOCKED + remaining_minutes
        ├─→ 验证:
        │     ├─→ crypto.timingSafeEqual(Buffer.from(code), Buffer.from(code_hash_plain))
        │     │     (注: code_hash 是 bcrypt, 需先 bcrypt.compare)
        │     └─→ 比较失败:
        │           ├─→ attempt_count +1
        │           ├─→ ≥ 5 → locked_until = now + 30min
        │           └─→ 返回 401 INVALID_CODE + remaining_attempts
        ├─→ 成功:
        │     ├─→ 清除验证码 (Redis DEL)
        │     ├─→ 更新 User2FA (status=verified, verified_at=NOW())
        │     └─→ 返回 {status: "verified"}
        └─→ 验证码过期 → 410 CODE_EXPIRED (引导重新 setup2FA)

SMS 通知门禁:
  updatePreferences(channels.sms=true)
    └─→ 读 User2FA WHERE user_id=$1 AND status='verified'
          ├─→ 存在 → 放行
          └─→ 不存在 → 400 2FA_REQUIRED + redirect_url
```

## 数据流

| 接口 | 方向 | 输入 | 输出 | 存储 |
|------|------|------|------|------|
| setup2FA | inbound | user_id, phone | {status, phone_masked} | PostgreSQL + Redis (code) |
| verify2FA | inbound | user_id, code | {status} | PostgreSQL + Redis (DEL) |

## 约束条件

| 类别 | 约束 | 来源 |
|------|------|------|
| 验证码比较 | crypto.timingSafeEqual | prd.md §Security (kernel.md §隐私防线) |
| 验证码过期 | 5 分钟 | prd.md §Security |
| 验证码长度 | 6 位数字 (crypto.randomInt) | prd.md §Security |
| 错误锁定 | 5 次 → 30 分钟 | prd.md §Security |
| 手机号格式 | E.164 | prd.md |
| 幂等 | 已验证用户重复 setup → 409 | prd.md |

## 待确认问题

| # | 问题 | 建议 |
|---|------|------|
| Q1 | 验证码时效？ | 5 分钟, Redis TTL 300 |
| Q2 | 验证码长度？ | 6 位数字, crypto.randomInt |
| Q3 | 解锁？ | 30 分钟自动解锁, 或联系客服手动清除 locked_until |

## 风险识别

| 风险 | 等级 | 说明 | 缓解措施 |
|------|------|------|---------|
| 暴力破解 | 🟡 P1 | 验证码穷举 | 5 次错误 → 30min 锁定 (Redis atomic INCR) |
| timing 攻击 | 🟡 P2 | 比较耗时差异泄露 | crypto.timingSafeEqual |
| 重放攻击 | 🟡 P2 | 相同验证码多次使用 | 一次性使用后 Redis DEL |
| 验证码 SMS 延迟 | 🟢 P3 | 发送慢 → 用户超时 | 异步发送 + 5min 窗口足够 |

## 项目特定引用

### AGENTS.md §铁律 映射
| 铁律 | 实现 |
|------|------|
| 禁止编造 | timingSafeEqual 引用 Node.js crypto 文档 |
| 隐私防线 | 验证码只存 bcrypt hash, 不存明文; phone 只在 User2FA 表 |
| 范围冻结 | 只做 2FA, 不涉及其他认证方式 |

### kernel.md §错误处理铁律
- Error DNA: 验证失败自动记录 (但 code 本身不入日志)
- Hook 永不阻塞: SMS 发送失败 → 500 (不保留 pending 状态)
- 隐私红线: 验证码永远不入 log, 永远不返回客户端

### 反模式防范 (claude-next.md)
- [seed:typescript] any 禁止: crypto.timingSafeEqual 类型断言精确
- R6 (隐私防线): 验证码 hash 用 bcrypt, 代码中无明文 code 路径
- R24: 清理脚本 `for x in $EXPIRED_CODES` → `set -f`

## 实现路径建议

1. **Phase 1**: setup2FA 手机号绑定 + E.164 校验 + 6 位验证码 bcrypt hash + SMS 发送
2. **Phase 2**: verify2FA + timingSafeEqual + 一次性验证码
3. **Phase 3**: 错误锁定 5 次 30min + 自动解锁 + SMS 通知门禁集成
