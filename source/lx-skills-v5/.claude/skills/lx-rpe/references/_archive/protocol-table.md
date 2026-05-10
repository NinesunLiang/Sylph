## 两端交互协议

| 交互内容 | 方向 | 触发时机 | Schema|
|---------|------|---------|--------|
|RPE 任务项 | OpenCode → Claude | Step 1 开始前 | `RPE-xxx [描述]`|
|设计方案 | Claude → OpenCode | Step 2 完成时 | 设计方案模板|
|实现摘要 | Claude → OpenCode | Step 5 | 文档 A 模板|
|测试方案 | Claude → OpenCode | Step 5 | 文档 B 模板|
|验收清单 | Claude → OpenCode | Step 5 | 文档 C 模板|
|验收报告 | OpenCode → Claude | Step 6 完成后 | 验收报告 Schema|
|buglist | OpenCode → Claude | 里程碑后 | `[#] [类型] [描述] [file:line]` |
