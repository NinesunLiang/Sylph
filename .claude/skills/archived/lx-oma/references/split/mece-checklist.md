# MECE 正交拆解原则

运用顶级架构师思维，将需求拆解为 N 个 Feature（通常 3-6 个）：

- **相互独立**：Feature 间职责清晰分离，减少终端同时修改同一文件的概率
- **完全穷尽**：所有 Feature 拼在一起完整实现原始 PRD

## MECE 自检清单

### 正交性
- [ ] 每个 feature 的"负责"条目不与其他 feature 重叠
- [ ] 没有两个 feature 同时 Own 同一实体
- [ ] 接口在 feature 间无重复定义

### 完整性
- [ ] 所有 Sub PRD 接口已分配到某个 feature
- [ ] 所有 Sub PRD 实体已分配到某个 feature
- [ ] Sub PRD 中每个功能场景至少被一个 feature 覆盖

### 独立性
- [ ] 每个 feature 可独立绑定 Mock 数据验证
- [ ] feature 间依赖关系是 DAG（无循环依赖）
- [ ] 依赖图中"被依赖"最多的 feature ≤3 个下游
