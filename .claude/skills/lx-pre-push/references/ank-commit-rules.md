# ank-commit-rules.md
# ANK Commit 规范（Aligned · Named · Known）
# Referenced by: lx-pre-push Gate 0

## 格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

## 类型
| Type | 用途 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| refactor | 重构（不新增功能也不修 bug） |
| docs | 仅文档变更 |
| test | 添加/修改测试 |
| chore | 构建/工具/依赖变更 |
| perf | 性能优化 |
| style | 代码格式（非语义变更）|

## Scope（按项目）
- `oma`: OMA 编排/拆解相关
- `rpe`: RPE 特性开发相关
- `gov`: 治理相关
- `hook`: Hook 脚本
- `doc`: 文档
- `test`: 测试
- `core`: 核心架构

## 规则
1. subject 不超过 72 字符
2. 祈使句开头（Add/Fix/Refactor 而非 Added/Fixed/Refactored）
3. body 说明 why 而非 what
4. footer 标注 Breaking Change（如有）
