# 共享状态机模式

> 各 skill 引用此文件获取通用状态机模式，避免重复定义。

## 模式 1: 线性管道 (Linear Pipeline)

```
Phase 0 → Phase 1 → Phase 2 → ... → Phase N → done
```

适用：skillify, learner, task-spec 等生成/处理管道。
回退：Phase N fail → Phase N-1（重试，max 3 轮）

## 模式 2: 检测→确认→生成 (Detect→Propose→Generate)

```
DETECT → PROPOSE → GENERATE → VALIDATE → DOCUMENT
  ↑       ↓ reject                         ↓
  └───────┴────────────────────────────────┘
```

适用：learner（被动检测）、skillify（主动创建）。
降级：PROPOSE reject → done/noop | VALIDATE fail<3 → GENERATE | VALIDATE fail≥3 → blocked

## 模式 3: 蜂群并行 (Swarm/Race)

```
Register → Dispatch → Collect → Report
```

适用：lx-race。
特点：无回退，失败子任务不阻断父任务。

## 模式 4: 闭环修复 (Fix-Verify-Close)

```
Capture → Triage → Execute → Verify → Close
```

适用：lx-todo, lx-rpe, lx-task-spec。
超限：>3 文件 ∨ 2 次失败 → 升级。
