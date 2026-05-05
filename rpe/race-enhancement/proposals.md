# Race Enhancement — 设计方案（修正版）

> 基于 OMC 现有基建重构：team skill（蜂群调度）+ OMA Lock（文件写锁）
> 结论：Race 不需要自己调度，只需要做**状态跟踪 + 冲突协调**。

---

## 核心洞察

现有基建已经提供了 Race 需要的大部分能力：

| 能力 | 已有方案 | 谁负责 |
|------|---------|--------|
| **代理调度** | `team` skill → `Task()`/`TeamCreate` 派发子 Agent | 直接复用 |
| **文件写锁** | OMA Lock → `oma_lock_manager.py` + pretool/posttool hooks | 直接复用 |
| **状态跟踪** | `race_manager.sh` 的 `owner.json` + `result.json` | 需增强 |
| **子任务管理** | `lx-task-spec` 已有 `race` mode 声明 | 需接入 |

**缺的：** 一个**轻量的协调层**，把这三者串起来。

---

## 方案修正：Race Swarm Coordinator（蜂群协调层）

### 核心思想

Race 不做调度，只做 **协调**。

```
用户: "race 模式，做 A、B、C"
         │
         ▼
lx-task-spec 识别独立子任务 [A, B, C]
         │
         ├── race_manager.sh register A B C   // 注册子任务到 Race 状态
         ├── team skill dispatch Agent(A)     // 复用 OMC team 调度
         │        └── oma_lock acquire file_X  // 写文件前自动加锁
         ├── team skill dispatch Agent(B)
         │        └── oma_lock acquire file_Y
         └── team skill dispatch Agent(C)
                  └── oma_lock acquire file_Z
         │
         ▼
    race_manager.sh status --all  // 轮询所有子任务状态
         │
         ▼
    aggregate → 合并报告 → lx-task-spec 最终验收
```

### 新增内容

| 文件 | 行数 | 说明 |
|------|:----:|------|
| `.claude/skills/lx-race/SKILL.md` | ~250 | 协调层 skill：register → dispatch → collect → report 4 步 |
| `修改 race_manager.sh` | ~100 | 新增 `register`（注册子任务列表）、`status --all`（聚合状态） |
| `修改 feature-registry.yaml` | +3 | 新增 lx-race skill |
| `.claude/scripts/test_race.sh` | ~200 | 集成测试 |
| 更新 `lx-task-spec/SKILL.md` | ~20 | race mode 说明指向 lx-race |

**不新建：**
- ❌ 不建调度引擎 — 用 `team` skill
- ❌ 不建写锁 — 用 OMA Lock
- ❌ 不加 Hook — 不需要
- ❌ 不造新文件协议 — 复用 `owner.json` + `result.json`

### 工作流详解

#### Step 1: 注册（race_manager.sh register）

```bash
race_manager.sh register parent-task --subtasks "A,B,C"
# → 创建 .omc/race/parent-task/
#   ├── owner.json           # 父任务元数据
#   ├── manifest.json        # 子任务列表 + 状态
#   └── subtasks/
#       ├── A/owner.json     # 子任务 A 状态 (assigned/running/completed/failed)
#       ├── B/owner.json
#       └── C/owner.json
```

#### Step 2: 派发（复用 team skill）

```bash
# lx-race 不调度，它告诉 team skill 要做什么
team dispatch:
  - agent: executor
    task: A
    race_id: parent-task/A
  - agent: executor
    task: B
    race_id: parent-task/B
  - agent: executor
    task: C
    race_id: parent-task/C
```

每个 agent 在工作时：
- 写文件 → pretool-write-lock.sh 自动触发 OMA Lock
- 完成后 → 写 `result.json`
- 失败 → 写 failed 状态，其他子任务不受影响

#### Step 3: 收集（race_manager.sh status --all）

```bash
race_manager.sh status parent-task --all
# → 聚合所有子任务状态
# → 输出进度：2/3 completed, 1 running
# → 检测冲突：子任务 A 和 B 修改了同一文件
```

#### Step 4: 报告

```bash
race_manager.sh report parent-task
# → 汇总各子任务输出
# → 标记冲突的文件
# → 输出最终状态
```

### OMA Lock 在 Race 中的角色

Race **不替代** OMA Lock，而是**和它协同**：

| 场景 | 谁保护 | 机制 |
|------|--------|------|
| 两个 agent 同时写同一个文件 | OMA Lock | `pretool-write-lock.sh` 自动加锁 |
| agent A 不知道 agent B 在做什么 | Race | `race_manager.sh status --all` 可见 |
| agent B 改了 agent A 依赖的文件 | OMA Lock + Race | 锁阻止同时写入，Race 标记依赖冲突 |

### 对比原方案

| 维度 | 原 B 方案（Agent编排） | 修正版（蜂群协调） |
|------|:-------------------:|:-----------------:|
| 总行数 | ~800 | ~570 |
| 调度引擎 | 自建 | 复用 `team` skill |
| 写锁 | 不涉及 | 复用 OMA Lock |
| 文件协议 | 新建 | 复用 `owner.json`/`result.json` |
| 测试 | ~200 | ~200 |
| 风险 | 中（新系统） | 低（全是复用） |
| 哲学符合度 | 中等 | ✅ "少即是多" |

### 评估

| 维度 | 评价 |
|------|------|
| 工作量 | ~570 行，4-6 小时 |
| 可用性 | 高 — 协调 team + OMA Lock，不重复造轮子 |
| 风险 | 低 — 不建新基建，只做编排 |
| 哲学 | ✅ 符合 "the less, the more" |
| 人性 | ✅ 用户说"race 模式" → 自动走注册→派发→收集流程 |

### 与 lx-task-spec race mode 的集成

目前 `lx-task-spec/SKILL.md:49` 已有：
```
race：规划完成后并行执行独立子任务
```

修正后，这个 mode 的实际行为变为：
1. task-spec 识别独立子任务
2. 调用 `race_manager.sh register` 注册
3. 通过 `team` skill 派发子 agent
4. agent 工作时 OMA Lock 自动保护写入
5. `race_manager.sh status --all` 轮询收集
6. 全部完成 → 合并验证 → 验收

无需改 lx-task-spec 的代码，只需要在文档中指明 race mode 的实际后端实现。
