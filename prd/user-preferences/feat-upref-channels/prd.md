# Feature: UpRef Notification Channels

> 所属 Sub PRD：User Preferences & Premium
> 职责：通知渠道偏好管理 + 静默时段 + 测试通知

## 功能边界

- **负责**：
  - 通知渠道独立开关（Push/Email/SMS）
  - 设备令牌管理（Push tokens 注册/注销）
  - 静默时段配置（start/end/timezone）
  - 偏好变更即时生效（< 30 秒）
  - 通知测试发送（调用 Notification Delivery testChannel）
  - 发布 PreferencesChanged 事件

- **不负责**：
  - 通知实际投递（由 Notification Delivery 负责）
  - SMS 2FA（由 2FA 模块负责）

## 对外接口

| 接口 | 方向 | 说明 |
|------|------|------|
| `getPreferences` | inbound | 查询偏好 |
| `updatePreferences` | inbound | 更新偏好 |
| `testNotification` | inbound | 测试通知通道 |
| `PreferencesChanged` | outbound | 偏好变更事件 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| NotificationPreference | Own | CRUD | 用户通知渠道偏好配置（含静默时段） |

## 依赖关系

- **依赖**：Notification Delivery（testChannel 调用）
- **被依赖**：无
