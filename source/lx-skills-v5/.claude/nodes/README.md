# 共享节点索引（v5 MVP）

> 12 个通用执行节点，按功能 + 使用频率分类

---

## 按功能分类

### 输入处理（2 个）| 节点 | 引用率 | 用途 |

|------|--------|------|
| [interactive_prompt.md](interactive_prompt.md) | 16/19 | 无参数时引导式问答 |
| [target_resolver.md](target_resolver.md) | 12/19 | 解析审查/分析/扫描目标 |

### 上下文收集（1 个）| 节点 | 引用率 | 用途 |

|------|--------|------|
| [context_collector.md](context_collector.md) | 12/19 | 收集项目配置/已知问题/基线数据 |

### 扫描分析（1 个）| 节点 | 引用率 | 用途 |

|------|--------|------|
| [scanner.md](scanner.md) | 8/19 | 按规则集并行扫描代码 |

### 执行修复（2 个）| 节点 | 引用率 | 用途 |

|------|--------|------|
| [execute_node.md](execute_node.md) | 3/19 | 5-Why 根因 + 降级触发 + 3 轮修复上限 |
| [auto_fixer.md](auto_fixer.md) | 8/19 | P0/P1 自动修复 |

### 验证报告（2 个）| 节点 | 引用率 | 用途 |

|------|--------|------|
| [verifier.md](verifier.md) | 8/19 | 修复后 re-scan 验证 |
| [report_generator.md](report_generator.md) | 12/19 | 结构化报告生成 |

### 行为约束（1 个）| 节点 | 引用率 | 用途 |

|------|--------|------|
| [behavior_rules.md](behavior_rules.md) | 19/19 (100%) | 宪法铁律 + 修复上限 + 危险操作确认 |

### 生成（1 个）| 节点 | 引用率 | 用途 |

|------|--------|------|
| [generator.md](generator.md) | 3/19 | Spec/AC/测试代码生成 |

### 门禁判定（1 个）| 节点 | 引用率 | 用途 |

|------|--------|------|
| [gate_checker.md](gate_checker.md) | 2/19 | Gate 判定（安全/推送门禁） |

### 状态机参考（1 个）| 节点 | 引用率 | 用途 |

|------|--------|------|
| [orchestrator.md](orchestrator.md) | 0（参考） | 通用状态机参考实现 |

---

## 按使用频率分类

### 必选（100% skills）| 节点 | 用途 |

|------|------|
| [behavior_rules.md](behavior_rules.md) | 所有 skill 必须加载的行为约束 |

### 高频（>50% skills）| 节点 | 引用数 | 用途 |

|------|--------|------|
| [interactive_prompt.md](interactive_prompt.md) | 16/19 | 引导式问答 |
| [target_resolver.md](target_resolver.md) | 12/19 | 目标解析 |
| [context_collector.md](context_collector.md) | 12/19 | 上下文收集 |
| [report_generator.md](report_generator.md) | 12/19 | 报告生成 |
| [scanner.md](scanner.md) | 8/19 | 扫描框架 |
| [auto_fixer.md](auto_fixer.md) | 8/19 | 自动修复 |
| [verifier.md](verifier.md) | 8/19 | 验证框架 |

### 中频（15-50% skills）| 节点 | 引用数 | 用途 |

|------|--------|------|
| [execute_node.md](execute_node.md) | 3/19 | 根因执行 |
| [generator.md](generator.md) | 3/19 | 代码/文档生成 |

### 低频（<15% skills）| 节点 | 引用数 | 用途 |

|------|--------|------|
| [gate_checker.md](gate_checker.md) | 2/19 | Gate 判定 |
| [orchestrator.md](orchestrator.md) | 0 | 状态机参考 |

---

## 已删除节点（6 个，Oracle 评审 P0）

| 原节点 | 删除理由 |
|--------|---------|
| `plan_node.md` | 0 引用，规划逻辑内联到 skill |
| `a0_clarifier.md` | 0 引用，澄清合并到 interactive_prompt |
| `spec_generator.md` | 0 引用，generator.md 已覆盖 |
| `fallback_exploration.md` | 0 引用，降级触发在 execute_node 中 |
| `fallback_framework.md` | 0 引用，同上 |
| `judge.md` | 0 引用，verdict schema 已定义判定结构 |

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
1
0. **需要生成代码/文档时加载**：`generator.md`
1
1. **需要 Gate 判定时加载**：`gate_checker.md`
1
2. **参考状态机设计时阅读**：`orchestrator.md`
