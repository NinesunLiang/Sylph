# Commit 规范（lx-rpe Step 8 加载）

## 格式

```<type>(<scope>): <RPE-task-id> <描述>
<type>(<scope>): <RPE-task-id> <描述>
```

## type 允许值
| type | 适用场景|
|------|---------|
|feat | 新功能、新接口|
|fix | Bug 修复|
|refactor | 重构（不改功能）|
|docs | 文档更新|
|test | 测试补充|
|chore | 构建/依赖/配置 |\|

## 规则
- scope 可选，填模块名（如 `user`、`auth`、`handler`）- 描述：祈使句，≤50字符，不加句号- RPE task ID 必须包含（如 `RPE-003`）- 禁止 `git add -A`，逐文件暂存

## 示例

```fea
t
(user): RPE-003 新增手机号登录接口fix(auth): RPE-007 修复 JWT token 过期未刷新问题refactor(handler): RPE-012 拆分 QueryHandler 减少耦合
feat(user): RPE-003 新增手机号登录接口fix(auth): RPE-007 修复 JWT token 过期未刷新问题refactor(handler): RPE-012 拆分 QueryHandler 减少耦合
```
