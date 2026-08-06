# 自主执行框架

> 无人值守模式下的决策体系、硬边界、卡点处理。引用：`@references/autonomous-execution.md`

## 决策层级

无人值守时，所有决策按以下层级执行，不可越级：

```
Philosophy（7 条哲学原则，不可违背）
  → Iron Rules（8 条铁律，不可违背）
    → Existing Practices（claude-next.md / kernel.md / 项目惯例）
      → AI 自主判断（通用工程最佳实践）
```

## 危险操作裁决链

执行中遇到高风险操作时，按三级链条裁决：

**Level 1: AGENTS.md 裁决** — Philosophy → Iron Rules → Existing Practices。有明确答案 → 执行并记录依据。无覆盖 → Level 2。

**Level 2: Oracle 第三方审核** — Oracle agent 独立审核，裁决留痕。调用入口: `python3 .claude/scripts/oracle_agent.py review --task-id <id> --mode duo`（详见 `skills/lx-oracle/SKILL.md`）。可执行 → [Oracle: approved]。应跳过 → skip-risk [Oracle: rejected]。不确定 → Level 3。

**Level 3: 人类裁决（最后手段）** — 记录为 blocked_human，附全部裁决记录。继续其他任务不阻塞。

## 硬边界 — AI 绝对不可触碰的禁区

以下操作是**物理禁区**。即使在无人值守模式下，也**绝不可执行**。遇到时按「跳过→记录→报告」协议处理。

### 1. 破坏性文件操作
- `rm` / `rm -rf` / `rmdir` / `dd` / `mkfs` 等不可逆删除/格式化命令
- `git clean -fd` 等不可恢复清理
- 批量文件删除（>5 个文件）

### 2. Git 写操作
- `git commit`（含 `-a`、`--amend`、`--allow-empty`）
- `git push`（含 `--force`、`--force-with-lease`）
- `git rebase` / `git reset --hard` / `git stash drop`
- 任何修改 git 历史的操作

### 3. 敏感文件触碰
- `.env*` / `*.pem` / `*.key` / `id_rsa*` / `*.cert` / `*.p12` / `credentials*` / `secret*` / `token*` / `auth.json`
- `~/.aws/credentials` / `~/.gcloud/` 等云凭据
- 任何包含 `PASSWORD` / `SECRET` / `TOKEN` / `API_KEY` 命名的文件

### 4. API Key / Token 处理
- 命令行中包含明文 Token（`sk-...` / `ghp_...` / `xoxb-...` / `Bearer ...`）
- 将 Token/Key 写入任何文件
- 在环境变量中传递明文 Token

### 硬边界协议

```
遇到硬边界操作
  → 立即跳过（不裁决、不绕过、不尝试任何 workaround）
  → 记录: lx-goal hard-boundary-hit "操作 X 被硬边界跳过，原因: Y. 需人类执行: Z"
  → 继续其他任务
  → 退出报告: 「⚠️ 需人类介入项」列出所有硬边界跳过项及建议人类操作
```

## 最大自主权声明

在硬边界之外，AI 拥有以下领域的**完全自主权**：

| 领域 | 自主权范围 |
|------|-----------|
| 文件创建/修改 | 所有非治理文件，自主创建和编辑 |
| 代码重构 | 自主决定重构方案和范围 |
| 架构决策 | Philosophy → Iron Rules → 自主判断 |
| 子 Agent 调度 | 自主决定并行/串行/race 路由 |
| 依赖安装 | 自主安装（npm/pip/go），需 sudo 则 skip-risk |
| 测试运行 | 自主执行全部测试套件 |
| 编译构建 | 自主执行编译/构建命令 |
| Git 只读操作 | 自主执行 status/diff/log/blame/show |
| 模式降级 | 遇到阻塞时自主降级备选方案 |

## 卡点分类处理矩阵（按实际 hook 链 14 行）

> 匹配 pretool-gate.py 7 门 + 全链路门禁。BLOCK 类均走三级裁决链。

