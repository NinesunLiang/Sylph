# Orchestrator - 任务调度器 [SUPERSEDED]

> 状态: SUPERSEDED — 请参考 `@.claude/references/current-task-architecture.md`
> 最后对齐: 2026-07-28
>
> 此文件为历史设计文档。实际实现已重构：
> - 状态机替换为 token + field 驱动的生命周期（无 spec_review / fallback_exploring 状态）
> - 裁决逻辑由 GateKeeper 分层链统一处理
> - 实际代码见 carros_base.py（~2521行）+ gatekeeper.py（~705行）

---

## 概述

实际任务引擎不再使用形式化状态机轮转。任务生命周期映射为以下阶段：

```
init → tick/verify → archive
 ├─ 创建 token + 计划
 ├─ 执行步骤 + 证据留痕
 └─ 归档 + 墓碑
```

裁决通过 GateKeeper 分层链（6 种输出）在下列 5 个 gate 处介入：

```
pretool-gate → execute → completion-gate → verify-gate → claim-audit
```

## 关键引用

| 组件 | 位置 |
|:-----|:-----|
| 任务引擎 | `carros_base.py:init → tick → verify → report → archive` |
| GateKeeper | `gatekeeper.py` (~705行) |
| Token 结构 | `carros_base.py _default_token()` |
| 阈值 | `kernel.md` 水位防线 |
