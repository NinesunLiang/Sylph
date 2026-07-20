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

**Level 2: Oracle 第三方审核** — Oracle agent 独立审核，裁决留痕。可执行 → [Oracle: approved]。应跳过 → skip-risk [Oracle: rejected]。不确定 → Level 3。

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

## 卡点分类处理矩阵

| 卡点类型 | 判定标准 | 处理方式 |
|---------|---------|---------|
| **硬边界** | rm / git写 / 敏感文件 / API Key | 立即跳过 → 记录 hard-boundary-hit → 报告需人类 |
| 可跳过 | 不阻断目标，有替代路径 | skip-risk 记录，继续 |
| 可绕行 | 可换方案达成目标 | 自动降级到备选方案 |
| 危险操作 | 远程推送/权限操作/破坏性命令 | 走三级裁决链 |
| 真阻断 | 核心路径被堵死 | 记录 blocked，继续其他 |
| 需人类 | 裁决链三级均无法确定 | 记录 blocked_human，继续其他 |

## Phase 1→N 全自动执行

### 核心铁律

1. **不暂停** — 不等待人类输入
2. **不提问** — 歧义按决策框架判断
3. **不中断** — 卡点处理后继续
4. **只记录** — 风险和阻断写入 skipped_risks

### 常见场景自主处理

| 场景 | 自主处理 |
|------|---------|
| 修复范围超预期 | 评估仍在目标内 → 继续，否则 skip-risk |
| 需安装依赖 | 能自动装则装，需管理员权限 → skip-risk |
| 远程推送 | commit 照常，push → 走裁决链 |
| Context Guard 阻断 | 创建 override 文件，改用 Bash |
| Permission Gate 拦截 | 走三级裁决链 |
| 发现无关问题 | 记入附带发现，不偏离主线 |
| 子任务冲突 | Philosophy #2 选择更高价值路径 |
| 硬边界触发 | 立即跳过 → hard-boundary-hit → 继续其他 |

| **L1→L2 就地升级** | 检测到 L1 任务在执行中触及敏感路径/不可逆操作/跨模块 → 走就地升级通道（见下方） |

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
