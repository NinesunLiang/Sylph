# 系统不变量 — CarrorOS 12 条铁律

schema_version: carros.invariants.v1

## 真相
- INV-01 聊天不是任务状态源。状态在 token.json。
- INV-02 transcript 是审计记录，不是正常恢复入口。
- INV-03 LLM Summary 是有损导航，不是真相源。
- INV-04 完整工具输出 → artifacts；evidence 只存索引。

## 执行
- INV-05 每个 tick 只执行一个可验证动作。
- INV-06 只改 allowed_paths；denied_paths 优先级最高。
- INV-07 只有 VerifyGate 可以把 step 标记为 VERIFIED。

## Context
- INV-08 每轮 Context 从文件重建，不在旧 transcript 上追加。
- INV-09 默认只读 Hot Card + 当前文件切片 + 最近工具预览。
- INV-10 reviews/ 禁止默认入模。

## Compaction
- INV-11 工具落盘 + 有界预览属于无损可回滚治理。
- INV-12 禁止 L5 AutoCompact 当记忆。
