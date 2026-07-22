# 外部节点契约定义

lx-root-cause-analysis 依赖的5个外部节点及其输入/输出/失败行为。

## target_resolver

| 项目 | 定义 |
|------|------|
| 输入 | 症状描述、代码路径 |
| 输出 | 可疑代码文件:行号列表 |
| 依赖 | 项目代码库可读 |
| 失败行为 | 无匹配 → 降级全量扫描 |
| 引用路径 | `../../nodes/target_resolver.md` |

## context_collector

| 项目 | 定义 |
|------|------|
| 输入 | target_resolver 输出的文件列表 |
| 输出 | `{history_patterns, known_issues, change_log}` |
| 依赖 | git log / claude-next.md 可读 |
| 失败行为 | git不可用 → 返回空上下文 |
| 引用路径 | `../../nodes/context_collector.md` |

## report_generator

| 项目 | 定义 |
|------|------|
| 输入 | 全部 Phase 产物（症状/断点/Why链/置信度/修复） |
| 输出 | RCA 报告（verdict + schema 格式） |
| 依赖 | 至少 Phase1-3 完成 |
| 失败行为 | 部分缺失 → 标记 incomplete |
| 引用路径 | `../../nodes/report_generator.md` |

## behavior_rules

| 项目 | 定义 |
|------|------|
| 输入 | 研究阶段目标描述 |
| 输出 | 约束条件列表 |
| 依赖 | 无 |
| 失败行为 | 不适用 → 跳过 |
| 引用路径 | `../../nodes/behavior_rules.md` |

## verifier

| 项目 | 定义 |
|------|------|
| 输入 | finding 列表（含证据类型/置信度） |
| 输出 | `{verified: bool, confidence_adjustment: int, reasons: []}` |
| 依赖 | finding 数据完整 |
| 失败行为 | 超时 → 降级 warn，不阻断 |
| 引用路径 | `../../nodes/verifier.md` |
