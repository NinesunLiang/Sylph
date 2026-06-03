# 接口归属完整性校验（阻断门禁）

> 拆解完成后强制执行，不修复不得跳过。

## 执行序列

```
1. 调用校验脚本:
   python3 .claude/scripts/verify_oma_interface_coverage.py \
     sub-prds/domain-{sub_prd_name}.md

2. exit code:
   ├─ 0 → ✅ 全部接口/事件有归属 → 继续
   └─ 1 → ❌ 存在未归属缺口 → 阻断

3. 修复（exit 1）:
   a. 分析接口流向 → 确定归属 feature
   b. 追加到对应 feature prd.md
   c. 重新执行 → exit 0
```

## 校验规则

| 检查项 | 通过标准 | 阻断条件 |
|--------|---------|---------|
| 所有接口有归属 | 命中率 100% | exit 1 |
| 命名严格一致 | Sub PRD 名称 == feature 名称 | exit 1 |
| 无 phantom 接口 | feature 不声明 Sub PRD 未定义的接口 | ⚠️ 警告不阻断 |

## 完成标准
- ✅ 校验脚本 exit 0
- ✅ 未归属接口已分配到 feature
- ✅ 命名与 Sub PRD 完全对齐
