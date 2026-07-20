# Phase 3: 五层 Why + 证据链（核心）

加载置信度评分：`references/confidence-scoring.md` | Go 模式：`references/go-root-cause-patterns.md` | 工具引用规则：`references/tool-output-rules.md`

## 执行纪律

- Why 1-5 按顺序执行，不可跳过
- 每层格式：

```
Why [N]: [答案]
Tool: [命令]
原始输出（≤3 行）: [粘贴实际输出]
证据类型: [LSP/Grep/race/pprof/git/AST]
解读: [从输出得出的结论]
反事实验证: 若此工具输出为空或结果相反，本层结论是否仍成立？[否=证据有效 / 是=⚠️ 证据不足]
一致性: [✅ / ⚠️ 与 Why X 矛盾]
```

## 提前终止条件

置信度 ≥ 18/25 **且** 满足全部条件：
1. 根因指向可定位代码位置（file:line）
2. 修复方案不需要跨 package 变更
3. 至少 2 个独立证据源支持

不满足任一 → 继续下一层 Why。

## 置信度评分

5 维度 × 5 分 = 最高 25：证据强度 / 可复现性 / 跨系统一致性 / 设计可追溯性 / 防护可操作性

## 裁决

- ≥ 18/25 → 进入 Phase 4（18-20 需 2 个独立证据源交叉验证）
- 13-17 → Oracle 升级 → `references/oracle-escalation.md`
- < 13 → 中止

CP-3 检查点：故障链 → 断点 → 根因 → 置信度 → 修复目标 file:line
