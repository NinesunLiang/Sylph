# 根因置信度评分

## 评分标准（满分 25 分）
完成每个 Why 层级后，对各维度打 1-5 分。最终分数决定后续动作。
| 维度 | 1（弱） | 3（中） | 5（强）|
|------|---------|---------|---------|
|**证据强度** | 仅代码推测 | Grep/日志匹配 | LSP/`-race`/`pprof` 确认|
|**可复现性** | 仅理论 | 部分复现（间歇性） | 已创建最小复现脚本|
|**跨系统一致性** | 仅单点 | 2 个模块受影响 | 多个模块/服务确认|
|**设计可追溯性** | 无记录 | 找到相关 commit | 定位到确切 PR/架构决策|
|**防御可行性** | 仅"加强培训" | 部分 Go 防御（单层） | 完整 Go 防御：interface + context + sync |

## 分数阈值
| 分数 | 动作|
|------|------|
|≥ 18 | 进入 Phase 4|
|18-20（边界区） | 必须有 2 个独立证据来源交叉验证|
|13-17 | 升级至 Oracle 咨询|
|< 13 | 调查终止——证据不足 |

## 评分模板
Phase 3 完成后填写：

```Confidenc
e
: [X]/25- Evidence strength: [N]/5 (source: [tool])- Reproducibility: [N]/5 (repro script: yes/no)- Cross-system: [N]/5 (modules affected: [list])- Traceability: [N]/5 (source: [commit/PR/doc])- Actionability: [N]/5 (defense: [mechanism])Boundary zone (18-20): Source 1: [tool] | Source 2: [tool]
Confidence: [X]/25- Evidence strength: [N]/5 (source: [tool])- Reproducibility: [N]/5 (repro script: yes/no)- Cross-system: [N]/5 (modules affected: [list])- Traceability: [N]/5 (source: [commit/PR/doc])- Actionability: [N]/5 (defense: [mechanism])Boundary zone (18-20): Source 1: [tool] | Source 2: [tool]
```

## 截断输出惩罚
若任意维度的证据使用了截断的工具输出（包含 `...`、`truncated`、`> N lines`、`output omitted`）：- 该维度自动扣 **-2 分**- 必须以更大的输出限制重新执行工具，再使用该证据
