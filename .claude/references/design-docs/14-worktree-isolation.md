# 14. Worktree 隔离 —— 多智能体并发治理方案提案

> 状态: **PROPOSAL（待高阶模型评审）** | 日期: 2026-08-14
> 性质: 设计提案，非 ADR（尚未决策）。用于外部高阶模型（Opus/GPT/Grok）独立评审。
> 背景锚点: ADR0019「治理定位再校准」——CarrorOS 定位为「长期多智能体治理基础设施」，并发协调是唯一未证明的硬核。

---

## 0. TL;DR

CarrorOS 面临一个身份缺口：**多智能体并发编辑同一文件会冲突**。提案用 **git worktree 隔离**（每个任务一个独立工作副本）解决，而非悲观锁。PoC 已证可行性（文件隔离 ✅、规则遵守 ✅、审计局部闭环 ✅），但暴露一个此前误判为"缺陷"、实际是**正确封装**的行为：审计记录写在各 worktree 自己的账本，主树看不到。本提案请高阶模型评审三点：(1) 隔离模型是否成立；(2) 审计局部闭环是否应维持（不做全局合并）；(3) 通用化的最小实现边界。

---

## 1. 背景与动机

### 1.1 问题

CarrorOS 的 ADR0019 定位为「长期多智能体治理基础设施」，并发协调是唯一未被证明的硬核。现状：

| 并发层 | 现有机制 | 是否解决"两任务编辑同一文件" |
|---|---|---|
| 元数据/状态 | `write_lock.py`（fcntl）+ token.json.lock | 否（只锁状态文件） |
| 任务编号 | `alloc_report_index.py`（flock） | 否（只锁编号分配） |
| **业务源文件** | **无锁** | **❌ 缺口：两 agent 同时 Edit 同一文件互相覆盖** |

### 1.2 候选方案对比

| 方案 | 机制 | 死锁风险 | 复杂度 | 与"少即是多" |
|---|---|---|---|---|
| A. 悲观锁（等待编辑） | 全局文件互斥锁 | 高 | 高 | 冲突 |
| **B. worktree 隔离（本提案）** | 每任务独立 git worktree | **无** | 中 | ✅ 契合 |
| C. 冲突检测 + REDIRECT | 写前查其他任务声明 | 中 | 中 | 部分契合 |

**选择 B**：worktree 隔离消除共享可变状态（死锁根源），是"少即是多"的天然实现。且项目已有成熟先例。

---

## 2. 现有资产（非从零造）

### 2.1 CandidateWorkspace（frontend-overnight 已有完整闭环）

```python
# .claude/workflows/frontend-overnight/scripts/ui_autopilot/domain.py:428-440
@dataclass(slots=True)
class CandidateWorkspace:
    """Uses git worktree to create isolated copy where worker can modify files.
    Gate failure → remove worktree, main tree untouched.
    Gate pass → merge changes back to main tree, remove worktree.
    """
    worktree_path: str
    branch_name: str
    created_at: str
    patch_id: str
```

已有模式：隔离 → 修改 → 门禁 → 通过合并/失败删除。**这是可复用的成熟资产，不是从零实现。**

### 2.2 PoC 验证结果（2026-08-14 实测）

| 验证项 | 结果 | 判定 |
|---|---|---|
| V1 治理在 worktree 内触发 | ✅ 5 道 gate 全 ALLOW | 通过 |
| V2 路径解析 | ✅ `git rev-parse --show-toplevel` 正确返回 worktree 根 | 通过 |
| V3 审计写入位置 | ⚠️ 写 worktree 自己的 `.omc/state/audit/` | **隔离（见 §3.2）** |
| V5 主树无污染 | ✅ 主树 .omc 未被混写 | 通过 |
| 回滚 | ✅ `git worktree remove` 零残留 | 通过 |

---

## 3. 两个关键设计判断

### 3.1 规则遵守（无需担心）

worktree 里的 AI **100% 遵守 CarrorOS 规则**：gate 正常触发、正常拦/放行、审计正常记录。规则跟着 AI 走，不跟着目录走。**不存在"worktree 逃逸治理"。**

### 3.2 审计局部闭环（本提案的核心设计判断）

