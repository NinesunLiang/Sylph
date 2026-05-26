# explore — 文件发现与内容读取

> 通用执行节点。读取文件/目录，识别核心实体。
> hier 用其读取 PRD 并识别业务实体，gov 用其扫描 feature 目录。

## 输入

```yaml
target: string          # 文件路径或目录路径
entity_hint: string     # 可选，提示要识别的实体类型（如"业务实体"/"feature 目录"）
depth: 1|2|3            # 目录扫描深度，默认 1
```

## 流程

1. **路径检测**：文件 → 直接读取；目录 → 扫描 `*.md`；不存在 → 报错
2. **内容读取**：读所有目标文件内容
3. **实体识别**：根据 entity_hint 提取关键实体名称和候选归属
4. **输出实体清单**

## 输出

```yaml
type: file | directory
files_read: int
entities:
  - name: string
    source: "file:line"
    candidate_domain: string | null
```

## 边界

| 不做 | 原因 |
|------|------|
| 内容分析/语义理解 | 那是调用方 skill 的职责 |
| 写入任何文件 | 只读节点 |
