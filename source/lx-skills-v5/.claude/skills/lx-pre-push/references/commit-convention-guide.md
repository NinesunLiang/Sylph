# Commit 规范管理指南

## 三步上手

### Step 1：学习你的规范（一次性）

```
bashpy
thon3 .claude/skills/lx-pre-push/scripts/commit_convention.py learn \ "feat(user): add phone login
- Support SMS verification
- Token refresh integration
Issue-ID: myproject#42"
```
脚本自动提取：type格式、scope格式、分隔符、header长度、footer键名。

### Step 2：校验待推送的 commits

```
bashpy
thon3 .claude/skills/lx-pre-push/scripts/commit_convention.py validate-batch \ --prod <线上版本commit-hash>
bashpython3 .claude/skills/lx-pre-push/scripts/commit_convention.py validate-batch \ --prod <线上版本commit-hash>

```

### Step 3：查看/删除规范

```
bash# 查看当前规范python3 .claude/skills/lx-pre-push/scripts/commit_convention.py show

# 删除规范（恢复无约束）python3 .claude/skills/lx-pre-push/scripts/commit_convention.py reset
```

## 无规范时的行为

未运行 `learn` → 校验直接通过（不阻断），输出提示建议设置规范。

## 规范存储位置

`.omc/state/commit-convention.json` — 项目级，可提交到版本库共享给团队。
