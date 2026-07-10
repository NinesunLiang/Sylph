# Oracle 路线决策记录（草案）

> Status: draft | 待人类裁决 | Module: oracle

## 现状

当前 Oracle 体系全部为 **static_stub**：

| 脚本 | 等级 | 说明 |
|------|------|------|
| oracle_engine.py | static_stub | 静态启发式评分，7 维度扣分 |
| oracle_gate.py | static_stub | 5 点静态触发门 |
| oracle_agent.py | static_stub | 文件分析 + 规则 |
| meta_oracle.py | static_stub | 聚合静态 + 运行时裁决 |
| static_oracle_agent.py | static_stub | 文件证据分析 |
| runtime_oracle_agent.py | static_stub | 运行时证据分析 |
| oracle_spawn.py | static_stub | 子进程编排 |

所有脚本均在文件头标注 `⚠️ 实现等级: static_stub`。

## 选项分析

### 选项 A：维持 static_stub，改名 Static Oracle

放弃"真实 Oracle 高阶复核"的说法，改为：
- 更名所有文件 `static_oracle_engine.py` 等（消除名称误导）
- 继续做 lint 级静态分析
- 不接入模型 API

**优点**：零额外成本、低延迟、零故障点
**代价**：永远不是设计文档中描述的"高阶模型语义复核"

### 选项 B：接入模型 API，成为真实语义复核

基础设施已存在：
- `localhost:8765` Adapter Server 可调用 `gpt-5.5`、`opus-4.8` 等
- 只需在 `oracle_engine.py` 或新 `model_oracle.py` 中添加 HTTP 调用

接入路径：
1. 新 `model_oracle.py` — 只做 API 调用 + 结果解析
2. `oracle_engine.py` 检测模型可用性 → 可用则调用 model_oracle → 不可用降级 static_stub
3. 审计日志记录 `调用模型 / 降级为static`

**优点**：对齐设计文档、真正高阶复核、差异化能力
**代价**：API 成本、网络延迟、失败降级处理、配额管理

## 建议

**推荐选项 B（有条件）：*
- 先做 Option A（改名 + 稳定 static_stub）作为 BASE
- Option B 作为 ENHANCE 特性，仅 L2 任务触发
- 不分叉代码，用配置/检测切：`model_oracle.py` 检测到 API 可用则启用，不可用则静默降级 static_stub
- 成本通过 QuotaConfig（`quota.py` 现有）控制，防止意外大量调用

## 人类裁决（2026-07-09）

- [ ] 走 Option A（一直保持 static_stub）
- [ ] 走 Option B（接入模型，降级式架构）
- [ ] 先 A 后 B 按 BASE/ENHANCE 分
- [x] **不走任何选项 — 模型 API 是私人"挂"，不是 CarrorOS 组件**

## 决定

模型 API（GPT-5.5/Opus-4.8 adapter on port 8765）是私人临时工具，不接入 CarrorOS 治理体系。CarrorOS 内的 Oracle 保持 static_stub，按现有标注运行。

后续影响：
- CarrorOS 不依赖 adapter_server 运行
- Oracle 能力公布为 static_stub（已如实标注）
- 不存在降级问题（因为从未接入）
- 未来如需高阶复核，走 AGENTS.md Oracle skill（lx-oracle-agent / lx-oracle-meta / lx-oracle-review），由子 Agent 自行调用模型。这不属于 CarrorOS 治理机制，不改变代码
