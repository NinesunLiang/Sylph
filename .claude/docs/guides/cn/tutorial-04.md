# T04 — 武器目录

> 📍 我有哪些武器 | [← T03](tutorial-03.md) | 下一篇：[T05 自主执行](tutorial-05.md) →

26 个技能，按用途分类。选对武器比用好武器重要 10 倍。

## 日常工作流

| 场景 | 用这个 | 一句话 |
|------|--------|--------|
| 随手修 1-3 个文件 | `/lx-todo` | 5 步闭环：捕获→修复→验证 |
| 中等任务，3-10 个文件 | `/lx-task-spec` | 3 问引导 → 结构化执行 |
| 完整 feature | `/lx-rpe` | 9 步：TDD→审查→验收→回滚 |
| 要不要一步步来 | `/lx-stepwise` | 原子级拆分，步步 VERIFIED |
| 交代码前 | `/lx-pre-commit` | 编译→测试→代码审查 |
| 推送前 | `/lx-pre-push` | commit校验→覆盖分析→安全扫描 |
| 看看状态 | `/lx-status` | Token节省/任务通过率/拦截错误 |
| 生成测试 | `/lx-test-gen` | 语言无关，自动路由 |
| 审查代码 | `/lx-code-review` | 8 类别 39 条规则 |

## 选武器法则

```
问题出现了
  ├─ 1-3 个文件，无 spec → /lx-todo
  ├─ 3-10 个文件，有验收条件 → /lx-task-spec
  ├─ 原子级步步验收 → /lx-stepwise
  └─ 完整 feature → /lx-rpe
```

**不要对完整 feature 用 /lx-todo。也不要对随手修复开 /lx-rpe。**

---

← [T03 亲手配置](tutorial-03.md) | 下一篇：[T05 自主执行](tutorial-05.md) →
📖 深入：[技能目录](skills-catalog.md)
