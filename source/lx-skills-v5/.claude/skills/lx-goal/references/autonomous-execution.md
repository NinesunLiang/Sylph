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
