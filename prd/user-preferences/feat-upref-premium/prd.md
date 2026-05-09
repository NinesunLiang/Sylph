# Feature: UpRef Premium Management

> 所属 Sub PRD：User Preferences & Premium
> 职责：Premium 订阅管理与计费

## 功能边界

- **负责**：
  - Premium 订阅状态查询（tier / features / expires_at）
  - Premium 订阅升级/降级/取消
  - Stripe 计费集成（支付/发票/退款）
  - 功能权限门禁（根据 tier 解锁/锁定 feature）
  - 订阅过期自动降级
  - 发布 PremiumTierChanged 事件

- **不负责**：
  - 具体 feature 实现（仅控制权限门禁）
  - SSR 认证（由现有 OAuth 系统负责）

## 对外接口

| 接口 | 方向 | 说明 |
|------|------|------|
| `getPremiumStatus` | inbound | 查询订阅状态 |
| `upgradePremium` | inbound | 升级订阅 |
| `cancelPremium` | inbound | 取消订阅 |
| `PremiumTierChanged` | outbound | Tier 变更事件 |

## 数据实体归属

| 实体名 | 归属关系 | 操作类型 | 说明 |
|--------|---------|---------|------|
| PremiumSubscription | Own | CRUD | Premium 订阅记录（等级、到期时间、支付状态） |

## 依赖关系

- **依赖**：Stripe（第三方计费）、User Preferences（用户基础信息）
- **被依赖**：所有需 tier 校验的模块
