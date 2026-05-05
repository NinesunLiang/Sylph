# state/progress.md — Race Enhancement (蜂群协调层)

> RPE 特性：race-enhancement
> 创建日期：2026-05-04
> 状态：✅ 全部完成

---

## 概述

将 Race 从半成品升级为生产级蜂群协调层。核心洞察：Race 不做调度，只做**状态跟踪 + 冲突协调**。

**哲学**："the less, the more" — 复用现有基建，不重复造轮子。
- 调度 → 复用 `team` skill / Task() API
- 写锁 → 复用 OMA Lock (`pretool-write-lock.sh`)
- 状态 → `race_manager.sh` (bash + 文件 I/O，全平台通用)

---

## Phase 1 — Design

- 状态：✅ 已完成
- 迭代次数：2 (Proposal A/B/C → Oracle 评审 → 用户纠正: "Race = swarm + OMA Lock" → Oracle 再评审)
- 用户确认：是
- 关键发现：
  - 三个提案都有共同缺陷：假设 Race 需要建调度引擎
  - 用户指出："Race = omc 的蜂群战术（swarm）+ 文件写锁"
  - Oracle 确认：lx-race 不应调 team skill，应使用相同底层原语 (Task()/TeamCreate)
  - 6 平台调研：仅 Claude Code 支持原生子 Agent 派发，其他 5 平台退化为 bash 后台/顺序执行

---

## Phase 2 — Implementation

| 任务 | 状态 | 交付物 |
|------|------|--------|
| race_manager.sh 增强 | ✅ 完成 | register/status --all/report 3 新命令，hierarchical subtask 状态树 |
| lx-race SKILL.md | ✅ 完成 | 4 步协调流程 + 双路径派发 + Worker 协议 + OMA Lock 协同 |
| test_race.sh | ✅ 完成 | 12 项集成测试 (12/12 PASS) |
| feature-registry.yaml | ✅ 完成 | +3 行注册 lx-race skill |
| lx-task-spec SKILL.md | ✅ 完成 | race mode 文档更新指向 lx-race 后端 |

---

### 交付文件清单

| 文件 | 行数 | 说明 |
|------|:----:|------|
| `.claude/scripts/race_manager.sh` | ~637 | 状态引擎：register/status --all/report + 原有命令 |
| `.claude/skills/lx-race/SKILL.md` | ~200 | 蜂群协调层 skill：4 步流程定义 |
| `.claude/scripts/test_race.sh` | ~380 | 12 项集成测试 |
| `.claude/feature-registry.yaml` | +3 | lx-race entry |
| `.claude/skills/lx-task-spec/SKILL.md` | 修改 | race mode 文档更新 |

**不新建：**
- ❌ 不建调度引擎 — 用 team skill / Task()
- ❌ 不建写锁 — 用 OMA Lock
- ❌ 不加 Hook — 不需要
- ❌ 不造新文件协议 — 复用 owner.json + result.json

### 跨平台支持

| 平台 | 子 Agent 派发 | race_manager.sh | OMA Lock |
|------|:-------------:|:---------------:|:--------:|
| Claude Code | ✅ Task()/TeamCreate | ✅ bash | ✅ Hook 协议 |
| OpenCode | ❌ 无子 Agent | ✅ bash | ✅ AGENTS.md |
| Codex CLI | ❌ 无子 Agent | ✅ bash | ✅ AGENTS.md |
| Gemini CLI | ❌ 无子 Agent | ✅ bash | ⚠️ 有限 Hook |
| Qwen Code | ❌ 无子 Agent | ✅ bash | ✅ AGENTS.md |
| Cursor | ❌ 无子 Agent | ✅ bash | ⚠️ 仅 Prompt |

---

## 验证

- `test_race.sh`: 12/12 全部通过
  - register: 3 subtasks + structure, missing --subtasks error, duplicate parent error
  - status --all: aggregation, JSON output, non-parent error
  - complete: updates parent manifest, invalid status error
  - report: full aggregation, non-parent error
  - list: shows swarm X/Y
  - clean: removes parent race
- OMA Lock: 7/7 测试继续通过 (并发压力/心跳/可观测性，不受 Race 影响)
