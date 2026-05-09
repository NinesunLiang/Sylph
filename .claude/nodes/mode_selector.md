# mode_selector — 执行模式选择节点

> **参考**: `.claude/references/execution-modes.md`（完整模式定义）
> **用途**: 输入任务特性 → 输出推荐执行模式 + 对应门禁列表
>
> 其他 skill 可通过 `@../nodes/mode_selector.md` 引用本节点

---

## 输入

```yaml
task_characteristics:
  count: int                # 子任务数量
  dependencies:             # 子任务间依赖关系
    - independent           # MECE：无共享状态/顺序依赖
    - sequential            # 每一步依赖上一步结果
    - tightly_coupled       # 强耦合，不可拆解
  complexity: low|medium|high
  failure_blast_radius: isolated|cascading
  requires_human_gates: true|false  # 是否需要每阶段人工批准
  is_read_only: true|false
```

---

## 选择逻辑

### 决策树

```
输入任务特性
  → 是只读操作？ → 无模式（直接执行）
  → 子任务可 MECE 分解？
    → Yes + ≥3 子任务 + 无顺序依赖
      → 推荐: Race Mode
    → No / <3 子任务 / 有顺序依赖
      → 需要人工阶段审批？
        → Yes → 推荐: Stepwise Mode（含 gate）
        → No → 复杂度 high？
          → Yes → 推荐: Stepwise Mode（简化 gate）
          → No → 直接执行（无需正式模式）
```

### 快速查询表

| 任务画像 | 推荐模式 | 理由 |
|---------|---------|------|
| 调研/分析/阅读代码 | 直接执行 | 只读，无副作用 |
| 单文件 bug 修复 | 直接执行 | 简单，1-2 文件 |
| 单元测试编写（1-3 个） | 直接执行 | 明确边界 |
| 多个独立功能同时开发 | Race | MECE 子任务，并发吞吐 |
| 状态聚合（多数据源） | Race | 独立数据源，无共享状态 |
| 跨模块功能开发（3+ 文件） | Stepwise | 有序依赖，需阶段验证 |
| PRD 编写 | Stepwise | 多阶段，前后依赖 |
| 安全审查 | Stepwise | 严格的阶段门禁 |
| 多人并行+编排调度 | Race/Stepwise 级联 | 外层 Stepwise，内层 Race fan-out |

---

## 输出

```yaml
recommended_mode: race|stepwise|direct
rationale: "选择理由（引用 execution-modes.md 对应章节）"

gates:
  race:
    entry:
      - "子任务 MECE 确认"
      - "每个子任务有完成标准"
      - "最大并发度 K 定义"
    per_subtask:
      - "完成标准验证"
      - "失败隔离+重试"
    exit:
      - "聚合报告生成"
      - "通过率 N/M 记录"

  stepwise:
    stage_entry:
      - "上一阶段 exit gate 确认"
      - "输入产物验证"
      - "回滚方案确认"
    stage_exit:
      - "exit 标准逐条验证"
      - "证据写入"
      - "跨阶段一致性检查"
    final:
      - "所有阶段完成"
      - "证据汇总"
      - "经验记录"

failure_handling:
  race:
    individual_failure: "隔离失败子任务，其余继续"
    lock_conflict: "指数退避重试（1s, 2s, 4s），3 次后跳过"
    mass_failure: ">50% 失败 → 继续但标记报告"
    misselection: "发现非独立 → 终止 Race，回退 Stepwise"

  stepwise:
    stage_retry: "单阶段最多重试 2 次"
    rollback: "触发回滚→重回上阶段 exit gate"
    re_plan: "重新规划剩余阶段"
    budget_exceeded: "3 次升级 → 终止全部执行"

mode_cascade:
  race_to_stepwise: "Race 子任务本身可以是 Stepwise 流程"
  stepwise_to_race: "Stepwise 某阶段可展开为 Race fan-out"
```

---

## 在 skill 中引用

在 SKILL.md 的原子化声明中添加：

```markdown
### 使用的通用节点
| 节点 | 路径 | 用途 |
|------|------|------|
| mode_selector | `../../nodes/mode_selector.md` | 执行模式选择 |
```

在 skill 逻辑中调用模式选择（Stage 0/前置检查）：

```markdown
### Step 0: 模式选择

加载 `@../../nodes/mode_selector.md`，输入当前任务特性：

```yaml
task_characteristics:
  count: {子任务数}
  dependencies: {independent|sequential}
  complexity: {low|medium|high}
```

根据输出 `recommended_mode` 路由：
- **race** → 执行 Race 流程（fan-out → collect → report）
- **stepwise** → 执行 Stepwise 流程（stage gate → advance）
- **direct** → 直接执行，跳过模式开销
```

---

## 与 orchestrator 集成

`lx-oma-orch` 调用 skill 前，通过本节点确定 mode：

1. 读取 skill 的 frontmatter `execution_mode` 字段
2. 根据 mode 自动挂载对应的 entry/exit gates
3. Race 模式 → 使用 `race_manager.sh` 跟踪子任务
4. Stepwise 模式 → 使用 `completion-gate.sh` + `plan-gate.sh` 验证阶段

---

## 现有 skill 模式一览

| execution_mode | skills | 公共门禁 |
|---------------|--------|---------|
| **race** | lx-oma-split, lx-race, lx-status | 子任务 MECE 检查, 聚合报告, 失败隔离 |
| **stepwise** | lx-browser-verify, lx-code-review, lx-debug-spec, lx-golang-test, lx-oma-gov, lx-oma-hier, lx-pre-commit, lx-pre-push, lx-prd, lx-react-review, lx-root-cause-analysis, lx-rpe, lx-security-review, lx-task-spec, lx-tdd-spec, lx-todo, lx-validate-skill, lx-varlock, lx-web-perf | 阶段 entry/exit, 回滚方案, 证据验证 |
| **stepwise** (hybrid) | lx-oma-orch | 外层 stepwise, 内部可 dispatch race |
