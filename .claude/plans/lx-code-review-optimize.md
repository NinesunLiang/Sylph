# lx-code-review 优化方案

## 当前状态
- 73行: 15行 frontmatter + 58行 body（违反渐进式披露）
- 7个nodes引用 + 6个schemas引用 → 全部存在 ✅
- 3个OMA引用 → 全部存在 ✅
- Go代码审查: 8类39条规则

## 问题
body 58行占用 SKILL.md，每次加载skill都全量注入context。按CarrorOS skill体系，body应下沉到 references/body.md，SKILL.md只保留 frontmatter + 路由表。

## 方案
### 结构改造
```
lx-code-review/
├── SKILL.md           # 仅frontmatter + 路由（~20行）
├── references/
│   ├── body.md        # 原58行body内容（执行流程+状态机+降级策略）
│   ├── rules-catalog.md   # 39条规则（已存在）
│   └── auto-fix-templates.md  # 自动修复模板（已存在）
```

### 效果
- SKILL.md 从73行降到~20行（-72%）
- body按需加载（引用 references/body.md）
- 原有 rules-catalog 和 auto-fix-templates 不变

### 不动
- nodes/schemas/OMA引用不变
- 39条Go规则内容不变
- 状态机/执行流程/降级策略不变
- 心智模式不变

## 验证
- 所有引用路径正确（../../references/ → ../references/ 路径需验证）
- 所有节点路径正确（../../nodes/ → ../nodes/ 路径需验证）

## 审阅问题
1. 结构改造是否充分？
2. 还有没有其他优化点？
3. 是否可以直接执行？
