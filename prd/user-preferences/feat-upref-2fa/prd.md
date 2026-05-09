# Feature: UpRef SMS 2FA

> 所属 Sub PRD：User Preferences & Premium
> 职责：SMS 双因素认证设置与验证

## 功能边界

- **负责**：
  - SMS 2FA 绑定设置（手机号录入）
  - 验证码发送与校验
  - 2FA 状态管理（已绑定/已验证/已解绑）
  - SMS 功能的前置门禁（未通过 2FA 不可启用 SMS 通知）

- **不负责**：
  - SMS 通知投递（由 Notification Delivery 负责）
  - Premium 订阅校验（由 Premium 模块负责）

## 对外接口

| 接口 | 方向 | 说明 |
|------|------|------|
| `setup2FA` | inbound | 绑定手机号 |
| `verify2FA` | inbound | 验证验证码 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| User2FA | Own | CRUD | 用户 2FA 密钥与验证状态 |

## 依赖关系

- **依赖**：Notification Delivery SMS 通道（验证码发送）
- **被依赖**：User Preferences - 通知渠道（SMS 前置门禁）