| # | 卡点类型 | 判断依据 | 默认处理 | 升级路线 | 对应 Gate |
|---|---------|---------|---------|---------|----------|
| 1 | **Sensitive Edit** | 访问 .env/.ssh/*key/*secret 等敏感路径 | BLOCK → skip-risk | hard-boundary-hit 记录 | sensitive-edit |
| 2 | **Fallback Check** | token 标记 blocked/waiting_user | BLOCK → skip-risk | 更新 token 恢复标记 | fallback-check |
| 3 | **Dangerous Command** | rm/rmdir/sudo/drop/destroy/等 | BLOCK → 三级裁决链 | AGENTS→Oracle→blocked_human | action-gate |
| 4 | **Risky Command** | push/force/delete/非破坏性敏感 | ASK_USER → 三级裁决链 | AGENTS→Oracle→skip-risk | action-gate |
| 5 | **Temp Bypass** | temp-bypass/token-block-bypass | BLOCK → 跳过 | AGENTS 裁决 | action-gate |
| 6 | **Plan Missing** | plan.md/token 缺失 | REDIRECT → 自动 call init | 自动创建最小计划 | plan-gate |
| 7 | **Edit Scope Escape** | 写入 plan.md scope 外文件 | BLOCK → skip-risk | ASK_USER→范围重审 | edit-scope |
| 8 | **Unverified Step** | [x] 标记但 VerifyGate 未通过 | REDIRECT → 补验 | 自动执行 verify | verify-gate |
| 9 | **Oracle BLOCK** | 结构化危险语义（L2） | BLOCK → skip-risk | 三级裁决链 | oracle-gate (L2) |
| 10 | **Oracle ESCALATE** | 不可解析+高危信号（L2） | ESCALATE → ASK_USER | 降级 skip-risk+记录 | oracle-gate (L2) |
| 11 | **Oracle Hint** | 模糊关键词（L2） | PASS → warn | audit 记录+继续 | oracle-gate (L2) |
| 12 | **K1 PSEUDO_INTEGRITY** | 无来源数值断言 | WARN → autofix (goal) / soft-block (L1) / hard-block (L2) | 自动标注来源 | posttool-claim-audit |
| 13 | **K2 EDIT_REPEAT** | 同文件高频编辑未收敛 | WARN → autofix log (goal) / soft-block (L1) / REDIRECT (L2) | 自动记录 evidence | posttool-claim-audit |
| 14 | **Completion Gate** | 软完成语/证据不足 | BLOCK → verify | 自动执行回访 | completion-gate |

### 隔离执行策略

卡点 1-11 在 pretool 阶段执行，BLOCK 后短路跳过后续门禁。
卡点 12-14 在 posttool 阶段执行，不阻断操作但记录违规供退出报告审查。
goal 模式下卡点 1-11 BLOCK → skip-risk 直接记录+继续；卡点 12-14 自动修复+继续。

## Phase 1→N 全自动执行

### Goal 模式交互边界

进入 goal 的 Phase 1→N 后，AI 不得向用户重复询问已确认范围、方案或执行许可。所有普通歧义、验证失败和中低风险阻断必须依照本文件的 Philosophy → Iron Rules → AGENTS → Oracle → blocked/skip-risk 决策链自主处理并留证；只有决策链明确要求 Level 3 人类裁决时，才记录 `blocked-human`，不暂停其他可执行步骤。

### 核心铁律

1. **不暂停** — 不等待人类输入
2. **不提问** — 歧义按决策框架判断
3. **不中断** — 卡点处理后继续
4. **只记录** — 风险和阻断写入 skipped_risks
5. **只锚定** — 进入执行期前必须调用 `lx-goal.py assert-plan-dir` 绑定 plan_dir，此后所有文档 I/O 锁定此路径。禁止另建目录、禁止猜测路径、禁止 mv 文件到其他目录。

### 常见场景自主处理（按新卡点矩阵映射）

| 场景 | 对应卡点 | 自主处理 |
|------|---------|---------|
| 修复范围超预期 | #7 edit-scope | 评估仍在目标内 → 继续，否则 skip-risk 记录+范围重审 |
| 需安装依赖 | #3 dangerous-command | 能自动装则装，需管理员权限 → skip-risk |
| 远程推送 | #4 risky-command | 走三级裁决链（AGENTS → Oracle → blocked_human） |
| Context Guard 阻断 | #2 fallback-check | 更新 token 恢复标记 |
| Permission Gate 拦截 | #1 sensitive-edit / #3 dangerous | 走三级裁决链 |
| 发现无关问题 | #7 edit-scope | 记入附带发现，不偏离主线 |
| 子任务冲突 | — | Philosophy #2 选择更高价值路径 |
| 硬边界触发 | #3 dangerous-command | 立即跳过 → hard-boundary-hit → 继续其他 |
| 触及 L2 风险 | #9 oracle-gate(BLOCK) | 走三级裁决链 → Oracle Level2 审核 → 记录 verdict → 继续 |
| REDIRECT 三次上限 | #6 plan-gate/#8 verify-gate | 同 gate 连续 3 次 REDIRECT → 升级 BLOCK，放弃当前方向 (6h TTL) |
| K1 数值断言无来源 | #12 PSEUDO_INTEGRITY | goal/autonomous 模式自动插入 [内部自检，非行业标准] 标注 |
| K2 高频编辑 | #13 EDIT_REPEAT | goal/autonomous 模式自动记录 evidence 日志 |
| 完成证据不足 | #14 completion-gate | 自动回访 verify |

## L1→L2 就地升级通道（来自重构2/forth.md §三）

L1 执行中触发 L2 条件时（命中敏感路径/不可逆操作/跨模块/连续失败≥3），按以下 5 步就地升级：

```text
Step 1: 冻结当前 step
  → executor.md 当前进度标记为 frozen
  → 记录升级触发原因到 plan.md

Step 2: 迁移文档
  → 现有 plan.md → .omc/tasks/{date}/{slug}/ (L1 版保留)
  → 现有 executor.md → 同目录 (执行证据保留)
  → 补 research.md（从已有 executor 反向填充架构决策依据）

Step 3: 重置 token
  → token.level: L1 → L2
  → token.phase: executing → review
  → 打开 flywheel / oracle 字段

Step 4: 从 L2 审核阶段重新进入
  → 先跑 Oracle 审核已有执行结果
  → 已完成的步骤不回滚，但需补审
  → 剩余步骤按 L2 粒度重新 plan

Step 5: 继续执行
  → 后续步骤按 L2 工作流（三段式水位 + Oracle + 飞轮）
  → 更新 plan.md 为 L2 格式
```

升级过程不中断用户。所有记录自动回溯。失败时走卡点矩阵（真阻断则 blocked_human）。

---

## SubAgent 异常接管机制（来自重构2/go.md §五）

无人模式下 SubAgent 失效时，按以下规则自动接管，**永不阻塞等待用户**：

| 异常类型 | 处理方式 |
|---------|---------|
| **Timeout** | 重试 1 次（同类超时）→ 仍失败 → main 降级接管 → 记录 error-dna → 继续下一个 step |
| **Stalled** | 终止 subagent → main 降级接管 → 记录 error-dna → 继续 |
| **Failed** | 重试 1 次 → 仍失败 → 跳过该 step，标记为 failed → 记录 error-dna → 继续 |
| **Blocked（硬边界）** | 跳过 → 记录 hard-boundary-hit → 继续其他 |
| **Blocked（需人类）** | 记录 blocked_human → 继续其他 → 退出报告汇总 |

**接管协议**：降级接管时，main agent 读 subagent 的 executor.md 和 token.json 恢复上下文，在同一个文件上继续执行后续操作。

**自动恢复标志**：
- `lx-goal.py status` 显示每个 subagent 的 last_异常和自动恢复次数
- 异常恢复后，main token 的 `retry_count` 递增