PoC 发现 gate 的审计写到 worktree 自己的 `.omc/state/audit/`，主树看不到。**此前的初步判断（"审计分裂是缺陷，需合并回主树"）已被推翻**：

- **正确语义**：每个 worktree 是自治的治理单元，内部闭环；主终端只看聚合结果（任务成败 + 合并代码），不实时盯每个 gate 判断。这如同微服务的局部日志。
- **按需可查**：worktree 目录保留期间，主终端随时可进 worktree 查其内部账本——"按需可查"天然满足。
- **不做全局审计合并**：避免引入双写 + 合并机制（违反"少即是多"）。

**⚠️ 请评审此判断**：审计局部闭环是否应维持？还是主树仍需汇总各 worktree 的审计（例如安全事件需全局可见）？

---

## 4. 通用化方案设计

### 4.1 目标

把 worktree 隔离从「frontend-overnight 专属」提升为**任意 L2 任务可选模式**，从机制上消除并发编辑冲突。

### 4.2 入口设计

```bash
# 任务初始化时选择隔离模式
python3 .claude/scripts/carros_base.py init --task-id <ID> --isolated
# 或 skill 层: /lx-goal --isolated "..."
```

`--isolated` 触发：
1. `git worktree add /tmp/carros-wt-<task-id> -b <task-id>-branch`
2. 任务文档系统（token/plan/executor）在 worktree 内创建
3. AI 在 worktree 内执行全部工具调用
4. 任务归档时：门禁验证 → merge 回主树 → remove worktree

### 4.3 与现有机制衔接

| 机制 | 关系 |
|---|---|
| `write_lock.py` | **保留**——worktree 内仍锁 .omc/state 元数据 |
| `.omc/` tracked 骨架（8 个 index.md/handoff） | worktree 会带骨架副本；任务若改骨架，merge 时冲突——需明确"骨架只读" |
| hook 路径解析 | 已验证 worktree 内正确（`--show-toplevel` 返回 worktree 根） |
| merge 冲突 | 两任务改同文件不同位置 → git 自动合并；同行 → 冲突需人工/高阶裁决 |

### 4.4 明确不做的事（少即是多）

- ❌ 不做全局审计合并（见 §3.2）
- ❌ 不做悲观锁/等待队列
- ❌ 不为所有任务强制隔离（仅 `--isolated` 可选）
- ❌ 不隔离 `.omc/` 运行时状态（骨架只读，数据在 worktree 内各自闭环）

---

## 5. 代价与收益

### 5.1 收益

| 收益 | 程度 |
|---|---|
| 消除并发编辑冲突 | 高（核心） |
| 补上 ADR0019 唯一硬核缺口 | 高（定位真正成立） |
| 失败隔离（任务失败删 worktree 零污染） | 高 |
| 复用成熟 CandidateWorkspace | 中高 |
| 对齐"少即是多" | 高 |

### 5.2 代价

| 代价 | 程度 | 说明 |
|---|---|---|
| 实现成本 | 中 | 抽通用脚本 + 接 carros_base.py init |
| merge 冲突仍在 | 中 | 事后一次性，非运行时死锁 |
| 磁盘/性能 | 低 | 完整 checkout，可 shallow 缓解 |
| **审计全局可见性** | **低（本提案判定为可接受）** | 局部闭环，按需可查 |

---

## 6. 请高阶模型评审的三点

1. **隔离模型是否成立**：worktree 隔离（而非锁）作为多智能体并发的默认机制，是否健全？有无死锁/一致性漏洞？
2. **审计局部闭环是否应维持**：主树不汇总各 worktree 审计，是否可接受？还是安全/合规要求全局审计可见？（若需全局，最小代价方案是什么？）
3. **通用化最小边界**：§4.4 的"不做清单"是否合理？有无被遗漏的必须项（如并发 init 的 token 冲突、`--isolated` 与 goal 模式交互）？

---

## 7. 证据锚点

- ADR0019（治理定位再校准）: `.claude/references/adr/0019-governance-positioning-model-maturity.md`
- CandidateWorkspace 先例: `.claude/workflows/frontend-overnight/scripts/ui_autopilot/domain.py:428-440`
- PoC 实测: 本提案 §2.2（可复现：`git worktree add` + 触发 gate）
- 现状并发缺口: §1.1（write_lock 只锁状态，不锁源文件）
