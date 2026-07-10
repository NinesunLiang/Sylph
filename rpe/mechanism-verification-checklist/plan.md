# Plan: 机制验证清单

> Phase: Plan | Date: 2026-07-08 | Source: research.md

## Goal
建立四级验证体系（L1-L4），确认 CarrorOS 核心机制真实可用。

## AC (from research.md)
| AC | 描述 | 验证方式 |
|----|------|----------|
| AC1 | 验证清单覆盖所有核心机制 (15+) | 清单文件存在 |
| AC2 | verify_p0.sh 可运行，输出清晰报告 | bash scripts/verify_p0.sh |
| AC3 | 发现并记录所有 P0 阻塞问题 | block-*.md 文件 |
| AC4 | 至少 1 个 L4 端到端场景通过 | 对话测试证据 |

## Scope
- `rpe/mechanism-verification-checklist/scripts/` — 验证脚本
- `rpe/mechanism-verification-checklist/results/` — 验证结果
- `rpe/mechanism-verification-checklist/blocks/` — 阻塞问题记录

## Steps

### S1: 创建 L1 静态完整性验证脚本
- 检查所有核心文件/目录存在
- 覆盖: 执行引擎/OMA/状态管理/安全/治理/AGENTS
- 输出: 通过/失败/警告 报告
- **Depends on**: research.md (complete)

### S2: 运行 L1 验证 + 记录结果
- 执行 verify_l1.sh
- 记录发现的问题 → blocks/ 目录
- 统计覆盖率

### S3: 创建 L2 逻辑自洽性验证
- 检查 skills 的 SKILL.md frontmatter
- 检查 @ 引用目标是否存在
- 检查 settings.json hook 引用路径有效性

### S4: 运行 L2 验证 + 记录结果

### S5: 创建 L3 运行测试
- 测试核心 Python 脚本可 import/执行
- 测试 hook 脚本无语法错误
- 测试 carros_base.py 基本命令

### S6: 运行 L3 验证 + 记录结果

### S7: L4 端到端验证（当前会话即为证据）
- 本会话已经完成了: hook合并、settings更新、审计摘要
- 记录为 L4 实战证据

## Execution Order
S1 → S2 → S3 → S4 → S5 → S6 → S7 (sequential)
