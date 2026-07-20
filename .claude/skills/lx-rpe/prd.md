# CarrorOS 设计落地与强证据验证 — PRD

## 背景
CarrorOS 项目在 `重构指导文档/` 中有 10 份完整的设计文档（1.md~10.md），定义了从 IntakeGate 到 Archive 的完整治理架构。但磁盘上的实际代码是由安装脚本生成的模板骨架，**不是按设计文档落地的**。

### 关键问题
1. `context_engine.py` 不存在 → 每个 session 启动时 hook 调用会阻塞
2. VerifyGate 挂在 Stop 事件上（任务结束才检查），设计要求做 PreToolUse 拦截
3. 无 SessionStart hooks → 无知识注入/compact/resume
4. Fallback 是 stamp-only 桩代码
5. 特征验证 63 条检查中 11 条 `lambda: True`，52 条 grep 关键字匹配，全是假阳性
6. `randomized_bench.py` 每次清理中间状态，不测试真正 hook 链

## 阶段性目标

### 🔴 Phase 0：修复致命断裂
1. 创建 `.claude/scripts/context_engine.py`（按 6.md §13 完整代码）
2. 修复 `userprompt-session-resume.py` 的调用路径
3. 注册 SessionStart hooks（按 1.md §6.1）

### 🔴 Phase 1：VerifyGate 完成门
1. 创建 `.claude/scripts/verify_gate.py`（按 5.md spec）
2. VerifyGate 从 Stop 改为 PreToolUse 拦截
3. 创建 `pretool-verify-gate.py`

### 🟡 Phase 2：Output Compression
1. 创建 `output_compress.py` + `posttool-output-compress.py`
2. Bash 输出 >2000 chars 裁剪中间段

### 🟡 Phase 3：Fallback 熔断
1. 重写 `fallback_engine.py`（按 8.md §17 代码）
2. 重写 `pretool-fallback-check.py`（移除 stamp 一次性逻辑）

### 🟡 Phase 4：Context Engine 完整
1. 补齐 compact-check/resume-check/state-injection 命令
2. 确保 context_watermark.py 输出对齐 6.md

### 🟢 Phase 5：Oracle/Meta-Oracle 接入
1. 创建 `pretool-oracle-gate.py`
2. 重写 `oracle_engine.py`（按 7.md spec）

### 🟢 Phase 6：Archive Engine 完整
1. 创建 `posttool-archive-check.py`
2. 验证对齐 10.md §11

### 🟢 Phase 7：PreActionGate 完善
1. 补齐 9 种动作 × 4 种裁决（按 3.md spec）

### 🔵 Phase 8：强证据验证
1. 重写 `feature_verify.py`（实际运行 hook 测试）
2. 重写 `randomized_bench.py`（不清理状态）
3. 创建 `verify_tests.py`

## 路径约定
```
.claude/hooks/          ← Hook 层（被 settings.json 注册）
.claude/scripts/        ← Engine 实现层（hooks call）
.omc/tokens/{date}/{task}.json  ← Token 状态
.omc/tasks/{date}/{task}/        ← 任务文档
.omc/audit/{date}.jsonl          ← 审计
.omc/archive/{date}/{task}/      ← 归档
```

## 设计文档参考
- `重构指导文档/1.md` — IntakeGate
- `重构指导文档/2.md` — PlanBuilder
- `重构指导文档/3.md` — PreActionGate
- `重构指导文档/4.md` — Executor Ledger
- `重构指导文档/5.md` — VerifyGate
- `重构指导文档/6.md` — Context Engine
- `重构指导文档/7.md` — Oracle/Meta-Oracle
- `重构指导文档/8.md` — Fallback
- `重构指导文档/9.md` — CLI Integration
- `重构指导文档/10.md` — Archive
