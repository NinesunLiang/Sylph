# 工具输出引用规则（全局强制）

## 引用顺序（每次工具输出均适用）

1. **原始引用**（≤3 行）：粘贴实际工具输出，不裁剪关键信息
2. **再进行解读**：从原始输出推导结论

### 示例（正确）

```
Tool: go test -race ./...Raw output: WARNING: DATA RACE Write at 0x... goroutine 12 Read at 0x... goroutine 15Interpretation: Concurrent write/read race detected; goroutine 12 and 15 share unprotected variable

```

### 示例（禁止）

```
"Tests show a race condition exists" ← 未引用原始输出。这是幻觉输出（E2 违规）。
```

## 反事实检查（每次引用后强制执行）

引用工具输出后，自问：> 如果这个工具输出为空或显示相反结果，我的结论还能成立吗？> - **能** → 证据不足，寻找更强证据> - **不能** → 证据是关键支撑，可以继续
**此检查的落地方式**：在 Phase 3 每层 Why 的格式中作为必填字段执行（见 Phase 3 Why 层格式中的"反事实验证"字段）。

## 截断输出处理

若输出包含任何截断标记（`...`、`truncated`、`> N lines`、`output omitted`）：
- 该证据维度分数自动扣 **-2 分**
- 若仍需使用 → 以更大输出限制重新执行工具（`-A 50` 或等效参数）
- 只引用重新执行后的完整输出

## 禁止行为

- 跳过原始输出直接给出结论（X17）
- 转述工具输出而不引用原文（E2 风险）
- 引用与当前调查不属于同一次工具运行的输出
- 在未执行工具的情况下假设输出内容（"我知道它会显示什么"）
