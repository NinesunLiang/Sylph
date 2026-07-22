# lx-code-review 去Go化方案

## 问题
当前 lx-code-review 是 Go 专项（39条Go规则），违反 CarrorOS skill "不指定语言、不指定领域"的通用性原则。

## 方案：去Go化

### 结构改造
```
lx-code-review/
├── SKILL.md                 # 通用: "代码审查"，不写Go
├── references/
│   ├── body.md              # 通用审查流程（编译检查+测试运行+明显bug识别）
│   ├── rules-general.md     # 通用规则（语言无关: 空指针/资源泄漏/硬编码/日志规范）
│   ├── rules-go.md          # Go专项39条（原rules-catalog.md，按需加载）
│   └── auto-fix-templates.md  # 通用修复模板
```

### 加载策略
- 项目检测到 Go（go.mod 存在）→ 自动引用 rules-go.md
- 非 Go 项目 → 只加载 rules-general.md
- 通用流程（编译检测/测试运行/明显bug/空指针）→ 始终可用，不依赖语言

### 不动
- nodes/schemas/OMA 引用不变
- 状态机/执行流程/降级策略不变
- auto-fix-templates.md 去Go化（保留通用模板，Go模板放rules-go的同级引用）

## 审阅问题
1. 结构设计是否合理？
2. `rules-general.md` 应该包含哪些通用规则？
3. 自动检测语言（go.mod/pom.xml/package.json）还是通过参数传递？
