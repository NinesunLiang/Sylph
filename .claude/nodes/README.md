# 共享节点索引（v5 MVP）

> 10 个通用执行节点，按功能 + 使用频率分类。
> 目录内另有 3 个非通用节点文件：`a_terminal.md` / `b_terminal.md`（终端执行节点）、`orchestrator.md`（通用状态机参考，引用率 0，仅参考）——不占通用节点名额。
> 注：`generator.md` 已于 2026-10-23 物理删除（与 spec_generator 合并后无独立引用，见下方归档表）；部分 skill 文档中的 `nodes/generator.md` 链接为历史残留，待各自 skill 维护者清理。

---

## 按功能分类

### 输入处理（2 个）
| 节点 | 引用率 | 用途 |
|------|--------|------|
| [interactive_prompt.md](interactive_prompt.md) | 16/19 | 无参数时引导式问答 |
| [target_resolver.md](target_resolver.md) | 12/19 | 解析审查/分析/扫描目标 |

### 上下文收集（1 个）
| 节点 | 引用率 | 用途 |
|------|--------|------|
| [context_collector.md](context_collector.md) | 12/19 | 收集项目配置/已知问题/基线数据 |

### 扫描分析（1 个）
| 节点 | 引用率 | 用途 |
|------|--------|------|
| [scanner.md](scanner.md) | 8/19 | 按规则集并行扫描代码 |

### 执行修复（2 个）
| 节点 | 引用率 | 用途 |
|------|--------|------|
| [execute_node.md](execute_node.md) | 3/19 | 5-Why 根因 + 降级触发 + 3 轮修复上限 |
| [auto_fixer.md](auto_fixer.md) | 8/19 | P0/P1 自动修复 |

### 验证报告（2 个）
| 节点 | 引用率 | 用途 |
|------|--------|------|
| [verifier.md](verifier.md) | 8/19 | 修复后 re-scan 验证 |
| [report_generator.md](report_generator.md) | 12/19 | 结构化报告生成 |

### 行为约束（1 个）
| 节点 | 引用率 | 用途 |
|------|--------|------|
| [behavior_rules.md](behavior_rules.md) | 19/19 (100%) | 宪法铁律 + 修复上限 + 危险操作确认 |

### 生成（1 个）
| 节点 | 引用率 | 用途 |
|------|--------|------|
| [generator.md](generator.md) | 3/19 | Spec/AC/测试代码生成 |

---

## 按使用频率分类

### 必选（100% skills）
| 节点 | 用途 |
|------|------|
| [behavior_rules.md](behavior_rules.md) | 所有 skill 必须加载的行为约束 |

### 高频（>50% skills）
| 节点 | 引用数 | 用途 |
|------|--------|------|
| [interactive_prompt.md](interactive_prompt.md) | 16/19 | 引导式问答 |
| [target_resolver.md](target_resolver.md) | 12/19 | 目标解析 |
| [context_collector.md](context_collector.md) | 12/19 | 上下文收集 |
| [report_generator.md](report_generator.md) | 12/19 | 报告生成 |

### 中频（15-50% skills）
| 节点 | 引用数 | 用途 |
|------|--------|------|
| [scanner.md](scanner.md) | 8/19 | 扫描框架 |
| [auto_fixer.md](auto_fixer.md) | 8/19 | 自动修复 |
| [verifier.md](verifier.md) | 8/19 | 验证框架 |

### 低频（<15% skills）
| 节点 | 引用数 | 用途 |
|------|--------|------|
| [execute_node.md](execute_node.md) | 3/19 | 根因执行 |
| [generator.md](generator.md) | 3/19 | 代码/文档生成 |

---

## 节点选择指南

### 新建 skill 时

1. **必须加载**：`behavior_rules.md`
2. **无参数时加载**：`interactive_prompt.md`
3. **需要解析目标时加载**：`target_resolver.md`
4. **需要收集上下文时加载**：`context_collector.md`
5. **需要扫描代码时加载**：`scanner.md`
6. **需要修复时加载**：`auto_fixer.md`
7. **需要验证时加载**：`verifier.md`
8. **需要生成报告时加载**：`report_generator.md`
9. **需要根因分析时加载**：`execute_node.md`
10. **需要生成代码/文档时加载**：`generator.md`
11. **需要 Gate 判定时加载**：`gate_checker.md`
12. **参考状态机设计时阅读**：`orchestrator.md`

> 已删除节点（8 个：plan_node / a0_clarifier / spec_generator / fallback_exploration / fallback_framework / judge / mode_selector / oracle_terminal）与 gate_checker/orchestrator 的完整出处见 `../references/archived/nodes-retired-20261023.md`。
