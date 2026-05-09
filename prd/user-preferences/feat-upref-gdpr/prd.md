# Feature: UpRef GDPR Compliance

> 所属 Sub PRD：User Preferences & Premium
> 职责：GDPR 合规 — 用户数据删除与隐私管理

## 功能边界

- **负责**：
  - 用户数据删除请求处理（deleteUserData）
  - 级联删除（通知 + 投递记录 + 偏好 + 订阅历史）
  - 72 小时内完成删除（P0）
  - 数据留存策略管理
  - 删除确认与审计日志

- **不负责**：
  - 用户认证（由现有 OAuth 系统负责）
  - 计费数据保留（Stripe 侧数据按 Stripe 政策处理）

## 对外接口

| 接口 | 方向 | 说明 |
|------|------|------|
| `deleteUserData` | inbound | GDPR 数据删除 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| UserDataRetention | Own | CRUD | 用户数据保留策略与删除请求记录 |

## 依赖关系

- **依赖**：User Preferences 所有子模块（级联删除）、Stripe（保留计费数据）
- **被依赖**：无
