# OMA 铸造厂 — 一人成军的工业流水线

一个 400 行的 PRD 被扔进了铸造厂的入口。它不是完整的需求文档——它是一块原矿。lx-oma-hier 站在传送带前端，看了一眼原矿的纹理，开始画切割线。

"功能域 A：用户认证。功能域 B：数据同步。功能域 C..."

两个小时后，原矿变成了 7 块 Sub PRD，每块带着自己的接口契约、Mock 数据和依赖排序。lx-oma-split 接手，继续往下切——Sub PRD 变成 feature，feature 变成可独立开发的 RPE 包。

铸造厂没有 CEO。它只有一条传送带，和四个知道怎么切的匠人。

---

## 一条龙流水线

OMA 铸造厂的流水线分为四站：

```
lx-oma-hier (巨型 PRD → 按功能域拆分)
    ↓
lx-oma-split (Sub PRD → 按 feature 拆分)
    ↓
lx-oma-gov (治理：漂移检测、冲突裁决)
    ↓
lx-oma-orch (编排：管线推进、Oracle 门禁)
```

每站的产物流入下一站，每站有独立的输入/输出契约、Mock 数据、黑盒边界。

---

## 第一站：lx-oma-hier — 分层拆解师

她是铸造厂的入口。接收一个超大型 PRD（可能数百行），按功能域进行 MECE（Mutually Exclusive, Collectively Exhaustive）拆解。

关键约束：
- **黑盒原则**：每个 Sub PRD 不假设其他 Sub PRD 的内部实现——只定义接口契约
- **接口契约**：Sub PRD 之间通过明确的接口数据结构通信
- **Mock 数据**：每个 Sub PRD 附带 Mock 数据，允许并行开发
- **依赖排序**：明确哪些 Sub PRD 依赖哪些，提供开发顺序建议

分出 Sub PRD 后，她委托 lx-oma-split 继续向下拆解。

---

## 第二站：lx-oma-split — Feature 级的 MECE 拆解

他是铸造厂的核心引擎。从 lx-oma-hier 接收 Sub PRD，进一步拆解为 feature 级的 RPE（可独立开发、独立验证）。

每个 feature 获得独立的 `rpe/{sub_prd}/{feature}/` 目录，包含四份文件：
- `design.md` — 设计方案、选型理由
- `spec.md` — 接口规格、验收条件
- `executor.md` — 执行记录、进度跟踪
- `qa.md` — 验证报告、证据汇总

核心约束：**Feature 间必须 MECE 正交。** 一个功能点不能出现在两个 feature 的 scope 中。但共享依赖（如通用工具函数）必须明确归属于某个 feature，不得遗漏。

---

## 第三站：lx-oma-gov — PRD 治理官

他是铸造厂的"纪委"。当主 PRD 发生变更时，他检测每个 Sub PRD 和 feature 是否与上游产生了**漂移**。

三种漂移类型：
1. **主 PRD 变更** → Sub PRD 未同步 → 冲突
2. **Feature 实现偏离 spec** → 实现漂移
3. **多 feature 间的接口契约破裂** → 集成漂移

漂移检测后，lx-oma-gov 支持 reconcile（合入上游变更）和 propagate（向下游传播变更）。当自动合入无法裁决时——触发**人工冲突裁决**，提交给用户决定。

---

## 第四站：lx-oma-orch — 管线编钟

他是铸造厂的指挥。不在流水线上做具体加工——他管理**管线本身**。

状态查看：当前哪个 Sub PRD 处于哪个阶段？哪个 feature 在开发中？哪个在 Oracle 审查？
管线推进：当前阶段完成 → 检查 Oracle 门禁 → 推进到下一阶段
并行管理：哪些 feature 可以并行开发？哪些互相阻塞？

Oracle 门禁是双重的：方案审核（进入执行前）和终审（执行完成后）。两者都必须通过，但不通过不是失败——不通过意味着回到上一阶段，带着 Oracle 给出的具体问题和改进方向。

---

## 铸造厂的地下设施

流水线之上的三个基础设施支撑着整个 OMA 体系：

### oma_lock_manager.py — 分布式写锁

多个 AI 实例并行编辑文件时，如何防止互相踩踏？

oma_lock_manager.py 实现了基于文件系统的分布式锁，使用 `os.rename(tmp_file, lock_file)`——POSIX 原子操作，避免了 unlink + O_EXCL 两步操作的 TOCTOU 竞争窗口（rpe-014 教训）。

生命周期：`acquire → heartbeat（定期续约）→ release`

锁过期时，下一个请求者检测超时 → 原子替换锁文件 → 写后读验证所有权。只有唯一赢家。

### pretool-write-lock + posttool-write-lock — 锁的钩子执行者

pretool-write-lock 在每次 Edit/Write 前调用 oma_lock_manager 获取写锁。如果锁被其他终端持有——等待或放弃。posttool-write-lock 在操作完成后释放锁。

这两个 hook 是整个 OMA 并发安全的物理保障。

### race_manager.sh — 蜂群协调引擎

当一个 OMA 阶段的多个 feature 可以并行开发时，race_manager.sh 充当蜂群的协调器：

`register → dispatch（分发给多个并行 agent）→ collect（收集结果）→ report（汇总报告）`

它不做调度引擎——只做协调。子任务的调度由底层的 team skill 执行，race_manager.sh 关注的是**结果的一致性**：多个并行 feature 的输出之间，有没有遗漏的交互点？有没有重复的功能点？

---

## 可观测性

oma_lock_manager.py 使用 `tmp + os.rename` 原子写入 JSON 状态文件，确保并发读取端始终看到完整内容——不是部分写入的破碎 JSON。这是 rpe-014 的两条锁相关教训的产物。

铸造厂的每一条管道、每一个阀门，都输出结构化状态，可被 lx-oma-orch 的状态查看器实时读取。

---

## 为什么叫 OMA？

一人成军，不是 AI 一个人完成所有工作——是**一个协议体系**让多个人（多个 AI 实例、多个用户、多个终端）像一个人一样协同。

OMA 铸造厂不追求"一个超级 AI 搞定一切"。它追求的是：把大目标拆成小步骤，让每一步的执行者不必理解全局，只需遵守接口契约。

这是软件工程的基本原则，投射到 AI 辅助开发的世界中。而铸造厂里最安静的时刻，是传送带上只有一块 Sub PRD 在移动——四个匠人站在各自的工位上，没人说话，但流水线在转。

---

## 相关故事

- [双生之子](story-08.md) — lx-ghost/lx-goal 与 OMA 锁的协作：自主模式下写锁仍然生效
- [三重门神谕](story-11.md) — lx-oma-orch 管线上的 Oracle 门禁
- [圣器锻造所](story-14.md) — lx-rpe/lx-prd 是 OMA 流水线的下游执行工具
