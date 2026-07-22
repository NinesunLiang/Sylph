---
name: lx-codebase-design
version: v1.0.0
description: "代码设计哲学 — deep module（深模块）设计：小接口大行为、seam、adapter。适用于模块设计/重构/接口拆分场景。纯指令调用，不接入治理管线。"
when_to_use: "Use when designing or restructuring a module, deciding where a seam goes, or making code more testable."
harness_version: ">=6.3.0"
status: stable
role: "Codebase design philosophy — deep modules, seams, adapters. Command-only."
execution_mode: stepwise
triggers:
  - "/lx-codebase-design"
---
# lx-codebase-design — 深模块设计哲学

> 纯指令调用。设计模块接口时使用这套语言和原则。

## 核心概念

| 术语 | 含义 | 避免说 |
|:----|:----|:-------|
| **模块(Module)** | 有接口(Interface)+实现(Implementation)的单元 | 组件/服务 |
| **接口(Interface)** | 调用方必须知道的所有信息：类型+不变量+顺序约束+错误模式+配置+性能特征 | API/签名 |
| **实现(Implementation)** | 模块内部代码 | — |
| **深度(Depth)** | 接口的杠杆率：小接口背后的大行为 = 深模块 | — |
| **缝(Seam)** | 可以不改此处代码而改变行为的位置(Feathers) | 边界 |
| **适配器(Adapter)** | 在缝上满足接口的具体实现 | — |

## 深 vs 浅

```
深模块 = 小接口 + 大实现（目标）
     ┌─────────────┐
     │  小接口      │  ← 少数方法，简单参数
     ├─────────────┤
     │  深实现      │  ← 复杂逻辑隐藏在内
     └─────────────┘

浅模块 = 大接口 + 少实现（避免）
     ┌─────────────────────┐
     │  大接口              │  ← 很多方法，复杂参数
     ├─────────────────────┤
     │  薄实现              │  ← 只是透传
     └─────────────────────┘
```

设计接口时问：能减少方法数吗？能简化参数吗？能把更多复杂度藏到内部吗？

## 原则

1. **深度是接口的属性，不是实现的属性** — 模块内部可以有私有 seam，供内部测试用
2. **删除测试** — 删掉这个模块，复杂度会消失吗？还是散布到 N 个调用方？
3. **接口 = 测试面** — 调用方和测试跨同一个 seam。想绕过接口测试 → 模块形状错了
4. **一个适配器=假 seam，两个=真 seam** — 没有真实的变体之前不引入 seam

## 可测试性设计

1. **接受依赖，不创建依赖**
   ```
   ✅ processOrder(order, paymentGateway)
   ❌ processOrder(order) { const gateway = new StripeGateway() }
   ```

2. **返回值，不产生副作用**
   ```
   ✅ calculateDiscount(cart) → Discount
   ❌ applyDiscount(cart): void { cart.total -= discount }
   ```

3. **小表面积** — 少方法=少测试，少参数=简单setup

## 流程

1. 识别当前模块的接口和实现
2. 评估深度：接口大小 vs 实现复杂度
3. 问三个问题：reduction？简化？隐藏？
4. 定位 seam：在哪里可以替换行为？
5. 删除测试：删掉这个模块，谁痛苦？
6. 输出设计方案
