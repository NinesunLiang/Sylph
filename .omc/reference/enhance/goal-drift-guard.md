# 目标漂移防线 (E1)

> L2 Enhance Gate: pretool-gate edit-scope 越界检测 + 逃逸升级
> 越界阻断 + CARROROS_EDIT_SCOPE=warn 逃生门 → 连续越界自动回锁

## 越界升级条件

| 条件 | 阈值 | 行为 |
|------|------|------|
| 路径不在 token scope 内 | 单次 | BLOCK，提示加入 scope 或使用 bypass |
| 路径不在 plan scope 内 | 单次 | BLOCK，提示加入 Scope 段 |
| CARROROS_EDIT_SCOPE=warn 越界 | 1-2 次 | 警告通过（柔性约束） |
| CARROROS_EDIT_SCOPE=warn 越界 | **≥3 次** | **自动升级为 BLOCK**（逃逸惯性惩罚） |
| scope 内合法写入 | 任意次 | 重置越界计数（streak=0） |

## E1 硬化（v7.2+）— 逃逸升级检测

### 变更摘要

| 项 | 旧行为 | 新行为 |
|----|--------|--------|
| warn 模式 | 永久放行，审计记录 | 连续 ≥3 次越界自动升回 BLOCK |
| 越界计数 | 无（每次独立判断） | `scope-violation-streak` 文件持久化 |
| scope 内写入 | 无操作 | 重置 streak（正向行为清空黑历史） |
| `_in_scope()` 绝对路径 | scope `.claude/scripts/` 不匹配 `/Users/.../.claude/scripts/verify_gate.py` | 支持绝对路径匹配相对 scope |

### 持久化文件

```
文件: .omc/state/scope-violation-streak
格式: 纯文本整数（越界次数）
清理条件:
  - scope 内合法写入 → unlink
  - 升级至 BLOCK → unlink（防无限重复）
```

### 检测流程

```
1. _check_edit_scope(payload)
2.   读取 scope-violation-streak
3.   检查 token scope
4.   ├─ 在 scope 内 → 清 streak, return None
5.   ├─ 越界 → streak++, 写文件
6.   │   ├─ warn 模式 + streak≥3 → BLOCK（逃逸惩罚）
7.   │   └─ warn 模式 + streak<3 → 放行
8.   └─ block 模式 → BLOCK
9.   回退到 plan scope（同逻辑）
```

## 集成点

- `.claude/hooks/pretool-gate.py` — `_check_edit_scope()` 函数（Gate 5）
- `.omc/state/scope-violation-streak` — streak 持久化
- 环境变量 `CARROROS_EDIT_SCOPE=warn` — 柔性逃生门

## 配置

无配置文件，纯自包含。逃逸阈值 3 次硬编码为模块级常量。
