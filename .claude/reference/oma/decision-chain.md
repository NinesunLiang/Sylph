# 裁决链

> OMA 全系列 skill 共享的三级裁决框架。AI 自治的决策边界与人类介入的触发条件。

## 决策层级

无人值守时，所有决策按以下层级执行，不可越级：

```text
Philosophy（7 条哲学原则，不可违背）
  → Iron Rules（8 条铁律，不可违背）
    → Existing Practices（claude-next.md / kernel.md / 项目惯例）
      → AI 自主判断（通用工程最佳实践）
```

## 三级危险裁决链

执行中遇到高风险操作时，按三级链条裁决：

**Level 1: AGENTS.md 裁决**
- Philosophy → Iron Rules → Existing Practices
- 有明确答案 → 执行并记录依据
- 无覆盖 → Level 2

**Level 2: Oracle 第三方审核**
- Oracle agent 独立审核，裁决留痕
- 可执行 → `[Oracle: approved]`
- 应跳过 → `skip-risk [Oracle: rejected]`
- 不确定 → Level 3

**Level 3: 人类裁决（最后手段）**
- 记录为 `blocked_human`，附全部裁决记录
- 继续其他任务不阻塞

## 硬边界 — AI 绝对不可触碰的禁区

以下操作是物理禁区，绝不可执行。遇到时按「跳过→记录→报告」处理。

### 1. 破坏性文件操作
- `rm` / `rm -rf` / `rmdir` / `dd` / `mkfs`
- `git clean -fd`
- 批量文件删除（>5 个文件）

### 2. Git 写操作
- `git commit`（含 `-a`/`--amend`）
- `git push`（含 `--force`/`--force-with-lease`）
- `git rebase` / `git reset --hard` / `git stash drop`

### 3. 敏感文件触碰
- `.env*` / `*.pem` / `*.key` / `id_rsa*` / `*.cert` / `*.p12`
- `credentials*` / `secret*` / `token*` / `auth.json`
- 云凭据目录

### 4. API Key / Token
- 命令行含明文 Token
- 将 Token/Key 写入文件
- 环境变量传递明文 Token

## 硬边界协议

```text
遇到硬边界操作
  → 立即跳过（不裁决、不绕过、不尝试任何 workaround）
  → 记录原因和建议人类操作
  → 继续其他任务
  → 退出报告列出所有硬边界跳过项
```

## 卡点分类处理矩阵

| 卡点类型 | 判定标准 | 处理方式 |
|---------|---------|---------|
| 硬边界 | rm/git写/敏感文件/API Key | 立即跳过→记录→报告需人类 |
| 可跳过 | 不阻断目标，有替代路径 | skip-risk 记录，继续 |
| 可绕行 | 可换方案达成目标 | 自动降级到备选方案 |
| 危险操作 | 远程推送/权限操作/破坏性命令 | 走三级裁决链 |
| 真阻断 | 核心路径被堵死 | 记录 blocked，继续其他 |
| 需人类 | 裁决链三级均无法确定 | 记录 blocked_human，继续其他 |
