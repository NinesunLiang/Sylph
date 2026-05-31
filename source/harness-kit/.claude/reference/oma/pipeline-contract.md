# Pipeline 更新契约

## 原子写入

写 tmp 文件 → `os.rename(tmp, pipeline.yaml)`（参考 RPE-014 教训）。

## 更新规则

```yaml
# stages.{stage}: running → completed
# sub_prds[].status: 推进到下一状态
# features[].stage: 推进到下一状态
# oracle_gates[].status: 新 gate → pending
```

## Oracle gate 创建

子 skill 完成时检查是否需要创建新 Oracle gate。需要 → 创建 gate 条目并记录到 pipeline.yaml。
