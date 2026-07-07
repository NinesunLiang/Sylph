# Alignment Progress

**Goal**: 4 项代码对齐  
**Status**: running  
**Started**: 2026-07-08 02:50 UTC  
**Expires**: 2026-07-08 08:50 UTC  

---

## Task 1: 统一 Level 命名 L1_BASE → L1
- Status: pending
- Files: carros_base.py
- Strategy: 替换所有 `L1_BASE` → `L1`, `L2_ENHANCE` → `L2`

## Task 2: 统一 Token schema（废掉旧 "steps" 数组格式）
- Status: pending
- Files: carros_base.py, omc_lint.py
- Strategy: 删除 `"steps"` 相关 if/else 分支，统一用 `task.current_step` 新格式

## Task 3: 修 lint → archive 阈值（warning 不应阻断）
- Status: pending
- Files: carros_base.py cmd_archive
- Strategy: lint exit_code >= 2 才阻断，exit_code == 1（warnings）允许归档

## Task 4: 跑 bench 全部 7 场景验证 L2 集成
- Status: pending
- Strategy: python3 .claude/scripts/carros_base.py bench
