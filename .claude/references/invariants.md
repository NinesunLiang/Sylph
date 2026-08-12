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

## 治理架构（ADR0016 降噪三面，防策略回退）
- INV-13 前置引导（schema）定路径：working-set 的 allowed/denied_paths 是路径契约真源；init 激活时打印契约，scorecard-gate 路径预检越界即 REDIRECT。AI 一开始就走对路径，而非走错被拦。
- INV-14 途中不防错（防不过来）：L1 仅 5 道真安全门（sensitive-edit/governance-bypass/action/secret-scan/stall），L2 15 道含末端校验。砍掉的途中 gate（edit-scope/source-marker/fallback/plan/claim-source）不得恢复为每工具调用拦截——其防线由前置引导+末端校验补位。
- INV-15 末端 TDD 校验保留：verify_gate（断言匹配/防编造）+ completion-gate（软完成检测/防虚假完成）是最后防线，不得砍减。防线从"途中拦截"迁移为"前置定路径 + 末端严校验"，强度不降位置变。
- INV-16 hook 进程合并：hook-launcher 单次 spawn 串行执行多 hook（settings 合并），减少每工具调用 spawn 数。

## Context
- INV-08 每轮 Context 从文件重建，不在旧 transcript 上追加。
- INV-09 默认只读 Hot Card + 当前文件切片 + 最近工具预览。
- INV-10 reviews/ 禁止默认入模。

## Compaction
- INV-11 工具落盘 + 有界预览属于无损可回滚治理。
- INV-12 禁止 L5 AutoCompact 当记忆。
